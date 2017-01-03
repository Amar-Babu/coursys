from django.conf.urls import url, include
from django.views.generic import RedirectView
from courselib.urlparts import USERID_SLUG, ACTIVITY_SLUG

from discipline.urls import discipline_offering_patterns
from discuss.urls import discussion_patterns
from groups.urls import group_patterns
from marking.urls import marking_patterns
from pages.urls import pages_patterns
from submission.urls import submission_patterns

activity_patterns = [ # prefix /COURSE_SLUG/+ACTIVITY_SLUG/
    url(r'^$', 'grades.views.activity_info', name='activity_info'),
    url(r'^stat$', 'grades.views.activity_stat', name='activity_stat'),
    url(r'^cal_all$', 'grades.views.calculate_all', name='calculate_all'),
    url(r'^cal_all_letter$', 'grades.views.calculate_all_lettergrades', name='calculate_all_lettergrades'),
    url(r'^cal_idv_ajax$', 'grades.views.calculate_individual_ajax', name='calculate_individual_ajax'),
    url(r'^official$', 'grades.views.compare_official', name='compare_official'),
    url(r'^change/' + USERID_SLUG + '$', 'grades.views.grade_change', name='grade_change'),
    #url(r'^' + USERID_SLUG + '/cal_idv$', 'grades.views.calculate_individual', name='calculate_individual'),
    url(r'^edit$', 'grades.views.edit_activity', name='edit_activity'),
    url(r'^cutoffs$', 'grades.views.edit_cutoffs', name='edit_cutoffs'),
    url(r'^groups$', 'grades.views.activity_info_with_groups', name='activity_info_with_groups'),
    url(r'^release$', 'grades.views.release_activity', name='release_activity'),
    url(r'^delete$', 'grades.views.delete_activity', name='delete_activity'),

    url(r'^gradestatus/' + USERID_SLUG + '/$', 'marking.views.change_grade_status', name='change_grade_status'),
    url(r'^csv$', 'marking.views.export_csv', name='export_csv'),
    url(r'^sims_csv$', 'marking.views.export_sims', name='export_sims'),

    url(r'^markall/students$', 'marking.views.mark_all_students', name='mark_all_students'),
    url(r'^markall/groups$', 'marking.views.mark_all_groups', name='mark_all_groups'),

    url(r'^submission/', include(submission_patterns, namespace='submission')),
    url(r'^marking/', include(marking_patterns, namespace='marking')),
]

offering_patterns = [ # prefix /COURSE_SLUG/
    url(r'^$', 'grades.views.course_info', name='course_info'),
    url(r'^reorder_activity$', 'grades.views.reorder_activity', name='reorder_activity'),
    url(r'^new_message$', 'grades.views.new_message', name='new_message'),
    url(r'^config/$', 'grades.views.course_config', name='course_config'),
    url(r'^config/tas$', 'coredata.views.manage_tas', name='manage_tas'),
    url(r'^config/copysetup$', 'marking.views.copy_course_setup', name='copy_course_setup'),

    url(r'^grades$', 'grades.views.all_grades', name='all_grades'),
    url(r'^grades_csv$', 'grades.views.all_grades_csv', name='all_grades_csv'),
    url(r'^activity_choice$', 'grades.views.activity_choice', name='activity_choice'),
    url(r'^new_numeric$', 'grades.views.add_numeric_activity', name='add_numeric_activity'),
    url(r'^new_letter$', 'grades.views.add_letter_activity', name='add_letter_activity'),
    url(r'^new_cal_numeric$', 'grades.views.add_cal_numeric_activity', name='add_cal_numeric_activity'),
    url(r'^new_cal_letter$', 'grades.views.add_cal_letter_activity', name='add_cal_letter_activity'),
    url(r'^formula_tester$', 'grades.views.formula_tester', name='formula_tester'),
    url(r'^list$', 'grades.views.class_list', name='class_list'),
    url(r'^photolist$', 'grades.views.photo_list', name='photo_list'),
    url(r'^photolist-(?P<style>\w+)$', 'grades.views.photo_list', name='photo_list'),
    url(r'^students/$', 'grades.views.student_search', name='student_search'),
    url(r'^students/' + USERID_SLUG + '$', 'grades.views.student_info', name='student_info'),
    url(r'^grade-history$', 'grades.views.grade_history', name='grade_history'),
    url(r'^export$', 'grades.views.export_all', name='export_all'),

    url(r'^config/tugs/' + USERID_SLUG + '/$', 'ta.views.view_tug', name='view_tug'),
    url(r'^config/tugs/' + USERID_SLUG + '/new$', 'ta.views.new_tug', name='new_tug'),
    url(r'^config/tugs/' + USERID_SLUG + '/edit$', 'ta.views.edit_tug', name='edit_tug'),
    url(r'^config/taoffers/$', 'ta.views.ta_offers', name='ta_offers'),

    url(r'^groups$', RedirectView.as_view(url='/%(course_slug)s/groups/', permanent=True)),
    url(r'^groups/', include(group_patterns, namespace='groups')),
    url(r'^discussion/', include(discussion_patterns, namespace='discussion')),

    url(r'^\+' + ACTIVITY_SLUG + '/', include(activity_patterns)),
    url(r'^dishonesty/', include(discipline_offering_patterns, namespace='discipline')),
    url(r'^pages/', include(pages_patterns, namespace='pages')),

    # redirect for old-style activity URLs (must be last to avoid conflict with other rules)
    url(r'^' + ACTIVITY_SLUG + '/(?P<tail>.*)$', 'grades.views.activity_info_oldurl', name='activity_info_oldurl'),
]
