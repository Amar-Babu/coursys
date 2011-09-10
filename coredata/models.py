from django.db import models
from django.template.defaultfilters import slugify
from autoslug import AutoSlugField
#from timezones.fields import TimeZoneField
from django.conf import settings
import datetime, urlparse
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from jsonfield import JSONField
from courselib.json_fields import getter_setter

def repo_name(offering, slug):
    """
    Label for a SVN repository
    """
    name = offering.subject.upper() + offering.number + '-' + offering.semester.name + '-' + slug
    return name[:30]

class Person(models.Model):
    """
    A person in the system (students, instuctors, etc.).
    """
    emplid = models.PositiveIntegerField(db_index=True, unique=True, null=False,
        help_text='Employee ID (i.e. student number)')
    userid = models.CharField(max_length=8, null=True, db_index=True, unique=True,
        help_text='SFU Unix userid (i.e. part of SFU email address before the "@").')
    last_name = models.CharField(max_length=32)
    first_name = models.CharField(max_length=32)
    middle_name = models.CharField(max_length=32, null=True, blank=True)
    pref_first_name = models.CharField(max_length=32)
    
    def __unicode__(self):
        return "%s, %s" % (self.last_name, self.first_name)
    def name(self):
        return "%s %s" % (self.pref_first_name, self.last_name)
    def sortname(self):
        return "%s, %s" % (self.last_name, self.pref_first_name)
    @staticmethod
    def emplid_header():
        return "ID Number"
    @staticmethod
    def userid_header():
        return "Userid"
    def initials(self):
        return "%s%s" % (self.first_name[0], self.last_name[0])
    def email(self):
        return "%s@sfu.ca" % (self.userid)
    def full_email(self):
        return "%s <%s@sfu.ca>" % (self.name(), self.userid)
    def __cmp__(self, other):
        return cmp((self.last_name, self.first_name, self.userid), (other.last_name, other.first_name, other.userid))
    class Meta:
        verbose_name_plural = "People"
        ordering = ['last_name', 'first_name', 'userid']
    
    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."


class Semester(models.Model):
    """
    A semester object: not imported, must be created manually.
    """
    label_lookup = {
        '1': 'Spring',
        '4': 'Summer',
        '7': 'Fall',
        }
    slug_lookup = {
        '1': 'sp',
        '4': 'su',
        '7': 'fa',
        }
    name = models.CharField(max_length=4, null=False, db_index=True, unique=True,
        help_text='Semester name should be in the form "1097".')
    start = models.DateField(help_text='First day of classes.')
    end = models.DateField(help_text='Last day of classes.')
    # TODO: validate that there is a SemesterWeek for week #1.

    class Meta:
        ordering = ['name']

    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."
    
    def label(self):
        """
        The human-readable label for the semester, e.g. "Summer 2010".
        """
        name = str(self.name)
        year = 1900 + int(name[0:3])
        semester = self.label_lookup[name[3]]
        return semester + " " + str(year)
    def slugform(self):
        """
        The slug version of the semester, e.g. "2010su".
        """
        name = str(self.name)
        year = 1900 + int(name[0:3])
        semester = self.slug_lookup[name[3]]
        return str(year) + semester

    def __unicode__(self):
        return self.label()
    
    def timely(self):
        """
        Is this semester temporally relevant (for display in menu)?
        """
        today = datetime.date.today()
        month_ago = today - datetime.timedelta(days=40)
        two_weeks_ago = today + datetime.timedelta(days=14)
        return self.end > month_ago and self.start < two_weeks_ago
    
    def week_weekday(self, dt):
        """
        Given a datetime, return the week-of-semester and day-of-week (with 0=Monday).
        """
        # gracefully deal with both date and datetime objects
        if isinstance(dt, datetime.datetime):
            date = dt.date()
        else:
            date = dt

        # find the "base": first known week before the given date
        weeks = list(SemesterWeek.objects.filter(semester=self))
        weeks.reverse()
        base = None
        for w in weeks:
            if w.monday <= date:
                base = w
                break

        if base is None:
            raise ValueError, "Date seems to be before the start of semester."

        diff = date - base.monday
        diff = int(round(diff.days + diff.seconds/86400.0)+0.5) # convert to number of days, rounding off any timezone stuff
        week = base.week + diff//7
        wkday = date.weekday()
        return week, wkday
    
    def duedate(self, wk, wkday, time):
        """
        Calculate duedate based on week-of-semester and weekday.  Provided argument time can be either datetime.time or datetime.datetime: time is copied from this to new duedate.
        """
        # find the "base": first known week before mk
        weeks = list(SemesterWeek.objects.filter(semester=self))
        weeks.reverse()
        base = None
        for w in weeks:
            if w.week <= wk:
                base = w
                break
        
        date = base.monday + datetime.timedelta(days=7*(wk-base.week)+wkday)
        # construct the datetime from date and time.
        dt = datetime.datetime(year=date.year, month=date.month, day=date.day, 
            hour=time.hour, minute=time.minute, second=time.second, 
            microsecond=time.microsecond, tzinfo=time.tzinfo)
        return dt
    
    @classmethod
    def first_relevant(cls):
        """
        The first semester that's relevant for most reporting: first semester that ends after two months ago.
        """
        today = datetime.date.today()
        year = today.year
        if 1 <= today.month <= 2:
            # last fall semester
            year -= 1
            sem = 7
        elif 3 <= today.month <= 6:
            # this spring
            sem = 1
        elif 7 <= today.month <= 10:
            # this summer
            sem = 4
        elif 11 <= today.month <= 12:
            # this fall
            sem = 7
        
        name = "%03d%1d" % ((year - 1900), sem)
        return Semester.objects.get(name=name)
        


class SemesterWeek(models.Model):
    """
    Starting points for weeks in the semester.
    
    Every semester object needs at least a SemesterWeek for week 1.
    """
    semester = models.ForeignKey(Semester, null=False)
    week = models.PositiveSmallIntegerField(null=False, help_text="Week of the semester (typically 1-13)")
    monday = models.DateField(help_text='Monday of this week.')
    # TODO: validate that monday is really a Monday.
    
    def __unicode__(self):
        return "%s week %i" % (self.semester.name, self.week)
    class Meta:
        ordering = ['semester','week']
        unique_together = (('semester', 'week'))

COMPONENT_CHOICES = (
        ('LEC', 'Lecture'),
        ('LAB', 'Lab'),
        ('TUT', 'Tutorial'),
        ('SEM', 'Seminar'),
        ('SEC', 'Section'), # "Section"?  ~= lecture?
        ('PRA', 'Practicum'),
        ('IND', 'Individual Work'),
        ('INS', 'INS'), # ???
        ('WKS', 'Workshop'),
        ('FLD', 'Field School'),
        ('STD', 'Studio'),
        ('OLC', 'OLC'), # ???
        ('STL', 'STL'), # ???
        ('CAN', 'Cancelled')
        )
COMPONENTS = dict(COMPONENT_CHOICES)
CAMPUS_CHOICES = (
        ('BRNBY', 'Burnaby Campus'),
        ('SURRY', 'Surrey Campus'),
        ('VANCR', 'Harbour Centre'),
        ('OFFST', 'Off-campus'),
        #('SEGAL', 'Segal Centre'),
        ('GNWC', 'Great Northern Way Campus'),
        #('KAM', 'Kamloops Campus'),
        ('METRO', 'METRO'), # ???
        )
CAMPUSES = dict(CAMPUS_CHOICES)

class CourseOffering(models.Model):
    subject = models.CharField(max_length=4, null=False, db_index=True,
        help_text='Subject code, like "CMPT" or "FAN".')
    number = models.CharField(max_length=4, null=False, db_index=True,
        help_text='Course number, like "120" or "XX1".')
    section = models.CharField(max_length=4, null=False,
        help_text='Section should be in the form "C100" or "D103".')
    semester = models.ForeignKey(Semester, null=False)
    component = models.CharField(max_length=3, null=False, choices=COMPONENT_CHOICES,
        help_text='Component of the course, like "LEC" or "LAB".')
    graded = models.BooleanField()
    # need these to join in the SIMS database: don't care otherwise.
    crse_id = models.PositiveSmallIntegerField(null=False, db_index=True)
    class_nbr = models.PositiveSmallIntegerField(null=False, db_index=True)
    
    title = models.CharField(max_length=30, help_text='The course title.')
    #title_long = models.CharField(max_length=80, help_text='The course title (full version).')
    campus = models.CharField(max_length=5, choices=CAMPUS_CHOICES)
    enrl_cap = models.PositiveSmallIntegerField()
    enrl_tot = models.PositiveSmallIntegerField()
    wait_tot = models.PositiveSmallIntegerField()

    members = models.ManyToManyField(Person, related_name="member", through="Member")
    config = JSONField(null=False, blank=False, default={}) # addition configuration stuff
      # c.config['url']: URL of course home page
      # c.config['department']: department responsible for course (used by discipline module)
      # c.config['taemail']: TAs' contact email (if not their personal email)
      # c.config['labtut']: are there lab sections? (default False)
    
    defaults = {'taemail': None, 'url': None, 'labtut': False}
    labtut, set_labtut = getter_setter('labtut')
    url, set_url = getter_setter('url')
    taemail, set_taemail = getter_setter('taemail')
    
    def autoslug(self):
        # changed slug format for fall 2011
        if self.semester.name >= "1117":
            if self.section[2:4] == "00":
                words = [str(s).lower() for s in self.semester.slugform(), self.subject, self.number, self.section[:2]]
            else:
                # these shouldn't be in the DB anymore, but there are a few left, so handle them
                words = [str(s).lower() for s in self.semester.slugform(), self.subject, self.number, self.section]
        else:
            words = [str(s).lower() for s in self.semester.name, self.subject, self.number, self.section]
        return '-'.join(words)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)

    def __unicode__(self):
        return "%s %s %s (%s)" % (self.subject, self.number, self.section, self.semester.label())
    def name(self):
        if self.graded:
            return "%s %s %s" % (self.subject, self.number, self.section[:-2])
        else:
            return "%s %s %s" % (self.subject, self.number, self.section)
        
    def get_absolute_url(self):
        return reverse('grades.views.course_info', kwargs={'course_slug': self.slug})
    
    def instructors(self):
        return (m.person for m in self.member_set.filter(role="INST"))
    def tas(self):
        return (m.person for m in self.member_set.filter(role="TA"))
    def student_count(self):
        return self.members.filter(person__role='STUD').count()
    def department(self):
        """
        Who is the controlling department?
        """
        if 'department' in self.config:
            return self.config['department']
        else:
            return self.subject
    def uses_svn(self):
        """
        Should students and groups in this course get Subversion repositories created?
        """
        return self.subject=="CMPT" and self.number=="470" and self.semester.name=="1117"

    
    def export_dict(self):
        """
        Produce dictionary of data about offering that can be serialized as JSON
        """
        d = {}
        d['subject'] = self.subject
        d['number'] = self.number
        d['section'] = self.section
        d['semester'] = self.semester.name
        d['component'] = self.component
        d['title'] = self.title
        d['campus'] = self.campus
        d['meetingtimes'] = [m.export_dict() for m in self.meetingtime_set.all()]
        d['instructors'] = [{'userid': m.person.userid, 'name': m.person.name()} for m in self.member_set.filter(role="INST").select_related('person')]
        return d
    
    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."

    def __cmp__(self, other):
        return cmp(other.semester.name, self.semester.name) \
            or cmp(self.subject, other.subject) \
            or cmp(self.number, other.number) \
            or cmp(self.section, other.section)

    class Meta:
        ordering = ['-semester', 'subject', 'number', 'section']
        unique_together = (
            ('semester', 'subject', 'number', 'section'),
            ('semester', 'crse_id', 'section'),
            ('semester', 'class_nbr') )


class Member(models.Model):
    """
    "Members" of the course.  Role indicates instructor/student/TA/etc.

    Includes dropped students and non-graded sections (labs/tutorials).  Often want to select with:
        Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(...)
    """
    ROLE_CHOICES = (
        ('STUD', 'Student'),
        ('TA', 'TA'),
        ('INST', 'Instructor'),
        ('APPR', 'Grade Approver'),
        ('DROP', 'Dropped'),
        #('AUD', 'Audit Student'),
    )
    REASON_CHOICES = (
        ('AUTO', 'Automatically added'),
        ('TRU', 'TRU/OU Distance Student'),
        ('TA', 'Additional TA'),
        ('TAIN', 'TA added by instructor'),
        ('INST', 'Additional Instructor'),
        ('UNK', 'Unknown/Other Reason'),
    )
    CAREER_CHOICES = (
        ('UGRD', 'Undergraduate'),
        ('GRAD', 'Graduate'),
        ('NONS', 'Non-Student'),
    )
    CAREERS = dict(CAREER_CHOICES)
    person = models.ForeignKey(Person, related_name="person")
    offering = models.ForeignKey(CourseOffering)
    role = models.CharField(max_length=4, choices=ROLE_CHOICES)
    credits = models.PositiveSmallIntegerField(null=False, default=3,
        help_text='Number of credits this course is worth.')
    career = models.CharField(max_length=4, choices=CAREER_CHOICES)
    added_reason = models.CharField(max_length=4, choices=REASON_CHOICES)
    labtut_section = models.CharField(max_length=4, null=True, blank=True,
        help_text='Section should be in the form "C101" or "D103".')
    config = JSONField(null=False, blank=False, default={}) # addition configuration stuff:
      # m.config['origsection']: The originating section (for crosslisted sections combined here)
      #     represented as a CourseOffering.slug
      #     default: self.offering (if accessed by m.get_origsection())

    def __unicode__(self):
        return "%s (%s) in %s" % (self.person.userid, self.person.emplid, self.offering,)
    def short_str(self):
        return "%s (%s)" % (self.person.name(), self.person.userid)
    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."
    def clean(self):
        """
        Validate unique_together = (('person', 'offering', 'role'),) UNLESS role=='DROP'
        """
        if self.role == 'DROP':
            return
        if not hasattr(self, 'person'):
            raise ValidationError('No person set.')
        others = Member.objects.filter(person=self.person, offering=self.offering, role=self.role)
        if self.pk:
            others = others.exclude(pk=self.pk)

        if others:
            raise ValidationError('There is another membership with this person, offering, and role.  These must be unique for a membership (unless role is "dropped").')

    def svn_url(self):
        "SVN URL for this member (assuming offering.uses_svn())"
        return urlparse.urljoin(settings.SVN_URL_BASE, repo_name(self.offering, self.person.userid))

    def get_origsection(self):
        """
        The real CourseOffering for this student (for crosslisted sections combined in this system).
        """
        if 'origsection' in self.config:
            return CourseOffering.objects.get(slug=self.config['origsection'])
        else:
            return self.offering
    
    class Meta:
        #unique_together = (('person', 'offering', 'role'),)  # now handled by self.clean()
        ordering = ['offering', 'person']
    def get_absolute_url(self):
        return reverse('grades.views.student_info', kwargs={'course_slug': self.offering.slug, 'userid': self.person.userid})


WEEKDAY_CHOICES = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
        )
WEEKDAYS = dict(WEEKDAY_CHOICES)
MEETINGTYPE_CHOICES = (
        ("LEC", "Lecture"),
        ("MIDT", "Midterm Exam"),
        ("EXAM", "Exam"),
        ("LAB", "Lab/Tutorial"),
        )
MEETINGTYPES = dict(MEETINGTYPE_CHOICES)
class MeetingTime(models.Model):
    offering = models.ForeignKey(CourseOffering, null=False)
    weekday = models.PositiveSmallIntegerField(null=False, choices=WEEKDAY_CHOICES,
        help_text='Day of week of the meeting')
    start_time = models.TimeField(null=False, help_text='Start time of the meeting')
    end_time = models.TimeField(null=False, help_text='End time of the meeting')
    start_day = models.DateField(null=False, help_text='Starting day of the meeting')
    end_day = models.DateField(null=False, help_text='Ending day of the meeting')
    room = models.CharField(max_length=20, help_text='Room (or other location) for the meeting')
    exam = models.BooleanField() # unused: use meeting_type instead
    meeting_type = models.CharField(max_length=4, choices=MEETINGTYPE_CHOICES, default="LEC")
    labtut_section = models.CharField(max_length=4, null=True, blank=True,
        help_text='Section should be in the form "C101" or "D103".  None/blank for the non lab/tutorial events.')
    def __unicode__(self):
        return "%s %s %s-%s" % (unicode(self.offering), WEEKDAYS[self.weekday], self.start_time, self.end_time)

    class Meta:
        ordering = ['weekday']
        #unique_together = (('offering', 'weekday', 'start_time'), ('offering', 'weekday', 'end_time'))
    
    def export_dict(self):
        """
        Produce dictionary of data about meeting time that can be serialized as JSON
        """
        d = {}
        d['weekday'] = self.weekday
        d['start_day'] = str(self.start_day)
        d['end_day'] = str(self.end_day)
        d['start_time'] = str(self.start_time)
        d['end_time'] = str(self.end_time)
        d['room'] = self.room
        d['type'] = self.meeting_type
        return d

class Role(models.Model):
    """
    Additional roles within the system (not course-related).
    """
    ROLE_CHOICES = (
        ('ADVS', 'Advisor'),
        ('FAC', 'Faculty Member'),
        ('SESS', 'Sessional Instructor'),
        ('COOP', 'Co-op Staff'),
        ('PLAN', 'Planning Administrator'),
        ('DISC', 'Discipline Case Administrator'),
        ('DICC', 'Discipline Case Filer (email BCC)'),
        ('ADMN', 'Departmental Administrator'),
        ('SYSA', 'System Administrator'),
        ('NONE', 'none'),
    )
    ROLES = dict(ROLE_CHOICES)
    person = models.ForeignKey(Person)
    role = models.CharField(max_length=4, choices=ROLE_CHOICES)
    department = models.CharField(max_length=4, help_text="Department where this role is relevant, or '!!!!' for global.")

    def __unicode__(self):
        return "%s (%s)" % (self.person, self.ROLES[str(self.role)])
    class Meta:
        unique_together = (('person', 'role'),)

