from coredata.models import Person
from django.db import transaction

class SIMSConn(object):
    """
    Singleton object representing SIMS DB connection
    
    Exceptions that might be thrown:
      SIMSConn.DatabaseError
    
    singleton pattern implementation from: http://stackoverflow.com/questions/42558/python-and-the-singleton-pattern
    
    Absolutely NOT thread safe.
    Implemented as a singleton to minimize number of times SIMS connection overhead occurs.
    Should only be created on-demand (in function) to minimize startup for non-SIMS requests.
    """
    sims_user = "ggbaker"
    sims_db = "csrpt"
    dbpass_file = "./dbpass"
    table_prefix = "dbsastg."
    
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SIMSConn, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        self.conn, self.db = self.get_connection()

    def get_connection(self):
        passfile = open(self.dbpass_file)
        _ = passfile.next()
        _ = passfile.next()
        _ = passfile.next()
        simspasswd = passfile.next().strip()
        
        import DB2
        SIMSConn.DatabaseError = DB2.DatabaseError
        dbconn = DB2.connect(dsn=self.sims_db, uid=self.sims_user, pwd=simspasswd)
        return dbconn, dbconn.cursor()

    def escape_arg(self, a):
        """
        Escape argument for DB2
        """
        # Based on description of PHP's db2_escape_string
        if type(a) in (int,long):
            return str(a)
        
        a = unicode(a).encode('utf8')
        # assume it's a string if we don't know any better
        a = a.replace("\\", "\\\\")
        a = a.replace("'", "\\'")
        a = a.replace('"', '\\"')
        a = a.replace("\r", "\\r")
        a = a.replace("\n", "\\n")
        a = a.replace("\x00", "\\\x00")
        a = a.replace("\x1a", "\\\x1a")
        return "'"+a+"'"

    def execute(self, query, args):
        "Execute a query, safely substituting arguments"
        # should be ensuring real/active connection here?
        clean_args = tuple((self.escape_arg(a) for a in args))
        real_query = query % clean_args
        #print ">>>", real_query
        return self.db.execute(real_query)


    def prep_value(self, v):
        """
        get DB2 value into a useful format
        """
        if isinstance(v, basestring):
            return v.strip().decode('utf8')
        else:
            return v

    def __iter__(self):
        "Iterate query results"
        row = self.db.fetchone()
        while row:
            yield tuple((self.prep_value(v) for v in row))
            row = self.db.fetchone()

    def rows(self):
        "List of query results"
        return list(self.__iter__())


class SIMSProblem(unicode):
    """
    Class used to pass back problems with the SIMS connection.
    """
    pass

def SIMS_problem_handler(func):
    """
    Decorator to deal somewhat gracefully with any SIMS database problems.
    Any decorated function may return a SIMSProblem instance to indicate a
    problem with the database connection.
    
    Should be applied to any functions that use a SIMSConn object.
    """
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # check for the types of errors we know might happen
            # (need more than regular exception syntax, since SIMSConn.DatabaseError isn't always there)
            if hasattr(SIMSConn, 'DatabaseError') and isinstance(e, SIMSConn.DatabaseError):
                return SIMSProblem("could not connect to reporting database")
            elif isinstance(e, ImportError):
                return SIMSProblem("could not import DB2 module")
            raise e

    wrapped.__name__ = func.__name__
    return wrapped

@SIMS_problem_handler
def find_person(emplid):
    """
    Find the person in SIMS: return data or None (not found) or a SIMSProblem instance (error message).
    """
    db = SIMSConn()
    db.execute("SELECT emplid, last_name, first_name, middle_name FROM dbsastg.ps_personal_data WHERE emplid=%s",
               (str(emplid),))

    for emplid, last_name, first_name, middle_name in db:
        return {'emplid': emplid, 'last_name': last_name, 'first_name': first_name, 'middle_name': middle_name}

def add_person(emplid):
    """
    Add a Person object based on the found SIMS data
    """
    data = find_person(emplid)
    if not data:
        return
    elif isinstance(data, SIMSProblem):
        return data

    with transaction.commit_on_success():
        ps = Person.objects.filter(emplid=data['emplid'])
        if ps:
            # person already there: ignore
            return ps[0]
        p = Person(emplid=data['emplid'], userid=None, last_name=data['last_name'], first_name=data['first_name'],
                   pref_first_name=data['first_name'], middle_name=data['middle_name'])
        p.save()
    return p




