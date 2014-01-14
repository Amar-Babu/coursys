from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'gpaconvert.views.list_grade_sources'),
    url(r'^(?P<grade_source_slug>[\d\w-]+)$', 'gpaconvert.views.convert_grades'),
)
