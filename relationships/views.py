import operator
from django.shortcuts import render, get_object_or_404, HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.http import Http404
from courselib.auth import requires_role
from forms import ContactForm
from log.models import LogEntry
from models import Contact, Event, EVENT_CHOICES, EVENT_HANDLERS


def _get_handler_or_404(handler_slug):
    handler_slug = handler_slug.lower()
    if handler_slug in EVENT_HANDLERS:
        return EVENT_HANDLERS[handler_slug]
    else:
        raise Http404('Unknown event handler slug')


def _get_event_types():
    types = [{
        'slug': key.lower(),
        'name': Handler.name,
    } for key, Handler in EVENT_CHOICES]
    return sorted(types, key=operator.itemgetter('name'))


@requires_role('RELA')
def index(request):
    contacts = Contact.objects.filter(unit__in=request.units)
    return render(request, 'relationships/index.html', {'contacts': contacts})


@requires_role('RELA')
def view_contact(request, contact_slug):
    contact = get_object_or_404(Contact, slug=contact_slug, unit__in=request.units)
    events = Event.objects.filter(contact=contact)
    return render(request, 'relationships/view_contact.html', {'contact': contact, 'events': events})


@requires_role('RELA')
def new_contact(request):
    if request.method == 'POST':
        form = ContactForm(request, request.POST)
        if form.is_valid():
            contact = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Contact was created')
            l = LogEntry(userid=request.user.username,
                         description="Added contact %s" % contact,
                         related_object=contact)
            l.save()
            return HttpResponseRedirect(reverse('relationships:index'))
    else:
        form = ContactForm(request)
    return render(request, 'relationships/new_contact.html', {'form': form})


@requires_role('RELA')
def edit_contact(request, contact_slug):
    contact = get_object_or_404(Contact, slug=contact_slug, unit__in=request.units)
    if request.method == 'POST':
        form = ContactForm(request, request.POST, instance=contact)
        if form.is_valid():
            contact = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Contact was edited')
            l = LogEntry(userid=request.user.username,
                         description="Edited contact %s" % contact,
                         related_object=contact)
            l.save()
            return HttpResponseRedirect(reverse('relationships:index'))
    else:
        form = ContactForm(request, instance=contact)
    return render(request, 'relationships/edit_contact.html', {'form': form, 'contact': contact})


@requires_role('RELA')
def delete_contact(request, contact_slug):
    contact = get_object_or_404(Contact, slug=contact_slug, unit__in=request.units)
    if request.method == 'POST':
        contact.deleted = True
        contact.save()
        messages.add_message(request,
                             messages.SUCCESS,
                             u'Contact was deleted')
        l = LogEntry(userid=request.user.username,
                     description="Deleted contact %s" % contact,
                     related_object=contact)
        l.save()
    return HttpResponseRedirect(reverse('relationships:index'))


@requires_role('RELA')
def list_events(request, contact_slug):
    contact = get_object_or_404(Contact, slug=contact_slug, unit__in=request.units)
    events = _get_event_types()
    return render(request, 'relationships/list_events.html', {'contact': contact, 'events': events})


@requires_role('RELA')
def add_event(request, contact_slug, event_slug):
    contact = get_object_or_404(Contact, slug=contact_slug, unit__in=request.units)
    handler = _get_handler_or_404(event_slug)
    if request.method == 'POST':
        form = handler.EntryForm(data=request.POST)
        # If the form has a file field, we should put the file data back in there.  Make sure the actual field is called
        # "files" in the form!
        if len(request.FILES) != 0:
            form.files = request.FILES
        if form.is_valid():
            event_handler = handler.create_for(contact=contact, form=form)
            event_handler.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Contact content was added')
            l = LogEntry(userid=request.user.username,
                         description="Added contact content %s" % event_handler.event,
                         related_object=event_handler.event)
            l.save()
            return HttpResponseRedirect(reverse('relationships:view_contact', kwargs={'contact_slug': contact_slug}))

    else:
        form = handler.EntryForm()
    return render(request, 'relationships/add_event.html', {'form': form, 'contact': contact, 'event_slug': event_slug})


@requires_role('RELA')
def view_event(request, contact_slug, event_slug):
    contact = get_object_or_404(Contact, slug=contact_slug, unit__in=request.units)
    event = get_object_or_404(Event, slug=event_slug, contact=contact)
    handler = event.get_handler()
    return render(request, 'relationships/view_event.html', {'contact': contact, 'event': event, 'handler': handler})


@requires_role('RELA')
def delete_event(request, contact_slug, event_slug):
    contact = get_object_or_404(Contact, slug=contact_slug, unit__in=request.units)
    event = get_object_or_404(Event, slug=event_slug, contact=contact)
    if request.method == 'POST':
        event.deleted = True
        event.save(call_from_handler=True)
        messages.add_message(request,
                             messages.SUCCESS,
                             u'Contact content was deleted')
        l = LogEntry(userid=request.user.username,
                     description="Deleted contact content %s" % event,
                     related_object=event)
        l.save()
        return HttpResponseRedirect(reverse('relationships:view_contact', kwargs={'contact_slug': contact_slug}))
