from django.conf.urls import url
from . import views


quiz_patterns = [
    url(r'^$', views.index, name='index'),
    url(r'edit', views.EditView.as_view(), name='edit'),

]