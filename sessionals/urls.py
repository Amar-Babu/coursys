from django.conf.urls import url
from sessionals import views
from courselib.urlparts import SLUG_RE, ID_RE


ACCOUNT_ID = '(?P<account_id>' + ID_RE + ')'
ACCOUNT_SLUG = '(?P<account_slug>' + SLUG_RE + ')'
CONFIG_SLUG = '(?P<config_slug>' + SLUG_RE + ')'


sessionals_patterns = [ # prefix /sessionals/
    url(r'^$', views.sessionals_index, name='sessionals_index'),
    url(r'^manage_accounts/$', views.manage_accounts, name='manage_accounts'),
    url(r'^new_account/$', views.new_account, name='new_account'),
    url(r'^' + ACCOUNT_SLUG + '/edit$', views.edit_account, name='edit_account'),
    url(r'^' + ACCOUNT_ID + '/delete$', views.delete_account, name='delete_account'),
    url(r'^' + ACCOUNT_SLUG + '/view$', views.view_account, name='view_account'),
    url(r'^manage_configs/$', views.manage_configs, name='manage_configs'),
    url(r'^new_config/$', views.new_config, name='new_config'),
    url(r'^config/' + CONFIG_SLUG + '/edit$', views.edit_config, name='edit_config'),
    ]
