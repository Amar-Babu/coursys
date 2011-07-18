import sys, os, datetime, string, time, copy
import MySQLdb
sys.path.append(".")
sys.path.append("..")
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from coredata.models import *
from dashboard.models import NewsItem
from django.db import transaction
from django.contrib.sessions.models import Session
today = datetime.date.today()
cutoff = today - datetime.timedelta(days=30)

# these users will be given sysadmin role (for bootstrapping)
sysadmin = ["ggbaker"]

# first term we care about in import
FIRSTTERM = "1104"
DATA_WHERE = '(subject="CMPT" or subject="MACM") and strm>="'+FIRSTTERM+'"'

# artificial combined sections to create: kwargs for CourseOffering creation,
# plus 'subsections' list of sections we're combining.
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
        ]


import_host = '127.0.0.1'      
import_user = 'ggbaker'
import_name = 'ggbaker_crse_mgmt'
import_port = 4000
#timezone = "America/Vancouver" # timezone of imported class meeting times

ta_host = '127.0.0.1'      
ta_user = 'ta_data_import'
ta_name = 'ta_data_drop'
ta_port = 4000

#TODO: add sanity check for no DB info

"""
v_ps_class_instr: only getting primary/printing instructors

pref_first_name always empty
SELECT * FROM v_ps_personal_data v where length(pref_first_name)>0 LIMIT 100
"""

def import_semester(sems):
    """
    Should this QuerySet of semesters be imported?
    """
    if not sems:
        return False
    s = sems[0]
    return s.end >= cutoff

def decode(s):
    """
    Turn database string into proper Unicode.
    """
    return s.decode('utf8')

def create_semesters():
    # http://students.sfu.ca/calendar/for_students/dates.html
    s = Semester.objects.filter(name="1094")
    if not s:
        s = Semester(name="1094", start=datetime.date(2009, 5, 4), end=datetime.date(2009, 8, 4))
        s.save()
        wk = SemesterWeek(semester=s, week=1, monday=datetime.date(2009, 5, 4))
        wk.save()

    s = Semester.objects.filter(name="1097")
    if not s:
        s = Semester(name="1097", start=datetime.date(2009, 9, 8), end=datetime.date(2009, 12, 7))
        s.save()
        wk = SemesterWeek(semester=s, week=1, monday=datetime.date(2009, 9, 7))
        wk.save()

    s = Semester.objects.filter(name="1101")
    if not s:
        s = Semester(name="1101", start=datetime.date(2010, 1, 4), end=datetime.date(2010, 4, 16))
        s.save()
        wk = SemesterWeek(semester=s, week=1, monday=datetime.date(2010, 1, 4))
        wk.save()
        wk = SemesterWeek(semester=s, week=7, monday=datetime.date(2010, 3, 1))
        wk.save()

    s = Semester.objects.filter(name="1104")
    if not s:
        s = Semester(name="1104", start=datetime.date(2010, 5, 12), end=datetime.date(2010, 8, 11))
        s.save()
        wk = SemesterWeek(semester=s, week=1, monday=datetime.date(2010, 5, 10))
        wk.save()

    s = Semester.objects.filter(name="1107")
    if not s:
        s = Semester(name="1107", start=datetime.date(2010, 9, 7), end=datetime.date(2010, 12, 6))
        s.save()
        wk = SemesterWeek(semester=s, week=1, monday=datetime.date(2010, 9, 6))
        wk.save()

    s = Semester.objects.filter(name="1111")
    if not s:
        s = Semester(name="1111", start=datetime.date(2011, 1, 4), end=datetime.date(2011, 4, 7))
        s.save()
        wk = SemesterWeek(semester=s, week=1, monday=datetime.date(2011, 1, 3))
        wk.save()
        wk = SemesterWeek(semester=s, week=8, monday=datetime.date(2011, 2, 28))
        wk.save()

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


def find_offering_by_crse_id(crse_id, section, semester):
    """
    Return the (unique) corresponding course offering object.
    """
    cs = CourseOffering.objects.filter(crse_id=crse_id, section=section, semester=semester)
    if len(cs)==0:
        raise KeyError, "Unknown course: %r %r %r." % ((crse_id, section, semester))
    elif len(cs)>1:
        raise KeyError, "Course not uniquely selected: %r %r %r." % ((crse_id, section, semester))

    return cs[0]

def find_offering_by_class_nbr(class_nbr, semester):
    """
    Return the (unique) corresponding course offering object.
    """
    cs = CourseOffering.objects.filter(class_nbr=class_nbr, semester=semester)
    if len(cs)==0:
        raise KeyError, "Unknown course: %r %r." % ((class_nbr, semester))
    elif len(cs)>1:
        raise KeyError, "Course not uniquely selected: %r %r." % ((class_nbr, semester))

    return cs[0]





def fix_emplid(db):
    """
    Any manually-entered people will have emplid 0000?????.  Update them with the real emplid from the database.
    """
    people = Person.objects.filter(emplid__lt=100000)
    for p in people:
        print " ", p.userid
        db.execute('SELECT emplid FROM v_ps_personal_data WHERE username=%s', p.userid)
        row = db.fetchone()
        if row:
            emplid, = row
            p.emplid = emplid
            p.save()

def import_offerings(db):
    """
    Import course offerings
    """
    db.execute('SELECT subject, catalog_nbr, class_section, strm, crse_id, class_nbr, ssr_component, descr, campus, enrl_cap, enrl_tot, wait_tot, cancel_dt FROM v_ps_class_tbl WHERE ' + DATA_WHERE)
    for subject, number, section, strm, crse_id, class_nbr, component, title, campus, enrl_cap, enrl_tot, wait_tot, cancel_dt in db:
        # only import for defined semesters.
        semesters = Semester.objects.filter(name=strm)
        #print semesters, import_semester(semesters)
        if not import_semester(semesters):
            continue
        semester = semesters[0]
        
        graded = section.endswith("00")

        # make sure the data is as we expect:
        if not CAMPUSES.has_key(campus):
            raise KeyError, "Unknown campus: %r." % (campus)
        if not COMPONENTS.has_key(component):
            raise KeyError, "Unknown course component: %r." % (component)

        if cancel_dt != "None":
            # mark cancelled sections
            component="CAN"

        c_old = CourseOffering.objects.filter(subject=subject, number=number, section=section, semester=semester)
        if len(c_old)>1:
	    c_old
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
            	c_old.save()
            else:
            	# new record: create.
            	c = CourseOffering(subject=subject, number=number, section=section, semester=semester, crse_id=crse_id, class_nbr=class_nbr, component=component, graded=graded, title=title, campus=campus, enrl_cap=enrl_cap, enrl_tot=enrl_tot, wait_tot=wait_tot)
            	c.save()

def import_meeting_times(db):
    """
    Import course meeting times
    """
    db.execute('SELECT crse_id, class_section, strm, meeting_time_start, meeting_time_end, facility_id, mon,tues,wed,thurs,fri,sat,sun, start_dt, end_dt, stnd_mtg_pat FROM v_ps_class_mtg_pat WHERE strm>="'+FIRSTTERM+'"')
    # keep track of meetings we've found, so we can remove old (non-importing semesters and changed/gone)
    found_mtg = set()

    for crse_id, section, strm, start, end, room, mon,tues,wed,thurs,fri,sat,sun, start_dt, end_dt, stnd_mtg_pat in db:
        semester = Semester.objects.filter(name=strm)
        if not import_semester(semester):
            continue
        semester = semester[0]
        c = find_offering_by_crse_id(crse_id, section, semester)

        wkdays = [n for n, day in zip(range(7), (mon,tues,wed,thurs,fri,sat,sun)) if day=='Y']
        for wkd in wkdays:
            m_old = MeetingTime.objects.filter(offering=c, weekday=wkd, start_time=start, end_time=end)
            if len(m_old)>1:
                raise KeyError, "Already duplicate meeting: %r" % (m_old)
            elif len(m_old)==1:
                # new data: just replace.
                m_old = m_old[0]
                if m_old.start_day==start_dt and m_old.end_day==end_dt and m_old.room==room \
                        and m_old.exam == (stnd_mtg_pat in ["EXAM","MIDT"]):
                    # unchanged: leave it.
                    found_mtg.add(m_old.id)
                    continue
                else:
                    # it has changed: remove and replace.
                    m_old.delete()
            
            m = MeetingTime(offering=c, weekday=wkd, start_day=start_dt, end_day=end_dt,
                            start_time=start, end_time=end, room=room)
            m.exam = stnd_mtg_pat in ["EXAM","MIDT"]
            m.save()
            found_mtg.add(m.id)
    
    # delete any meeting times we haven't found in the DB
    MeetingTime.objects.exclude(id__in=found_mtg).delete()


def import_instructors(db):
    """
    Import course instructors
    """
    n = db.execute('SELECT crse_id, class_section, strm, emplid, instr_role, sched_print_instr FROM v_ps_class_instr WHERE strm>="'+FIRSTTERM+'"')
    members = []

    for crse_id, section, strm, emplid, instr_role, print_instr in db:
        # only import for defined semesters.
        semester = Semester.objects.filter(name=strm)
        if not import_semester(semester):
            continue

        c = find_offering_by_crse_id(crse_id, section, semester)

        # find existing membership objects and update if appropriate
        p = Person.objects.filter(emplid=emplid)
        if len(p)==0:
            m_old = []
        else:
            m_old = Member.objects.filter(person=p, offering=c)

        if len(m_old)>1:
            raise KeyError, "Already duplicate instructor entries: %r" % (m_old)
        elif len(m_old)==1:
            m = m_old[0]
            m.credits = 0
            m.added_reason = "AUTO"
            m.career = "NONS"
            m.role = "INST"
        else:
            m = Member(offering=c, role="INST", credits=0, added_reason="AUTO", career="NONS")

        members.append((emplid, m))
        # need to get personal and link info before saving

    return members

def import_tas(dbpasswd):
    """
    Import TAs
    """
    dbconn = MySQLdb.connect(host=ta_host, user=ta_user,
             passwd=dbpasswd, db=ta_name, port=ta_port)
    db = dbconn.cursor()
    
    db.execute('SELECT strm, emplid, subject, catalog_nbr, class_section FROM ta_data WHERE strm>="'+FIRSTTERM+'"')
    members = []
    for strm, emplid, subject, catalog_nbr, class_section in db:
        class_section = class_section+"00"
        semester = Semester.objects.filter(name=strm)
        if not import_semester(semester):
            continue

        # there's some fuzziness in the courseoffering mapping here: 376 vs 376W, D100 vs G100
        cs = CourseOffering.objects.filter(subject=subject, number__in=[catalog_nbr,catalog_nbr+"W"],
            section__in=[class_section, "G"+class_section[1:]], semester=semester)
        if len(cs)==0:
            raise KeyError, "Unknown course: %r %r %r %r." % (subject, catalog_nbr, class_section, semester)
        elif len(cs)>1:
            raise KeyError, "Course not uniquely selected: %r %r %r %r." % (subject, catalog_nbr, class_section, semester)
        c = cs[0]

        # find existing membership objects and update if appropriate
        p = Person.objects.filter(emplid=emplid)
        if len(p)==0:
            m_old = []
        else:
            m_old = Member.objects.filter(person=p, offering=c)

        if len(m_old)>1:
            raise KeyError, "Already duplicate TA entries: %r" % (m_old)
        elif len(m_old)==1:
            m = m_old[0]
            m.credits = 0
            m.added_reason = "AUTO"
            m.career = "NONS"
            m.role = "TA"
        else:
            m = Member(offering=c, role="TA", credits=0, added_reason="AUTO", career="NONS")

        members.append((str(emplid), m))

    return members
        

def import_students(db):
    """
    Import students in course
    """
    db.execute('SELECT class_nbr, strm, emplid, acad_career, unt_taken FROM v_ps_stdnt_enrl WHERE strm>="'+FIRSTTERM+'" and stdnt_enrl_status="E"')
    members = []
    for class_nbr, strm, emplid, acad_career, unt_taken in db:
        # only import for defined semesters.
        semester = Semester.objects.filter(name=strm)
        if not import_semester(semester):
            continue

        # make sure the data is as we expect:
        if not Member.CAREERS.has_key(acad_career):
            raise KeyError, "Unknown career: %r." % (campus)

        c = find_offering_by_class_nbr(class_nbr, semester)
        
        # find existing membership objects and update if appropriate
        p = Person.objects.filter(emplid=emplid)
        if len(p)==0:
            m_old = []
        else:
            m_old = Member.objects.filter(person=p, offering=c)

        if len(m_old)>1:
            raise KeyError, "Already duplicate student entries: %r" % (m_old)
        elif len(m_old)==1:
            m = m_old[0]
            m.credits = unt_taken
            m.added_reason = "AUTO"
            m.career = acad_career
            m.role = "STUD"
        else:
            m = Member(offering=c, role="STUD", credits=unt_taken, added_reason="AUTO", career=acad_career)

        members.append((emplid, m))
        # need to get personal info and link info before saving

    return members


def handle_person(membership, userid, emplid, last_name, first_name, middle_name, pref_first_name):
    """
    Create or update record for this user.
    """
    if emplid not in membership:
        return
    if not pref_first_name:
        pref_first_name = first_name

    p_old = Person.objects.filter(emplid=emplid)
    if len(p_old)>1:
        raise KeyError, "Already duplicate people: %r" % (p_old)
    elif len(p_old)==1:
        # existing entry: make sure it's updated
        p = p_old[0]
        p.userid = userid
        p.last_name = decode(last_name)
        p.first_name = decode(first_name)
        p.middle_name = decode(middle_name)
        p.pref_first_name = decode(pref_first_name)
        p.save()
    else:
        # newly-found person: insert
        p = Person(emplid=emplid, userid=userid, last_name=decode(last_name), first_name=decode(first_name), middle_name=decode(middle_name), pref_first_name=decode(pref_first_name))
        p.save()
        
    # update the membership records we're working with and save.
    for m in membership[emplid]:
        m.person = p
        m.save()


def import_people(db, members):
    """
    Import people (but only those known to the system)
    """
    # turn list of memberships into dictionary
    membership = {}
    for emplid, offering in members:
        if offering is not None:
            membership[emplid] = membership.get(emplid, []) + [offering]
        else:
            membership[emplid] = membership.get(emplid, [])

    # make sure role accounts have personal data imported too
    for r in Role.objects.all():
        emplid = str(r.person.emplid)
        membership[emplid] = membership.get(emplid, [])

    # find all relevant people
    # Importing everybody in one query seems to bog things down: query is too large?  Import in managable segments.
    for c in string.ascii_lowercase:
        time.sleep(1)
        print " " + c
        db.execute('SELECT username, emplid, last_name, first_name, middle_name, pref_first_name FROM v_ps_personal_data WHERE username LIKE "' + c + '%"')
        for userid, emplid, last_name, first_name, middle_name, pref_first_name in db:
            handle_person(membership, userid, emplid, last_name, first_name, middle_name, pref_first_name)
    # anybody else?
    print " others"
    db.execute('SELECT username, emplid, last_name, first_name, middle_name, pref_first_name FROM v_ps_personal_data WHERE username<"a" or username>"zzzzzzzz"')
    for userid, emplid, last_name, first_name, middle_name, pref_first_name in db:
        handle_person(membership, userid, emplid, last_name, first_name, middle_name, pref_first_name)


def combine_sections(db):
    """
    Combine sections in the database to co-offered courses look the same.
    """
    for info in combined_sections:
        # create the section if necessary
        courses = CourseOffering.objects.filter(subject=info['subject'], number=info['number'], section=info['section'], semester=info['semester'], component=info['component'], campus=info['campus'])
        if courses:
            course = courses[0]
        else:
            kwargs = copy.copy(info)
            del kwargs['subsections']
            course = CourseOffering(**kwargs)
            course.save()
        
        cap_total = 0
        tot_total = 0
        wait_total = 0
        for sub in info['subsections']:
            cap_total += sub.enrl_cap
            tot_total += sub.enrl_tot
            wait_total += sub.wait_tot
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
                    old_m.save()
                else:
                    # new membership: duplicate into combined
                    new_m = Member(offering=course, person=m.person, role=m.role,
                            credits=m.credits, career=m.career, added_reason=m.added_reason)
                    new_m.config['origsection'] = sub.slug
                    new_m.save()

        # update totals        
        course.enrl_cap = cap_total
        course.tot_total = tot_total
        course.wait_total = wait_total
        course.save()





@transaction.commit_on_success
def main():
    dbpasswd = raw_input()
    tapasswd = raw_input()

    create_semesters()
    dbconn = MySQLdb.connect(host=import_host, user=import_user,
             passwd=dbpasswd, db=import_name, port=import_port)
    db = dbconn.cursor()

    print "fixing any unknown emplids"
    fix_emplid(db)
    time.sleep(1)
    
    # Drop everybody (and re-add later if they're still around)
    #Member.objects.filter(added_reason="AUTO").update(role="DROP")
    for s in Semester.objects.all():
        if import_semester([s]):
            Member.objects.filter(added_reason="AUTO", offering__semester=s).update(role="DROP")
    
    # People to fetch: manually-added members of courses (and everybody else we find later)
    members = [(m.person.emplid, m.offering) for m in Member.objects.exclude(added_reason="AUTO")]
    time.sleep(1)
    
    print "importing course offerings"
    import_offerings(db)
    time.sleep(1)
    print "importing meeting times"
    import_meeting_times(db)
    time.sleep(1)
    print "importing instructors"
    members += import_instructors(db)
    time.sleep(1)
    print "importing students"
    members += import_students(db)
    time.sleep(1)
    print "importing TAs"
    members += import_tas(tapasswd)
    time.sleep(1)  
    print "importing personal info"
    import_people(db, members)
    time.sleep(1)
    
    print "creating combined sections"
    combine_sections(db)
    
    time.sleep(1)
    print "giving sysadmin permissions"
    for userid in sysadmin:
        p = Person.objects.get(userid=userid)
        r = Role.objects.filter(person=p, role="SYSA")
        if not r:
            r = Role(person=p, role="SYSA", department="!!!!")
            r.save()
    
    time.sleep(1)
    # cleanup sessions table
    Session.objects.filter(expire_date__lt=datetime.datetime.now()).delete()
    # cleanup old news items
    NewsItem.objects.filter(updated__lt=datetime.datetime.now()-datetime.timedelta(days=60)).delete()
        
    print "committing to DB"


if __name__ == "__main__":
    main()
