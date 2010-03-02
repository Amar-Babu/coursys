from django.contrib.auth.decorators import login_required
from coredata.models import Member, CourseOffering
from django.shortcuts import render_to_response, get_object_or_404#, redirect
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, Http404
from courselib.auth import requires_course_by_slug,requires_course_staff_by_slug
from submission.forms import *
from dashboard.templatetags.course_display import display_form
from courselib.auth import is_course_staff_by_slug, is_course_member_by_slug
from submission.models import select_all_components
from django.core.urlresolvers import reverse

@login_required
def index(request):
    userid = request.user.username
    memberships = Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(person__userid=userid) \
            .select_related('offering','person','offering__semester')
    return render_to_response("submission/index.html", {'memberships': memberships}, context_instance=RequestContext(request))


@login_required
def show_components(request, course_slug, activity_slug):
    #if course staff
    if is_course_staff_by_slug(request.user, course_slug):
        return _show_components_staff(request, course_slug, activity_slug)
    #else course member
    elif is_course_member_by_slug(request.user, course_slug):
        return _show_components_student(request, course_slug, activity_slug)
    #else not found, return 403
    else:
        resp = render_to_response('403.html', context_instance=RequestContext(request))
        resp.status_code = 403
        return resp
    
#student submission main page
#@requires_course_by_slug
def _show_components_student(request, course_slug, activity_slug):
    """
    Show all the component submission history of this activity
    """
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(course.activity_set,slug = activity_slug)
    component_list = select_all_components(activity)
    all_submitted = select_students_submitted_components(activity, request.user.username)

    # pair<component, latest_submission>
    submitted_pair_list = []
    for component in component_list:
        pair = []
        pair.append(component)
        c = [sub for sub in all_submitted if sub.component == component]
        if len(c) == 0:
            pair.append(None)
        else:
            pair.append(c[0])
        submitted_pair_list.append(pair)
    
    return render_to_response("submission/component_view.html",
        {"course":course, "activity":activity, "submitted_pair":submitted_pair_list},
        context_instance=RequestContext(request))
        
#student's submission page
@requires_course_by_slug
def add_submission(request, course_slug, activity_slug):
    """
    enable student to upload files to a activity
    """
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(course.activity_set,slug = activity_slug)
    component_list = select_all_components(activity)
    component_list.sort()
    component_form_list=[]
    for component in component_list:
        if component.get_type() == 'URL':
            pair = []
            pair.append(component)
            pair.append(SubmittedURLForm(prefix=component.id))
            component_form_list.append(pair)
        elif component.get_type() == 'Archive':
            pair = []
            pair.append(component)
            pair.append(SubmittedArchiveForm(prefix = component.id))
            component_form_list.append(pair)
        elif component.get_type() == 'Cpp':
            pair = []
            pair.append(component)
            pair.append(SubmittedCppForm(prefix = component.id))
            component_form_list.append(pair)
        elif component.get_type() == 'Java':
            pair = []
            pair.append(component)
            pair.append(SubmittedJavaForm(prefix = component.id))
            component_form_list.append(pair)
        elif component.get_type() == 'PlainText':
            pair = []
            pair.append(component)
            pair.append(SubmittedPlainTextForm(prefix = component.id))
            component_form_list.append(pair)
    if request.method == 'POST':
        for component in component_list:
            get(component.id+form.field)
            url.component = component
            pass

        return HttpResponse("uploded")
        #form = Submission.ContactForm(request.POST, request.FILE)
        #if form.is_valid():
#            pass
#        pass
    else:
        component_list = select_all_components(activity)
        return render_to_response("submission/submission_add.html",
        {'component_form_list': component_form_list, "course": course, "activity": activity},
        context_instance = RequestContext(request))

#student submission history page
@login_required
def show_components_submission_history(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(course.activity_set,slug = activity_slug)
    all_submitted_components = select_students_submitted_components(activity, request.user.username)
    component_list = select_all_components(activity)
    empty_component = []
    for component in component_list:
        if select_students_submission_by_component(component, request.user.username) == []:
            empty_component.append(component)
    return render_to_response("submission/submission_history_view.html", 
        {'submitted_component': all_submitted_components,'empty_component': empty_component, 'course':course, 'activity':activity},
        context_instance = RequestContext(request))

#staff submission configuratiton
@login_required
def _show_components_staff(request, course_slug, activity_slug):
    """
    Show all the components of this activity
    Responsible for updating position
    """
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(course.activity_set,slug = activity_slug)

    #if POST, update the positions
    if request.method == 'POST':
        component_list = select_all_components(activity)
        counter = 0
        for component in component_list:
            counter = counter + 1
            t = request.POST.get('' + str(counter) + '_position');
            #in case t is not a number
            try:
                component.position = int(t)
                component.save()
            except:
                pass
        return HttpResponseRedirect(reverse(show_components, args=[course_slug, activity_slug]))

    
    component_list = select_all_components(activity)
    return render_to_response("submission/component_view_staff.html",
        {"course":course, "activity":activity, "component_list":component_list},
        context_instance=RequestContext(request))


@requires_course_staff_by_slug
def confirm_remove(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(course.activity_set, slug = activity_slug)
    component_list = select_all_components(activity)
    
    #show confirm message
    del_id = request.GET.get('id')
    del_type = request.GET.get('type')
    component = None
    if del_id == None or del_type == None:
        #url is invalid
        pass
    else:
        #make sure type, id, and activity is correct
        for c in component_list:
            if str(c.get_type()) == del_type and str(c.id) == del_id and c.activity == activity:
                component = c
                break

    #if confirmed
    if request.method == 'POST' and component != None:
        component.delete()
        return HttpResponseRedirect(reverse(show_components, args=[course_slug, activity_slug]))

    return render_to_response("submission/component_remove.html",
            {"course":course, "activity":activity, "component":component, "del_id":del_id},
            context_instance=RequestContext(request))



@requires_course_staff_by_slug
def edit_single(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(course.activity_set, slug = activity_slug)
    component_list = select_all_components(activity)

    #get component
    edit_id = request.GET.get('id')
    #TODO: if id is unique, probably don't need to pass type in URL
    edit_type = request.GET.get('type')
    component = None
    if edit_id == None or edit_type == None:
        #url is invalid
        pass
    else:
        #make sure type, id, and activity is correct
        for c in component_list:
            if str(c.get_type()) == edit_type and str(c.id) == edit_id and c.activity == activity:
                component = c
                break
    #if component is invalid
    if component == None:
        return render_to_response("submission/component_edit_single.html",
            {"course":course, "activity":activity, "component":component},
            context_instance=RequestContext(request))

    #get type change
    type = request.GET.get('to_type')
    #if no type change
    if type == None:
        pass
    elif type == component.get_type():
        #no change
        return HttpResponseRedirect("?type="+type+"&id="+str(component.id))
    else:
    #if need to change type
        if type == 'Archive':
            new_component = ArchiveComponent()
        elif type == 'URL':
            new_component = URLComponent()
        elif type == 'Cpp':
            new_component = CppComponent()
        elif type == 'PlainText':
            new_component = PlainTextComponent()
        elif type == 'Java':
            new_component = JavaComponent()
        else:
            #to_type is invalid, just ignore
            new_component = component
        #copy a new component
        new_component.id = component.id
        new_component.activity = component.activity
        new_component.title = component.title
        new_component.description = component.description
        new_component.position = component.position
        #save new component
        component.delete()
        new_component.save()
        #refresh the form
        return HttpResponseRedirect("?type="+new_component.get_type()+"&id="+str(new_component.id))
        
    
    #make form
    form = None
    new_form = None
    if edit_type == 'Archive':
        form = ArchiveComponentForm(instance=component)
        new_form = ArchiveComponentForm(request.POST)
    elif edit_type == 'URL':
        form = URLComponentForm(instance=component)
        new_form = URLComponentForm(request.POST)
    elif edit_type == 'Cpp':
        form = CppComponentForm(instance=component)
        new_form = CppComponentForm(request.POST)
    elif edit_type == 'PlainText':
        form = PlainTextComponentForm(instance=component)
        new_form = PlainTextComponentForm(request.POST)
    elif edit_type == 'Java':
        form = JavaComponentForm(instance=component)
        new_form = JavaComponentForm(request.POST)
        
    #if form submitted
    if request.method == 'POST':
        if new_form.is_valid():
            new_component = new_form.save(commit=False)
            new_component.activity = activity
            new_component.id = component.id
            if new_component.position == None:
                count = len(select_all_components(activity))
                new_component.position = count*10 + 10
            new_component.save()
            return HttpResponseRedirect(reverse(show_components, args=[course_slug, activity_slug]))
        else:
            form = new_form

    #render the page
    return render_to_response("submission/component_edit_single.html",
            {"course":course, "activity":activity, "component":component, "edit_id":edit_id,
             "type":edit_type, "form":form},
            context_instance=RequestContext(request))

@requires_course_staff_by_slug
def add_component(request, course_slug, activity_slug, new_added=False):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(course.activity_set, slug = activity_slug)

    #default, Archive
    type = request.GET.get('type')
    if type == None:
        type = 'Archive'

    if type == 'Archive':
        form = ArchiveComponentForm()
        new_form = ArchiveComponentForm(request.POST)
    elif type == 'URL':
        form = URLComponentForm()
        new_form = URLComponentForm(request.POST)
    elif type == 'Cpp':
        form = CppComponentForm()
        new_form = CppComponentForm(request.POST)
    elif type == 'PlainText':
        form = PlainTextComponentForm()
        new_form = PlainTextComponentForm(request.POST)
    elif type == 'Java':
        form = JavaComponentForm()
        new_form = JavaComponentForm(request.POST)
    else:
        raise Http404()

    #if form is submitted, validate / add component
    if request.method == 'POST':
	#incoming_form = AddComponentForm(request.POST)
        if new_form.is_valid():
            #add component
            new_component = new_form.save(commit=False)
            new_component.activity = activity
            if new_component.position == None:
                count = len(select_all_components(activity))
                new_component.position = count*10 + 10
            new_component.save()
            new_added = True
            #TODO: how to add a redirect? blow doesn't work
            #return HttpResponseRedirect(reverse(add_component, args=[course_slug, activity_slug, True]))
        else:
            form = new_form
    return render_to_response("submission/component_add.html", 
        {"course":course, "activity":activity, "form":form, "new_added":new_added, "type":type},
        context_instance=RequestContext(request))