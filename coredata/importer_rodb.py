import sys, os, datetime, string, time, copy
import DB2, MySQLdb, random
sys.path.append(".")
sys.path.append("..")
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from coredata.models import *
from dashboard.models import NewsItem
from log.models import LogEntry
from django.db import transaction
from django.db.utils import IntegrityError
from django.contrib.sessions.models import Session
from django.conf import settings
from courselib.svn import update_offering_repositories
today = datetime.date.today()
past_cutoff = today - datetime.timedelta(days=30)
future_cutoff = today + datetime.timedelta(days=60)

# these users will be given sysadmin role (for bootstrapping)
sysadmin = ["ggbaker", "sumo"]

# first term we care even vaguely about in import (further selection happens later too)
FIRSTTERM = "1121"
#DATA_WHERE = '((subject="CMPT" or subject="MACM") and strm="1114") or strm>="'+FIRSTTERM+'"'
DATA_WHERE = "strm>='"+FIRSTTERM+"'"

# artificial combined sections to create: kwargs for CourseOffering creation,
# plus 'subsections' list of sections we're combining.

def get_combined():
    combined_sections = [
        {
            'subject': 'CMPT', 'number': '125', 'section': 'X100',
            'semester': Semester.objects.get(name="1114"),
            'component': 'LEC', 'graded': True, 
            'crse_id': 32760, 'class_nbr': 32760,
            'title': 'Intro CS/Progr(combined)',
            'campus': 'BRNBY',
            'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
            'config': {},
            'subsections': [
                CourseOffering.objects.get(slug='1114-cmpt-125-d100'),
                CourseOffering.objects.get(slug='1114-cmpt-126-d100')
            ]
        },
        {
            'subject': 'ENSC', 'number': '100', 'section': 'X100',
            'semester': Semester.objects.get(name="1117"),
            'component': 'LEC', 'graded': True, 
            'crse_id': 32761, 'class_nbr': 32761,
            'title': 'Eng.Technology and Society (combined)',
            'campus': 'BRNBY',
            'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
            'config': {},
            'subsections': [
                CourseOffering.objects.get(slug='2011fa-ensc-100-d1'),
                CourseOffering.objects.get(slug='2011fa-ensc-100w-d1')
            ]
        },
        {
            'subject': 'CMPT', 'number': '120', 'section': 'X100',
            'semester': Semester.objects.get(name="1117"),
            'component': 'LEC', 'graded': True, 
            'crse_id': 32762, 'class_nbr': 32762,
            'title': 'Intro.Cmpt.Sci/Programming I',
            'campus': 'BRNBY',
            'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
            'config': {},
            'subsections': [
                CourseOffering.objects.get(slug='2011fa-cmpt-120-d1'),
                CourseOffering.objects.get(slug='2011fa-cmpt-120-d2')
            ]
        },
        {
            'subject': 'CMPT', 'number': '461', 'section': 'X100',
            'semester': Semester.objects.get(name="1117"),
            'component': 'LEC', 'graded': True, 
            'crse_id': 32759, 'class_nbr': 32759,
            'title': 'Image Synthesis (ugrad/grad combined)',
            'campus': 'BRNBY',
            'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
            'config': {},
            'subsections': [
                CourseOffering.objects.get(slug='2011fa-cmpt-461-d1'),
                CourseOffering.objects.get(slug='2011fa-cmpt-761-g1')
            ]
        },
        {
            'subject': 'CMPT', 'number': '441', 'section': 'X100',
            'semester': Semester.objects.get(name="1117"),
            'component': 'LEC', 'graded': True, 
            'crse_id': 32758, 'class_nbr': 32758,
            'title': 'Bioinformatics Alg (ugrad/grad combined)',
            'campus': 'BRNBY',
            'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
            'config': {},
            'subsections': [
                CourseOffering.objects.get(slug='2011fa-cmpt-441-e1'),
                CourseOffering.objects.get(slug='2011fa-cmpt-711-g1')
            ]
        },
        {
            'subject': 'CMPT', 'number': '165', 'section': 'C000',
            'semester': Semester.objects.get(name="1121"),
            'component': 'LEC', 'graded': True, 
            'crse_id': 32757, 'class_nbr': 32757,
            'title': 'Intro Internet/WWW (combined)',
            'campus': 'BRNBY',
            'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
            'config': {},
            'subsections': [
                CourseOffering.objects.get(slug='2012sp-cmpt-165-c1'),
                CourseOffering.objects.get(slug='2012sp-cmpt-165-c2'),
                CourseOffering.objects.get(slug='2012sp-cmpt-165-c3')
            ]
        },
        {
            'subject': 'MACM', 'number': '101', 'section': 'X100',
            'semester': Semester.objects.get(name="1121"),
            'component': 'LEC', 'graded': True, 
            'crse_id': 32756, 'class_nbr': 32756,
            'title': 'Discrete Math I (combined)',
            'campus': 'BRNBY',
            'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
            'config': {},
            'subsections': [
                CourseOffering.objects.get(slug='2012sp-macm-101-d1'),
                CourseOffering.objects.get(slug='2012sp-macm-101-d2')
            ]
        },
        {
            'subject': 'CMPT', 'number': '471', 'section': 'X100',
            'semester': Semester.objects.get(name="1121"),
            'component': 'LEC', 'graded': True, 
            'crse_id': 32755, 'class_nbr': 32755,
            'title': 'Networking (ugrad/grad combined)',
            'campus': 'SURYY',
            'enrl_cap': 0, 'enrl_tot': 0, 'wait_tot': 0,
            'config': {},
            'subsections': [
                CourseOffering.objects.get(slug='2012sp-cmpt-471-d1'),
                CourseOffering.objects.get(slug='2012sp-cmpt-771-g1')
            ]
        },
        ]
    return combined_sections

amaint_host = '127.0.0.1'      
amaint_user = 'ggbaker'
amaint_name = 'sims'
amaint_port = 4000

ta_host = '127.0.0.1'      
ta_user = 'ta_data_import'
ta_name = 'ta_data_drop'
ta_port = 4000

sims_user = "ggbaker"
sims_db = "csrpt"





def escape_arg(a):
    """
    Escape argument for DB2
    """
    # Based on description of PHP's db2_escape_string
    if type(a) in (int,long):
        return str(a)
    
    a = unicode(a).encode('utf8')
    # assume it's a string if we don't know any better
    a = a.replace("\\", "\\\\")
    a = a.replace("'", "\\'")
    a = a.replace('"', '\\"')
    a = a.replace("\r", "\\r")
    a = a.replace("\n", "\\n")
    a = a.replace("\x00", "\\\x00")
    a = a.replace("\x1a", "\\\x1a")
    return "'"+a+"'"

def execute_query(db, query, args):
    """
    Execute DB2 query, escaping args as necessary
    """
    clean_args = tuple((escape_arg(a) for a in args))
    real_query = query % clean_args
    #print ">>>", real_query
    return db.execute(real_query)
    
def prep_value(v):
    """
    get a reporting DB value into a useful format
    """
    if isinstance(v, basestring):
        return v.strip().decode('utf8')
    else:
        return v

def iter_rows(c):
    """
    Iterate the rows returned by reporting database (since DB2 driver doesn't do that nicely).
    """
    row = c.fetchone()
    while row:
        yield tuple((prep_value(v) for v in row))
        row = c.fetchone()

def rows(c):
    """
    List of rows returned by reporting database.
    """
    return list(iter_rows(c))



#def decode(s):
#    """
#    Turn database string into proper Unicode.
#    """
#    return s.decode('utf8')

@transaction.commit_on_success
def create_semesters():
    # http://students.sfu.ca/calendar/for_students/dates.html
    s = Semester.objects.filter(name="1114")
    if not s:
        s = Semester(name="1114", start=datetime.date(2011, 5, 9), end=datetime.date(2011, 8, 8))
        s.save()
        wk = SemesterWeek(semester=s, week=1, monday=datetime.date(2011, 5, 9))
        wk.save()

    s = Semester.objects.filter(name="1117")
    if not s:
        s = Semester(name="1117", start=datetime.date(2011, 9, 6), end=datetime.date(2011, 12, 5))
        s.save()
        wk = SemesterWeek(semester=s, week=1, monday=datetime.date(2011, 9, 5))
        wk.save()

    s = Semester.objects.filter(name="1121")
    if not s:
        s = Semester(name="1121", start=datetime.date(2012, 1, 5), end=datetime.date(2012, 4, 11))
        s.save()
        wk = SemesterWeek(semester=s, week=1, monday=datetime.date(2012, 1, 9))
        wk.save()
        wk = SemesterWeek(semester=s, week=6, monday=datetime.date(2012, 2, 20))
        wk.save()

    s = Semester.objects.filter(name="1124")
    if not s:
        s = Semester(name="1124", start=datetime.date(2012, 5, 7), end=datetime.date(2012, 8, 3))
        s.save()
        wk = SemesterWeek(semester=s, week=1, monday=datetime.date(2012, 5, 7))
        wk.save()

    s = Semester.objects.filter(name="1127")
    if not s:
        s = Semester(name="1127", start=datetime.date(2012, 9, 4), end=datetime.date(2012, 12, 3))
        s.save()
        wk = SemesterWeek(semester=s, week=1, monday=datetime.date(2012, 9, 3))
        wk.save()


@transaction.commit_on_success
def fix_emplid(db):
    """
    Any manually-entered people will have emplid 0000?????.  Update them with the real emplid from the database.
    """
    people = Person.objects.filter(emplid__lt=100000)
    for p in people:
        print " ", p.userid
        db.execute('SELECT emplid FROM amaint.idMap WHERE username=%s', p.userid)
        row = db.fetchone()
        if row:
            emplid, = row
            p.emplid = emplid
            p.save()


def import_semester(sems):
    """
    Should this QuerySet of semesters be imported?
    """
    if not sems:
        return False
    s = sems[0]
    return s.end >= past_cutoff and s.start <= future_cutoff




@transaction.commit_on_success
def import_offerings(db, DATA_WHERE):
    """
    Import course offerings.  Returns set of CourseOffering objects imported.
    """
    db.execute('SELECT subject, catalog_nbr, class_section, strm, crse_id, class_nbr, ssr_component, descr, campus, enrl_cap, enrl_tot, wait_tot, cancel_dt FROM dbsastg.ps_class_tbl WHERE ' + DATA_WHERE)
    imported_offerings = set()
    for subject, number, section, strm, crse_id, class_nbr, component, title, campus, enrl_cap, enrl_tot, wait_tot, cancel_dt in iter_rows(db):
        # only import for defined semesters.
        semesters = Semester.objects.filter(name=strm)
        if not import_semester(semesters):
            continue
        semester = semesters[0]
        
        graded = section.endswith("00")
        if not graded:
            continue

        # make sure the data is as we expect:
        if not CAMPUSES.has_key(campus):
            raise KeyError, "Unknown campus: %r." % (campus)
        if not COMPONENTS.has_key(component):
            raise KeyError, "Unknown course component: %r." % (component)

        if cancel_dt is not None:
            # mark cancelled sections
            component="CAN"

        c_old = CourseOffering.objects.filter(subject=subject, number=number, section=section, semester=semester)
        if len(c_old)>1:
            raise KeyError, "Already duplicate courses: %r" % (c_old)
        elif len(c_old)==1:
            # already in DB: update things that might have changed
            c_old = c_old[0]
            c_old.crse_id = crse_id
            c_old.class_nbr = class_nbr
            c_old.component = component
            c_old.graded = graded
            c_old.title = title
            c_old.campus = campus
            c_old.enrl_cap = enrl_cap
            c_old.enrl_tot = enrl_tot
            c_old.wait_tot = wait_tot
            c_old.slug = c_old.autoslug() # rebuild slug in case section changes for some reason
            c_old.save()
            imported_offerings.add(c_old)
        else:
	    c_old = CourseOffering.objects.filter(class_nbr=class_nbr, semester=semester)
	    if len(c_old)>1:
		raise KeyError, "Already duplicate courses: %r" % (c_old)
	    elif len(c_old) == 1:
		# already in DB: update things that might have changed
            	c_old = c_old[0]
            	c_old.crse_id = crse_id
            	c_old.class_nbr = class_nbr
		c_old.section = section
            	c_old.component = component
            	c_old.graded = graded
            	c_old.title = title
            	c_old.campus = campus
            	c_old.enrl_cap = enrl_cap
            	c_old.enrl_tot = enrl_tot
            	c_old.wait_tot = wait_tot
            	c_old.slug = c_old.autoslug() # rebuild slug in case section changes for some reason
            	c_old.save()
            	imported_offerings.add(c_old)
            else:
            	# new record: create.
            	c = CourseOffering(subject=subject, number=number, section=section, semester=semester, crse_id=crse_id, class_nbr=class_nbr, component=component, graded=graded, title=title, campus=campus, enrl_cap=enrl_cap, enrl_tot=enrl_tot, wait_tot=wait_tot)
            	c.save()
                imported_offerings.add(c)


    return imported_offerings

imported_people = {}
def get_person(db, amaintdb, emplid):
    """
    Get/update personal info for this emplid and return (updated & saved) Person object.
    """
    global imported_people
    # use imported_people as a cache
    if emplid in imported_people:
        return imported_people[emplid]
    
    execute_query(db, 'SELECT emplid, last_name, first_name, middle_name, pref_first_name FROM dbsastg.ps_personal_data WHERE emplid=%s', (str(emplid),))
    for emplid, last_name, first_name, middle_name, pref_first_name in iter_rows(db):
        amaintdb.execute('SELECT username FROM amaint.idMap WHERE emplid=%s', (emplid,))
        try:
            userid = amaintdb.fetchone()[0]
        except TypeError:
            userid = None

        if not pref_first_name:
            pref_first_name = first_name
        
        p_old = Person.objects.filter(emplid=emplid)
        if len(p_old)>1:
            raise KeyError, "Already duplicate people: %r" % (p_old)
        elif len(p_old)==1:
            # existing entry: make sure it's updated
            p = p_old[0]
            if p.userid and p.userid != userid and userid is not None:
                raise ValueError, "Did somebody's userid change? " + `p.userid` + " " +  `userid`
            p.userid = userid
            p.last_name = last_name
            p.first_name = first_name
            p.middle_name = middle_name
            p.pref_first_name = pref_first_name
            try:
                p.save()
            except IntegrityError:
                print "    Changed userid: " + userid
                # other account with userid must have been deactivated: update
                other = Person.objects.get(userid=userid)
                assert other.emplid != p.emplid
                get_person(db, amaintdb, other.emplid)
                # try again now
                p.save()
        else:
            # newly-found person: insert
            p = Person(emplid=emplid, userid=userid, last_name=last_name, first_name=first_name, middle_name=middle_name, pref_first_name=pref_first_name)
            p.save()
        
        imported_people[emplid] = p
        return p


def fix_mtg_info(section, stnd_mtg_pat):
    """
    Normalize SIMS meeting data to something we can deal with.
    """
    # section: None for lecture/exams; lab/tutorial section for them.
    if section.endswith("00"):
        sec = None
    else:
        sec = section

    # meeting type: exams, lab/tutorials, other=lecture
    if stnd_mtg_pat in ['EXAM', 'MIDT']:
        mtype = stnd_mtg_pat
    elif not section.endswith('00'):
        mtype = 'LAB'
    else:
        mtype = 'LEC'
    
    return sec, mtype

@transaction.commit_on_success
def import_meeting_times(db, offering):
    """
    Import course meeting times
    """
    execute_query(db, 'SELECT meeting_time_start, meeting_time_end, facility_id, mon,tues,wed,thurs,fri,sat,sun, start_dt, end_dt, stnd_mtg_pat, class_section FROM dbsastg.ps_class_mtg_pat WHERE crse_id=%s and class_section like %s and strm=%s', ("%06i" % (int(offering.crse_id)), offering.section[0:2]+"%", offering.semester.name))
    # keep track of meetings we've found, so we can remove old (non-importing semesters and changed/gone)
    found_mtg = set()
    
    for start,end, room, mon,tues,wed,thurs,fri,sat,sun, start_dt,end_dt, stnd_mtg_pat, class_section in rows(db):
        # dates come in as strings from DB2/reporting DB
        start_dt = datetime.datetime.strptime(start_dt, "%Y-%m-%d").date()
        end_dt = datetime.datetime.strptime(end_dt, "%Y-%m-%d").date()

        wkdays = [n for n, day in zip(range(7), (mon,tues,wed,thurs,fri,sat,sun)) if day=='Y']
        labtut_section, mtg_type = fix_mtg_info(class_section, stnd_mtg_pat)
        for wkd in wkdays:
            m_old = MeetingTime.objects.filter(offering=offering, weekday=wkd, start_time=start, end_time=end, labtut_section=labtut_section, room=room)
            if len(m_old)>1:
                raise KeyError, "Already duplicate meeting: %r" % (m_old)
            elif len(m_old)==1:
                # new data: just replace.
                m_old = m_old[0]
                if m_old.start_day==start_dt and m_old.end_day==end_dt and m_old.room==room \
                        and m_old.meeting_type==mtg_type and m_old.labtut_section==labtut_section:
                    # unchanged: leave it.
                    found_mtg.add(m_old.id)
                    continue
                else:
                    # it has changed: remove and replace.
                    m_old.delete()
            
            m = MeetingTime(offering=offering, weekday=wkd, start_day=start_dt, end_day=end_dt,
                            start_time=start, end_time=end, room=room, labtut_section=labtut_section)
            m.meeting_type = mtg_type
            m.save()
            found_mtg.add(m.id)
    
    # delete any meeting times we haven't found in the DB
    MeetingTime.objects.filter(offering=offering).exclude(id__in=found_mtg).delete()



def ensure_member(person, offering, role, credits, added_reason, career, labtut_section=None):
    """
    Make sure this member exists with the right properties.
    """
    m_old = Member.objects.filter(person=person, offering=offering)

    if len(m_old)>1:
        # may be other manually-created dropped entries: that's okay.
        m_old = Member.objects.filter(person=person, offering=offering).exclude(role="DROP")
        if len(m_old)>1:
            raise KeyError, "Already duplicate entries: %r" % (m_old)
    if len(m_old)==1:
        m = m_old[0]
        m.role = role
        m.labtut_section = labtut_section
        m.credits = credits
        m.added_reason = added_reason
        m.career = career
    else:
        m = Member(person=person, offering=offering, role=role, labtut_section=labtut_section,
                credits=credits, added_reason=added_reason, career=career)
    
    # if offering is being given lab/tutorial sections, flag it as having them
    # there must be some way to detect this in ps_class_tbl, but I can't see it.
    if labtut_section and not offering.labtut():
        offering.set_labtut(True)
        offering.save()
    
    m.save()
    return m


@transaction.commit_on_success
def import_instructors(db, amaintdb, offering):
    Member.objects.filter(added_reason="AUTO", offering=offering, role="INST").update(role='DROP')
    n = execute_query(db, "SELECT emplid, instr_role, sched_print_instr FROM dbsastg.ps_class_instr WHERE crse_id=%s and class_section=%s and strm=%s and instr_role='PI'  and sched_print_instr='Y'", ("%06i" % (int(offering.crse_id)), offering.section, offering.semester.name))
    #
    
    for emplid, instr_role, print_instr in rows(db):
        if not emplid:
            continue
        p = get_person(db, amaintdb, emplid)
        ensure_member(p, offering, "INST", 0, "AUTO", "NONS")


@transaction.commit_on_success
def import_tas(db, tadb, amaintdb, offering):
    if offering.subject not in ['CMPT', 'MACM']:
        return

    nbr = offering.number
    if nbr[-1] == "W":
        nbr = nbr[:-1]

    Member.objects.filter(added_reason="AUTO", offering=offering, role="TA").update(role='DROP')
    tadb.execute('SELECT emplid, userid FROM ta_data WHERE strm=%s and subject=%s and catalog_nbr REGEXP %s and class_section=%s', (offering.semester.name, offering.subject, nbr+"W?", offering.section[0:2]))
    for emplid,userid in tadb:
        p = get_person(db, amaintdb, emplid)
        if p is None:
            print "    Unknown TA:", emplid, userid
            return
        ensure_member(p, offering, "TA", 0, "AUTO", "NONS")
    

@transaction.commit_on_success
def import_students(db, amaintdb, offering):
    Member.objects.filter(added_reason="AUTO", offering=offering, role="STUD").update(role='DROP')
    # find any lab/tutorial sections
    
    # c1 original lecture section
    # c2 related lab/tutorial section
    # s students in c2
    # WHERE lines: (1) match lab/tut sections of c1 class (2) students in those
    # lab/tut sections (3) with c1 matching offering
    query = "SELECT s.emplid, c2.class_section " \
        "FROM dbsastg.ps_class_tbl c1, dbsastg.ps_class_tbl c2, dbsastg.ps_stdnt_enrl s " \
        "WHERE c1.subject=c2.subject and c1.catalog_nbr=c2.catalog_nbr and c2.strm=c1.strm " \
        "and s.class_nbr=c2.class_nbr and s.strm=c2.strm and s.stdnt_enrl_status='E' " \
        "and c1.class_nbr=%s and c1.strm=%s and c2.class_section LIKE %s"
    n = execute_query(db, query, (offering.class_nbr, offering.semester.name, offering.section[0:2]+"%"))
    labtut = {}
    for emplid, section in iter_rows(db):
        if section == offering.section:
            # not interested in lecture section now.
            continue
        labtut[emplid] = section
    
    n = execute_query(db, "SELECT emplid, acad_career, unt_taken FROM dbsastg.ps_stdnt_enrl WHERE class_nbr=%s and strm=%s and stdnt_enrl_status='E'", (offering.class_nbr, offering.semester.name))
    for emplid, acad_career, unt_taken in rows(db):
        p = get_person(db, amaintdb, emplid)
        sec = labtut.get(emplid, None)
        ensure_member(p, offering, "STUD", unt_taken, "AUTO", acad_career, labtut_section=sec)


def import_offering(db, tadb, amaintdb, offering):
    """
    Import all data for the course: instructors, TAs, students, meeting times.
    """
    if random.randint(1,40) == 1:
        print " ", offering
    import_instructors(db, amaintdb, offering)
    import_tas(db, tadb, amaintdb, offering)
    import_students(db, amaintdb, offering)
    import_meeting_times(db, offering)
    update_offering_repositories(offering)
    
    
@transaction.commit_on_success
def combine_sections(db, combined):
    """
    Combine sections in the database to co-offered courses look the same.
    """
    for info in combined:
        # create the section if necessary
        courses = CourseOffering.objects.filter(subject=info['subject'], number=info['number'], section=info['section'], semester=info['semester'], component=info['component'], campus=info['campus'])
        if courses:
            course = courses[0]
        else:
            kwargs = copy.copy(info)
            del kwargs['subsections']
            course = CourseOffering(**kwargs)
            course.save()

        print "  ", course        
        cap_total = 0
        tot_total = 0
        wait_total = 0
        labtut = False
        in_section = set() # students who are in section and not dropped (so we don't overwrite with a dropped membership)
        for sub in info['subsections']:
            cap_total += sub.enrl_cap
            tot_total += sub.enrl_tot
            wait_total += sub.wait_tot
            labtut = labtut or sub.labtut()
            for m in sub.member_set.all():
                old_ms = course.member_set.filter(offering=course, person=m.person)
                if old_ms:
                    # was already a member: update.
                    old_m = old_ms[0]
                    old_m.role = m.role
                    old_m.credits = m.credits
                    old_m.career = m.career
                    old_m.added_reason = m.added_reason
                    old_m.config['origsection'] = sub.slug
                    old_m.labtut_section = m.labtut_section
                    if m.role != 'DROP' or old_m.person_id not in in_section:
                        # condition keeps from overwriting enrolled students with drops (from other section)
                        old_m.save()
                    if m.role != 'DROP':
                        in_section.add(old_m.person_id)
                else:
                    # new membership: duplicate into combined
                    new_m = Member(offering=course, person=m.person, role=m.role, labtut_section=m.labtut_section,
                            credits=m.credits, career=m.career, added_reason=m.added_reason)
                    new_m.config['origsection'] = sub.slug
                    new_m.save()
                    if m.role != 'DROP':
                        in_section.add(new_m.person_id)

        # update totals        
        course.enrl_cap = cap_total
        course.tot_total = tot_total
        course.wait_total = wait_total
        course.set_labtut(labtut)
        course.set_combined(True)
        course.save()


@transaction.commit_on_success
def give_sysadmin(sysadmin):
    """
    Give specified users sysadmin role (for bootstrapping)
    """
    for userid in sysadmin:
        p = Person.objects.get(userid=userid)
        r = Role.objects.filter(person=p, role="SYSA")
        if not r:
            r = Role(person=p, role="SYSA", department="!!!!")
            r.save()


def main():
    global DATA_WHERE, sysadmin
    amaintpasswd = raw_input()
    tapasswd = raw_input()
    _ = raw_input()
    simspasswd = raw_input()

    #create_semesters()
    dbconn = DB2.connect(dsn=sims_db, uid=sims_user, pwd=simspasswd)
    db = dbconn.cursor()
    amaintconn = MySQLdb.connect(host=amaint_host, user=amaint_user,
             passwd=amaintpasswd, db=amaint_name, port=amaint_port)
    amaintdb = amaintconn.cursor()
    tadbconn = MySQLdb.connect(host=ta_host, user=ta_user,
             passwd=tapasswd, db=ta_name, port=ta_port)
    tadb = tadbconn.cursor()

    print "fixing any unknown emplids"
    #fix_emplid(db)
    
    print "importing course offering list"
    offerings = import_offerings(db, DATA_WHERE)
    #offerings = [CourseOffering.objects.get(slug="2012sp-cmpt-276-d2"), CourseOffering.objects.get(slug="2012sp-cmpt-383-e2"), CourseOffering.objects.get(slug="2012sp-cmpt-470-e1")]
    #offerings = CourseOffering.objects.filter(slug__startswith="2012sp-cmpt")
    offerings = list(offerings)
    offerings.sort()

    print "importing course members"
    for o in offerings:
        import_offering(db, tadb, amaintdb, o)
        time.sleep(0.5)

    print "combining joint offerings"
    combine_sections(db, get_combined())
    
    print "giving sysadmin permissions"
    give_sysadmin(sysadmin)
    
    # cleanup sessions table
    Session.objects.filter(expire_date__lt=datetime.datetime.now()).delete()
    # cleanup old news items
    NewsItem.objects.filter(updated__lt=datetime.datetime.now()-datetime.timedelta(days=120)).delete()
    # cleanup old log entries
    LogEntry.objects.filter(datetime__lt=datetime.datetime.now()-datetime.timedelta(days=365)).delete()
    # cleanup already-run Celery jobs
    if settings.USE_CELERY:
        import djkombu.models
        djkombu.models.Message.objects.cleanup()
    
    print "People:", len(imported_people)
    print "Course Offerings:", len(offerings)


if __name__ == "__main__":
    main()

