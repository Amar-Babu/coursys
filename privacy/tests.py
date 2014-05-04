from django.test import TestCase
from django.core.urlresolvers import reverse
from courselib.testing import basic_page_tests, Client

from coredata.models import Person

class PrivacyTestCase(TestCase):
    fixtures = ['test_data']

    def test_workflow(self):
        """
        Test the privacy policy workflow and page exclusions
        """
        # clear privacy agreement from test data
        p = Person.objects.get(userid='dzhao')
        p.config = {}
        p.save()

        client = Client()
        client.login_user(p.userid)
        privacy_url = reverse('privacy.views.privacy')

        # non-role page should still render
        url = reverse('dashboard.views.index')
        basic_page_tests(self, client, url)

        # but role page should redirect to agreement
        url = reverse('advisornotes.views.advising')
        response = client.get(url)
        self.assertRedirects(response, privacy_url + '?next=' + url)

        # check privacy page
        basic_page_tests(self, client, privacy_url)

        # submit and expect recorded agreement
        response = client.post(privacy_url + '?next=' + url, {'agree': 'on'})
        self.assertRedirects(response, url)
        p = Person.objects.get(userid='dzhao')
        self.assertTrue(p.config['privacy_signed'])

        # now we should be able to access
        basic_page_tests(self, client, url)


