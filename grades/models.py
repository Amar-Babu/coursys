from django.db import models
from autoslug import AutoSlugField
from timezones.fields import TimeZoneField
from coredata.models import Member, CourseOffering
from dashboard.models import *
from django.core.urlresolvers import reverse
from contrib import messages
from django.core.cache import cache
from datetime import datetime, timedelta

FLAG_CHOICES = [
    ('NOGR', 'no grade'),
    ('GRAD', 'graded'), 
    ('CALC', 'calculated'), 
    ('EXCU', 'excused'), 
    ('DISH', 'academic dishonesty') ]
FLAGS = dict(FLAG_CHOICES)

ACTIVITY_STATUS_CHOICES = [
    ('RLS', 'released'),
    ('URLS', 'unreleased'),
    ('INVI', 'invisible') ]
ACTIVITY_STATUS = dict(ACTIVITY_STATUS_CHOICES)

LETTER_GRADE_CHOICES = [
    ('A+', 'A+ - Excellent performance'),
    ('A', 'A - Excellent performance'),
    ('A-', 'A- - Excellent performance'),
    ('B+', 'B+ - Good performance'),
    ('B', 'B - Good performance'),
    ('B-', 'B- - Good performance'),
    ('C+', 'C+ - Satisfactory performance'),
    ('C', 'C - Satisfactory performance'),
    ('C-', 'C- - Marginal performance'),
    ('D', 'D - Marginal performance'),
    ('F', 'F - Fail(Unsatisfactory performance)'),
    ('FD', 'FD - Fail(Academic discipline)'),
    ('N', 'N - Did not write exam or did not complete course'),
    ('P', 'P - Satisfactory performance or better (pass, ungraded)'),
    ('W', 'W - Withdrawn'),
    ('AE', 'AE - Aegrotat standing, compassionate pass'),
    ('AU', 'AU - Audit'),
    ('CC', 'CC - Course challenge'),
    ('CF', 'CF - Course challenge fail'),
    ('CN', 'CN - Did not complete challenge'),
    ('CR', 'CR - Credit without grade'),
    ('FX', 'FX - Formal exchange'),
    ('WD', 'WD - Withdrawal'),
    ('WE', 'WE - Withdrawal under extenuating circumstances'),
    ('DE', 'DE - Deferred grade'),
    ('GN', 'GN - Grade not reported'),
    ('IP', 'IP - In progress') ]
LETTER_GRADE = dict(LETTER_GRADE_CHOICES)

class Activity(models.Model):
    """
    Generic activity (i.e. column in the gradebook that can have a value assigned for each student).
    This should never be instantiated directly: only its sublcasses should.
    """
    name = models.CharField(max_length=30, db_index=True, help_text='Name of the activity.')
    short_name = models.CharField(max_length=15, db_index=True, help_text='Short-form name of the activity.')
    slug = AutoSlugField(populate_from='short_name', null=False, editable=False, unique_with='offering')
    status = models.CharField(max_length=4, null=False, choices=ACTIVITY_STATUS_CHOICES, help_text='Activity status.')
    due_date = models.DateTimeField(null=True, help_text='Activity due date')
    percent = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    position = models.PositiveSmallIntegerField(help_text="The order of displaying course activities.")
    group = models.BooleanField(null=False, default=False)
    deleted = models.BooleanField(null = False, db_index = True, default=False)
    
    offering = models.ForeignKey(CourseOffering)

    def __unicode__(self):
        return "%s - %s" % (self.offering, self.name)
    def __cmp__(self, other):
        return cmp(self.position, other.position)
    def get_absolute_url(self):
        return reverse('grades.views.activity_info', kwargs={'course_slug': self.offering.slug, 'activity_slug': self.slug})
    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."
    class Meta:
        verbose_name_plural = "activities"
        ordering = ['deleted', 'position']
    
    def display_label(self):
        if self.percent:
            return "%s (%s%%)" % (self.name, self.percent)
        else:
            return "%s" % (self.name)
        
    def display_grade_student(self, student):
        """
        String representing grade for this student
        """
        if self.status=="URLS":
            return u'\u2014'
        elif self.status=="INVI":
            raise RuntimeError, "Can't display invisible grade."
        else:
            return self.display_grade_visible(student)

    def display_grade_staff(self, student):
        """
        String representing grade for this student
        """
        return self.display_grade_visible(student)

    def markable(self):
        """
        Returns True if this activity is "markable".  i.e. has any marking components defined.
        """
        return self.activitycomponent_set.all().count() != 0

    def submitable(self):
        """
        Returns True if this activity is "submittable".
        i.e. has any submission components defined and within 30 days after due date
        """
        if self.no_submit_too_old():
            return False
        return self.submissioncomponent_set.filter(deleted=False).count() != 0
    def no_submit_too_old(self):
        """
        Returns True if this activity is not submittable because it is too old
        """
        if self.submissioncomponent_set.filter(deleted=False).count() == 0:
            return False
        now = datetime.now()
        if (now - self.due_date > timedelta(days=30)):
            return True
        return False
    


class NumericActivity(Activity):
    """
    Activity with a numeric mark
    """
    max_grade = models.DecimalField(max_digits=5, decimal_places=2)
    

    class Meta:
        verbose_name_plural = "numeric activities"

    def display_grade_visible(self, student):
        grades = NumericGrade.objects.filter(activity=self, member__person=student)
        if len(grades)==0:
            grade = u'\u2014'
        else:
            grade = grades[0].value
        return "%s/%s" % (grade, self.max_grade)

    def save(self, force_insert=False, force_update=False, newsitem=True, *args, **kwargs):
        # get old status so we can see if it's newly-released
        try:
            old = Activity.objects.get(id=self.id)
            self.group = old.group
        except Activity.DoesNotExist:
            old = None
        super(NumericActivity, self).save(*args, **kwargs)

        if newsitem and self.status == 'RLS' and old != None and old.status != 'RLS':
            # newly-released grades: create news items
            class_list = Member.objects.exclude(role="DROP").filter(offering=self.offering)
            for m in class_list:
                n = NewsItem(user=m.person, author=None, course=self.offering,
                    source_app="grades", title="%s grade released" % (self.name), 
                    content='Grades have been released for "%s in %s":%s.' \
                      % (self.name, self.offering.name(), self.get_absolute_url()),
                    url=self.get_absolute_url()
                    )
                n.save()


class LetterActivity(Activity):
    """
    Activity with a letter grade
    """
    class Meta:
        verbose_name_plural = "letter activities"
    
    def display_grade_visible(self, student):
        grades = LetterGrade.objects.filter(activity=self, member__person=student)
        if len(grades)==0:
            grade = u'\u2014'
        else:
            grade = str(grades[0].letter_grade)
        return grade

    def save(self, force_insert=False, force_update=False, newsitem=True, *args, **kwargs):
        # get old status so we can see if it's newly-released
        old = Activity.objects.filter(id=self.id)
        if old:
            old = old[0]
        else:
            old = None
        super(LetterActivity, self).save(*args, **kwargs)

        if newsitem and old and self.status == 'RLS' and old.status != 'RLS':
            # newly-released grades: create news items
            class_list = Member.objects.exclude(role="DROP").filter(offering=self.offering)
            for m in class_list:
                content = "Grades have been released for %s in %s. " \
                      % (self.name, self.offering.name())
                
                n = NewsItem(user=m.person, author=None, course=self.offering,
                    source_app="grades", title="%s grade released" % (self.name), 
                    content=content,
                    url=reverse('grades.views.course_info', kwargs={'course_slug':self.offering.slug})
                    )
                n.save()


class CalNumericActivity(NumericActivity):
    """
    Activity with a calculated numeric grade which is the final numeric grade of the course offering
    """
    formula = models.CharField(max_length=250, help_text='parsed formula to calculate final numeric grade')

    class Meta:
        verbose_name_plural = "cal numeric activities"

class CalLetterActivity(LetterActivity):
    """
    Activity with a calculated letter grade which is the final letter grade of the course offering
    """
    numeric_activity = models.ForeignKey(NumericActivity, related_name='numeric_source_set')
    exam_activity = models.ForeignKey(Activity, null=True, related_name='exam_set')
    letter_cutoff_formula = models.CharField(max_length=250, help_text='parsed formula to calculate final letter grade')
    
    class Meta:
        verbose_name_plural = 'cal letter activities'





# list of all subclasses of Activity:
# MUST have deepest subclasses first (i.e. nothing *after* a class is one of its subclasses)
ACTIVITY_TYPES = [CalNumericActivity, NumericActivity, CalLetterActivity, LetterActivity]

def all_activities_filter(**kwargs):
    """
    Return all activities as their most specific class.
    
    This isn't pretty, but it will do the job.
    """
    #key = "all_act_filt" +  '_'.join(k + "-" + str(kwargs[k]) for k in kwargs)
    #data = cache.get(key)
    #if data:
    #    return data

    activities = [] # list of activities
    found = set() # keep track of what has been found so we can exclude less-specific duplicates.
    for ActivityType in ACTIVITY_TYPES:
        acts = list(ActivityType.objects.filter(deleted=False, **kwargs))
        activities.extend( (a for a in acts if a.id not in found) )
        found.update( (a.id for a in acts) )

    activities.sort()
    #cache.set(key, activities, 60)
    return activities


class NumericGrade(models.Model):
    """
    Individual numeric grade for a NumericActivity.
    """
    activity = models.ForeignKey(NumericActivity, null=False)
    member = models.ForeignKey(Member, null=False)

    value = models.DecimalField(max_digits=5, decimal_places=2, default = 0, null=False)
    flag = models.CharField(max_length=4, null=False, choices=FLAG_CHOICES, help_text='Status of the grade', default = 'NOGR')
    
    def __unicode__(self):
        return "Member[%s]'s grade[%s] for [%s]" % (self.member.person.userid, self.value, self.activity)

    def display_staff(self):
        if self.flag == 'NOGR':
            return u'\u2014'
        else:
            return "%s/%s" % (self.value, self.activity.max_grade)

    def save(self, newsitem=True):
        super(NumericGrade, self).save()
        if self.activity.status == "RLS" and newsitem and self.flag != "NOGR":
            # new grade assigned, generate news item only if the result is released
            n = NewsItem(user=self.member.person, author=None, course=self.activity.offering,
                source_app="grades", title="%s grade available" % (self.activity.name), 
                content='A "new grade for %s":%s in %s is available.' 
                  % (self.activity.name, self.activity.get_absolute_url(), self.activity.offering.name()),
                url=self.activity.get_absolute_url())
            n.save()
     
    def save_status_flag(self, new_flag, comment):
        """
        status changed, generate the news item, regardless the grade of released or not
        """
        self.flag = new_flag
        super(NumericGrade, self).save()
        # link to activity information page ?
        info_url = reverse("grades.views.activity_info", kwargs={'course_slug':self.activity.offering.slug, 'activity_slug':self.activity.slug})
        n = NewsItem(user=self.member.person, author=None, course=self.activity.offering,
            source_app="grades", title="%s grade status changed" % (self.activity.name), 
            content = '"grade status changed to *{color:red}%s*":%s for %s in %s\nComment: %s' %
                      (FLAGS[self.flag], info_url, self.activity.name, self.activity.offering.name(), comment),
            url= info_url)
        n.save()   

    def get_absolute_url(self):
        """        
        for regular numeric activity return the mark summary page
        but for calculate numeric activity only return the activity information page
        because there is no associated mark summary record
        """
        if CalNumericActivity.objects.filter(id=self.activity.id):
            return reverse("grades.views.activity_info", kwargs={'course_slug':self.activity.offering.slug, 'activity_slug':self.activity.slug})
        else:
            return reverse("marking.views.mark_summary_student", kwargs={'course_slug':self.activity.offering.slug, 'activity_slug':self.activity.slug, 'userid':self.member.person.userid})
    class Meta:
        unique_together = (('activity', 'member'),)
    
class LetterGrade(models.Model):
    """
    Individual letter grade for a LetterActivity
    """
    activity = models.ForeignKey(LetterActivity, null=False)
    member = models.ForeignKey(Member, null=False)
    
    letter_grade = models.CharField(max_length=2, null=False, choices=LETTER_GRADE_CHOICES)
    flag = models.CharField(max_length=4, null=False, choices=FLAG_CHOICES, help_text='Status of the grade', default = 'NOGR')
    
    def __unicode__(self):
        return "Member[%s]'s letter grade[%s] for [%s]" % (self.member.person.userid, self.letter_grade, self.activity)

    def display_staff(self):
        if self.flag == 'NOGR':
            return u'\u2014'
        else:
            return "%s" % (self.letter_grade)
    
    def save(self, newsitem=True):
        super(NumericGrade, self).save()
        if self.activity.status=="RLS" and newsitem and self.flag != "NOGR":
            # new grade assigned, generate news item only if the result is released
            n = NewsItem(user=self.member.person, author=None, course=self.activity.offering,
                source_app="grades", title="%s grade available" % (self.activity.name), 
                content='A "new grade for %s":%s in %s is available.' 
                  % (self.activity.name, self.get_absolute_url(), self.activity.offering.name()),
                url=self.get_absolute_url())
            n.save()
            
    class Meta:
        unique_together = (('activity', 'member'), )
