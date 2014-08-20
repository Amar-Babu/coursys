from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
import django

from coredata.models import Semester, Unit
from coredata.queries import SIMSConn, SIMSProblem
from dashboard.photos import do_photo_fetch

import celery
import random, socket, subprocess, urllib2, os, stat


def _last_component(s):
    return s.split('.')[-1]

def _check_cert(filename):
    """
    Does this certificate file look okay?

    Returns error message, or None if okay
    """
    try:
        st = os.stat(filename)
    except OSError:
        return filename + " doesn't exist"
    else:
        good_perm = stat.S_IFREG | stat.S_IRUSR # | stat.S_IWUSR
        if (st[stat.ST_UID], st[stat.ST_GID]) != (0,0):
            return 'not owned by root.root'
        perm = st[stat.ST_MODE]
        if good_perm != perm:
            return "expected permissions %o but found %o." % (good_perm, perm)

def _check_file_create(directory):
    """
    Check that files can be created in the given directory.

    Returns error message, or None if okay
    """
    filename = os.path.join(directory, 'filewrite-' + str(os.getpid()) + '.tmp')

    if not os.path.isdir(directory):
        return 'directory does not exist'

    try:
        fh = open(filename, 'w')
    except IOError:
        return 'could not write to a file'
    else:
        fh.write('test file: may safely delete')
        fh.close()
        os.unlink(filename)



def settings_info():
    info = []
    info.append(('Deploy mode', settings.DEPLOY_MODE))
    info.append(('Database engine', _last_component(settings.DATABASES['default']['ENGINE'])))
    info.append(('Cache backend', _last_component(settings.CACHES['default']['BACKEND'])))
    info.append(('Haystack engine', _last_component(settings.HAYSTACK_CONNECTIONS['default']['ENGINE'])))
    info.append(('Email backend', '.'.join(settings.EMAIL_BACKEND.split('.')[-2:])))
    if hasattr(settings, 'CELERY_EMAIL') and settings.CELERY_EMAIL:
        info.append(('Celery email backend', '.'.join(settings.CELERY_EMAIL_BACKEND.split('.')[-2:])))
    if hasattr(settings, 'BROKER_URL'):
        info.append(('Celery broker', settings.BROKER_URL.split(':')[0]))

    return info


def deploy_checks():
    passed = []
    failed = []

    # cache something now to see if it's still there further down.
    randval = random.randint(1, 1000000)
    cache.set('check_things_cache_test', randval, 60)

    # Django database
    try:
        n = Semester.objects.all().count()
        if n > 0:
            passed.append(('Main database connection', 'okay'))
        else:
            failed.append(('Main database connection', "Can't find any coredata.Semester objects"))
    except django.db.utils.OperationalError:
        failed.append(('Main database connection', "can't connect to database"))
    except django.db.utils.ProgrammingError:
        failed.append(('Main database connection', "database tables missing"))

    # Celery tasks
    celery_okay = False
    try:
        if settings.USE_CELERY:
            try:
                from coredata.tasks import ping
            except ImportError:
                failed.append(('Celery task', "Couldn't import task: probably missing MySQLdb module"))
            else:
                t = ping.apply_async()
                res = t.get(timeout=5)
                if res == True:
                    passed.append(('Celery task', 'okay'))
                    celery_okay = True
                else:
                    failed.append(('Celery task', 'got incorrect result from task'))
        else:
            failed.append(('Celery task', 'celery disabled in settings'))
    except celery.exceptions.TimeoutError:
        failed.append(('Celery task', "didn't get result before timeout: celeryd maybe not running"))
    except socket.error:
        failed.append(('Celery task', "can't communicate with broker"))
    except NotImplementedError:
        failed.append(('Celery task', 'celery disabled'))
    except django.db.utils.ProgrammingError:
        failed.append(('Celery task', 'celery DB tables missing'))
    except django.db.utils.OperationalError:
        failed.append(('Celery task', 'djkombu tables missing: try migrating'))

    # Django cache
    # (has a subprocess do something to make sure we're in a persistent shared cache, not DummyCache)
    subprocess.call(['python', 'manage.py', 'check_things', '--cache_subcall'])
    cache_okay = False
    res = cache.get('check_things_cache_test')
    if res == randval:
        failed.append(('Django cache', 'other processes not sharing cache: dummy/local probably being used instead of memcached'))
    elif res is None:
        failed.append(('Django cache', 'unable to retrieve anything from cache'))
    elif res != randval + 1:
        failed.append(('Django cache', 'unknown result'))
    else:
        passed.append(('Django cache', 'okay'))
        cache_okay = True

    # Reporting DB connection
    try:
        db = SIMSConn()
        db.execute("SELECT last_name FROM ps_names WHERE emplid=200133427", ())
        n = len(list(db))
        if n > 0:
            passed.append(('Reporting DB connection', 'okay'))
        else:
            failed.append(('Reporting DB connection', 'query inexplicably returned nothing'))
    except SIMSProblem as e:
        failed.append(('Reporting DB connection', 'SIMSProblem, %s' % (unicode(e))))

    # compression enabled?
    if settings.COMPRESS_ENABLED:
        passed.append(('Asset compression enabled', 'okay'))
    else:
        failed.append(('Asset compression enabled', 'disabled in settings'))

    # Haystack searching
    from haystack.query import SearchQuerySet
    try:
        res = SearchQuerySet().filter(text='cmpt')
        if res:
            passed.append(('Haystack search', 'okay'))
        else:
            failed.append(('Haystack search', 'nothing found: maybe update_index, or wait for search server to fully start'))
    except IOError:
        failed.append(('Haystack search', "can't read/write index"))

    # photo fetching
    if cache_okay and celery_okay:
        try:
            res = do_photo_fetch(['301222726'])
            if '301222726' not in res: # I don't know who 301222726 is, but he/she is real.
                failed.append(('Photo fetching', "didn't find photo we expect to exist"))
            else:
                passed.append(('Photo fetching', 'okay'))
        except (KeyError, Unit.DoesNotExist, django.db.utils.ProgrammingError):
            failed.append(('Photo fetching', 'photo password not set'))
        except urllib2.HTTPError as e:
            failed.append(('Photo fetching', 'failed to fetch photo (%s). Maybe wrong password?' % (e)))
    else:
        failed.append(('Photo fetching', 'not testing since memcached or celery failed'))


    # certificates
    bad_cert = 0
    res = _check_cert('/etc/stunnel/stunnel.pem')
    if res:
        failed.append(('Stunnel cert', res))
        bad_cert += 1
    res = _check_cert('/etc/nginx/cert.pem')
    if res:
        failed.append(('SSL PEM', res))
        bad_cert += 1
    res = _check_cert('/etc/nginx/cert.key')
    if res:
        failed.append(('SSL KEY', res))
        bad_cert += 1

    if bad_cert == 0:
        passed.append(('Certificates', 'All okay, but maybe check http://www.digicert.com/help/'))

    # SVN database
    if settings.SVN_DB_CONNECT:
        from courselib.svn import SVN_TABLE, _db_conn
        import MySQLdb
        try:
            db = _db_conn()
            db.execute('SELECT count(*) FROM '+SVN_TABLE, ())
            n = list(db)[0][0]
            if n > 0:
                passed.append(('SVN database', 'okay'))
            else:
                failed.append(('SVN database', "couldn't access records"))
        except MySQLdb.OperationalError:
            failed.append(('SVN database', "can't connect to database"))
    else:
        failed.append(('SVN database', 'SVN_DB_CONNECT not set in secrets.py'))

    # AMAINT database
    if settings.AMAINT_DB_PASSWORD:
        from coredata.importer import AMAINTConn
        import MySQLdb
        try:
            db = AMAINTConn()
            db.execute("SELECT count(*) FROM idMap", ())
            n = list(db)[0][0]
            if n > 0:
                passed.append(('AMAINT database', 'okay'))
            else:
                failed.append(('AMAINT database', "couldn't access records"))
        except MySQLdb.OperationalError:
            failed.append(('AMAINT database', "can't connect to database"))
    else:
        failed.append(('AMAINT database', 'AMAINT_DB_PASSWORD not set in secrets.py'))


    # file creation in the necessary places
    dirs_to_check = [
        (settings.DB_BACKUP_DIR, 'DB backup dir'),
        (settings.SUBMISSION_PATH, 'submitted files path'),
        (os.path.join(settings.COMPRESS_ROOT, 'CACHE'), 'compressed media root'),
    ]
    for directory, label in dirs_to_check:
        res = _check_file_create(directory)
        if res is None:
            passed.append(('File creation in ' + label, 'okay'))
        else:
            failed.append(('File creation in ' + label, res))

    # are any services listening publicly that shouldn't?
    hostname = socket.gethostname()
    ports = [
        25, # mail server
        4369, # epmd, erlang port mapper daemon
        45130, # beam? rabbitmq something
        4000, # main DB stunnel
        50000, # reporting DB
        8000, # gunicorn
        11211, # memcached
        9200, 9300, # elasticsearch
    ]
    connected = []
    for p in ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((hostname, p))
        except socket.error:
            # couldn't connect: good
            pass
        else:
            connected.append(p)
        finally:
            s.close()

    if connected:
        failed.append(('Ports listening externally', 'got connections to port ' + ','.join(str(p) for p in connected)))
    else:
        passed.append(('Ports listening externally', 'okay'))


    return passed, failed


def send_test_email(email):
    try:
        send_mail('check_things test message', "This is a test message to make sure they're getting through.",
                  settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
        return True, "Message sent to %s." % (email)
    except socket.error:
        return False, "socket error: maybe can't communicate with AMPQ for celery sending?"
