from importlib import import_module
from .conf import settings

from celery import Celery
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)
app = Celery()
app.config_from_object(settings)

@app.task(bind=True, **settings.PIWIK_CELERY_TASK_KWARGS)
def track_page_view_task(self, kwargs):
    """
    Task to handle recording a request in Piwik asynchronously.
    """
    tracking_logic = import_module(settings.PIWIK_TRACKING_LOGIC).PiwikTrackerLogic()
    from .tracking import urllib_errors
    try:
        tracking_logic.do_track_page_view(fail_silently=False, **kwargs)
    except urllib_errors as exc:
        if self.request.retries == self.max_retries and settings.PIWIK_FAIL_SILENTLY:
            # don't allow the task to totally fail if we're asked not to.
            logger.error('Failing at Piwik API call.')
            return
        else:
            logger.warn('Retrying Piwik API call.')
            raise self.retry(exc=exc)