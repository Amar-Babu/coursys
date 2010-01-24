from django.conf.urls.defaults import *
#from courses.urls import COURSE_SLUG_RE

COURSE_SLUG_RE = '\d{4}-[a-z]{2,4}-\w{3,4}-[a-z]\d{3}'
urlpatterns = patterns('',
    url(r'^$', 'marking.views.index'),
    url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/$', 'marking.views.list_activities'),        
    url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/(?P<activity_short_name>.*)/components/$', 'marking.views.manage_activity_components'),    
)
