from django.conf.urls.defaults import patterns, url
from courselib.urlparts import SEMESTER, USERID_SLUG, COURSE_SLUG, SLUG_RE

PLAN_SLUG = '(?P<plan_slug>[\w\-]+)'
PLANNED_OFFERING_SLUG = '(?P<planned_offering_slug>[\w\-]+)'

urlpatterns = patterns('',
    url(r'^teaching/$', planning_views.instructor_index, name='instructor_index'),
    url(r'^teaching/courses$', planning_views.edit_capability, name='edit_capability'),
    url(r'^teaching/courses/(?P<course_id>\w+)/delete$', planning_views.delete_capability, name='delete_capability'),

    url(r'^teaching/semesters$', planning_views.edit_intention, name='edit_intention'),
    url(r'^teaching/semester/' + SEMESTER + '/delete$', planning_views.delete_intention, name='delete_intention'),
    url(r'^teaching/credits/$', planning_views.view_teaching_credits_inst, name='view_teaching_credits_inst'),
    url(r'^teaching/equivalent/(?P<equivalent_id>\d+)/$', planning_views.view_teaching_equivalent_inst, name='view_teaching_equivalent_inst'),
    url(r'^teaching/equivalent/(?P<equivalent_id>\d+)/edit/$', planning_views.edit_teaching_equivalent_inst, name='edit_teaching_equivalent_inst'),
    url(r'^teaching/equivalent/(?P<equivalent_id>\d+)/remove/$', planning_views.remove_teaching_equiv_inst, name='remove_teaching_equiv_inst'),
    url(r'^teaching/equivalent/new/$', planning_views.new_teaching_equivalent_inst, name='new_teaching_equivalent_inst'),
    url(r'^teaching/admin/$', planning_views.view_insts_in_unit, name='view_insts_in_unit'),
    url(r'^teaching/admin/instructor/' + USERID_SLUG + '/$', planning_views.view_teaching_credits_admin, name='view_teaching_credits_admin'),
    url(r'^teaching/admin/instructor/' + USERID_SLUG + '/new-equivalent/$', planning_views.new_teaching_equivalent_admin, name='new_teaching_equivalent_admin'),
    url(r'^teaching/admin/instructor/' + USERID_SLUG + '/equivalent/(?P<equivalent_id>\d+)/$', planning_views.view_teaching_equivalent_admin, name='view_teaching_equivalent_admin'),
    url(r'^teaching/admin/instructor/' + USERID_SLUG + '/equivalent/(?P<equivalent_id>\d+)/edit/$', planning_views.edit_teaching_equivalent_admin, name='edit_teaching_equivalent_admin'),
    url(r'^teaching/admin/instructor/' + USERID_SLUG + '/equivalent/(?P<equivalent_id>\d+)/confirm/$', planning_views.confirm_teaching_equivalent, name='confirm_teaching_equivalent'),
    url(r'^teaching/admin/instructor/' + USERID_SLUG + '/course/' + COURSE_SLUG + '/edit/$', planning_views.edit_course_offering_credits, name='edit_course_offering_credits'),

    url(r'^planning/teaching_plans$', planning_views.view_intentions, name='view_intentions'),
    url(r'^planning/teaching_plans/add$', planning_views.planner_create_intention, name='planner_create_intention'),
    url(r'^planning/teaching_plans/' + SEMESTER + '/$', planning_views.view_semester_intentions, name='view_semester_intentions'),
    url(r'^planning/teaching_plans/' + SEMESTER + '/add$', planning_views.planner_create_intention, name='planner_create_intention'),
    url(r'^planning/teaching_plans/' + SEMESTER + '/' + USERID_SLUG + '/edit$', planning_views.planner_edit_intention, name='planner_edit_intention'),
    url(r'^planning/teaching_plans/' + SEMESTER + '/' + USERID_SLUG + '/delete$', planning_views.planner_delete_intention, name='planner_delete_intention'),

    url(r'^planning/teaching_capabilities$', planning_views.view_capabilities, name='view_capabilities'),
    url(r'^planning/teaching_capabilities/' + USERID_SLUG + '/edit$', planning_views.planner_edit_capabilities, name='planner_edit_capabilities'),
    url(r'^planning/teaching_capabilities/' + USERID_SLUG + '/(?P<course_id>\w+)/delete$', planning_views.planner_delete_capability, name='planner_delete_capability'),

    url(r'^planning/$', planning_views.admin_index, name='admin_index'),
    url(r'^planning/add_plan$', planning_views.create_plan, name='create_plan'),
    url(r'^planning/copy_plan$', planning_views.copy_plan, name='copy_plan'),
    url(r'^planning/courses$', planning_views.manage_courses, name='manage_courses'),
    url(r'^planning/courses/add$', planning_views.create_course, name='create_course'),
    url(r'^planning/courses/(?P<course_slug>' + SLUG_RE + ')/edit$', planning_views.edit_course, name='edit_course'),
    url(r'^planning/courses/(?P<course_id>' + SLUG_RE + ')/delete$', planning_views.delete_course, name='delete_course'),
    url(r'^planning/' + SEMESTER + '/' + PLAN_SLUG + '/edit$', planning_views.edit_plan, name='edit_plan'),
    url(r'^planning/' + SEMESTER + '/' + PLAN_SLUG + '$', planning_views.update_plan, name='update_plan'),
    url(r'^planning/' + SEMESTER + '/' + PLAN_SLUG + '/' + PLANNED_OFFERING_SLUG + '/delete$', planning_views.delete_planned_offering, name='delete_planned_offering'),
    url(r'^planning/' + SEMESTER + '/' + PLAN_SLUG + '/' + PLANNED_OFFERING_SLUG + '/edit$', planning_views.edit_planned_offering, name='edit_planned_offering'),
    url(r'^planning/' + SEMESTER + '/' + PLAN_SLUG + '/' + PLANNED_OFFERING_SLUG + '/assign$', planning_views.view_instructors, name='view_instructors'),
    url(r'^planning/' + SEMESTER + '/' + PLAN_SLUG + '/delete$', planning_views.delete_plan, name='delete_plan'),

    url(r'^semester_plans/$', planning_views.plans_index, name='plans_index'),
    url(r'^semester_plans/' + SEMESTER + '/' + PLAN_SLUG + '$', planning_views.view_plan, name='view_plan'),
)
