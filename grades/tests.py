from django.test import TestCase
from grades.formulas import *
from grades.models import *
from coredata.models import *
from coredata.tests import create_offering
import pickle

from django.test.client import Client
from settings import CAS_SERVER_URL
from courselib.testing import *

# TODO: test activity modifiers ([A1.max], [A1.percent], [A1.final])

test_formulas = [ # expression, correct-result pairs
        ("-[A1] + +2", -8),
        ("9 + 2 - 3", 8),
        ("9 + 2 * 3", 15),
        ("(9 + 2) * 3", 33),
        ("[A1]/20+-3", -2.5),
        ("[Assignment #1]/20+-3", -2.5),
        ("SUM(1, 12.5, 3.4e2)", 353.5),
        ("SUM([A1]*2,[A2]/2)", 35),
        ("MAX([A1],[A2])", 30),
        ("max([A1],[A2])", 30),
        ("Min([A1],[A2], 12)", 10),
        ("AVG([A1],[A2], 12)", 17.3333333333333),
        (u"BEST(2, [A1], [A2])", 40),
        (u"BEST(2, [A1], [\u00b6],[A2], 12,-123)", 42),
        (u"BEST(3, [A1], [\u00b6],[A2], 12,123   )  ", 165),
        (u"[\u00b6] + 1", 5.5),
        ]

class GradesTest(TestCase):
    fixtures = ['test_data']
    
    def setUp(self):
        pass

    def test_formulas(self):
        """
        Test the formula parsing & evaluation.
        """
        # set up course and related data
        s, c = create_offering()
        p = Person.objects.get(userid="0kvm")
        m = Member(person=p, offering=c, role="STUD", credits=3, added_reason="UNK")
        m.save()
       
        a = NumericActivity(name="Paragraph", short_name=u"\u00b6", status="RLS", offering=c, position=3, max_grade=40)
        a.save()
        g = NumericGrade(activity=a, member=m, value="4.5", flag="CALC")
        g.save()
        a = NumericActivity(name="Assignment #1", short_name="A1", status="RLS", offering=c, position=1, max_grade=15)
        a.save()
        g = NumericGrade(activity=a, member=m, value=10, flag="GRAD")
        g.save()
        a = NumericActivity(name="Assignment #2", short_name="A2", status="RLS", offering=c, position=2, max_grade=40)
        a.save()
        g = NumericGrade(activity=a, member=m, value=30, flag="GRAD")
        g.save()
        
        activities = NumericActivity.objects.filter(offering=c)
        act_dict = activities_dictionary(activities)
        
        # make sure a formula can be pickled and unpickled safely (i.e. can be cached)
        tree = parse("sum([Assignment #1], [A1], [A2])/20*-3")
        p = pickle.dumps(tree)
        tree2 = pickle.loads(p)
        self.assertEqual(tree, tree2)
        # check that it found the right list of columns used
        self.assertEqual(cols_used(tree), set(['A1', 'A2', 'Assignment #1']))
        
        # test parsing and evaluation to make sure we get the right values out
        for expr, correct in test_formulas:
            tree = parse(expr)
            res = eval_parse(tree, act_dict, m)
            self.assertAlmostEqual(correct, res, msg=u"Incorrect result for %s"%(expr,))

        # test some badly-formed stuff for appropriate exceptions
        tree = parse("1 + BEST(3, [A1], [A2])")
        self.assertRaises(EvalException, eval_parse, tree, act_dict, m)
        tree = parse("1 + BEST(0, [A1], [A2])")
        self.assertRaises(EvalException, eval_parse, tree, act_dict, m)
        tree = parse("[Foo] /2")
        self.assertRaises(KeyError, eval_parse, tree, act_dict, m)
        tree = parse("[a1] /2")
        self.assertRaises(KeyError, eval_parse, tree, act_dict, m)
        
        self.assertRaises(ParseException, parse, "AVG()")
        self.assertRaises(ParseException, parse, "(2+3*84")
        self.assertRaises(ParseException, parse, "2+3**84")
        self.assertRaises(ParseException, parse, "AVG(2,3,4")
        
        # test unreleased/missing grade conditions
        expr = "[Assignment #2]"
        tree = parse(expr)
        
        # unrelased assignment (with grade)
        a.status='URLS'
        a.save()
        activities = NumericActivity.objects.filter(offering=c)
        act_dict = activities_dictionary(activities)
        res = eval_parse(tree, act_dict, m)
        self.assertAlmostEqual(res, 0.0)
        
        # explicit no grade (relased assignment)
        g.flag="NOGR"
        g.save()
        a.status='RLS'
        a.save()
        activities = NumericActivity.objects.filter(offering=c)
        act_dict = activities_dictionary(activities)
        res = eval_parse(tree, act_dict, m)
        self.assertAlmostEqual(res, 0.0)

        # no grade in database (relased assignment)
        g.delete()
        activities = NumericActivity.objects.filter(offering=c)
        act_dict = activities_dictionary(activities)
        res = eval_parse(tree, act_dict, m)
        self.assertAlmostEqual(res, 0.0)

    def test_activities(self):
        """
        Test activity classes: subclasses, selection, sorting.
        """
        s, c = create_offering()
       
        a = NumericActivity(name="Assignment 1", short_name="A1", status="RLS", offering=c, position=2, max_grade=15)
        a.save()
        a = NumericActivity(name="Assignment 2", short_name="A2", status="RLS", offering=c, position=6, max_grade=15)
        a.save()
        a = LetterActivity(name="Project", short_name="Proj", status="URLS", offering=c, position=1)
        a.save()
        a = CalNumericActivity(name="Total", short_name="Total", status="URLS", offering=c, position=42, max_grade=30, formula="[A1]+[A2]")
        a.save()
       
        allact = all_activities_filter(offering=c)
        self.assertEqual(len(allact), 4)
        self.assertEqual(allact[0].slug, 'proj') # make sure position=1 is first
        self.assertEqual(type(allact[1]), NumericActivity)
        self.assertEqual(type(allact[3]), CalNumericActivity)
        
    def test_activity_pages(self):
        """
        Test pages around activities
        """
        s, c = create_offering()

        # add some assignments and members
        a = NumericActivity(name="Assignment 1", short_name="A1", status="RLS", offering=c, position=2, max_grade=15, percent=10)
        a.save()
        a1=a
        a = NumericActivity(name="Assignment 2", short_name="A2", status="URLS", offering=c, position=6, max_grade=20, group=True)
        a.save()
        p = Person.objects.get(userid="ggbaker")
        m = Member(person=p, offering=c, role="INST", added_reason="UNK")
        m.save()
        p = Person.objects.get(userid="0kvm")
        m = Member(person=p, offering=c, role="STUD", added_reason="UNK")
        m.save()
        
        # test instructor pages
        client = Client()
        client.login(ticket="ggbaker", service=CAS_SERVER_URL)

        response = basic_page_tests(self, client, '/' + c.slug + '/')
        self.assertContains(response, 'href="' + reverse('groups.views.groupmanage', kwargs={'course_slug':c.slug}) +'"')

        basic_page_tests(self, client, c.get_absolute_url())
        basic_page_tests(self, client, c.get_absolute_url() + '_students/0kvm')
        basic_page_tests(self, client, reverse('grades.views.add_numeric_activity', kwargs={'course_slug':c.slug}))
        basic_page_tests(self, client, reverse('grades.views.add_letter_activity', kwargs={'course_slug':c.slug}))

        # test student pages
        client = Client()
        client.login(ticket="0kvm", service=CAS_SERVER_URL)
        response = basic_page_tests(self, client, '/' + c.slug + '/')
        self.assertContains(response, "Gregory Baker")
        self.assertContains(response, 'href="' + reverse('groups.views.groupmanage', kwargs={'course_slug':c.slug}) +'"')

        response = basic_page_tests(self, client, a.get_absolute_url())
        # small class (one student) shouldn't contain summary stats
        self.assertNotContains(response, "Histogram")
        self.assertNotContains(response, "Standard Deviation")

    def test_instructor_workflow(self):
        """
        Work through the site as an instructor
        """
        s, c = create_offering()
        userid1 = "0kvm"
        userid2 = "0aaa0"
        userid3 = "0aaa1"
        userid4 = "ggbaker"
        for u in [userid1, userid2, userid3, userid4]:
            p = Person.objects.get(userid=u)
            m = Member(person=p, offering=c, role="STUD", credits=3, career="UGRD", added_reason="UNK")
            m.save()
        m.role="INST"
        m.save()
        
        client = Client()
        client.login(ticket="ggbaker", service=CAS_SERVER_URL)
        
        # course main screen
        url = reverse('grades.views.course_info', kwargs={'course_slug': c.slug})
        response = basic_page_tests(self, client, url)
        url = reverse('grades.views.add_numeric_activity', kwargs={'course_slug': c.slug})
        self.assertContains(response, 'href="' + url +'"')
        
        # add activity
        import datetime
        now = datetime.datetime.now()
        due = now + datetime.timedelta(days=7)
        response = client.post(url, {'name':'Assignment 1', 'short_name':'A1', 'status':'URLS', 'due_date_0':due.strftime('%Y-%m-%d'), 'due_date_1':due.strftime('%H:%M:%S'), 'percent': '10', 'group': '1', 'max_grade': 25})
        self.assertEquals(response.status_code, 302)
        
        acts = NumericActivity.objects.filter(offering=c)
        self.assertEquals(len(acts), 1)
        a = acts[0]
        self.assertEquals(a.name, "Assignment 1")
        self.assertEquals(a.slug, "a1")
        self.assertEquals(a.max_grade, 25)
        self.assertEquals(a.group, False)
        self.assertEquals(a.deleted, False)
        
        # add calculated numeric activity
        url = reverse('grades.views.add_cal_numeric_activity', kwargs={'course_slug': c.slug})
        response = basic_page_tests(self, client, url)
        response = client.post(url, {'name':'Total', 'short_name':'Total', 'status':'URLS', 'group': '1', 'max_grade': 30, 'formula': '[A1]+5'})
        self.assertEquals(response.status_code, 302)

        acts = CalNumericActivity.objects.filter(offering=c)
        self.assertEquals(len(acts), 1)
        a = acts[0]
        self.assertEquals(a.slug, "total")
        self.assertEquals(a.max_grade, 30)
        self.assertEquals(a.group, False)
        self.assertEquals(a.deleted, False)
        self.assertEquals(a.formula, '[A1]+5')
        
        # formula tester
        url = reverse('grades.views.formula_tester', kwargs={'course_slug': c.slug})
        response = basic_page_tests(self, client, url)
        response = client.post(url, {'formula': '[A1]+5', 'a1-status': 'RLS', 'a1-value': '6', 'total-status': 'URLS'})
        self.assertContains(response, '<div id="formula_result">11.0</div>')
        validate_content(self, response.content, url)
        
        

