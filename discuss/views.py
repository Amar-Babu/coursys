from coredata.models import CourseOffering, Person, Member
from courselib.auth import is_course_student_by_slug, is_course_staff_by_slug
from discuss.models import DiscussionTopic, DiscussionMessage
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from discuss.forms import discussion_topic_form_factory,\
    DiscussionTopicStatusForm, DiscussionMessageForm

def _get_course_and_view(request, course_slug):
    """
    Validates the request and returns the course object and view perspective ('student', 'staff')
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    if not course.discussion():
        raise Http404
    if is_course_student_by_slug(request, course_slug):
        return course, 'student'
    elif is_course_staff_by_slug(request, course_slug):
        return course, 'staff'
    else:
        return HttpResponseForbidden()

@login_required
def discussion_index(request, course_slug):
    """
    Index page to view all discussion topics
    """
    course, view = _get_course_and_view(request, course_slug)
    topics = DiscussionTopic.objects.filter(offering=course).exclude(status='HID').order_by('-pinned', '-last_activity_at')
    paginator = Paginator(topics, 10)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        topics = paginator.page(page)
    except (EmptyPage, InvalidPage):
        topics = paginator.page(paginator.num_pages)
    return render(request, 'discuss/index.html', {'course': course, 'topics': topics, 'view': view})

@login_required()
def hidden_topics(request, course_slug):
    """
    Page to view all hidden discussion topics
    """
    course, view = _get_course_and_view(request, course_slug)
    if not view  == 'staff':
        return HttpResponseForbidden()
    topics = DiscussionTopic.objects.filter(offering=course, status='HID').order_by('-last_activity_at')
    return render(request, 'discuss/hidden_topics.html', {'course': course, 'topics': topics})

def _get_member_as_author(username, discussion_view, course_slug):
    """
    Retrieves the Member object for a discussion topic/message
    """
    if discussion_view is 'student':
        return Member.objects.filter(offering__slug=course_slug, person__userid=username, role="STUD", offering__graded=True).exclude(offering__component="CAN")[0]
    elif discussion_view is 'staff':
        return Member.objects.filter(offering__slug=course_slug, person__userid=username, role__in=['INST', 'TA', 'APPR'], offering__graded=True).exclude(offering__component="CAN")[0]
    else:
        raise ValueError("Discussion view type must be either 'student' or 'staff'")
    
@login_required
def create_topic(request, course_slug):
    """
    Form to create a new discussion topic
    """
    course, view = _get_course_and_view(request, course_slug)
    if request.method == 'POST':
        form = discussion_topic_form_factory(view, request.POST)
        if form.is_valid():
            topic = form.save(commit=False)
            topic.offering = course
            topic.author = _get_member_as_author(request.user.username, view, course_slug)
            topic.save()
            messages.add_message(request, messages.SUCCESS, 'Discussion topic created successfully.')
            return HttpResponseRedirect(reverse('discuss.views.view_topic', kwargs={'course_slug': course_slug, 'topic_id': topic.pk}))
    else:
        form = discussion_topic_form_factory(view)
    return render(request, 'discuss/create_topic.html', {'course': course, 'form': form})

@login_required
def view_topic(request, course_slug, topic_id):
    """
    Page to view a discussion topic and reply
    """
    course, view = _get_course_and_view(request, course_slug)
    topic = get_object_or_404(DiscussionTopic, pk=topic_id, offering=course)
    if view == 'student' and topic.status == 'HID':
        raise Http404
    replies = DiscussionMessage.objects.filter(topic=topic).exclude(status='HID').order_by('created_at')
    if request.method == 'POST':
        if topic.status == 'CLO' and not view  == 'staff':
            raise Http404
        form = DiscussionMessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.topic = topic
            message.author = _get_member_as_author(request.user.username, view, course_slug)
            message.save()
            messages.add_message(request, messages.SUCCESS, 'Sucessfully replied')
            return HttpResponseRedirect(reverse('discuss.views.view_topic', kwargs={'course_slug': course_slug, 'topic_id': topic.pk}))
    else:
        form = DiscussionMessageForm()
    return render(request, 'discuss/topic.html', {'course': course, 'topic': topic, 'replies': replies, 'view': view, 'form': form})

@login_required
def change_topic_status(request, course_slug, topic_id):
    """
    Form to change the status of a topic
    """
    course, view = _get_course_and_view(request, course_slug)
    topic = get_object_or_404(DiscussionTopic, pk=topic_id, offering=course)
    if view is not 'staff':
        return HttpResponseForbidden()
    if request.method == 'POST':
        form = DiscussionTopicStatusForm(request.POST, instance=topic)
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Discussion topic has been successfully changed.')
            return HttpResponseRedirect(reverse('discuss.views.view_topic', kwargs={'course_slug': course_slug, 'topic_id': topic_id}))
    else:
        form = DiscussionTopicStatusForm(instance=topic)
    return render(request, 'discuss/change_topic.html', {'course': course, 'topic': topic, 'form': form})

@login_required
def remove_message(request ,course_slug, topic_id, message_id):
    """
    POST to remove a topic message
    """
    course, view = _get_course_and_view(request, course_slug)
    if not view == 'staff':
        return HttpResponseForbidden()
    if request.method != 'POST':
        raise Http404
    topic = get_object_or_404(DiscussionTopic, pk=topic_id, offering=course)
    message = get_object_or_404(DiscussionMessage, pk=message_id, topic=topic)
    message.status = 'HID'
    message.save()
    messages.add_message(request, messages.SUCCESS, 'Reply successfully removed.')
    return HttpResponseRedirect(reverse('discuss.views.view_topic', kwargs={'course_slug': course_slug, 'topic_id': topic_id}))
    
    
