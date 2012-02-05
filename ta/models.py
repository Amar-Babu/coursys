from django.db import models
from coredata.models import Person, Member, CourseOffering, Semester, Unit
from jsonfield import JSONField
from courselib.json_fields import getter_setter #, getter_setter_2

class TUG(models.Model):
    """
    Time use guideline filled out by instructors
    
    Based on form in Appendix C (p. 73) of the collective agreement:
    http://www.tssu.ca/wp-content/uploads/2010/01/CA-2004-2010.pdf
    """	
    member = models.ForeignKey(Member, null=False)
    base_units = models.DecimalField(max_digits=4, decimal_places=2, blank=False, null=False)
    last_update = models.DateField(auto_now=True)
    config = JSONField(null=False, blank=False, default={}) # addition configuration stuff:
        # t.config['prep']: Preparation for labs/tutorials
        # t.config['meetings']: Attendance at planning meetings with instructor
        # t.config['lectures']: Attendance at lectures
        # t.config['tutorials']: Attendance at labs/tutorials
        # t.config['office_hours']: Office hours/student consultation
        # t.config['grading']
        # t.config['test_prep']: Quiz/exam preparation and invigilation
        # t.config['holiday']: Holiday compensation
        # Each of the above is a dictionary like:
        #     {
        #     'weekly': 2.0,
        #     'total': 26.0,
        #     'note': 'if more is required, we can revisit',
        #     }
        # t.config['other1']
        # t.config['other2']
        # As the other fields, but adding 'label'.
    
    prep = property(*getter_setter('prep'))
    meetings = property(*getter_setter('meetings'))
    lectures = property(*getter_setter('lectures'))
    tutorials = property(*getter_setter('tutorials'))
    office_hours = property(*getter_setter('office_hours'))
    grading = property(*getter_setter('grading'))
    test_prep = property(*getter_setter('test_prep'))
    holiday = property(*getter_setter('holiday'))
    other1 = property(*getter_setter('other1'))
    other2 = property(*getter_setter('other2'))
    
    regular_default = {'weekly': 0, 'total': 0, 'comment': ''}
    regular_fields = ['prep', 'meetings', 'lectures', 'tutorials', 
            'office_hours', 'grading', 'test_prep', 'holiday']
    other_default = {'label': '', 'weekly': 0, 'total': 0, 'comment': ''}
    other_fields = ['other1', 'other2']
    all_fields = regular_fields + other_fields
    
    defaults = dict([(field, regular_default) for field in regular_fields] + 
        [(field, other_default) for field in other_fields])
    
    # depicts the above comment in code
    config_meta = {'prep':{'label':'Preparation', 
                    'help':'1. Preparation for labs/tutorials'},
            'meetings':{'label':'Attendance at planning meetings', 
                    'help':'2. Attendance at planning/coordinating meetings with instructor'}, 
            'lectures':{'label':'Attendance at lectures', 
                    'help':'3. Attendance at lectures'}, 
            'tutorials':{'label':'Attendance at labs/tutorials', 
                    'help':u'4. Attendance at labs/tutorials'}, 
            'office_hours':{'label':'Office hours', 
                    'help':u'5. Office hours/student consultation/electronic communication'}, 
            'grading':{'label':'Grading', 
                    'help':u'6. Grading\u2020',
                    'extra':u'\u2020Includes grading of all assignments, reports and examinations.'}, 
            'test_prep':{'label':'Quiz/exam preparation and invigilation', 
                    'help':u'7. Quiz preparation/assist in exam preparation/Invigilation of exams'}, 
            'holiday':{'label':'Holiday compensation', 
                    'help':u'8. Statutory Holiday Compensation\u2021',
                    'extra':u'''\u2021To compensate for all statutory holidays which  
may occur in a semester, the total workload required will be reduced by one (1) 
hour for each base unit assigned excluding the additional 0.17 B.U. for 
preparation, e.g. 4 hours reduction for 4.17 B.U. appointment.'''}}
    
    #prep_weekly, set_prep_weekly = getter_setter_2('prep', 'weekly')

    def __unicode__(self):
        return "TA: %s  Base Units: %s" % (self.member.person.userid, self.base_units)

LEVEL_CHOICES = (
    ('NONE', 'None'),
    ('SOME', 'Some'),
    ('EXPR', 'Expert'),
)

class Skill(models.Model):
    """
    Skills an applicant specifies in their application.  Skills are specific to a department.
    """
    name = models.CharField(max_length=30)
    department = models.ForeignKey(Unit)
    level = models.CharField(max_length=4, choices=LEVEL_CHOICES)
    
    def __unicode__(self):
        return "Name: %s  Level: %s" % (self.name, self.level)


CATEGORY_CHOICES = (
        ('PHD', 'PhD'),
        ('MAS', 'Masters'),
        ('UGR', 'Undergrad'),
        ('EXT', 'External'),
        )

class TAApplication(models.Model):
    """
    TA application filled out by students
    """
    person = models.ForeignKey(Person)
    semester = models.ForeignKey(Semester)
    category = models.CharField(max_length=3, choices=CATEGORY_CHOICES)
    department = models.ForeignKey(Unit)
    base_units = models.DecimalField(max_digits=4, decimal_places=2)
    sin = models.PositiveIntegerField(unique=True)
    #Campus will be a csv separated field
    campus_prefered = models.CharField(max_length=30)
    skills = models.ManyToManyField(Skill) 
    experience =  models.TextField(blank=True, null=True,
        verbose_name="Experience",
        help_text='Describe any other experience that you think may be relevant to these courses.')
    course_load = models.TextField(verbose_name="Students intended course load.",
        help_text='Describe the intended course load of the semester being applied for.')
    other_support = models.TextField(blank=True, null=True,
        verbose_name="Other financial support",
        help_text='Describe any other funding you expect to receive this semester (grad students only).')
    comments = models.TextField(verbose_name="Additional comments", blank=True, null=True)
    
    class Meta:
        unique_together = (('person', 'semester', 'department'),)
    def __unicode__(self):
        return "Person: %s  Semester: %s" % (self.person, self.semester)

class TA_Job_Posting(models.Model):
    """
    Courses Which need a TA
    """
    semester = models.ForeignKey(Semester)
    department = models.ForeignKey(Unit)
    #course = models.ForeignKey(CourseOffering)
    def __unicode__(self):
        return "deparment: %s  Semester: %s" % (self.department, self.semester)

    
#what are the appointment categories?
"""APPOINTMENT_CHOICES = (
        ('GTA1', 'GTA1: ') 
        )"""

class TAContract(models.Model):
    """    
    TA Contract
    """
    person = models.ForeignKey(Person)
    department = models.ForeignKey(Unit)
    appt_start = models.DateField()
    appt_end = models.DateField()
    pay_start = models.DateField()
    pay_end = models.DateField()
    position_number = models.DecimalField(max_digits=5, decimal_places=0)
    #appt_category = models.CharField(max_length=4, choices=APPOINTMENT_CHOICES)
    init_appt = models.BooleanField(verbose_name="Initial appointment to this position")
    other_appt = models.BooleanField(verbose_name="Reappointment to same position or revision to appointment")
    sin = models.PositiveIntegerField(unique=True)
    
    ##need to clarify how to deal with courses and BU to calculate salary and scholarship
    
    remarks = models.TextField(verbose_name="Remarks")
    deadline = models.DateField()
    appt_cond = models.BooleanField()
    appt_tssu = models.BooleanField()


TAKEN_CHOICES = (
        ('YES', 'Yes: this course at SFU'),
        ('SIM', 'Yes: a similar course elsewhere'),
        ('KNO', 'No, but I know the course material'),
        ('NO', 'No, I don\'t know the material well'),
        )
EXPER_CHOICES = (
        ('TST', 'Placeholder option'),
        )



class CoursePreference(models.Model):
    app = models.ForeignKey(TAApplication)
    course = models.ForeignKey(CourseOffering)
    taken = models.CharField(max_length=3, choices=TAKEN_CHOICES, blank=False, null=False)
    exper = models.CharField(max_length=3, choices=EXPER_CHOICES, blank=False, null=False)

    def __unicode__(self):
        return "Course: %s  Taken: %s" % (self.course, self.taken)
