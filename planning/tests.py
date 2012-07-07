from django.test import TestCase
from django.test.client import Client
from settings import CAS_SERVER_URL
from django.core.urlresolvers import reverse
from courselib.testing import basic_page_tests


class PlanningTest(TestCase):
    fixtures = ['test_data']

    def test_planning_admin_returns_200_ok(self):
        """
        Tests basic page permissions
        """
        client = Client()
        client.login(ticket="dixon", service=CAS_SERVER_URL)
        url = reverse('planning.views.admin_index')
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        # Test create plan view
        url = reverse('planning.views.create_plan')
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        # Test copy plan view
        url = reverse('planning.views.copy_plan')
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        # Test update plan view
        url = reverse('planning.views.update_plan', kwargs={'semester': 1127, 'plan_slug': 'Offering-Alpha---Burnaby'})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        # Test edit plan view
        url = reverse('planning.views.edit_plan', kwargs={
                'semester': 1127,
                'plan_slug': 'Offering-Alpha---Burnaby'
        })
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        # Test assign instructor view
        url = reverse('planning.views.view_instructors', kwargs={
            'semester': 1127,
            'plan_slug': 'Offering-Alpha---Burnaby',
            'planned_offering_slug': 'CMPT-102-D100'
        })
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        # Test edit planned offering view
        url = reverse('planning.views.edit_planned_offering', kwargs={
            'semester': 1127,
            'plan_slug': 'Offering-Alpha---Burnaby',
            'planned_offering_slug': 'CMPT-102-D100'
        })
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        # Test manage courses view
        url = reverse('planning.views.manage_courses')
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        # Test create courses view
        url = reverse('planning.views.create_course')
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        # Test edit course view
        url = reverse('planning.views.edit_course', kwargs={'course_slug': 'CMPT-102'})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        # Test semester teaching plan view
        url = reverse('planning.views.view_intentions')
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        # Test create semester teaching plan view
        url = reverse('planning.views.planner_create_intention')
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        # Test create semester teaching plan view
        url = reverse('planning.views.view_capabilities')
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        # Test create semester teaching plan view
        url = reverse('planning.views.planner_edit_capabilities', kwargs={'userid': 'ggbaker'})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

    def test_planning_admin_returns_403_forbidden(self):
        """
        Tests basic page authentication for instructor
        """
        client = Client()
        client.login(ticket="ggbaker", service=CAS_SERVER_URL)
        response = client.get(reverse('planning.views.admin_index'))
        self.assertEqual(response.status_code, 403)

    def test_course_credits_inst_200_ok(self):
        client = Client()
        client.login(ticket="ggbaker", service=CAS_SERVER_URL)

        url = reverse('planning.views.view_teaching_credits_inst')
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        url = reverse('planning.views.view_teaching_equivalent_inst', kwargs={'equivalent_id': 1})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        url = reverse('planning.views.new_teaching_equivalent_inst')
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)

        url = reverse('planning.views.edit_teaching_equivalent_inst', kwargs={'equivalent_id': 1})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)
        
    def test_course_credits_admin_200_ok(self):
        client = Client()
        client.login(ticket="teachadmin", service=CAS_SERVER_URL)
        
        url = reverse('planning.views.view_insts_in_unit')
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)
        
        url = reverse('planning.views.view_teaching_credits_admin', kwargs={'userid': 'ggbaker'})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)
        
        url = reverse('planning.views.view_teaching_equivalent_admin', kwargs={'userid': 'ggbaker', 'equivalent_id': 1})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)
        
        url = reverse('planning.views.new_teaching_equivalent_admin', kwargs={'userid': 'ggbaker'})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)
        
        url = reverse('planning.views.edit_teaching_equivalent_admin', kwargs={'userid': 'ggbaker', 'equivalent_id': 1})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)
        
        url = reverse('planning.views.edit_course_offering_credits', kwargs={'userid': 'ggbaker', 'course_slug': '2012su-cmpt-383-d1'})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)
        
        
