from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django import forms
from django.forms.fields import FileField
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Q
from courselib.auth import NotFoundResponse, ForbiddenResponse, requires_role, requires_form_admin_by_slug,\
    requires_formgroup
from django.core.exceptions import ObjectDoesNotExist

from onlineforms.forms import FormForm,NewFormForm, SheetForm, FieldForm, DynamicForm, GroupForm, EditSheetForm, NonSFUFormFillerForm, AdminAssignForm, EditGroupForm, EmployeeSearchForm, AdminAssignForm_nonsfu
from onlineforms.models import Form, Sheet, Field, FIELD_TYPE_MODELS, FIELD_TYPES, neaten_field_positions, FormGroup, FieldSubmissionFile
from onlineforms.models import FormSubmission, SheetSubmission, FieldSubmission
from onlineforms.models import FormFiller, SheetSubmissionSecretUrl, reorder_sheet_fields

from coredata.models import Person, Role
from log.models import LogEntry

import os

#######################################################################
# Group Management

@requires_role('ADMN')
def manage_groups(request):
    groups = FormGroup.objects.filter(unit__in=request.units)
    context = {'groups': groups}
    return render(request, 'onlineforms/manage_groups.html', context)


@transaction.commit_on_success
@requires_role('ADMN')
def new_group(request):
    unit_choices = [(u.id, unicode(u)) for u in request.units]
    if request.method == 'POST':
        form = GroupForm(request.POST)
        form.fields['unit'].choices = unit_choices
        if form.is_valid():
            form.save()
            name = str(form.cleaned_data['name'])
            formgroup = FormGroup.objects.get(name=name)
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("created form group %s (%i)") % (formgroup, formgroup.id),
                  related_object=formgroup)
            l.save()
            return HttpResponseRedirect(reverse('onlineforms.views.manage_group', kwargs={'formgroup_slug': formgroup.slug }))
    else:
        form = GroupForm()
        form.fields['unit'].choices = unit_choices

    add_member_form = EmployeeSearchForm()
    context = {'form': form, 'addMemberForm': add_member_form}
    return render(request, 'onlineforms/new_group.html', context)


@transaction.commit_on_success
@requires_role('ADMN')
def manage_group(request, formgroup_slug):
    group = get_object_or_404(FormGroup, slug=formgroup_slug, unit__in=request.units)

    # for editting group name
    if request.method == 'POST':
        form = EditGroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("edited form group %s (%i)") % (group, group.id),
                  related_object=group)
            l.save()
            return HttpResponseRedirect(reverse('onlineforms.views.manage_groups'))
    form = EditGroupForm(instance=group)
    grouplist = FormGroup.objects.filter(slug__exact=formgroup_slug)

    # below is for finding person thru coredata/personfield and adding to group
    search_form = EmployeeSearchForm()

    context = {'form': form, 'group': group, 'grouplist': grouplist, 'search': search_form }
    return render(request, 'onlineforms/manage_group.html', context)


@transaction.commit_on_success
@requires_role('ADMN')
def add_group_member(request, formgroup_slug):
    group = get_object_or_404(FormGroup, slug=formgroup_slug, unit__in=request.units)

    if request.method == 'POST':
        if 'action' in request.POST:
            if request.POST['action'] == 'add':
                if request.POST['search'] != '':
                    search_form = EmployeeSearchForm(request.POST)
                    if search_form.is_valid(): 
                        # search returns Person object
                        member = search_form.cleaned_data['search']
                        group.members.add(member)
                        l = LogEntry(userid=request.user.username,
                             description=("added %s to form group %s") % (member.userid_or_emplid(), group),
                              related_object=group)
                        l.save()
                        return HttpResponseRedirect(reverse('onlineforms.views.manage_group', kwargs={'formgroup_slug': formgroup_slug}))
                else: # if accidentally don't search for anybody
                    return HttpResponseRedirect(reverse('onlineforms.views.manage_group', kwargs={'formgroup_slug': formgroup_slug }))     
    
    groups = FormGroup.objects.filter(unit__in=request.units)
    context = {'groups': groups}
    return render(request, 'onlineforms/manage_groups.html', context)

@transaction.commit_on_success
@requires_role('ADMN')
def remove_group_member(request, formgroup_slug, userid):
    group = get_object_or_404(FormGroup, slug=formgroup_slug, unit__in=request.units)
    member = Person.objects.get(emplid=userid)

    if group.unit not in request.units:
        return ForbiddenResponse(request)

    # remove m2m relationship
    if request.method == 'POST':
        if 'action' in request.POST:
            if request.POST['action'] == 'remove':
                group.members.remove(member)
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                    description=("Removed %s from form group %s") % (member.userid_or_emplid(), group),
                    related_object=group)
                l.save()
                return HttpResponseRedirect(reverse('onlineforms.views.manage_group', kwargs={'formgroup_slug': formgroup_slug}))
    
    groups = FormGroup.objects.filter(unit__in=request.units)
    context = {'groups': groups}
    return render(request, 'onlineforms/manage_groups.html', context)


#######################################################################
# Managing submissions & assigning sheets

@requires_formgroup()
def admin_list_all(request):
    admin = get_object_or_404(Person, userid=request.user.username)
    form_groups = FormGroup.objects.filter(members=admin)
    if form_groups:
        pend_submissions = FormSubmission.objects.filter(owner__in=form_groups, status='PEND')
        
        #Waiting submissions
        wait_submissions = FormSubmission.objects.filter(owner__in=form_groups, status='WAIT')
        for wait_sub in wait_submissions:
            last_sheet_assigned = SheetSubmission.objects.filter(form_submission=wait_sub).latest('given_at')
            wait_sub.assigned_to = last_sheet_assigned
        
        # Completed submissions
        done_submissions = FormSubmission.objects.filter(owner__in=form_groups, status='DONE')
        for done_sub in done_submissions:
            latest_sumbission = SheetSubmission.objects.filter(form_submission=done_sub).latest('completed_at')
            done_sub.completed_at = latest_sumbission.completed_at

    context = {'pend_submissions': pend_submissions, 'wait_submissions': wait_submissions, 'done_submissions': done_submissions}
    return render(request, "onlineforms/admin/admin_forms.html", context)


@requires_formgroup()
def admin_assign_nonsfu(request, form_slug, formsubmit_slug):
    return _admin_assign(request, form_slug=form_slug, formsubmit_slug=formsubmit_slug, assign_to_sfu_account=False)

@requires_formgroup()
def admin_assign(request, form_slug, formsubmit_slug, assign_to_sfu_account=True):
    return _admin_assign(request, form_slug=form_slug, formsubmit_slug=formsubmit_slug, assign_to_sfu_account=True)

@transaction.commit_on_success
def _admin_assign(request, form_slug, formsubmit_slug, assign_to_sfu_account=True):
    """
    Give a sheet on this formsubmission to a user
    """
    admin = get_object_or_404(Person, userid=request.user.username)
    form_submission = get_object_or_404(FormSubmission, form__slug=form_slug, slug=formsubmit_slug,
                                        owner__in=request.formgroups)

    # get the next sheet that hasn't been completed (as the default next sheet to assign)
    filled_orders = [val['sheet__order'] for val in
                     form_submission.sheetsubmission_set.filter(status='DONE').values('sheet__order')]
    later_sheets = Sheet.objects \
                   .filter(form=form_submission.form, active=True, order__gt=max(filled_orders)) \
                   .order_by('order')
    default_sheet = later_sheets[0] if later_sheets else None

    assign_args = {'data': request.POST or None,
                    'label': 'sheet',
                    'query_set': Sheet.objects.filter(form=form_submission.form, active=True),
                    'initial': {'sheet': default_sheet}}
    form = AdminAssignForm(**assign_args) if assign_to_sfu_account else AdminAssignForm_nonsfu(**assign_args)

    if request.method == 'POST' and form.is_valid():
        if assign_to_sfu_account:
            formFiller = _userToFormFiller(form.cleaned_data['assignee'])
        else:
            nonSFUFormFiller = form.save()  # in this case the form is a model form
            formFiller = FormFiller.objects.create(nonSFUFormFiller=nonSFUFormFiller)

        sheet_submission = SheetSubmission.objects.create(form_submission=form_submission,
            sheet=form.cleaned_data['sheet'],
            filler=formFiller)
        # create an alternate URL, if necessary
        if not assign_to_sfu_account:
            SheetSubmissionSecretUrl.objects.create(sheet_submission=sheet_submission)
        # send email
        if formFiller.full_email() != admin.full_email():
            sheet_submission.email_assigned(request, admin, formFiller)

        #LOG EVENT#
        l = LogEntry(userid=request.user.username,
            description=("Assigned form sheet %s to %s") % (sheet_submission.sheet, sheet_submission.filler.identifier()),
            related_object=sheet_submission)
        l.save()
        messages.success(request, 'Sheet assigned.')
        return HttpResponseRedirect(reverse('onlineforms.views.admin_list_all'))

    context = {'form': form, 'form_submission': form_submission, 'assign_to_sfu_account': assign_to_sfu_account}
    return render(request, "onlineforms/admin/admin_assign.html", context)


@requires_formgroup()
def admin_assign_any_nonsfu(request):
    return _admin_assign_any(request, assign_to_sfu_account=False)
@requires_formgroup()
def admin_assign_any(request, assign_to_sfu_account=True):
    return _admin_assign_any(request, assign_to_sfu_account=True)

@transaction.commit_on_success
def _admin_assign_any(request, assign_to_sfu_account=True):
    """
    Give a form('s initial sheet) to a user
    """
    admin = get_object_or_404(Person, userid=request.user.username)

    if assign_to_sfu_account:
        form = AdminAssignForm(data=request.POST or None, label='form',
            query_set=Form.objects.filter(active=True, owner__in=request.formgroups))
    else:
        form = AdminAssignForm_nonsfu(data=request.POST or None, label='form',
            query_set=Form.objects.filter(active=True, owner__in=request.formgroups))

    if request.method == 'POST' and form.is_valid():
        # get the person to assign too
        if assign_to_sfu_account:
            assignee = form.cleaned_data['assignee']
            formFiller = _userToFormFiller(assignee)
        else:
            nonSFUFormFiller = form.save()
            formFiller = FormFiller.objects.create(nonSFUFormFiller=nonSFUFormFiller)
        # create new form submission with a blank sheet submission
        form = form.cleaned_data['form']
        form_submission = FormSubmission.objects.create(form=form,
                            initiator=formFiller,
                            owner=form.owner,
                            status='WAIT')
        sheet_submission = SheetSubmission.objects.create(form_submission=form_submission,
            sheet=form.initial_sheet,
            filler=formFiller)
        # create an alternate URL, if necessary
        if not assign_to_sfu_account:
            SheetSubmissionSecretUrl.objects.create(sheet_submission=sheet_submission)
        # send email
        if formFiller.full_email() != admin.full_email():
            sheet_submission.email_assigned(request, admin, formFiller)
        #LOG EVENT#
        l = LogEntry(userid=request.user.username,
            description=("Assigned form %s to %s") % (form, sheet_submission.filler.identifier()),
            related_object=sheet_submission)
        l.save()
        messages.success(request, 'Form assigned.')
        return HttpResponseRedirect(reverse('onlineforms.views.admin_list_all'))

    context = {'form': form, 'assign_to_sfu_account': assign_to_sfu_account}
    return render(request, "onlineforms/admin/admin_assign_any.html", context)

@transaction.commit_on_success
@requires_formgroup()
def admin_done(request, form_slug, formsubmit_slug):
    form_submission = get_object_or_404(FormSubmission, form__slug=form_slug, slug=formsubmit_slug,
                                        owner__in=request.formgroups)
    form_submission.status = 'DONE'
    form_submission.save()
    #LOG EVENT#
    l = LogEntry(userid=request.user.username,
        description=("Marked form submission %s done.") % (form_submission,),
        related_object=form_submission)
    l.save()
    return HttpResponseRedirect(reverse('onlineforms.views.admin_list_all'))

def _userToFormFiller(user):
    try:
        form_filler = FormFiller.objects.get(sfuFormFiller=user)
    except ObjectDoesNotExist:
        form_filler = FormFiller.objects.create(sfuFormFiller=user)
    return form_filler


#######################################################################
# Creating/editing forms

@transaction.commit_on_success
@requires_formgroup()
def list_all(request):
    forms = Form.objects.filter(owner__in=request.formgroups, active=True)
    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'del':
        form_id = request.POST['form_id']
        forms = forms.filter(id=form_id)
        if forms:
            form = forms[0]
            form.delete()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                description=("Deleted form %s.") % (form,),
                related_object=form)
            l.save()
            messages.success(request, 'Removed the Form')
        return HttpResponseRedirect(reverse(list_all))
    else:
        form = FormForm()
        context = {'form': form, 'forms': forms}
    return render(request, 'onlineforms/manage_forms.html', context)


@transaction.commit_on_success
@requires_formgroup()
def new_form(request):
    group_choices = [(fg.id, unicode(fg)) for fg in request.formgroups]
    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'add':
        form = NewFormForm(request.POST)
        form.fields['owner'].choices = group_choices
        if form.is_valid():
            f = form.save(commit=False)
            # use FormGroup's unit as the Form's unit
            f.unit = f.owner.unit
            f.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                description=("Created form %s.") % (f,),
                related_object=f)
            l.save()
            return HttpResponseRedirect(reverse(view_form, kwargs={'form_slug':f.slug }))
    else:
        form = NewFormForm()
        form.fields['owner'].choices = group_choices
    return render(request, 'onlineforms/new_form.html', {'form': form})


@requires_form_admin_by_slug()
def view_form(request, form_slug):
    form = get_object_or_404(Form, slug=form_slug, owner__in=request.formgroups)
    sheets = Sheet.objects.filter(form=form, active=True).order_by('order')
    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'del':
        sheet_id = request.POST['sheet_id']
        sheets = Sheet.objects.filter(id=sheet_id, form=form)
        if sheets:
            sheet = sheets[0]
            sheet.delete()
            messages.success(request, 'Removed the sheet "%s".' % (sheet.title))
           
        return HttpResponseRedirect(
            reverse(view_form, kwargs={'form_slug':form.slug }))

    
    context = {'form': form, 'sheets': sheets}
    return render(request, "onlineforms/view_form.html", context)       


@transaction.commit_on_success
@requires_form_admin_by_slug()
def edit_form(request, form_slug):
    owner_form = get_object_or_404(Form, slug=form_slug, owner__in=request.formgroups)
    group_choices = [(fg.id, unicode(fg)) for fg in request.formgroups]

    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'edit':
        form = FormForm(request.POST, instance=owner_form)
        form.fields['owner'].choices = group_choices
        if form.is_valid():
            f = form.save(commit=False)
            # use FormGroup's unit as the Form's unit
            f.unit = f.owner.unit
            f.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                description=("Edited form %s.") % (f,),
                related_object=f)
            l.save()
            return HttpResponseRedirect(reverse('onlineforms.views.view_form', kwargs={'form_slug': owner_form.slug}))
    else:
        form = FormForm(instance=owner_form)
        form.fields['owner'].choices = group_choices

    context = {'form': form, 'owner_form': owner_form}
    return render(request, 'onlineforms/edit_form.html', context)


@transaction.commit_on_success
@requires_form_admin_by_slug()
def new_sheet(request, form_slug):
    owner_form = get_object_or_404(Form, slug=form_slug, owner__in=request.formgroups)
    if request.method == 'POST':
        form = SheetForm(request.POST)
        if form.is_valid():
            sheet = Sheet.objects.create(title=form.cleaned_data['title'], form=owner_form, can_view=form.cleaned_data['can_view'])
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                description=("Created form sheet %s.") % (sheet,),
                related_object=sheet)
            l.save()
            messages.success(request, 'Successfully created the new sheet "%s' % form.cleaned_data['title'])
            return HttpResponseRedirect(
                reverse('onlineforms.views.edit_sheet', kwargs={'form_slug': form_slug, 'sheet_slug': sheet.slug}))
    else:
        initial = {}
        other_sheets = Sheet.objects.filter(form=owner_form, active=True).count()
        if other_sheets == 0:
            initial['title'] = owner_form.title
            initial['can_view'] = 'NON'
        form = SheetForm(initial=initial)

    context = {'form': form, 'owner_form': owner_form}
    return render(request, "onlineforms/new_sheet.html", context)

@requires_form_admin_by_slug()
def preview_sheet(request, form_slug, sheet_slug):
    owner_form = get_object_or_404(Form, slug=form_slug, owner__in=request.formgroups)
    owner_sheet = get_object_or_404(Sheet, slug=sheet_slug, form=owner_form)
    
    form = DynamicForm(owner_sheet.title)
    fields = Field.objects.filter(sheet=owner_sheet, active=True).order_by('order')
    form.fromFields(fields)

    context = {'form': form, 'owner_form': owner_form, 'owner_sheet': owner_sheet}
    return render(request, "onlineforms/preview_sheet.html", context)

@transaction.commit_on_success
@requires_form_admin_by_slug()
def edit_sheet(request, form_slug, sheet_slug):
    owner_form = get_object_or_404(Form, slug=form_slug, owner__in=request.formgroups)
    owner_sheet = get_object_or_404(Sheet, form=owner_form, slug=sheet_slug)
    fields = Field.objects.filter(sheet=owner_sheet, active=True).order_by('order')
    # Non Ajax way to reorder activity, please also see reorder_activity view function for ajax way to reorder
    order = None
    field_slug = None
    if request.GET.has_key('order'):
        order = request.GET['order']
    if request.GET.has_key('field_slug'):
        field_slug = request.GET['field_slug']
    if order and field_slug:
        reorder_sheet_fields(fields, field_slug, order)
        return HttpResponseRedirect(
            reverse('onlineforms.views.edit_sheet', kwargs={'form_slug': form_slug, 'sheet_slug': sheet_slug}))

    # check if they are deleting a field from the sheet
    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'del':
        field_id = request.POST['field_id']
        fields = Field.objects.filter(id=field_id, sheet=owner_sheet)
        if fields:
            # need a new version of the form since we're making a change:
            owner_sheet = owner_sheet.safe_save()
            field = fields[0]
            field = Field.objects.get(sheet=owner_sheet, original=field.original) # get field on new version, not old
            field.active = False
            field.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                description=("Removed form field %s.") % (field,),
                related_object=field)
            l.save()
            messages.success(request, 'Removed the field %s.' % (field.label))
        return HttpResponseRedirect(
            reverse(edit_sheet, kwargs={'form_slug': owner_form.slug, 'sheet_slug': owner_sheet.slug}))

    # construct a form from this sheets fields
    form = DynamicForm(owner_sheet.title)
    form.fromFields(fields)

    # a list of dictionaries containing the field model object(for editing) and the field form object(for display)
    modelFormFields = []
    for (counter, field) in enumerate(form):
        field.type =  FIELD_TYPES[fields[counter].fieldtype]
        modelFormFields.append({'modelField': fields[counter], 'formField': field})

    context = {'owner_form': owner_form, 'owner_sheet': owner_sheet, 'form': form, 'fields': modelFormFields}
    return render(request, "onlineforms/edit_sheet.html", context)

@transaction.commit_on_success
@requires_form_admin_by_slug()
def reorder_field(request, form_slug, sheet_slug):
    """
    Ajax way to reorder activity.
    This ajax view function is called in the edit_sheet page.
    """
    form = get_object_or_404(Form, slug=form_slug, owner__in=request.formgroups)
    sheet = get_object_or_404(Sheet, form=form, slug=sheet_slug)
    if request.method == 'POST':
        neaten_field_positions(sheet)
        # find the fields in question
        id_up = request.POST.get('id_up')
        id_down = request.POST.get('id_down')
        if id_up == None or id_down == None:
            return ForbiddenResponse(request)
            # swap the order of the two fields
        field_up = get_object_or_404(Field, id=id_up, sheet=sheet)
        field_down = get_object_or_404(Field, id=id_down, sheet=sheet)

        temp = field_up.order
        field_up.order = field_down.order
        field_down.order = temp
        field_up.save()
        field_down.save()

        return HttpResponse("Order updated!")
    return ForbiddenResponse(request)


@transaction.commit_on_success
@requires_form_admin_by_slug()
def edit_sheet_info(request, form_slug, sheet_slug):
    owner_form = get_object_or_404(Form, slug=form_slug, owner__in=request.formgroups)
    owner_sheet = get_object_or_404(Sheet, form=owner_form, slug=sheet_slug)
    #owner_field = get_object_or_404(Field, slug=field_slug)

    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'edit':
        form = EditSheetForm(request.POST, instance=owner_sheet)
        if form.is_valid():
            new_sheet = owner_sheet.safe_save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                description=("Edited form sheet %s.") % (new_sheet,),
                related_object=new_sheet)
            l.save()
            return HttpResponseRedirect(reverse('onlineforms.views.edit_sheet',
                kwargs={'form_slug': owner_form.slug, 'sheet_slug': new_sheet.slug}))
    else:
        form = EditSheetForm(instance=owner_sheet)

    context = {'form': form, 'owner_form': owner_form, 'owner_sheet': owner_sheet}
    return render(request, 'onlineforms/edit_sheet_info.html', context)


@transaction.commit_on_success
@requires_form_admin_by_slug()
def new_field(request, form_slug, sheet_slug):
    owner_form = get_object_or_404(Form, slug=form_slug, owner__in=request.formgroups)
    owner_sheet = get_object_or_404(Sheet, form=owner_form, slug=sheet_slug)

    invalid_submission = False

    if request.method == 'POST' and 'type' in request.POST:
        ftype = request.POST['type']
        TypeModel = FIELD_TYPE_MODELS[ftype]
        custom_config = _clean_config(request.POST)
        field = TypeModel(config=custom_config)
        form = field.make_config_form()

        if form.is_valid():
            new_sheet = owner_sheet.safe_save()
            f = Field.objects.create(label=form.cleaned_data['label'],
                    sheet=new_sheet,
                    fieldtype=ftype,
                    config=custom_config,
                    active=True,
                    original=None, )
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                description=("Created form field %s.") % (f,),
                related_object=f)
            l.save()
            messages.success(request, 'Successfully created the new field \'%s\'' % form.cleaned_data['label'])

            return HttpResponseRedirect(
                    reverse('onlineforms.views.edit_sheet', args=(form_slug, new_sheet.slug)))
            
        # Fall-through to redisplay form with errors
        invalid_submission = True

    if (request.method == 'GET' and 'type' in request.GET) or invalid_submission == True:
        # have selected the field type: now configure the field.
        if request.method == 'GET':
            # these are set above in invalid_submission fallthrough case
            ftype = request.GET['type']
            TypeModel = FIELD_TYPE_MODELS[ftype]
            field = TypeModel()
            field.config = None # force form to behave as new, not as nothing-useful-submitted
            form = field.make_config_form()

        need_choices = field.choices
        type_description = FIELD_TYPES[ftype]
        
        # ... unless we don't have to configure. Then don't.
        if not field.configurable:
            new_sheet = owner_sheet.safe_save()
            f = Field.objects.create(label='',
                sheet=new_sheet,
                fieldtype=ftype,
                config={},
                active=True,
                original=None, )
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                description=("Created form field %s.") % (f,),
                related_object=f)
            l.save()
            messages.success(request, 'Successfully created a new field')

            return HttpResponseRedirect(
                reverse('onlineforms.views.edit_sheet', args=(form_slug, new_sheet.slug)))
        
        context = {'form': form, 'owner_form': owner_form, 'owner_sheet': owner_sheet, 'choices': need_choices, 'ftype': ftype, 'type_description': type_description}
        return render(request, 'onlineforms/new_field.html', context)

    else:
        # need to select field type
        form = FieldForm()
        context = {'form': form, 'owner_form': owner_form, 'owner_sheet': owner_sheet}
        return render(request, 'onlineforms/new_field_select.html', context)


def _clean_config(config):
    irrelevant_fields = ['csrfmiddlewaretoken', 'next_section', 'type_name']
    clean_config = dict((key, value) for (key, value) in config.iteritems() if key not in irrelevant_fields)
    clean_config['required'] = 'required' in clean_config

    return clean_config


@transaction.commit_on_success
@requires_form_admin_by_slug()
def edit_field(request, form_slug, sheet_slug, field_slug):
    owner_form = get_object_or_404(Form, slug=form_slug, owner__in=request.formgroups)
    owner_sheet = get_object_or_404(Sheet, form=owner_form, slug=sheet_slug)
    field = get_object_or_404(Field, sheet=owner_sheet, slug=field_slug)

    ftype = FIELD_TYPE_MODELS[field.fieldtype]
    need_choices = ftype().choices

    if request.POST:
        clean_config = _clean_config(request.POST)
        form = ftype(config=clean_config).make_config_form()
        if field.config == clean_config:
            messages.info(request, "Nothing modified")

        elif form.is_valid():
            new_sheet = owner_sheet.safe_save()
            # newfield = field.safe_save()
            new_field = Field.objects.create(label=form.cleaned_data['label'],
                #sheet=owner_sheet,
                sheet=new_sheet,
                fieldtype=field.fieldtype,
                config=clean_config,
                active=True,
                order=field.order,
                original=field.original)
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                description=("Edited form field %s.") % (new_field,),
                related_object=new_field)
            l.save()
            messages.success(request, 'Successfully updated the field "%s"' % form.cleaned_data['label'])

            return HttpResponseRedirect(
                reverse('onlineforms.views.edit_sheet', args=(new_sheet.form.slug, new_sheet.slug)))

    else:
        if not ftype.configurable:
            return HttpResponseRedirect(
                reverse('onlineforms.views.edit_sheet', args=(form_slug, sheet_slug)))
        form = FIELD_TYPE_MODELS[field.fieldtype](config=field.config).make_config_form()

    context = {'form': form, 'owner_form': owner_form, 'owner_sheet': owner_sheet, 'field': field,
               'choices': need_choices}

    return render(request, 'onlineforms/edit_field.html', context)

#######################################################################
# Submitting sheets

def index(request):
    form_groups = None
    sheet_submissions = None
    if(request.user.is_authenticated()):
        loggedin_user = get_object_or_404(Person, userid=request.user.username)
        forms = Form.objects.filter(active=True).exclude(initiators='NON')
        sheet_submissions = SheetSubmission.objects.filter(filler=_userToFormFiller(loggedin_user)).exclude(status='DONE')
        # get all the form groups the logged in user is a part of
        form_groups = FormGroup.objects.filter(members=loggedin_user)
    else:
        forms = Form.objects.filter(active=True, initiators='ANY')

    dept_admin = Role.objects.filter(role='ADMN', person__userid=request.user.username).count() > 0

    context = {'forms': forms, 'sheet_submissions': sheet_submissions, 'form_groups': form_groups, 'dept_admin': dept_admin}
    return render(request, 'onlineforms/submissions/forms.html', context)


is_displayable_sheet_sub = Q(status="DONE") | Q(sheet__is_initial=True)
def _readonly_sheets(form_submission):
    """
    Collect sheet subs and other info to display this form submission.
    """
    sheet_submissions = SheetSubmission.objects \
            .filter(form_submission=form_submission) \
            .filter(is_displayable_sheet_sub)
    sheet_sub_html = {}
    for sheet_sub in sheet_submissions:
        # get html from field submissions
        field_submissions = FieldSubmission.objects.filter(sheet_submission=sheet_sub)
        fields = []
        for field_sub in field_submissions:
            field = FIELD_TYPE_MODELS[field_sub.field.fieldtype](field_sub.field.config)
            field.fieldtype = field_sub.field.fieldtype
            if field.configurable:
                field.label = field.config['label']
                field.html = field.to_html(field_sub)

            fields.append(field)
        sheet_sub_html[sheet_sub] = fields
    return sheet_sub_html



@requires_formgroup()
def file_field_download(request, form_slug, formsubmit_slug, file_id, action):
    form_submission = get_object_or_404(FormSubmission, form__slug=form_slug, slug=formsubmit_slug,
                                        owner__in=request.formgroups)
    file_sub =  get_object_or_404(FieldSubmissionFile,
                                  field_submission__sheet_submission__form_submission=form_submission,
                                  id=file_id)
    file_path = file_sub.file_attachment.file.name
    filename = os.path.basename(file_path)

    file_sub.file_attachment.file.open()
    response = HttpResponse(file_sub.file_attachment.file, content_type=file_sub.file_mediatype)
    
    if action == 'download':
        disposition = 'download'
    else:
        disposition = 'inline'
    
    response['Content-Disposition'] = disposition + '; filename=' + filename
    return response


@login_required
def view_submission(request, form_slug, formsubmit_slug):
    # can access if in owning formgroup
    formgroups = FormGroup.objects.filter(members__userid=request.user.username)
    form_submissions = FormSubmission.objects.filter(form__slug=form_slug, slug=formsubmit_slug,
                                        owner__in=formgroups)
    is_advisor = False
    if not form_submissions:
        # advisors can access relevant completed forms
        advisor_roles = Role.objects.filter(person__userid=request.user.username, role='ADVS')
        units = set(r.unit for r in advisor_roles)
        form_submissions = FormSubmission.objects.filter(form__slug=form_slug, slug=formsubmit_slug,
                                        form__unit__in=units, form__advisor_visible=True, status='DONE')
        is_advisor = True

    if not form_submissions:
        raise Http404

    form_submission = form_submissions[0]
    sheet_submissions = _readonly_sheets(form_submission)

    context = {
               'form': form_submission.form,
               'form_sub': form_submission,
               'sheet_submissions': sheet_submissions,
               'form_slug': form_slug,
               'formsubmit_slug': formsubmit_slug,
               'is_advisor': is_advisor,
               }
    return render(request, 'onlineforms/admin/view_partial_form.html', context)



def sheet_submission_via_url(request, secret_url):
    """
    Sheet submission from a user who has been sent a secret URL
    """
    sheet_submission_secret_url = get_object_or_404(SheetSubmissionSecretUrl, key=secret_url)
    sheet_submission_object = sheet_submission_secret_url.sheet_submission
    sheet = sheet_submission_object.sheet
    form_submission = sheet_submission_object.form_submission
    form = form_submission.form
    alternate_url = reverse('onlineforms.views.sheet_submission_via_url', kwargs={'secret_url': secret_url})
    return _sheet_submission(request, form_slug=form.slug, formsubmit_slug=form_submission.slug,
                             sheet_slug=sheet.slug, sheetsubmit_slug=sheet_submission_object.slug,
                             alternate_url=alternate_url)

def sheet_submission_initial(request, form_slug):
    """
    Submission from a user who is initiating a new form submission
    """
    return _sheet_submission(request, form_slug=form_slug)

def sheet_submission_subsequent(request, form_slug, formsubmit_slug, sheet_slug, sheetsubmit_slug):
    """
    Submission by a user who is returning to a partially-completed sheet submission
    """
    return _sheet_submission(request, form_slug=form_slug, formsubmit_slug=formsubmit_slug,
                             sheet_slug=sheet_slug, sheetsubmit_slug=sheetsubmit_slug)

@transaction.commit_on_success
def _sheet_submission(request, form_slug, formsubmit_slug=None, sheet_slug=None, sheetsubmit_slug=None, alternate_url=None):
    owner_form = get_object_or_404(Form, slug=form_slug)
    this_path = request.get_full_path()
    
    # if no one can fill out this form, stop right now
    if owner_form.initiators == "NON":
        context = {'owner_form': owner_form, 'error_msg': "No one can fill out this form."}
        return render(request, 'onlineforms/submissions/sheet_submission.html', context)

    #get the sheet
    if sheet_slug:
        sheet = get_object_or_404(Sheet, form=owner_form, slug=sheet_slug)
    else:
        if not(owner_form.initial_sheet):
            raise Http404('No sheet found for this form.')
        sheet = owner_form.initial_sheet

    # get their info if they are logged in
    if(request.user.is_authenticated()):
        loggedin_user = get_object_or_404(Person, userid=request.user.username)
        logentry_userid = loggedin_user.userid
        nonSFUFormFillerForm = None
    else:
        loggedin_user = None
        logentry_userid = ""
        # make a form for non sfu people, unless they have an alternate_url
        # in which case the form filler object would already have been created
        nonSFUFormFillerForm = NonSFUFormFillerForm() if not alternate_url else None

    # a field -> field submission lookup
    field_submission_dict = {}
    # previously filled sheets to display
    filled_sheets = []
    # get the submission objects(if they exist) and create the form
    if formsubmit_slug and sheetsubmit_slug:
        form_submission = get_object_or_404(FormSubmission, form=owner_form, slug=formsubmit_slug)
        sheet_submission = get_object_or_404(SheetSubmission, sheet__original=sheet.original,
                                             form_submission=form_submission, slug=sheetsubmit_slug)
        sheet = sheet_submission.sheet # revert to the old version that the user was working with.
        # check if this sheet has already been filled
        if sheet_submission.status == "DONE":
            # TODO: show in display-only mode instead
            return NotFoundResponse(request)
        # check that they can access this sheet
        formFiller = sheet_submission.filler
        if sheet_submission.filler.isSFUPerson():
            if not(formFiller.sfuFormFiller) or loggedin_user != formFiller.sfuFormFiller:
                return ForbiddenResponse(request)
        # do we do need to do any checking for non sfu form fillers?

        form = DynamicForm(sheet.title)
        form.fromFields(sheet.fields, sheet_submission.field_submissions)

        # populate the field -> fieldSubmission lookup
        for field_submission in sheet_submission.field_submissions:
            field_submission_dict[field_submission.field] = field_submission

        # get previously filled in sheet's data
        if sheet.can_view == 'ALL':
            filled_sheets = _readonly_sheets(form_submission)
    else:
        # make sure we are allowed to initiate this form
        if not loggedin_user and owner_form.initiators != "ANY":
            return ForbiddenResponse(request)
        form = DynamicForm(sheet.title)
        form.fromFields(sheet.fields)
        form_submission = None
        sheet_submission = None
        formFiller = None

    if request.method == 'POST' and ('save' in request.POST or 'submit' in request.POST):
            # get the info from post
            if 'save' in request.POST:
                form.fromPostData(request.POST, request.FILES, ignore_required=True)
            elif 'submit' in request.POST:
                form.fromPostData(request.POST, request.FILES)

            if form.is_valid():
                # sheet is valid, lets get a form filler (if we don't already have one)
                if not formFiller:
                    # we don't have a form filler from above (could be initial sheet submission)
                    # if they provided a non-SFU form use that info, otherwise grab their logged in credentials
                    formFiller = None
                    if 'add-nonsfu' in request.POST and sheet.is_initial and owner_form.initiators == "ANY":
                        nonSFUFormFillerForm = NonSFUFormFillerForm(request.POST)
                        if nonSFUFormFillerForm.is_valid():
                            nonSFUFormFiller = nonSFUFormFillerForm.save()
                            #LOG EVENT#
                            l = LogEntry(userid=logentry_userid,
                                description=("Non SFU Form Filler created with email %s to submit form %s") % (nonSFUFormFiller.email_address, owner_form.title),
                                related_object=nonSFUFormFiller)
                            l.save()
                            formFiller = FormFiller(nonSFUFormFiller=nonSFUFormFiller)
                            formFiller.save()
                        else:
                            formFiller = None
                    elif loggedin_user:
                        formFiller = _userToFormFiller(loggedin_user)
                    else:
                        # they didn't provide nonsfu info and they are not logged in
                        # (or the sheet doesn't allow non-SFU people to fill it in)
                        context = {'owner_form': owner_form,
                                   'error_msg': "You must have a SFU account and be logged in to fill out this form."}
                        return render(request, 'onlineforms/submissions/sheet_submission.html', context)

                if formFiller:
                    # we have a form filler, the data is valid, create the formsubmission and sheetsubmission objects if necessary
                    if not(form_submission):
                        # create the form submission
                        form_submission = FormSubmission(form=owner_form, initiator=formFiller, owner=owner_form.owner)
                        form_submission.save()
                        #LOG EVENT#
                        l = LogEntry(userid=logentry_userid,
                            description=("Form submission created for form %s by %s") % (owner_form.title, formFiller.email()),
                            related_object=form_submission)
                        l.save()
                    if not(sheet_submission):
                        # create the sheet submission
                        sheet_submission = SheetSubmission(sheet=sheet, form_submission=form_submission, filler=formFiller)
                        sheet_submission.save()
                        #LOG EVENT#
                        l = LogEntry(userid=logentry_userid,
                            description=("Sheet submission created for sheet %s of form %s by %s") % (sheet.title, owner_form.title, formFiller.email()),
                            related_object=sheet_submission)
                        l.save()

                    # save the data from the fields
                    for name, field in form.fields.items():
                        # a field can be skipped if we are saving (not submitting) the form, and it is not in the cleaned data
                        if not('submit' in request.POST) or str(name) in form.cleaned_data:
                            cleaned_data = form.display_fields[field].serialize_field(form.cleaned_data[str(name)])
                            # if we already have a field submission, edit it. Otherwise create a new one
                            if sheet.fields[name] in field_submission_dict:
                                fieldSubmission = field_submission_dict[sheet.fields[name]]
                                fieldSubmission.data = cleaned_data
                            else:
                                fieldSubmission = FieldSubmission(field=sheet.fields[name], sheet_submission=sheet_submission, data=cleaned_data)
                            fieldSubmission.save()
                            
                            # save files
                            if isinstance(field, FileField):
                                # remove old files if asked
                                if request.POST.get(str(name)+"-clear", False):
                                    old_fsf = FieldSubmissionFile.objects.filter(field_submission=fieldSubmission)
                                    for fsf in old_fsf:
                                        fsf.file_attachment.delete()
                                        fsf.delete()
                                
                                # save the new submission
                                if str(name) in request.FILES:

                                    new_file = request.FILES[str(name)]
                                    new_file_submission = FieldSubmissionFile(field_submission=fieldSubmission,
                                                                              file_attachment=new_file,
                                                                              file_mediatype=new_file.content_type)
                                    new_file_submission.save()
                                    
                                    # delete any old files for this fieldsub
                                    old_fsf = FieldSubmissionFile.objects.filter(field_submission=fieldSubmission) \
                                              .exclude(id=new_file_submission.id)
                                    for fsf in old_fsf:
                                        fsf.file_attachment.delete()
                                        fsf.delete()

                            #LOG EVENT#
                            l = LogEntry(userid=logentry_userid,
                                description=("Field submission created for field %s of sheet %s of form %s by %s") % (sheet.fields[name].label, sheet.title, owner_form.title, formFiller.email()),
                                related_object=fieldSubmission)
                            l.save()

                    # cleanup for each submit-mode
                    if 'save' in request.POST:
                        # refill the form with the new data
                        form.fromFields(sheet.fields, sheet_submission.get_field_submissions(refetch=True))
                        # don't redirect, show the form with errors(if they exist) but notify them that info was saved

                        if alternate_url:
                            access_url = alternate_url
                        elif not formFiller.isSFUPerson():
                            # if they aren't accessing via an alternate url, they aren't a SFU account,
                            # and they are saving then we need to create a alternate url for them to use
                            secret_url = SheetSubmissionSecretUrl(sheet_submission=sheet_submission)
                            secret_url.save()
                            #LOG EVENT#
                            l = LogEntry(userid=logentry_userid,
                                description=("Secret URL created for sheet submission %s of sheet %s of form %s by %s") % (sheet_submission, sheet.title, owner_form.title, formFiller.email()),
                                related_object=secret_url)
                            l.save()
                            # email them the URL
                            sheet_submission.email_started(request)
                            access_url = reverse('onlineforms.views.sheet_submission_via_url', kwargs={'secret_url': secret_url.key})
                        else:
                            sheet_submission.email_started(request)
                            access_url = reverse('onlineforms.views.sheet_submission_subsequent', kwargs={
                                'form_slug': owner_form.slug,
                                'formsubmit_slug': form_submission.slug,
                                'sheet_slug': sheet.slug,
                                'sheetsubmit_slug': sheet_submission.slug})

                        messages.success(request, 'All fields without errors were saved. Use this pages URL to edit this submission in the future.')
                        return HttpResponseRedirect(access_url)
                    elif 'submit' in request.POST:
                        # all the fields have been submitted, this sheet is done
                        sheet_submission.status = 'DONE'
                        sheet_submission.save()
                        l = LogEntry(userid=logentry_userid,
                            description=("Sheet submission %s completed by %s") % (sheet_submission.slug, formFiller.email()),
                            related_object=sheet_submission)
                        l.save()
                        
                        sheet_submission.email_submitted(request)

                        messages.success(request, 'You have succesfully completed sheet %s of form %s.' % (sheet.title, owner_form.title))
                        return HttpResponseRedirect(reverse(index))
                else:
                    messages.error(request, "Error in user data.")
            else:
                messages.error(request, "The form could not be submitted because of errors in the supplied data, please correct them and try again.")

    context = {'owner_form': owner_form,
                'sheet': sheet,
                'form': form,
                'form_submission': form_submission,
                'filled_sheets': filled_sheets,
                'alternate_url': alternate_url,
                'nonSFUFormFillerForm': nonSFUFormFillerForm,
                'this_path': this_path,}
    return render(request, 'onlineforms/submissions/sheet_submission.html', context)
