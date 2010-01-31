from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from coredata.models import Member, CourseOffering,Person
from courselib.auth import requires_course_by_slug
from grades.models import ACTIVITY_STATUS

@login_required
def index(request):
    # TODO: should distinguish student/TA/instructor roles in template
    userid = request.user.username
    memberships = Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(person__userid=userid) \
            .select_related('offering','person','offering__semester')
    return render_to_response("grades/index.html", {'memberships': memberships}, context_instance=RequestContext(request))
    
    
# Todo: Role authentication required
@requires_course_by_slug
def course(request, course_slug):
    """
    Course front page
    """
    course = CourseOffering.objects.get(slug=course_slug)
    activities = course.activity_set.all()
    context = {'course': course, 'activities': activities}
    return render_to_response("grades/course.html", context,
                              context_instance=RequestContext(request))



@login_required
def student_view(request, student_id):
    target_student = Person.objects.get(userid = student_id )
    enrollment= Member.objects.filter(person=target_student).exclude(role="DROP")
    context ={'student_id':student_id,'enrollment':enrollment,'student':target_student}
    #student's view:
    if target_student.userid == request.user.username:      
        return render_to_response('grades/student_view.html', context,
                                  context_instance=RequestContext(request))


@requires_course_by_slug
def student_grade(request,student_id,course_slug):
    course = CourseOffering.objects.get(slug=course_slug)
    activities = course.activity_set.all()
    
    context = {'student_id':student_id, 'course': course, 'activities': activities}
    return render_to_response("grades/student_grade.html", context,
                              context_instance=RequestContext(request))

