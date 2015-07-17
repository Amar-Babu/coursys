from django.conf import settings
from appconf import AppConf

class PiwikAppConf(AppConf):
    SITEID = 1
    URL = 'http://example.com/piwik/piwik.php'
    TOKEN = None
    TRACKING_LOGIC = 'piwik_middleware.tracking'
    CELERY = False
    CELERY_TASK_KWARGS = {}

    class Meta:
        prefix = 'piwik'