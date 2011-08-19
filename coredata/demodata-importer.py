# do the import with fake data for development
# suggestion execution:
#   rm db.sqlite; echo "no" | ./manage.py syncdb; ./manage.py migrate; echo "dbpassword" | python coredata/fake-importer.py

import MySQLdb, random, string, socket, datetime, itertools
from django.core import serializers
from importer import import_host, import_name, import_user, import_port
from importer import give_sysadmin, create_semesters, import_offerings, import_instructors, import_meeting_times
from coredata.models import Member, Person, CourseOffering, Semester, MeetingTime, Role
from grades.models import Activity, NumericActivity, LetterActivity, CalNumericActivity, CalLetterActivity
from submission.models.base import SubmissionComponent
from submission.models.code import CodeComponent
from submission.models.pdf import PDFComponent
from marking.models import ActivityComponent
from groups.models import Group, GroupMember

FIRSTTERM = "1111"
DATA_WHERE = 'strm>="'+FIRSTTERM+'"'
FULL_TEST_DATA = "1114-cmpt-120-d100"
MIN_TEST_DATA = "1114-cmpt-165-c100"

fakes = {}
next_emplid = 100

def fake_emplid(emplid=None):
    """
    Return a fake EMPLID for this person
    """
    global fakes, next_emplid
    base = 200000000
    
    if emplid != None and emplid in fakes:
        return fakes[emplid]
    
    next_emplid += 1
    fake = base + next_emplid
    fakes[emplid] = fake
    return fake

def fake_emplids():
    """
    Replace student numbers with fakes
    """
    people = Person.objects.all()
    for p in people:
        p.emplid = fake_emplid(p.emplid)
        p.save()

def randname(l):
    n = random.choice(string.ascii_uppercase)
    for i in range(l-1):
        n = n + random.choice(string.ascii_lowercase)
    return n



def test_class_2(slug):
    """
    another test course with jsut some student and no other config
    """
    crs = CourseOffering.objects.get(slug=slug)
    for i in range(40):
        lab = "D1%02i" % (random.randint(1,4))
        fname = randname(8)
        p = Person(emplid=fake_emplid(), userid="0bbb%i"%(i), last_name="Student", first_name=fname, middle_name="", pref_first_name=fname[:4])
        p.save()
        m = Member(person=p, offering=crs, role="STUD", credits=3, career="UGRD", added_reason="AUTO",
                labtut_section=lab)
        m.save()


all_students = {}
def create_fake_students():
    """
    Make a bunch of fake students so we can add them to classes later.
    """
    global all_students
    for lett in string.ascii_lowercase:
        for i in range(21):
            if i==20:
                userid = "0%sta" % (lett*3)
                fname = randname(8)
                lname = "TheTA"
            else:
                userid = "0%s%i" % (lett*3, i)
                fname = randname(8)
                lname = "Student"
            p = Person(emplid=fake_emplid(), userid=userid, last_name=lname, first_name=fname, middle_name="", pref_first_name=fname[:4])
            p.save()
            all_students[userid] = p

def fill_courses():
    """
    Put 20 students and a TA in each course.
    """
    global all_students
    for crs in CourseOffering.objects.exclude(component="CAN"):
        lett = random.choice(string.ascii_lowercase)
        for i in range(20):
            userid = "0%s%i" % (lett*3, i)
            m = Member(person=all_students[userid], offering=crs, role="STUD", credits=3, career="UGRD", added_reason="AUTO")
            m.save()

        # and the TA
        userid = "0%sta" % (lett*3)
        m = Member(person=all_students[userid], offering=crs, role="TA", credits=0, career="NONS", added_reason="AUTO")
        m.save()

def create_classes():
    print "creating fake students"
    create_fake_students()
    print "filling classes with students"
    fill_courses()


def import_offering(db, offering):
    """
    Import all data for the course: instructors meeting times.
    """
    # drop all automatically-added members: will be re-added later on import
    Member.objects.filter(added_reason="AUTO", offering=offering).update(role='DROP')
    
    import_instructors(db, offering)
    import_meeting_times(db, offering)

def create_others():
    """
    Create other users for the test data set
    """
    p = Person(emplid=fake_emplid(), first_name="Susan", last_name="Kindersley", pref_first_name="sumo", userid="sumo")
    p.save()
    p = Person(emplid=fake_emplid(), first_name="Danyu", last_name="Zhao", pref_first_name="Danyu", userid="dzhao")
    p.save()
    r = Role(person=p, role="ADVS", department="CMPT")
    r.save()


def serialize(filename):
    """
    output JSON of everything we created
    """
    objs = itertools.chain(
            Semester.objects.all(),
            CourseOffering.objects.all(),
            MeetingTime.objects.all(),
            Person.objects.all(),
            Member.objects.all(),
            Activity.objects.all(),
            NumericActivity.objects.all(),
            LetterActivity.objects.all(),
            CalNumericActivity.objects.all(),
            CalLetterActivity.objects.all(),
            SubmissionComponent.objects.all(),
            CodeComponent.objects.all(),
            PDFComponent.objects.all(),
            ActivityComponent.objects.all(),
            Group.objects.all(),
            GroupMember.objects.all(),
            Role.objects.all(),
            )
    
    data = serializers.serialize("json", objs, sort_keys=True, indent=1)
    fh = open(filename, "w")
    fh.write(data)
    fh.close()


def main(passwd):
    create_semesters()
    dbconn = MySQLdb.connect(host=import_host, user=import_user,
             passwd=passwd, db=import_name, port=import_port)
    db = dbconn.cursor()
    print "importing course offerings"
    offerings = import_offerings(db, DATA_WHERE)
    
    for o in offerings:
        import_offering(db, o)
    
    # should now have all the "real" people: fake their emplids
    fake_emplids()
    
    print "creating fake classess"
    create_classes()
    
    create_others()

    print "giving sysadmin permissions"
    give_sysadmin(['ggbaker', 'sumo'])
    
    serialize("new-test.json")


if __name__ == "__main__":
    passwd = raw_input()
    hostname = socket.gethostname()
    if hostname == 'courses':
        raise NotImplementedError, "Don't do that."
    main(passwd)
