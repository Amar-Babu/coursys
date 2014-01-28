from django.conf.urls import patterns, url
from courselib.urlparts import USERID_OR_EMPLID, UNIT_SLUG

FACULTY_SLUG = UNIT_SLUG + '/' + USERID_OR_EMPLID

urlpatterns = patterns('',
    url(r'^$', 'faculty.views.index'),
    url(r'^' + USERID_OR_EMPLID + '/summary$', 'faculty.views.summary', name="faculty_summary"),
    url(r'^' + USERID_OR_EMPLID + '/career_events$', 'faculty.views.events_list', name="faculty_events_list"),
    url(r'^' + USERID_OR_EMPLID + '/otherinfo$', 'faculty.views.otherinfo', name="faculty_otherinfo"),
    url(r'^' + USERID_OR_EMPLID + '/new-event$', 'faculty.views.create_event', name="faculty_create_event"),
    url(r'^' + USERID_OR_EMPLID + '/(?P<slug>[^//]+)/change$', 'faculty.views.change_event', name="faculty_change_event"),
)
