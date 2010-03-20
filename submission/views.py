from django.contrib.auth.decorators import login_required
from coredata.models import Member, CourseOffering, Person
from django.shortcuts import render_to_response, get_object_or_404#, redirect
from django.template import RequestContext
from django.http import HttpResponseRedirect, QueryDict
from courselib.auth import requires_course_by_slug,requires_course_staff_by_slug, ForbiddenResponse, NotFoundResponse
from courses.submission.forms import make_form_from_data_and_list
from submission.forms import *
from courselib.auth import is_course_staff_by_slug, is_course_member_by_slug
from submission.models import *
from django.core.urlresolvers import reverse
from contrib import messages
from datetime import *
from marking.views import marking_student, marking_group
from groups.models import Group, GroupMember

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
        return ForbiddenResponse(request);
    
#student submission main page
#may be viewed by a staff
def _show_components_student(request, course_slug, activity_slug, userid=None, template="dashboard_student.html"):
    """
    Show all the component submission history of this activity
    """
    if userid == None:
        userid = request.user.username
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(course.activity_set,slug = activity_slug)
    student = get_object_or_404(Person, userid=userid)

    submitted_pair_list = get_current_submission(userid, activity)
    late, submit_time, owner = get_submit_time_and_owner(activity, submitted_pair_list)

    if len(submitted_pair_list) == 0:
        messages.add_message(request, messages.WARNING, 'There is no submittable component of this activity.')

    return render_to_response("submission/" + template,
        {"course":course, "activity":activity, "submitted_pair":submitted_pair_list, "userid":userid, "submit_time":submit_time, "late":late, "student":student, "owner":owner},
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
    if request.method == 'POST':
        component_form_list = make_form_from_data_and_list(request, component_list)
        submitted_comp = []    # list all components which has content submitted in the POST
        not_submitted_comp = [] #list allcomponents which has no content submitted in the POST
        new_sub = StudentSubmission()   # the submission foreign key for newly submitted components
        new_sub.activity = activity
        member = Member.objects.filter(person__userid = request.user.username)
        new_sub.member = get_object_or_404(member, offering__slug = course_slug)
        new_sub_saved = False
        #TODO: test if the submission is a group or student submission then adit accordingly
        for form in component_form_list:
            form[1].component = form[0]
            if form[1].is_valid():
                #save the froeign submission first at the first time a submission conponent is read in
                if new_sub_saved == False:
                    # save the submission forgein key
                    new_sub_saved = True
                    new_sub.save()
                if form[0].get_type() == 'URL' :
                    file = request.POST.get(str(form[0].id) + '-' + form[0].get_type().lower())
                    sub = SubmittedURL()        #submitted component
                    sub.url = file
                elif form[0].get_type() == 'PlainText':
                    file = request.POST.get(str(form[0].id) + '-' + 'text')
                    sub = SubmittedPlainText()
                    sub.text = file
                else:
                    file = request.FILES.get(str(form[0].id) + '-' + form[0].get_type().lower())
                    if form[0].get_type() == 'Archive':
                        sub = SubmittedArchive()
                        sub.archive = file
                    if form[0].get_type() == 'Cpp':
                        sub = SubmittedCpp()
                        sub.cpp = file
                    if form[0].get_type() =='Java':
                        sub = SubmittedJava()
                        sub.java = file
                sub.submission = new_sub    #point to the submission foreign key
                sub.component = form[0]
                sub.save()
                submitted_comp.append(form[0])
            else:
                not_submitted_comp.append(form[0])
        return render_to_response("submission/submission_error.html",
            {"course":course, "activity":activity, "component_list":component_form_list,
            "submitted_comp":submitted_comp, "not_submitted_comp":not_submitted_comp},
            context_instance=RequestContext(request))
    else: #not POST
        component_form_list = make_form_from_list(component_list)
        return render_to_response("submission/submission_add.html",
        {'component_form_list': component_form_list, "course": course, "activity": activity},
        context_instance = RequestContext(request))

def check_me_or_member(request, target_uid, course, activity, staff=True):
    """
    if it's me or it's a member of my group, return true; otherwise false;
    staff=True means staff will always return true
    """
    get_object_or_404(Person, userid=target_uid)
    if target_uid == request.user.username:
        return True
    if is_course_staff_by_slug(request.user, course.slug):
        return staff
    my_group = GroupMember.objects.all().filter(student__person__userid=request.user.username).filter(activity=activity)
    if len(my_group) != 0:
        target_group = GroupMember.objects.all().filter(student__person__userid=target_uid).filter(activity=activity)
        if len(target_group) != 0:
            if target_group[0].group == my_group[0].group:
                return True
    return False

@login_required
def show_components_submission_history(request, course_slug, activity_slug):
    userid = request.GET.get('userid')
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(course.activity_set,slug = activity_slug)
    
    if userid==None:
        userid = request.user.username
    if not check_me_or_member(request, userid, course, activity):
        return ForbiddenResponse(request)
    
    all_submitted_components = select_students_submitted_components(activity, userid)
    component_list = select_all_components(activity)
    empty_component = []
    for component in component_list:
        if select_students_submission_by_component(component, userid) == []:
            empty_component.append(component)
            messages.add_message(request, messages.WARNING, "You have no submission for "+component.title+".")
    return render_to_response("submission/submission_history_view.html", 
        {"course":course, "activity":activity,'userid':userid,'submitted_component': all_submitted_components,'empty_component': empty_component, 'course':course, 'activity':activity},
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
        messages.add_message(request, messages.SUCCESS, 'Component positions updated.')
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
    component = check_component_id_type_activity(component_list, del_id, del_type, activity)

    #if confirmed
    if request.method == 'POST' and component != None:
        component.delete()
        messages.add_message(request, messages.SUCCESS, 'Component "' +  component.title + '" removed.')
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
    edit_type = request.GET.get('type')
    component = check_component_id_type_activity(component_list, edit_id, edit_type, activity)
    if component == None:
        messages.add_message(request, messages.ERROR, 'The component you specified is invalid.')
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
                new_component.position = count + 1
            new_component.save()
            messages.add_message(request, messages.SUCCESS, 'Component "' + new_component.title + '" successfully updated.')
            return HttpResponseRedirect(reverse(show_components, args=[course_slug, activity_slug]))
        else:
            form = new_form
            messages.add_message(request, messages.ERROR, 'Please correct the errors in the form.')

    #render the page
    return render_to_response("submission/component_edit_single.html",
            {"course":course, "activity":activity, "component":component, "edit_id":edit_id,
             "type":edit_type, "form":form},
            context_instance=RequestContext(request))

@requires_course_staff_by_slug
def add_component(request, course_slug, activity_slug):
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
        return NotFoundResponse(request)

    #if form is submitted, validate / add component
    if request.method == 'POST':
	#incoming_form = AddComponentForm(request.POST)
        if new_form.is_valid():
            #add component
            new_component = new_form.save(commit=False)
            new_component.activity = activity
            if new_component.position == None:
                count = len(select_all_components(activity))
                new_component.position = count + 1
            new_component.save()
            messages.add_message(request, messages.SUCCESS, 'New component "' + new_component.title + '" successfully added.')
            return HttpResponseRedirect(reverse(show_components, args=[course_slug, activity_slug]))
        else:
            messages.add_message(request, messages.ERROR, 'Please correct the errors in the form.')
            form = new_form
    return render_to_response("submission/component_add.html", 
        {"course":course, "activity":activity, "form":form, "type":type},
        context_instance=RequestContext(request))

@login_required
def download_file(request, course_slug, activity_slug, userid):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(course.activity_set, slug = activity_slug)
    
    type = request.GET.get('type') #targeted file type
    id = request.GET.get('id') #targeted submitted component id
    #student_id = request.GET.get('user-id') #targeted student
    group_id = request.GET.get('group-id') #targeted group

    if not check_me_or_member(request, userid, course, activity):
        return ForbiddenResponse(request)

    # download as (file type + submitted id)
    if type != None:
        return download_single_component(type, id)

    #download current submission as a zip file for userid='id'
    if userid != None:
        student = get_object_or_404(Person, userid=userid)
    else:
        get_object_or_404(Group, group_id)
        #TODO: group submission

    #TODO: modify the function to work for group submission
    submitted_pair_list = get_current_submission(userid, activity)
    # if no submission, jump to the other page
    no_submission = True
    for pair in submitted_pair_list:
        if pair[1] != None:
            no_submission = False
            break
    if no_submission == True:
        return render_to_response("submission/download_error_no_submission.html",
        {"course":course, "activity":activity, "student":student},
        context_instance=RequestContext(request))

    #return a zip file containing all components
    return generate_zip_file(submitted_pair_list, userid, activity_slug)

@requires_course_staff_by_slug
def show_student_submission_staff(request, course_slug, activity_slug, userid):
    return _show_components_student(request, course_slug, activity_slug, userid, "view_student_dashboard_staff.html")

@requires_course_staff_by_slug
def show_student_history_staff(request, course_slug, activity_slug, userid):
    return show_components_submission_history(request, course_slug, activity_slug, userid)

@requires_course_staff_by_slug
def take_ownership_and_mark(request, course_slug, activity_slug, userid):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(course.activity_set, slug = activity_slug)
    
    # get the urlencode
    qDict = request.GET
    urlencode = ''
    if qDict.items():
        urlencode = '?' +  qDict.urlencode()
        
    #TODO: for group marking ?
    response = HttpResponseRedirect(reverse(marking_student, args=[course_slug, activity_slug, userid]) + urlencode)
    
    component = select_students_submitted_components(activity, userid)
    #if it is taken by someone not me, show a confirm dialog
    if request.GET.get('confirm') == None:
        for c in component:
            if c.submission.owner != None and c.submission.owner.person.userid != request.user.username:
                return _override_ownership_confirm(request, course, activity, userid, c.submission.owner.person, activity_mark_suffix, from_page_suffix)
            
    for c in component:
        c.submission.set_owner(course, request.user.username)
    return response

def _override_ownership_confirm(request, course, activity, userid, old_owner, activity_suffix, from_suffix):
    student = get_object_or_404(Person, userid=userid)
    
    return render_to_response("submission/override_ownership_confirm.html",
        {"course":course, "activity":activity, "student":student, "old_owner":old_owner, "true":True,
        "activity_suffix":activity_suffix, "from_suffix":from_suffix},
        context_instance=RequestContext(request))
