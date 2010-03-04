import copy
from django.db import models
from grades.models import NumericActivity, NumericGrade, LetterGrade 
from groups.models import Group, GroupMember

class ActivityComponent(models.Model):
    """    
    Markable Component of a numeric activity   
    """
    numeric_activity = models.ForeignKey(NumericActivity, null = False)
    max_mark = models.DecimalField(max_digits=5, decimal_places=2, null = False)
    title = models.CharField(max_length=30, null = False)
    description = models.TextField(max_length = 200, null = True, blank = True)
    position = models.IntegerField(null = True, default = 0, blank =True)
    
    # set this flag if it is deleted by the user
    deleted = models.BooleanField(null = False, db_index = True, default = False)
    def __unicode__(self):        
        return self.title
    class Meta:
        verbose_name_plural = "Activity Marking Components"
        ordering = ['numeric_activity', 'deleted', 'position']
         
class CommonProblem(models.Model):
    """
    Common problem of a activity component. One activity component can have several common problems.
    """
    activity_component = models.ForeignKey(ActivityComponent, null = False)
    title = models.CharField(max_length=30, null = False)
    penalty = models.IntegerField(null = True, default = 0, blank = True)
    description = models.TextField(max_length = 200, null = True, blank = True)
    deleted = models.BooleanField(null = False, db_index = True, default = False)
    def __unicode__(self):
        return "common problem %s for %s" % (self.title, self.activity_component)
     
class ActivityMark(models.Model):
    """
    General Marking class for one numeric activity 
    """    
    overall_comment = models.TextField(null = True, max_length = 1000, blank = True)
    late_penalty = models.IntegerField(null = True, default = 0, blank = True)
    mark_adjustment = models.IntegerField(null = True, default = 0, blank = True)
    mark_adjustment_reason = models.TextField(null = True, max_length = 1000, blank = True)
    file_attachment = models.FileField(null = True, upload_to = "student&group/files/%Y %m %d %H:%M:%S'", blank=True)#TODO: need to add student name or group name to the path  
     
    def __unicode__(self):
        return "Supper object containing additional info for marking"
    
    def copyFrom(self, obj):
        """
        Copy information form another ActivityMark object
        """
        self.late_penalty = obj.late_penalty
        self.overall_comment = obj.overall_comment
        self.mark_adjustment = obj.mark_adjustment
        self.mark_adjustment_reason = obj.mark_adjustment_reason
        self.file_attachment = obj.file_attachment
    
    def setMark(self, grade):
        pass


class StudentActivityMark(ActivityMark):
    """
    Marking of one student on one numeric activity 
    """        
    numeric_grade = models.OneToOneField(NumericGrade, null = False)
       
    def __unicode__(self):
        # get the student and the activity
        student = self.numeric_grade.member.person
        activity = self.numeric_grade.activity      
        return "Marking for student [%s] for activity [%s]" %(student, activity)   
      
    def setMark(self, grade):
        """         
        Set the mark
        """
        self.numeric_grade.value = grade
        self.numeric_grade.flag = 'GRAD'
        self.numeric_grade.save()            
        
        
class GroupActivityMark(ActivityMark):
    """
    Marking of one group on one numeric activity
    """
    group = models.ForeignKey(Group, null = False) 
    numeric_activity = models.ForeignKey(NumericActivity, null = False)
    # The grade can be also found through any group memeber's numeric_grade object
    # Keep a copy here just for fast query for the grade given the group and the activity
    grade = models.DecimalField(max_digits=5, decimal_places=2)
    
    class Meta:
        unique_together = (('group', 'numeric_activity'),)
    
    def __unicode__(self):
        return "Marking for group [%s] for activity [%s]" %(self.group,)#TODO: need some way to find the activity
    
    def setMark(self, grade):
        self.grade = grade        
        #assign mark for each member in the group
        group_members = self.group.groupmember_set.filter(confirmed = True)
        for g_member in group_members:
            try: 
                ngrade = NumericGrade.objects.get(activity = self.numeric_activity, member = g_member.student)                  
            except NumericGrade.DoesNotExist: #if the  NumericalGrade does not exist yet, create a new one
                ngrade = NumericGrade(activity = self.numeric_activity, member = g_member.student)
            ngrade.value = grade
            ngrade.flag = 'GRAD'
            ngrade.save()            
            
 
class ActivityComponentMark(models.Model):
    """
    Marking of one particular component of an activity for one student  
    Stores the mark the student gets for the component
    """
    activity_mark = models.ForeignKey(ActivityMark, null = False)    
    activity_component = models.ForeignKey(ActivityComponent, null = False)
    value = models.DecimalField(max_digits=5, decimal_places=2)
    comment = models.TextField(null = True, max_length=1000, blank=True)
    
    def __unicode__(self):
        # get the student and the activity
        return "Marking for [%s]" %(self.activity_component,)
        
    class Meta:
        unique_together = (('activity_mark', 'activity_component'),)

from django.forms import ModelForm
class ActivityComponentMarkForm(ModelForm):
    class Meta:
        model = ActivityComponentMark            
        fields = ['comment', 'value']
        exclude = ['activity_mark', 'activity_component']

        
class ActivityMarkForm(ModelForm):
    class Meta:
        model = ActivityMark
        fields = ['late_penalty', 'mark_adjustment', 'mark_adjustment_reason', 'overall_comment', \
                  'file_attachment']

        
def copyCourseSetup(course_copy_from, course_copy_to):
    # copy course setup from one to another
    # TODO: code for copying other kinds of activity can be added on demand
    for numeric_activity in NumericActivity.objects.filter(offering = course_copy_from):
        new_numeric_activity = copy.deepcopy(numeric_activity)
        new_numeric_activity.id = None
        new_numeric_activity.pk = None
        new_numeric_activity.offering = course_copy_to
        new_numeric_activity.save()
        print "Activity %s is copied" % new_numeric_activity
        for activity_component in ActivityComponent.objects.filter(numeric_activity = numeric_activity):
            new_activity_component = copy.deepcopy(activity_component)
            new_activity_component.id = None
            new_activity_component.pk = None
            new_activity_component.numeric_activity = new_numeric_activity
            new_activity_component.save()
            print "component %s is copied" % new_activity_component

    
    
