from django.conf.urls.defaults import *
from django.conf import settings

if settings.DEBUG:
    from django.contrib import admin
    admin.autodiscover()

COURSE_SLUG_RE = '\d{4}-[a-z]{2,4}-\w{3,4}-[a-z]\d{3}'

urlpatterns = patterns('',
    (r'^login/$', 'django_cas.views.login'),
    (r'^logout/$', 'django_cas.views.logout'),

    (r'^$', 'courses.dashboard.views.index'),
    (r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/$', 'courses.dashboard.views.course'),
    
    (r'^roles/$', 'courses.coredata.views.role_list'),
    (r'^roles/new$', 'courses.coredata.views.new_role'),
    
    # for Advisor_A
    (r'^advisors_A/', include('advisors_A.urls')),
    #for Advisors_B
    (r'^advisors_B/', include('advisors_B.urls')),
    
    # for Marking
    (r'^marking/', include('marking.urls')),

    # for Grades
    (r'^grades/', include('grades.urls')),

    # for groups
    (r'^groups/', include('groups.urls')),
)
if settings.DEBUG:
    # URLs for development only:
    urlpatterns += patterns('',
        (r'^admin/(.*)', admin.site.root),
        (r'^media/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT}),
        #(r'^import/', 'courses.coredata.views.importer'),
    )

