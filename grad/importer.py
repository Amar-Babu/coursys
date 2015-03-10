from coredata.queries import add_person, SIMSConn, SIMS_problem_handler, cache_by_args
from coredata.models import Semester
from grad.models import STATUS_DONE, STATUS_APPLICANT
import datetime
from collections import defaultdict
from pprint import pprint
import intervaltree

# TODO: should make better decision if we find multiple adm_appl_nbr records in find_gradstudent
# TODO: handle students that switch programs between units




# in ps_acad_prog dates within about this long of the semester start are actually things that happen next semester
DATE_OFFSET = datetime.timedelta(days=28)
ONE_DAY = datetime.timedelta(days=1)
GRAD_OFFSET = -datetime.timedelta(days=90)

def build_semester_lookup():
    """
    Build data structure to let us easily look up date -> strm.
    """
    all_semesters = Semester.objects.all()
    intervals = ((s.name, Semester.start_end_dates(s)) for s in all_semesters)
    intervals = (
        intervaltree.Interval(st, en+ONE_DAY, name)
        for (name, (st, en)) in intervals)
    return intervaltree.IntervalTree(intervals)

semester_lookup = build_semester_lookup()

IMPORT_START_DATE = datetime.date(1990, 1, 1)
IMPORT_START_SEMESTER = semester_lookup[IMPORT_START_DATE].pop().data

# if we find programs starting before this semester, don't import
RELEVANT_PROGRAM_START = Semester.objects.get(name='1031')



@SIMS_problem_handler
@cache_by_args
def grad_program_changes(acad_prog):
    db = SIMSConn()
    db.execute("""
        SELECT emplid, stdnt_car_nbr, adm_appl_nbr, acad_prog, prog_status, prog_action, prog_reason,
            effdt, effseq, admit_term
        FROM ps_acad_prog
        WHERE acad_career='GRAD' AND acad_prog=%s AND effdt>=%s AND admit_term>=%s
        ORDER BY effdt, effseq
    """, (acad_prog, IMPORT_START_DATE, IMPORT_START_SEMESTER))
    return list(db)

@SIMS_problem_handler
@cache_by_args
def grad_semesters(emplid):
    db = SIMSConn()
    db.execute("""
        SELECT emplid, strm, stdnt_car_nbr, withdraw_code, acad_prog_primary, unt_taken_prgrss
        FROM ps_stdnt_car_term
        WHERE acad_career='GRAD' AND emplid=%s AND strm>=%s
            AND unt_taken_prgrss>0
        ORDER BY strm
    """, (emplid, IMPORT_START_SEMESTER))
    return list(db)




def build_program_map():
    """
    Return a dict mapping SIMS's ACAD_PROG to GradProgram
    i.e.:
        { 'CPPHD': GradProgram.objects.get(label='PhD'... ) }
    """
    cmptunit = Unit.objects.get(label="CMPT")
    program_map = {
        'CPPHD': GradProgram.objects.get(label="PhD", unit=cmptunit),
        'CPPZU': GradProgram.objects.get(label="PhD", unit=cmptunit),
        'CPMSC': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
        'CPMZU': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
        'CPMBD': GradProgram.objects.get(label="MSc Big Data", unit=cmptunit),
        'CPGQL': GradProgram.objects.get(label="Qualifying", unit=cmptunit),
        'CPMCW': GradProgram.objects.get(label="MSc Course", unit=cmptunit),
        'CPGND': GradProgram.objects.get(label="Special", unit=cmptunit),
    }
    if True or settings.DEPLOY_MODE == 'production':
        engunit = Unit.objects.get(label="ENSC")
        mechunit = Unit.objects.get(label="MSE")
        program_map['MSEPH'] = GradProgram.objects.get(label="Ph.D.", unit=mechunit)
        program_map['MSEMS'] = GradProgram.objects.get(label="M.A.Sc.", unit=mechunit)
        program_map['ESMEN'] = GradProgram.objects.get(label="M.Eng.", unit=engunit)
        program_map['ESMAS'] = GradProgram.objects.get(label="M.A.Sc.", unit=engunit)
        program_map['ESPHD'] = GradProgram.objects.get(label="Ph.D.", unit=engunit)

    return program_map

def build_reverse_program_map():
    program_map = build_program_map()
    rev_program_map = defaultdict(list)
    for acad_prog, gradprog in program_map.items():
        rev_program_map[gradprog].append(acad_prog)

    cmptunit = Unit.objects.get(label="CMPT")
    rev_program_map[GradProgram.objects.get(label="MSc Course", unit=cmptunit)].append('CPMSC')
    rev_program_map[GradProgram.objects.get(label="MSc Proj", unit=cmptunit)].append('CPMSC')
    return rev_program_map

class GradHappening(object):
    """
    Superclass to represent things that happen to grad students.
    """
    program_map = None
    def effdt_to_strm(self):
        "Look up the semester that goes with this date"
        # within a few days of the end of the semester, things applicable next semester are being entered
        offset = DATE_OFFSET
        if hasattr(self, 'status') and self.status == 'GRAD':
            # ... except graduation which is entered after it effectively happens.
            offset = GRAD_OFFSET

        try:
            strm = semester_lookup[self.effdt + offset].pop().data
        except KeyError:
            raise KeyError, "Couldn't find semester for %s." % (self.effdt)

        self.strm = strm

    def acad_prog_to_gradprogram(self):
        if GradHappening.program_map is None:
            GradHappening.program_map = build_program_map()

        try:
            self.grad_program = GradHappening.program_map[self.acad_prog]
        except KeyError:
            self.grad_program = None


class ProgramStatusChange(GradHappening):
    def __init__(self, emplid, stdnt_car_nbr, adm_appl_nbr, acad_prog, prog_status, prog_action,
            prog_reason, effdt, effseq, admit_term):
        # argument order must match grad_program_changes query
        self.emplid = emplid
        self.stdnt_car_nbr = None # these seem meaningless
        self.adm_appl_nbr = adm_appl_nbr
        self.acad_prog = acad_prog
        self.effdt = datetime.datetime.strptime(effdt, '%Y-%m-%d').date()
        self.admit_term = admit_term

        self.prog_status = prog_status
        self.prog_action = prog_action
        self.prog_reason = prog_reason

        self.status = self.prog_status_translate()
        self.acad_prog_to_gradprogram()
        self.effdt_to_strm()

        self.key = [emplid, 'GRAD', stdnt_car_nbr, effdt, effseq]

        self.in_career = False

    def __repr__(self):
        return "%s at %s (%s)" % (self.status, self.effdt, self.strm)

    def prog_status_translate(self):
        """
        Convert a SIMS admission applicant status (e.g. "AD", "ADMT")
        into a Coursys Status Code (e.g. "OFFO")

        See ps_adm_action_tbl and ps_prog_rsn_tbl in reporting DB for some explanations of the codes.
        """
        st_ac = (self.prog_status, self.prog_action)

        # application-related
        if st_ac == ('AP', 'APPL'):
            return 'INCO'
        if st_ac == ('AP', 'RAPP'):
            # application for readmission
            return 'INCO'
        elif st_ac == ('CN', 'WAPP'):
            return 'DECL'
        elif st_ac == ('CN', 'WADM'):
            return 'INCO'
        elif st_ac == ('AD', 'ADMT'):
            return 'OFFO'
        elif st_ac == ('AD', 'COND'):
            # conditional offer
            return 'OFFO'
        elif st_ac == ('AC', 'MATR'):
            return 'CONF'
        elif st_ac == ('CN', 'DENY'):
            return 'REJE'
        elif st_ac == ('CN', 'ADRV'):
            return 'CANC'
        elif self.prog_action == 'RECN':
            # "reconsideration"
            return None
        elif self.prog_action == 'DEFR':
            # deferred start: probably implies start semester change
            return None

        elif self.prog_action == 'DATA':
            if self.prog_reason == 'APPR':
                # approved by department: close enough to ('AD', 'COND')
                return 'OFFO'
            # updated data, like a program or start semester change
            return None
        elif self.prog_action in ['PRGC', 'PLNC']:
            # changed to different program/plan
            return None

        elif st_ac == ('AC', 'ACTV'):
            return 'ACTI'
        elif st_ac == ('DC', 'DISC'):
            return 'WIDR'
        elif st_ac == ('LA', 'LEAV'):
            return 'LEAV'
        elif st_ac == ('AC', 'RLOA'):
            return 'ACTI'
        elif st_ac == ('AC', 'RADM'):
            return 'ACTI'
        elif st_ac == ('CM', 'COMP'):
            return 'GRAD'

        raise KeyError, str((self.prog_status, self.prog_action, self.prog_reason))

    def update_application_timing(self, admit_term):
        """
        We like application-related things to be effective in their start semester, not the current
        """
        if self.status in STATUS_APPLICANT:
            self.strm = admit_term

    def import_key(self):
        # must be JSON-serializable (and comparable for equality after serializing/deserializing)
        return self.key

    def find_existing_status(self, statuses):
        # look for something previously imported from this
        key = self.import_key()
        existing = [s for s in statuses
               if 'imported_from' in s.config and s.config['imported_from'] == key]

        # look for a match in old data
        exact = [s for s in statuses
               if s.start.name == self.strm and s.status == self.status]

    def update_local_data(self, student_info, verbosity=1, dry_run=False):
        if self.status:
            statuses = student_info['statuses']
            print ">>>", self.emplid, self.strm, self.effdt, self.status
            st = self.find_existing_status(statuses)
            print st


        #print "...", [(s.start.name, s.start_date, s.status) for s in statuses]
        #print "...", [s for s in statuses if s.start.name == self.strm]

        # TODO: it still might be a program change


class GradSemester(GradHappening):
    """
    Used to make sure we catch them being active: program status doesn't always record it.
    """
    def __init__(self, emplid, strm, stdnt_car_nbr, withdraw_code, acad_prog_primary, unt_taken_prgrss):
        # argument order must match grad_semesters query
        self.emplid = emplid
        self.strm = strm
        self.stdnt_car_nbr = stdnt_car_nbr
        self.withdraw_code = withdraw_code
        self.acad_prog = acad_prog_primary
        self.unt_taken_prgrss = unt_taken_prgrss

        self.acad_prog_to_gradprogram()

        self.adm_appl_nbr = None
        self.in_career = False

    def __repr__(self):
        return "%s in %s" % (self.withdraw_code, self.strm)

    def update_application_timing(self, admit_term):
        pass

    def update_local_data(self, student_info, verbosity=1, dry_run=False):
        # only job: make sure student is Active if relevant
        pass



class GradTimeline(object):
    def __init__(self, emplid):
        self.emplid = emplid
        self.happenings = []
        self.careers = []

    def __repr__(self):
        return 'GradTimeline(%s, %s)' % (self.emplid, repr(self.happenings))

    def add(self, happening):
        self.happenings.append(happening)

    def add_semester_happenings(self):
        for gs in grad_semesters(self.emplid):
            h = GradSemester(*gs)
            self.add(h)

    def split_careers(self, verbosity=1):
        # pass 1: we know the adm_appl_nbr
        for h in self.happenings:
            if not h.grad_program:
                continue

            if h.adm_appl_nbr:
                cs = [c for c in self.careers if c.adm_appl_nbr == h.adm_appl_nbr]
                if len(cs) == 1:
                    c = cs[0]
                else:
                    c = GradCareer(self.emplid, h.adm_appl_nbr)
                    self.careers.append(c)

                c.add(h)
                h.in_career = True

        # pass 2: look at admit_term
        for h in self.happenings:
            if h.in_career or not h.grad_program:
                continue

            possible_careers = [c for c in self.careers if c.admit_term <= h.strm]
            if not possible_careers:
                continue

            possible_careers.sort(key=lambda c: c.admit_term)
            c = possible_careers[-1]
            c.check_stdnt_car_nbr(h)
            c.add(h)
            h.in_career = True

        # pass 3: look at first_admit_term: some stdnt_car_terms happen but then they defer
        for h in self.happenings:
            if h.in_career or not h.grad_program:
                continue

            possible_careers = [c for c in self.careers if c.first_admit_term <= h.strm]
            if not possible_careers:
                if verbosity:
                    print "ignoring %s %s because it's old and/or has no adm_appl_nbr" % (self.emplid, h)
                continue

            possible_careers.sort(key=lambda c: c.admit_term)
            c = possible_careers[-1]
            c.add(h)
            h.in_career = True

        for c in self.careers:
            c.sort_happenings()


class GradCareer(object):
    program_map = None
    reverse_program_map = None

    def __init__(self, emplid, adm_appl_nbr):
        self.emplid = emplid
        self.adm_appl_nbr = adm_appl_nbr
        self.happenings = []
        self.admit_term = None
        self.first_admit_term = None
        self.stdnt_car_nbr = None
        self.last_program = None

        self.gradstudent = None

        if not GradCareer.program_map:
            GradCareer.program_map = build_program_map()
        if not GradCareer.reverse_program_map:
            GradCareer.reverse_program_map = build_reverse_program_map()

    def __repr__(self):
        return "%s@%s:%s" % (self.emplid, self.adm_appl_nbr, self.stdnt_car_nbr)

    def add(self, h):
        if h.adm_appl_nbr:
            if not self.adm_appl_nbr:
                self.adm_appl_nbr = h.adm_appl_nbr
            if not self.stdnt_car_nbr:
                self.stdnt_car_nbr = h.stdnt_car_nbr

            if self.adm_appl_nbr != h.adm_appl_nbr or (h.stdnt_car_nbr and self.stdnt_car_nbr != h.stdnt_car_nbr):
                raise ValueError

        if hasattr(h, 'admit_term'):
            # record earliest-ever-proposed admit term we find
            if self.first_admit_term is None or self.first_admit_term > h.admit_term:
                self.first_admit_term = h.admit_term

        if hasattr(h, 'admit_term'):
            # record most-recent admit term we find
            self.admit_term = h.admit_term

        self.last_program = h.acad_prog

        self.happenings.append(h)

    def sort_happenings(self):
        self.happenings.sort(key=lambda h: h.strm)

    def check_stdnt_car_nbr(self, h):
        if not self.stdnt_car_nbr and h.stdnt_car_nbr:
            self.stdnt_car_nbr = h.stdnt_car_nbr
        #elif self.stdnt_car_nbr and h.stdnt_car_nbr and self.stdnt_car_nbr != h.stdnt_car_nbr:
        #    raise ValueError

    # program selection methods:
    def by_adm_appl_nbr(self, gs):
        return gs.config.get('adm_appl_nbr', 'none') == self.adm_appl_nbr

    def by_program_and_start(self, gs):
        return (GradCareer.program_map[self.last_program] == gs.program
                and gs.start_semester
                and gs.start_semester.name == self.admit_term)

    def by_similar_program_and_start(self, gs):
        return (self.last_program in GradCareer.reverse_program_map[gs.program]
                and gs.start_semester
                and gs.start_semester.offset_name(-2) <= self.admit_term <= gs.start_semester.offset_name(2)
        )

    GS_SELECTORS = [ # (method_name, is_okay_to_find_multiple_matches)
        ('by_adm_appl_nbr', True),
        ('by_program_and_start', True),
        ('by_similar_program_and_start', True),
    ]

    def find_gradstudent(self, verbosity=1):
        gss = GradStudent.objects.filter(person__emplid=self.emplid).select_related('start_semester')
        gss = list(gss)

        if self.admit_term < RELEVANT_PROGRAM_START.name:
            return

        for method, multiple_okay in GradCareer.GS_SELECTORS:
            by_selector = [gs for gs in gss if getattr(self, method)(gs)]
            if len(by_selector) == 1:
                return by_selector[0]
            elif len(by_selector) > 1:
                if multiple_okay:
                    return by_selector[-1]
                else:
                    raise ValueError, "Multiple records found by %s for %s." % (method, self)

        if verbosity:
            print
            print "can't find %s" % (self)
            print self.adm_appl_nbr, [gs.config.get('adm_appl_nbr', 'none') for gs in gss]
            print self.admit_term, [(gs.start_semester.name if gs.start_semester else None) for gs in gss]
            print self.last_program, [GradCareer.reverse_program_map[gs.program] for gs in gss]

    def fill_gradstudent(self, verbosity=1):
        gs = self.find_gradstudent(verbosity=verbosity)
        self.gradstudent = gs

    def update_local_data(self, verbosity=1, dry_run=False):
        if not self.gradstudent:
            return

        print self.emplid, self.admit_term, self.gradstudent
        student_info = {
            'student': self.gradstudent,
            'statuses': list(GradStatus.objects.filter(student=self.gradstudent)
                .select_related('start').order_by('start__name', 'start_date')),
            'programs': list(GradProgramHistory.objects.filter(student=self.gradstudent)
                .select_related('start_semester').order_by('start_semester__name', 'starting')),
        }

        for h in self.happenings:
            h.update_application_timing(self.admit_term)
            h.update_local_data(student_info, verbosity=verbosity, dry_run=dry_run)



        # TODO: GradProgramHistory

        if not dry_run:
            self.update_status_fields()








def NEW_import_unit_grads(unit, dry_run=False, verbosity=1):
    prog_map = build_program_map()
    acad_progs = [acad_prog for acad_prog, program in prog_map.iteritems() if program.unit == unit]

    timelines = {}
    for acad_prog in acad_progs:
        appls = grad_program_changes(acad_prog)
        for a in appls:
            emplid = a[0]
            timeline = timelines.get(emplid, None)
            if not timeline:
                timeline = GradTimeline(emplid)
                timelines[emplid] = timeline
            status = ProgramStatusChange(*a)
            timeline.add(status)


    emplids = timelines.keys()
    #emplids = ['301013710', '961102054', '953018734', '200079269', '301042450', '301148552',
    #           '301241424']
    emplids = ['301199421', '301002760', '301192850', '301085871']
    for emplid in emplids:
        if emplid not in timelines:
            continue

        timeline = timelines[emplid]
        timeline.add_semester_happenings()
        timeline.split_careers(verbosity=0)
        for c in timeline.careers:
            c.fill_gradstudent(verbosity=0)
            c.update_local_data(dry_run=True, verbosity=verbosity)


    #    csplit = split_by_car_nbr(timeline)
    #    print csplit

    #pprint(timelines)

    #add_semester_happenings('301013710', timelines['301013710'])
    #csplit = split_by_car_nbr(timelines['301013710']))
    #pprint (split_by_appl_nbr(timelines['301013710']))

    return







































from django.db import IntegrityError
from django.conf import settings
import coredata
from coredata.models import Semester, Unit
from grad.models import GradStudent, GradStatus, GradProgramHistory, GradProgram, Supervisor
from collections import defaultdict

IGNORE_CMPT_STUDENTS = True
def create_or_update_student( emplid, dryrun=False, verbose=False ):
    """
        Given an emplid, create (or update) a GradStudent record.
        If dryrun is true, do not call any .save() calls.
    """
    if verbose:
        print "Create/Update Student: ", emplid

    # First we generate a person to tie all of the generated records to.
    person = coredata.queries.find_or_generate_person( emplid )
    if verbose:
        print "\t", person

    prog_map = program_map()

    # This bit is really important: a combined query which makes a bunch of
    #  guesses as to what the student's actually been doing all this time.
    timeline = coredata.queries.get_timeline(emplid)
    if verbose:
        import json
        print "--- Timeline ---"
        print json.dumps( timeline, indent=2 )

    # Strip any programs from the timeline that aren't our grad programs
    timeline = [x for x in timeline if x['program_code'] in prog_map.keys()]
    # Split the programs into groups based on completion status
    #  groups are important, especially because we're bad about detecting
    #  program changes. If a student is in ESMSC one semester and ESPHD the
    #  next, without a withdrawal or completion between the two, we're going
    #  assume it is part of the same grad career.
    groups = split_timeline_into_groups(timeline)

    # keep track of which adm_appl_nbrs we've encountered
    #  if you're reading along from home, 'adm_appl_nbr' is a unique identifier
    #  for a single admission application. There should probably be about
    adm_appl_nbrs = []

    # For each group, and then each program in each group, try
    #  to reconcile this group with a GradStudent record that exists.
    for group_no, group in groups.iteritems():
        if verbose:
            print "\tGroup: ", group_no

        # ignore empty groups
        if len(group) < 1:
            continue

        first_program = group[0]
        last_program = group[-1]
        all_previous_programs = group[:-1]

        # if this program has an adm_appl_nbr, write down that we've seen it
        for program in group:
            if 'adm_appl_nbr' in program and program['adm_appl_nbr']:
                adm_appl_nbrs.append(str(program['adm_appl_nbr']))

        # this is a special case for CMPT.
        if IGNORE_CMPT_STUDENTS and first_program['program_code'].startswith("CP"):
            if verbose:
                print "\tIgnoring CMPT data"
            continue

        last_program_object = prog_map[last_program['program_code']]

        # does this person/program already exist?
        gradstudents = GradStudent.objects.filter(person=person, program=last_program_object)

        if len(gradstudents) < 1:
            if verbose:
                print "\tGrad student not found, creating"
            student = GradStudent.create( person, last_program_object )

            if not dryrun:
                if verbose:
                    print "saving GradStudent"
                student.save()
            else:
                if verbose:
                    print "dry run: not saving GradStudent."
        elif len(gradstudents) > 1:
            if verbose:
                print "\tRECOVERABLE ERROR: Somehow we found more than one GradStudent record for", last_program_object

            # try to use the adm_appl_nbr to reconcile things.
            if 'adm_appl_nbr' in first_program:
                with_adm_appl = [x for x in gradstudents if
                                    'adm_appl_nbr' in x.config
                                    and x.config['adm_appl_nbr'] == first_program['adm_appl_nbr'] ]
                if len(with_adm_appl) > 0:
                    student = with_adm_appl[0]
                    if verbose:
                        print "\t picking the one with adm_appl_nbr match: ", first_program['adm_appl_nbr']
                else:
                    student = gradstudents[0]
                    if verbose:
                        print "\t no matching adm_appl_nbr found, going with the first grad student record ", student
            else:
                student = gradstudents[0]
                if verbose:
                    print "\t no matching adm_appl_nbr found, going with ", student
        else:
            if verbose:
                print "\tGrad student found"
            student = gradstudents[0]

        # If we have an adm_appl_nbr, use it to build an admission history
        statuses_to_save = []
        if 'adm_appl_nbr' in first_program:
            student.config['adm_appl_nbr'] = first_program['adm_appl_nbr']
            if not dryrun:
                student.save()
        for program in group:
            if 'admission_records' in program:
                admission_records = program['admission_records']
                if verbose:
                    print "Admission Records:"
                    print admission_records
                admission_statuses = admission_records_to_grad_statuses( admission_records, student )
                for status in admission_statuses:
                    statuses_to_save.append(status)

        # create a GradProgramHistory for every previous program
        for program in all_previous_programs:
            program_object = prog_map[program['program_code']]
            start_semester = Semester.objects.get(name=program['start'])
            try:
                gph = GradProgramHistory.objects.get(
                    student = student,
                    program = program_object,
                    start_semester = start_semester )
                if verbose:
                    print "\tFound Program History:", gph
            except GradProgramHistory.DoesNotExist:
                gph = GradProgramHistory(
                    student = student,
                    program = program_object,
                    start_semester = start_semester )
                if verbose:
                    print "\tCreating Program History:", gph
                if not dryrun:
                    if verbose:
                        print "saving GradProgramHistory."
                    gph.save()
                else:
                    if verbose:
                        print "dry run: not saving GradProgramHistory."

        # find/create a GradStatus "Active" at the first semester
        active_status = find_or_create_status( student, 'ACTI', Semester.objects.get(name=first_program['start']))
        statuses_to_save.append(active_status)

        on_leaves = coredata.queries.merge_leaves(group)

        # for every on-leave, create an LEAV status for the student
        # when that leave ends, create an ACTI status for the student
        for leave_start_semester, leave_end_semester in on_leaves:
            start_semester_object = Semester.objects.get(name=leave_start_semester)
            end_semester_object = Semester.objects.get(name=leave_end_semester)
            on_leave_status = find_or_create_status( student, 'LEAV', start_semester_object )
            statuses_to_save.append(on_leave_status)
            next_semester_object = end_semester_object.offset(1)
            if int(next_semester_object.name) < int(last_program['end']):
                active_again_status = find_or_create_status( student, 'ACTI', next_semester_object )
                statuses_to_save.append(active_again_status)

        # how did this end?
        if 'how_did_it_end' in last_program and last_program['how_did_it_end']:
            end_code = last_program['how_did_it_end']['code']
            end_semester = last_program['how_did_it_end']['semester']
            end_semester_object = Semester.objects.get(name=end_semester)

            if end_code == "COMP":
                # Graduated!
                created_status = find_or_create_status( student, 'GRAD', end_semester_object )
            if end_code == "DISC":
                # Withdrawn!
                created_status = find_or_create_status( student, 'WIDR', end_semester_object )
            statuses_to_save.append(created_status)

        if not dryrun:
            if verbose:
                print "saving GradStatus objects"
            GradStatus.overrun(student, statuses_to_save)
        else:
            if verbose:
                print "dry run, not saving GradStatus"

        # We need the very startest of start dates and the very endest of end dates
        #  for this student to run the Supervisor query
        first_day_of_first_semester = Semester.objects.get( name=first_program['start'] ).start
        last_day_of_last_semester = Semester.objects.get( name=last_program['end'] ).end

        supervisory_committee = coredata.queries.get_supervisory_committee(
            emplid, first_day_of_first_semester, last_day_of_last_semester )

        supervisors_to_add = []
        for supervisor_sims, supervisor_emplid, supervisor_date in supervisory_committee:
            try:
                supervisor = coredata.queries.find_or_generate_person( supervisor_emplid )
            except IntegrityError as e:
                if verbose:
                    print e
                continue
            supervisor_type = supervisor_sims_to_supervisor_type( supervisor_sims )
            if not supervisor_type:
                continue
            s = find_or_create_supervisor( student, supervisor_type, supervisor, supervisor_date )
            supervisors_to_add.append(s)

        if not dryrun:
            for supervisor in supervisors_to_add:
                supervisor.save()

    # Create records for any spare adm_appl_nbrs
    all_adm_appl_nbrs = coredata.queries.get_adm_appl_nbrs(emplid)
    remaining_adm_appl_nbrs = [a for a in all_adm_appl_nbrs if str(a[0]) not in adm_appl_nbrs]
    if verbose:
        print "\t All Adm Appl Nbrs: ", all_adm_appl_nbrs
        print "\t Adm Appl Nbrs: ", adm_appl_nbrs
        print "\t Remaining Adm Appl Nbrs: ", remaining_adm_appl_nbrs

    for adm_appl_nbr, program_code in remaining_adm_appl_nbrs:
        if verbose:
            print "\tAdm Appl Nbr: ", adm_appl_nbr

        if IGNORE_CMPT_STUDENTS and program_code.startswith("CP"):
            if verbose:
                print "\tIgnoring CMPT data"
            continue

        if program_code not in prog_map.keys():
            if verbose:
                print "\t", program_code, " is not a grad program."
            continue

        program = prog_map[program_code]

        gradstudents = GradStudent.objects.filter(person=person, program=program)

        with_adm_appl = [s for s in gradstudents if 'adm_appl_nbr' in s.config and
                                                    s.config['adm_appl_nbr'] == adm_appl_nbr ]

        admission_records = coredata.queries.get_admission_records( emplid, adm_appl_nbr )
        if verbose:
            print "\tAdmission Records:"
            print "\t", admission_records

        if len(with_adm_appl) == 0:
            if verbose:
                print "\tNot found."
            student = GradStudent.create( person, program )
            student.config['adm_appl_nbr'] = adm_appl_nbr
            if not dryrun:
                student.save()
        else:
            student = with_adm_appl[0]
            if verbose:
                print "\t Found."

        admission_statuses = admission_records_to_grad_statuses( admission_records, student )

        if not dryrun:
            GradStatus.overrun(student, admission_statuses)

def split_timeline_into_groups( timeline ):
    """
        If we have a timeline containing
        CPMSC - 1094-1097
        CPMZU - 1097-1127 - graduated,
        CPPHD - 1134-1147,
        then we want to separate this student into two groups
        {
            '0': [ {CPMSC...}, {CPMZU...} ],
            '1': [ {CPPHD...} ]
        }
    """
    prog_groups = defaultdict(list)
    last_group = 0
    for program in timeline:
        prog_groups[last_group].append( program )
        if 'how_did_it_end' in program and program['how_did_it_end']:
            last_group = last_group + 1

    return prog_groups

def program_map():
    """
    Return a dict mapping SIMS's ACAD_PROG to GradProgram
    i.e.:
        { 'CPPHD': GradProgram.objects.get(label='PhD'... ) }
    """
    if settings.DEPLOY_MODE != 'production':
        cmptunit = Unit.objects.get(label="CMPT")
        engunit = Unit.objects.get(label="ENSC")
        program_map = {
            'CPPHD': GradProgram.objects.get(label="PhD", unit=cmptunit),
            'CPPZU': GradProgram.objects.get(label="PhD", unit=cmptunit),
            'CPMSC': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
            'CPMCW': GradProgram.objects.get(label="MSc Project", unit=cmptunit),
            'CPMZU': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
            'CPGND': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
            'CPGQL': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
            'CPMBD': GradProgram.objects.get(label="MSc Big Data", unit=cmptunit),

            'ESMEN': GradProgram.objects.get(label="MEng", unit=engunit),
            'ESMAS': GradProgram.objects.get(label="MEng", unit=engunit),
            'ESPHD': GradProgram.objects.get(label="PhD", unit=engunit),
            'MSEPH': GradProgram.objects.get(label="PhD", unit=engunit),
            'MSEMS': GradProgram.objects.get(label="MEng", unit=engunit)
        }
    else:
        cmptunit = Unit.objects.get(label="CMPT")
        mechunit = Unit.objects.get(label="MSE")
        engunit = Unit.objects.get(label="ENSC")
        program_map = {
            'CPPHD': GradProgram.objects.get(label="PhD", unit=cmptunit),
            'CPPZU': GradProgram.objects.get(label="PhD", unit=cmptunit),
            'CPMSC': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
            'CPMCW': GradProgram.objects.get(label="MSc Course", unit=cmptunit),
            'CPMZU': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
            'CPGND': GradProgram.objects.get(label="Special", unit=cmptunit),
            'CPGQL': GradProgram.objects.get(label="Qualifying", unit=cmptunit),
            'CPMBD': GradProgram.objects.get(label="MSc Big Data", unit=cmptunit),

            'ESMEN': GradProgram.objects.get(label="M.Eng.", unit=engunit),
            'ESMAS': GradProgram.objects.get(label="M.A.Sc.", unit=engunit),
            'ESPHD': GradProgram.objects.get(label="Ph.D.", unit=engunit),

            'MSEPH': GradProgram.objects.get(label="Ph.D.", unit=mechunit),
            'MSEMS': GradProgram.objects.get(label="M.A.Sc.", unit=mechunit),
        }
    return program_map

def get_admission_status_code( admission_action, admitted=False ):
    """
        Convert a SIMS admission applicant "action" code
        (e.g. "ADMT")
        into a Coursys Status Code
        (e.g. "OFFO")
    """
    if admission_action in ["ADMT", "COND"]:
        return "OFFO"
    if admission_action == "APPL":
        return "COMP"
    if admission_action == "MATR":
        return "CONF"
    if admission_action == "DENY":
        return "REJE"
    if admission_action in ["WAPP", "WADM"]:
        if admitted:
            return "DECL"
        else:
            return "EXPI"
    return None

def admission_records_to_grad_statuses( admission_records, student ):
    """
        Convert a list of admission records:
        [
            ('ADMIT', datetime.date('2012-10-10'), '1124'),
            ('MATR', datetime.date('2012-11-11'), '1124')
        ]
        into a list of GradStatus objects:
        [
            <GradStatus 'OFFO' 1124>,
            <GradStatus 'CONF' 1124>
        ]
    """
    return_list = []
    admitted = False
    for action, date, semester in admission_records:
        status_code = get_admission_status_code( action, admitted )
        if status_code == "OFFO":
            admitted = True
        if status_code == None:
            continue
        semester_object = Semester.objects.get(name=semester)
        gs = find_or_create_status( student, status_code, semester_object )
        return_list.append(gs)
    return return_list

def find_or_create_status( student, status, semester):
    active_statuses = GradStatus.objects.filter(
        student = student,
        status = status,
        start = semester)
    if len(active_statuses) > 0:
        active_status = active_statuses[0]
        active_status.hidden = False
    else:
        active_status = GradStatus(
            student = student,
            status = status,
            start = semester)
    return active_status

def supervisor_sims_to_supervisor_type( supervisor_sims ):
    """
        supervisor_sims is 'Senior Supervisor', 'Supervisor', 'Internal Examiner', etc.

        convert these into one of our supervisor codes - e.g. "SEN" for Senior Supervisor
    """
    supervisor_sims = str(supervisor_sims)
    if supervisor_sims in [ "Chair",
                            "Committee Chair",
                            "Chair of Nominating Committee",
                            "Co-Chair" ]:
        return 'CHA'
    if supervisor_sims == "Internal Examiner":
        return 'SFU'
    if supervisor_sims == "External Examiner":
        return 'EXT'
    if supervisor_sims in [ "Committee Member",
                            "Generic Committee Member",
                            "Member",
                            "Member of Committee" ]:
        return 'COM'
    if supervisor_sims == "Senior Supervisor":
        return 'SEN'
    if supervisor_sims == "Supervisor":
        return 'COS'
    if supervisor_sims == "Admission Staff Support":
        return None

def find_or_create_supervisor( student, supervisor_type, supervisor, date ):
    s = Supervisor.objects.filter(student=student,
                                    supervisor=supervisor,
                                    supervisor_type=supervisor_type )
    if len(s) > 0:
        return s[0]
    else:
        s = Supervisor(student=student,
                        supervisor=supervisor,
                        supervisor_type=supervisor_type,
                        updated_at=date)
        return s