import sys, os, datetime, string
import MySQLdb
sys.path.append(".")
sys.path.append("..")
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from coredata.models import *

# only import people matching this WHERE:
#CONDITION = 'username LIKE "g%" OR username LIKE "b%"'
#CONDITION = '1=1'

import_host = '127.0.0.1'      
import_user = 'ggbaker'
import_name = 'ggbaker_crse_mgmt'
import_port = 3309
timezone = "America/Vancouver" # timezone of imported class meeting times

#TODO: add sanity check for no DB info

"""
need TA data

v_ps_class_instr: only getting primary/printing instructors

need to be able to detect cancelled offerings (for deletion)

Also getting exam times in import.  Can we distinguish?
SELECT * FROM v_ps_class_mtg_pat v where crse_id=004232 and class_section="D200" and strm="1097"

pref_first_name always empty
SELECT * FROM v_ps_personal_data v where length(pref_first_name)>0 LIMIT 100
"""

def decode(s):
    """
    Turn database string into proper Unicode.
    """
    return s.decode('latin1')

def create_semesters():
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





def import_offerings(db):
    """
    Import course offerings
    """
    db.execute('SELECT subject, catalog_nbr, class_section, strm, crse_id, class_nbr, ssr_component, descr, campus, enrl_cap, enrl_tot, wait_tot FROM v_ps_class_tbl')
    for subject, number, section, strm, crse_id, class_nbr, component, title, campus, enrl_cap, enrl_tot, wait_tot in db:
        # only import for defined semesters.
        semesters = Semester.objects.filter(name=strm)
        if not semesters:
            continue
        semester = semesters[0]
        
        graded = section.endswith("00")

        #print subject, number, section, semester, crse_id

        # make sure the data is as we expect:
        if not CourseOffering.CAMPUSES.has_key(campus):
            raise KeyError, "Unknown campus: %r." % (campus)
        if not CourseOffering.COMPONENTS.has_key(component):
            raise KeyError, "Unknown course component: %r." % (component)

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
            c_old.save()
        else:
            # new record: create.
            c = CourseOffering(subject=subject, number=number, section=section, semester=semester, crse_id=crse_id, class_nbr=class_nbr, component=component, graded=graded, title=title, campus=campus, enrl_cap=enrl_cap, enrl_tot=enrl_tot, wait_tot=wait_tot)
            c.save()

def import_meeting_times(db):
    """
    Import course meeting times
    """
    db.execute('SELECT crse_id, class_section, strm, meeting_time_start, meeting_time_end, facility_id, mon,tues,wed,thurs,fri,sat,sun FROM v_ps_class_mtg_pat')
    for crse_id, section, strm, start, end, room, mon,tues,wed,thurs,fri,sat,sun in db:
        semester = Semester.objects.filter(name=strm)
        if not semester:
            continue
        c = find_offering_by_crse_id(crse_id, section, semester)

        #print crse_id, section, strm, start, end, room, (mon,tues,wed,thurs,fri,sat,sun)
        wkdays = [n for n, day in zip(range(7), (mon,tues,wed,thurs,fri,sat,sun)) if day=='Y']
        for wkd in wkdays:
            m_old = MeetingTime.objects.filter(offering=c, weekday=wkd, start_time=start, end_time=end)
            if len(m_old)>1:
                raise KeyError, "Already duplicate meeting: %r" % (m_old)
            elif len(m_old)==1:
                # new data: just replace.
                m_old = m_old[0]
                m_old.delete()

            m = MeetingTime(offering=c, weekday=wkd, start_time=start, end_time=end, timezone=timezone, room=room)
            #m.save()
            # TODO: ignore until we can distinguish exam times.


def import_instructors(db):
    """
    Import course instructors
    """
    n = db.execute('SELECT crse_id, class_section, strm, emplid, instr_role, sched_print_instr FROM v_ps_class_instr')
    members = []

    for crse_id, section, strm, emplid, instr_role, print_instr in db:
        # only import for defined semesters.
        semester = Semester.objects.filter(name=strm)
        if not semester:
            continue

        c = find_offering_by_crse_id(crse_id, section, semester)

        # find existing membership objects and update if appropriate
        p = Person.objects.filter(emplid=emplid)
        if len(p)==0:
            m_old = []
        else:
            m_old = Member.objects.filter(person=p, offering=c, role="DROP")

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

def import_students(db):
    """
    Import students in course
    """
    db.execute('SELECT class_nbr, strm, emplid, acad_career, unt_taken FROM v_ps_stdnt_enrl WHERE strm>="1097" and stdnt_enrl_status="E"')
    members = []
    for class_nbr, strm, emplid, acad_career, unt_taken in db:
        # only import for defined semesters.
        semester = Semester.objects.filter(name=strm)
        if not semester:
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
            m_old = Member.objects.filter(person=p, offering=c, role="DROP")

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
        # need to get personal and link info before saving

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

    # find all relevant people
    # Importing everybody in one query seems to bog things down: query is too large?  Import in managable segments.
    for c in string.ascii_lowercase:
        print " " + c
        db.execute('SELECT username, emplid, last_name, first_name, middle_name, pref_first_name FROM v_ps_personal_data WHERE username LIKE "' + c + '%"')
        for userid, emplid, last_name, first_name, middle_name, pref_first_name in db:
            handle_person(membership, userid, emplid, last_name, first_name, middle_name, pref_first_name)
    # anybody else?
    print " others"
    db.execute('SELECT username, emplid, last_name, first_name, middle_name, pref_first_name FROM v_ps_personal_data WHERE username<"a" or username>"zzzzzzzz"')
    for userid, emplid, last_name, first_name, middle_name, pref_first_name in db:
        handle_person(membership, userid, emplid, last_name, first_name, middle_name, pref_first_name)
    

def main(passwd=None):
    if passwd == None:
        raise NotImplementedError, "TODO: web form input"
    
    create_semesters()
    dbconn = MySQLdb.connect(host=import_host, user=import_user,
             passwd=passwd, db=import_name, port=import_port)
    db = dbconn.cursor()
    
    # Drop everybody (and re-add later if they're still around)
    Member.objects.filter(added_reason="AUTO").update(role="DROP")
    
    # People to fetch: manually-added members of courses (and everybody else we find later)
    members = [(m.person.emplid, m.offering) for m in Member.objects.exclude(added_reason="AUTO")]
    
    print "importing course offerings"
    import_offerings(db)
    print "importing meeting times"
    #import_meeting_times(db)
    print "importing instructors"
    members += import_instructors(db)
    print "importing students"
    members += import_students(db)
    
    print "importing personal info"
    import_people(db, members)
    


if __name__ == "__main__":
    import getpass
    passwd = getpass.getpass('Database password: ')
    main(passwd)
