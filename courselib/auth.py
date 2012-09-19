from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.http import urlquote
from coredata.models import Role, CourseOffering, Member

try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps

# adapted from django_cas.decorators: returns 403 on failure, and passes **kwargs to test_func.
def user_passes_test(test_func, login_url=None,
                     redirect_field_name=REDIRECT_FIELD_NAME):
    """Replacement for django.contrib.auth.decorators.user_passes_test that
    returns 403 Forbidden if the user is already logged in.
    """

    if not login_url:
        from django.conf import settings
        login_url = settings.LOGIN_URL

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if test_func(request, **kwargs):
                return view_func(request, *args, **kwargs)
            elif request.user.is_authenticated():
                return ForbiddenResponse(request)
            else:
                path = '%s?%s=%s' % (login_url, redirect_field_name,
                                     urlquote(request.get_full_path()))
                return HttpResponseRedirect(path)
        return wrapper
    return decorator


def HttpError(request, status=404, title="Not Found", error="The requested resource cannot be found.", errormsg=None):
    resp = render_to_response('error.html', {'title': title, 'error': error, 'errormsg': errormsg}, context_instance=RequestContext(request))
    resp.status_code = status
    return resp

def ForbiddenResponse(request, errormsg=None):
    return HttpError(request, status=403, title="Forbidden", error="You do not have permission to access this resource.", errormsg=errormsg)

def NotFoundResponse(request, errormsg=None):
    return HttpError(request, status=404, title="Not Found", error="The requested resource cannot be found.", errormsg=errormsg)

def is_advisor(request, **kwargs):
    """
    Return True is the given user is an advisor
    """
    perms = Role.objects.filter(person__userid=request.user.username, role='ADVS')
    count = perms.count()
    return count>0

def requires_advisor(function=None, login_url=None):
    """
    Allows access if user is an advisor.
    """
    actual_decorator = user_passes_test(is_advisor, login_url=login_url)
    if function:
        return  actual_decorator(function)
    else:
        return actual_decorator

def has_global_role(role, request, **kwargs):
    """
    Return True is the given user has the specified role
    """
    perms = Role.objects.filter(person__userid=request.user.username, role=role, unit__label="UNIV")
    count = perms.count()
    return count>0

def requires_role(role, login_url=None):
    """
    Allows access if user has the given role in ANY unit
    """
    def has_this_role(req, **kwargs):
        return has_role(role, req, **kwargs)
        
    actual_decorator = user_passes_test(has_this_role, login_url=login_url)
    return actual_decorator

def has_role(role, request, **kwargs):
    """
    Return True is the given user has the specified role in ANY unit
    """
    roles = Role.objects.filter(person__userid=request.user.username, role=role)
    request.units = [r.unit for r in roles]
    count = roles.count()
    return count>0

def requires_global_role(role, login_url=None):
    """
    Allows access if user has the given role
    """
    def has_this_role(req, **kwargs):
        return has_global_role(role, req, **kwargs)
        
    actual_decorator = user_passes_test(has_this_role, login_url=login_url)
    return actual_decorator

def is_course_member_by_slug(request, course_slug, **kwargs):
    """
    Return True if user is any kind of member (non-dropped) from course indicated by 'course_slug' keyword.
    """
    memberships = Member.objects.exclude(role="DROP", offering__component="CAN").filter(offering__slug=course_slug, person__userid=request.user.username, offering__graded=True)
    count = memberships.count()
    return count>0

def requires_course_by_slug(function=None, login_url=None):
    """
    Allows access if user is any kind of member (non-dropped) from course indicated by 'course_slug'.
    """
    actual_decorator = user_passes_test(is_course_member_by_slug, login_url=login_url)
    if function:
        return actual_decorator(function)
    else:
        return actual_decorator

def is_course_student_by_slug(request, course_slug, **kwargs):
    """
    Return True if user is student from course indicated by 'course_slug' keyword.
    """
    memberships = Member.objects.filter(offering__slug=course_slug, person__userid=request.user.username, role="STUD", offering__graded=True).exclude(offering__component="CAN")
    count = memberships.count()
    return count>0

def requires_course_student_by_slug(function=None, login_url=None):
    """
    Allows access if user is student from course indicated by 'course_slug'.
    """
    actual_decorator = user_passes_test(is_course_student_by_slug, login_url=login_url)
    if function:
        return actual_decorator(function)
    else:
        return actual_decorator

def is_course_staff_by_slug(request, course_slug, **kwargs):
    """
    Return True if user is a staff member (instructor, TA, approver) from course indicated by 'course_slug' keyword.
    """
    memberships = Member.objects.filter(offering__slug=course_slug, person__userid=request.user.username,
            role__in=['INST', 'TA', 'APPR'], offering__graded=True).exclude(offering__component="CAN")
    count = memberships.count()
    return count>0

def requires_course_staff_by_slug(function=None, login_url=None):
    """
    Allows access if user is a staff member (instructor, TA, approver) from course indicated by 'course_slug'.
    """
    actual_decorator = user_passes_test(is_course_staff_by_slug, login_url=login_url)
    if function:
        return actual_decorator(function)
    else:
        return actual_decorator

def is_course_instr_by_slug(request, course_slug, **kwargs):
    """
    Return True if user is a staff member (instructor, TA, approver) from course indicated by 'course_slug' keyword.
    """
    memberships = Member.objects.filter(offering__slug=course_slug, person__userid=request.user.username,
            role__in=['INST', 'APPR'], offering__graded=True).exclude(offering__component="CAN")
    count = memberships.count()
    return count>0

def requires_course_instr_by_slug(function=None, login_url=None):
    """
    Allows access if user is a staff member (instructor, TA, approver) from course indicated by 'course_slug'.
    """
    actual_decorator = user_passes_test(is_course_instr_by_slug, login_url=login_url)
    if function:
        return actual_decorator(function)
    else:
        return actual_decorator

def is_dept_admn_by_slug(request, course_slug, **kwargs):
    offering = CourseOffering.objects.get(slug=course_slug)
    return Role.objects.filter(person__userid=request.user.username, role='ADMN',
            unit=offering.owner).count() > 0

def requires_course_staff_or_dept_admn_by_slug(function=None, login_url=None):
    """
    Allows access if user is a staff member (instructor, TA, approver) from course indicated by 'course_slug'
    *or* if they are the departmental admin for the course's department 
    """
    def test_func(request, **kwargs):
        return is_course_staff_by_slug(request, **kwargs) or is_dept_admn_by_slug(request, **kwargs)
    actual_decorator = user_passes_test(test_func, login_url=login_url)
    if function:
        return actual_decorator(function)
    else:
        return actual_decorator


def is_discipline_user(request, course_slug, **kwargs):
    """
    Return True if user is a discipline user (instructor, approver or discipline admin)
    """
    # departmental discipline admins    
    roles = set()
    offerings = CourseOffering.objects.filter(slug=course_slug)
    if offerings:
        offering = offerings[0]
    else:
        return False

    perms = Role.objects.filter(person__userid=request.user.username, role='DISC', unit=offering.owner).count()
    if perms>0:
        roles.add("DEPT")

    # instructors
    memberships = Member.objects.filter(offering__slug=course_slug, person__userid=request.user.username,
            role__in=['INST', 'APPR']).exclude(offering__component="CAN")
    count = memberships.count()
    
    if count>0:
        roles.add("INSTR")
    
    # record why we have permission in the session
    request.session['discipline-'+course_slug] = roles
    return bool(roles)


def requires_discipline_user(function=None, login_url=None):
    """
    Allows access if user is a discipline user for this case
    """
    actual_decorator = user_passes_test(is_discipline_user, login_url=login_url)
    if function:
        return actual_decorator(function)
    else:
        return actual_decorator


def is_instructor(request, **kwargs):
    """
    Return True if the user is an instructor
    """
    roles = Role.objects.filter(person__userid=request.user.username, role__in=['FAC','SESS','COOP'])
    perms = roles.count()
    request.units = [r.unit for r in roles]
    return perms>0

def requires_instructor(function=None, login_url=None):
    """
    Allows access if user is an instructor.
    """
    actual_decorator = user_passes_test(is_instructor, login_url=login_url)
    if function:
        return actual_decorator(function)
    else:
        return actual_decorator

def is_techstaff(request, **kwargs):
    """
    Return True if the user is part of the tech staff
    """
    roles = Role.objects.filter(person__userid=request.user.username, role__in=['TECH'])
    perms = roles.count()
    request.units = [r.unit for r in roles]
    return perms>0

def requires_techstaff(function=None, login_url=None):
    """
    Allows access if user is part of the tech staff.
    """
    actual_decorator = user_passes_test(is_techstaff, login_url=login_url)
    if function:
        return actual_decorator(function)
    else:
        return actual_decorator