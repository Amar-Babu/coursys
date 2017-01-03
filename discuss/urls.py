from django.conf.urls import url
from courselib.urlparts import SLUG_RE

discussion_patterns = [ # prefix /COURSE_SLUG/discussion/
    url(r'^$', 'discuss.views.discussion_index', name='discussion_index'),
    url(r'^create_topic/$', 'discuss.views.create_topic', name='create_topic'),
    url(r'^subscribe$', 'discuss.views.manage_discussion_subscription', name='manage_discussion_subscription'),
    url(r'^topic/(?P<topic_slug>' + SLUG_RE + ')/$', 'discuss.views.view_topic', name='view_topic'),
    url(r'^topic/(?P<topic_slug>' + SLUG_RE + ')/edit$', 'discuss.views.edit_topic', name='edit_topic'),
    url(r'^topic/(?P<topic_slug>' + SLUG_RE + ')/change$', 'discuss.views.change_topic_status', name='change_topic_status'),
    url(r'^topic/(?P<topic_slug>' + SLUG_RE + ')/subscribe$', 'discuss.views.manage_topic_subscription', name='manage_topic_subscription'),
    url(r'^topic/(?P<topic_slug>' + SLUG_RE + ')/remove/(?P<message_slug>' + SLUG_RE + ')$', 'discuss.views.remove_message', name='remove_message'),
    url(r'^topic/(?P<topic_slug>' + SLUG_RE + ')/edit/(?P<message_slug>' + SLUG_RE + ')$', 'discuss.views.edit_message', name='edit_message'),
]
