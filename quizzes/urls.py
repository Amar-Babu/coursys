from django.conf.urls import url

from courselib.urlparts import USERID_OR_EMPLID
from . import views


quiz_patterns = [
    url(r'^$', views.index, name='index'),
    url(r'edit$', views.EditView.as_view(), name='edit'),
    url(r'edit/(?P<question_id>\d+)$', views.question_edit, name='question_edit'),
    url(r'add$', views.question_add, name='question_add'),
    url(r'preview$', views.preview_student, name='preview_student'),
    url(r'submissions/$', views.submissions, name='submissions'),
    url(r'submissions/' + USERID_OR_EMPLID + '$', views.view_submission, name='view_submission'),
    url(r'download$', views.download_submissions, name='download_submissions'),
]