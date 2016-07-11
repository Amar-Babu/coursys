from courselib.testing import test_views, Client
from django.test import TestCase
from django.core.urlresolvers import reverse


class InventoryTestCase(TestCase):
    fixtures = ['basedata', 'coredata', 'inventory']

    def test_unaccessible_pages(self):
        client = Client()
        # First, without logging in:
        url = reverse('inventory_index')
        response = client.get(url)
        self.assertEquals(response.status_code, 302)

        # Now log in but without the correct role
        client.login_user('pba7')
        response = client.get(url)
        self.assertEquals(response.status_code, 403)


    def test_pages(self):
        client = Client()
        asset_slug = 'cmpt-something'
        asset_id = 1
        client.login_user('ggbaker')
        test_views(self, client, '', ['inventory_index', 'new_asset'], {})
        test_views(self, client, '', ['edit_asset', 'view_asset'], {'asset_slug': asset_slug})
        url = reverse('delete_asset', kwargs={'asset_id': asset_id})
        response = client.post(url, follow=True)
        self.assertEquals(response.status_code, 200)
