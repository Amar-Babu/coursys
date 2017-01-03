from django.conf.urls import url, include
from django.views.generic import RedirectView
from courselib.urlparts import USERID_SLUG, COURSE_SLUG, SLUG_RE, USERID_OR_EMPLID
from privacy.urls import privacy_patterns

config_patterns = [ # prefix /config/
    url(r'^$', 'dashboard.views.config', name='config'),
    url(r'^news/set$', 'dashboard.views.create_news_url', name='create_news_url'),
    url(r'^news/del$', 'dashboard.views.disable_news_url', name='disable_news_url'),
    url(r'^calendar/set$', 'dashboard.views.create_calendar_url', name='create_calendar_url'),
    url(r'^calendar/del$', 'dashboard.views.disable_calendar_url', name='disable_calendar_url'),
    url(r'^advisor-api/set$', 'dashboard.views.enable_advisor_token', name='enable_advisor_token'),
    url(r'^advisor-api/del$', 'dashboard.views.disable_advisor_token', name='disable_advisor_token'),
    url(r'^advisor-api/change$', 'dashboard.views.change_advisor_token', name='change_advisor_token'),
    url(r'^news$', 'dashboard.views.news_config', name='news_config'),
    url(r'^photos$', 'dashboard.views.photo_agreement', name='photo_agreement'),
    url(r'^privacy/', include(privacy_patterns)),
    url(r'^tokens/', 'api.views.manage_tokens', name='manage_tokens'),
]

news_patterns = [ # prefix /news/
    url(r'^$', 'dashboard.views.news_list', name='news_list'),
    url(r'^configure/$', RedirectView.as_view(url='/config/', permanent=True)),
    url(r'^(?P<token>[0-9a-f]{32})/' + USERID_SLUG + '$', 'dashboard.views.atom_feed', name='atom_feed'),
    url(r'^(?P<token>[0-9a-f]{32})/' + USERID_SLUG + '/' + COURSE_SLUG + '$', 'dashboard.views.atom_feed', name='atom_feed'),
]

calendar_patterns = [ # prefix /calendar/
    url(r'^(?P<token>[0-9a-f]{32})/' + USERID_SLUG + '(?:~*)$', 'dashboard.views.calendar_ical', name='calendar_ical'),
    url(r'^$', 'dashboard.views.calendar', name='calendar'),
    url(r'^data$', 'dashboard.views.calendar_data', name='calendar_data'),

]

docs_patterns = [ # prefix /docs/
    url(r'^$', 'dashboard.views.list_docs', name='list_docs'),
    url(r'^(?P<doc_slug>' + SLUG_RE + ')$', 'dashboard.views.view_doc', name='view_doc'),
]

studentsearch_patterns = [ # prefix /students/
    # basic student search: hopefully replace with full text search
    url(r'^$', 'dashboard.views.student_info', name='student_info'),
    url(r'^' + USERID_OR_EMPLID + '$', 'dashboard.views.student_info', name='student_info'),
]
