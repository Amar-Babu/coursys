from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from courselib.auth import *
from grades.models import ACTIVITY_STATUS, all_activities_filter, Activity
from groups.models import *
from submission.models import GroupSubmission, StudentSubmission
from datetime import datetime

from dashboard.views import _get_memberships, _get_news_list, _get_roles

@login_required
def index(request):
    userid = request.user.username
    memberships = _get_memberships(userid)
    news_list = _get_news_list(userid, 1)
    roles = _get_roles(userid)

    context = {'memberships': memberships ,'news_list': news_list, 'roles': roles}
    return render_to_response('mobile/dashboard.html',
        context, context_instance=RequestContext(request));

@login_required
def course_info(request,course_slug):
    if is_course_student_by_slug(request.user, course_slug):
        return _course_info_student(request, course_slug)
    elif is_course_staff_by_slug(request.user, course_slug):
        return _course_info_staff(request, course_slug)
    else:
        return ForbiddenResponse(request)

def _course_info_student(request, course_slug):
    return HttpResponse('Student View')

def _course_info_staff(request, course_slug):
    """
    Course front page
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(offering=course)

    activities_info = []
    for activity in activities:
        count = 0 # group/student count, based on activity type
        student_count = 0 # count of all students
        sub_count= 0 # count of submissions
        grade_count = 0 # count of graded students
        
        if activity.due_date and activity.due_date < datetime.now():
            passdue = True
        else:
            passdue = False

        # count number of students
        students = Member.objects.filter(role="STUD", offering=activity.offering).select_related('person')
        for student in students:
            student_count = student_count + 1
            if len(StudentSubmission.objects.filter(member=student))!=0:
                sub_count = sub_count + 1
        
        # if group, count group submission
        if activity.group:
            groups = Group.objects.filter(courseoffering=course)
            for group in groups:
                # count how many groups have submitted for this activity
                groupMembers = GroupMember.objects.filter(group=group, activity=activity, confirmed=True)
                if(len(groupMembers)!=0):
                    count = count + 1
                    if len(GroupSubmission.objects.filter(group=group, activity=activity))!=0:
                        sub_count = sub_count + 1
        else:
            count = student_count

        # count number of graded students
        if activity.is_numeric():
            grades_list = activity.numericgrade_set.filter().select_related('member__person', 'activity')
        else:
            grades_list = activity.lettergrade_set.filter().select_related('member__person', 'activity')
        grade_count = len(grades_list)

        print count, sub_count, grade_count
        #TODO: Calculate how many student has submitted the assignment
        activities_info.append({'activity':activity, 'count':count,'sub_count':sub_count, 'student_count':student_count,
                            'grade_count': grade_count, 'passdue':passdue})
        

    context = {'course': course, 'activities_info': activities_info}
    return render_to_response("mobile/course_info_staff.html", context,
                              context_instance=RequestContext(request))
