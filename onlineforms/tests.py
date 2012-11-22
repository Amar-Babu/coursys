from django.test import TestCase
from django.db.utils import IntegrityError
from django.test.client import Client
from django.core.urlresolvers import reverse

from django.forms import Field as DjangoFormsField, Form as DjangoForm

from coredata.models import Person, Unit
from settings import CAS_SERVER_URL
from courselib.testing import basic_page_tests

from onlineforms.models import FormGroup, Form, Sheet, Field
from onlineforms.models import FormSubmission, SheetSubmission, FieldSubmission, SheetSubmissionSecretUrl
from onlineforms.models import FIELD_TYPE_MODELS

from onlineforms.views import get_sheet_submission_url


def log_in():
    logged_in_person = Person.objects.get(userid="ggbaker")
    # log them in
    client = Client()
    client.login(ticket=logged_in_person.userid, service=CAS_SERVER_URL)
    return client


class ModelTests(TestCase):
    fixtures = ['test_data']

    def setUp(self):
        self.unit = Unit.objects.get(label="COMP")

    def test_FormGroup(self):
        groupName = "admins_test"
        u1 = Unit.objects.get(label="COMP")
        u2 = Unit.objects.get(label="ENG")
        # Test saving one form group
        fg = FormGroup(name=groupName, unit=u1)
        fg.save()
        self.assertEqual(fg.name, groupName)
        # now try adding another fromgroup in the same name with the same unit
        # should throw an db integrity exception
        fg2 = FormGroup(name=groupName, unit=u1)
        self.assertRaises(IntegrityError, fg2.save)
        # now add a formgroup with the same name into a different unit
        fg2 = FormGroup(name=groupName, unit=u2)
        fg2.save()
        self.assertEqual(fg2.name, groupName)
        self.assertEqual(fg2.unit, u2)
        # add some people to the fg
        p1 = Person.objects.get(userid="ggbaker")
        p2 = Person.objects.get(userid="dzhao")
        fg.members.add(p1)
        fg.members.add(p2)
        self.assertEqual(len(fg.members.all()), 2)

    def test_coherence_mixin(self):
        """
        Make sure .active and .original are getting manipulated correctly.
        """
        # create new form
        form = Form(title="Test Form", unit=self.unit, owner=FormGroup.objects.all()[0])
        form.save()
        orig_form_id = form.id
        self.assertEqual(form.active, True)
        self.assertEqual(form.original_id, orig_form_id)

        # make a clone and save
        form = form.clone()
        form.save()

        # check the state of the forms
        self.assertEqual(form.active, True)
        self.assertEqual(form.original_id, orig_form_id)
        self.assertNotEqual(form.id, orig_form_id)
        orig_form = Form.objects.get(id=orig_form_id)
        self.assertEqual(orig_form.original_id, orig_form_id)
        self.assertEqual(orig_form.active, False)

        # create a sheet
        sheet = Sheet(form=form, title="Test Sheet", is_initial=True)
        sheet.save()
        orig_sheet_id = sheet.id
        self.assertEqual(sheet.active, True)
        self.assertEqual(sheet.original_id, orig_sheet_id)
        # fake a same-original sheet on another version of the form
        sheetX = Sheet(form=orig_form, title="Test Sheet", is_initial=True, original=sheet.original)
        sheetX.save()

        # make a clone and save
        sheet = sheet.clone()
        sheet.save()

        # check the state of the forms
        self.assertEqual(sheet.active, True)
        self.assertEqual(sheet.original_id, orig_sheet_id)
        self.assertNotEqual(sheet.id, orig_sheet_id)
        orig_sheet = Sheet.objects.get(id=orig_sheet_id)
        self.assertEqual(orig_sheet.original_id, orig_sheet_id)
        self.assertEqual(orig_sheet.active, False)
        self.assertEqual(sheetX.active, True)  # cousin shouldn't be deactivated, since it's on a different version of the form

    def test_sheet_copy(self):
        fg = FormGroup.objects.create(name="Admin Test", unit=self.unit)
        form = Form.objects.create(title="Test Form", unit=self.unit, owner=fg)
        sheet1 = Sheet.objects.create(title="Initial Sheet", form=form)
        # create three fields
        Field.objects.create(label="F1", sheet=sheet1)
        Field.objects.create(label="F2", sheet=sheet1)
        Field.objects.create(label="F3", sheet=sheet1, active=False)

        self.assertEqual(Field.objects.filter(sheet=sheet1).count(), 3)
        self.assertEqual(Field.objects.filter(sheet=sheet1, active=True).count(), 2)

        # copy the sheet and make sure things are okay
        sheet2 = sheet1.safe_save()
        sheet1 = Sheet.objects.get(id=sheet1.id)  # get sheet1 again, as changed in the DB

        self.assertEqual(sheet1.original, sheet2.original)
        self.assertEqual(sheet1, sheet2.original)
        self.assertTrue(sheet2.active)
        self.assertFalse(sheet1.active)
        self.assertEqual(Field.objects.filter(sheet=sheet1).count(), 3)
        self.assertEqual(Field.objects.filter(sheet=sheet1, active=True).count(), 2)
        self.assertEqual(Field.objects.filter(sheet=sheet2).count(), 2)  # inactive isn't copied


class IntegrationTestCase(TestCase):
    fixtures = ['test_data']

    def test_valid_simple_initial_form_submission_loggedin(self):
        # get a person
        logged_in_person = Person.objects.get(userid="ggbaker")
        # log them in
        client = Client()
        client.login(ticket=logged_in_person.userid, service=CAS_SERVER_URL)

        old_form_submission_count = len(FormSubmission.objects.all())
        old_sheet_submission_count = len(SheetSubmission.objects.all())

        url = reverse('onlineforms.views.sheet_submission', kwargs={'form_slug': "comp-simple-form"})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)
        # make sure it's not displaying the add-nonsfu form
        self.assertNotContains(response, '<input type="hidden" name="add-nonsfu" value="True"/>')
        # check for some important fields
        # note: the keys are the slugs of the field
        fill_data = {"favorite-color": "Black", "reason": "Because it's metal", "second-favorite-color": "Green"}
        # submit the form
        post_data = {
            '0': fill_data["favorite-color"],
            '1': fill_data["reason"],
            '2': fill_data["second-favorite-color"],
            'submit-mode': "Submit",
        }
        response = client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        # check that a success messaging is being displayed
        self.assertContains(response, '<li class="success">')
        # check that one form submission and one sheet submission got created
        self.assertEqual(old_form_submission_count + 1, len(FormSubmission.objects.all()))
        self.assertEqual(old_sheet_submission_count + 1, len(SheetSubmission.objects.all()))
        # find the submission in the database
        form_submission = FormSubmission.objects.latest('id')
        self.assertTrue(form_submission)
        sheet_submission = SheetSubmission.objects.latest('id')
        self.assertTrue(sheet_submission)
        self.assertEqual(sheet_submission.form_submission, form_submission)
        # make sure the person we logged in as got form initiator credits
        self.assertTrue(form_submission.initiator.isSFUPerson())
        self.assertEqual(form_submission.initiator.sfuFormFiller, logged_in_person)
        # do the same for the sheet submission
        self.assertTrue(sheet_submission.filler.isSFUPerson())
        self.assertEqual(sheet_submission.filler.sfuFormFiller, logged_in_person)
        # verify the data
        field_submissions = FieldSubmission.objects.filter(sheet_submission=sheet_submission).order_by('field__order')
        self.assertEqual(len(fill_data), len(field_submissions))
        for field_submission in field_submissions:
            self.assertEqual(fill_data[field_submission.field.slug], field_submission.data['info'])
        # check the sheet submission and form submission status
        self.assertEqual(sheet_submission.status, "DONE")
        # form submissions is pending until someone manually marks it done
        self.assertEqual(form_submission.status, "PEND")

    def test_valid_simple_initial_form_submission_anonymous(self):
        client = Client()
        person = {'first_name': "Alan", 'last_name': "Turing", 'email_address': "alan.turing@gmail.com"}
        old_form_submission_count = len(FormSubmission.objects.all())
        old_sheet_submission_count = len(SheetSubmission.objects.all())

        url = reverse('onlineforms.views.sheet_submission', kwargs={'form_slug': "comp-simple-form"})
        response = basic_page_tests(self, client, url)
        self.assertEqual(response.status_code, 200)
        # check that the non sfu form is up
        self.assertContains(response, '<input type="hidden" name="add-nonsfu" value="True"/>')
        # check for some important fields
        # note: the keys are the slugs of the field
        fill_data = {"favorite-color": "Black", "reason": "Because it's metal", "second-favorite-color": "Green"}
        # submit the form
        post_data = {
            'first_name': person["first_name"],
            'last_name': person["last_name"],
            'email_address': person["email_address"],
            'add-nonsfu': True,
            '0': fill_data["favorite-color"],
            '1': fill_data["reason"],
            '2': fill_data["second-favorite-color"],
            'submit-mode': "Submit",
        }
        response = client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        # check that a success messaging is being displayed
        self.assertContains(response, '<li class="success">')
        # check that one form submission and one sheet submission got created
        self.assertEqual(old_form_submission_count + 1, len(FormSubmission.objects.all()))
        self.assertEqual(old_sheet_submission_count + 1, len(SheetSubmission.objects.all()))
        # find the submission in the database
        form_submission = FormSubmission.objects.latest('id')
        self.assertTrue(form_submission)
        sheet_submission = SheetSubmission.objects.latest('id')
        self.assertTrue(sheet_submission)
        self.assertEqual(sheet_submission.form_submission, form_submission)
        # make sure the person we logged in as got form initiator credits
        self.assertFalse(form_submission.initiator.isSFUPerson())
        self.assertEqual(form_submission.initiator.name(), "%s %s" % (person["first_name"], person["last_name"]))
        self.assertEqual(form_submission.initiator.email(), person["email_address"])
        # do the same for the sheet submission
        self.assertFalse(sheet_submission.filler.isSFUPerson())
        self.assertEqual(form_submission.initiator.name(), "%s %s" % (person["first_name"], person["last_name"]))
        self.assertEqual(form_submission.initiator.email(), person["email_address"])
        # verify the data
        field_submissions = FieldSubmission.objects.filter(sheet_submission=sheet_submission).order_by('field__order')
        self.assertEqual(len(fill_data), len(field_submissions))
        for field_submission in field_submissions:
            self.assertEqual(fill_data[field_submission.field.slug], field_submission.data['info'])
        # check the sheet submission and form submission status
        self.assertEqual(sheet_submission.status, "DONE")
        # form submissions is pending until someone manually marks it done
        self.assertEqual(form_submission.status, "PEND")

    def test_invalid_nonsfu_missing_elements(self):
        client = Client()
        old_form_submission_count = len(FormSubmission.objects.all())
        old_sheet_submission_count = len(SheetSubmission.objects.all())

        url = reverse('onlineforms.views.sheet_submission', kwargs={'form_slug': "comp-simple-form"})
        response = basic_page_tests(self, client, url)
        # test with each field missing
        person_nofirst = {'first_name': "", 'last_name': "Turing", 'email_address': "alan.turing@gmail.com"}
        person_nolast = {'first_name': "Alan", 'last_name': "", 'email_address': "alan.turing@gmail.com"}
        person_noemail = {'first_name': "Alan", 'last_name': "Turing", 'email_address': ""}
        people = [person_nofirst, person_nolast, person_noemail]
        fill_data = {"favorite-color": "Black", "reason": "Because it's metal", "second-favorite-color": "Green"}

        for person in people:
            # submit with empty user info
            post_data = {
                'first_name': person['first_name'],
                'last_name': person['last_name'],
                'email_address': person['email_address'],
                'add-nonsfu': True,
                '0': fill_data["favorite-color"],
                '1': fill_data["reason"],
                '2': fill_data["second-favorite-color"],
                'submit-mode': "Submit",
            }

            response = client.post(url, post_data, follow=True)
            self.assertEqual(response.status_code, 200)
            # make sure no success
            self.assertNotContains(response, '<li class="success">')
            # make sure there was an error
            self.assertContains(response, '<li class="error">')
            # make sure nothing got added to the database
            self.assertEqual(old_form_submission_count, len(FormSubmission.objects.all()))
            self.assertEqual(old_sheet_submission_count, len(SheetSubmission.objects.all()))

    def test_invalid_forbidden_initial(self):
        client = Client()
        # this form doesn't allow non-sfu students to fill it out, so if we
        # are not logged in and we try to access it it should return forbidden
        url = reverse('onlineforms.views.sheet_submission', kwargs={'form_slug': "comp-multi-sheet-form"})
        response = response = client.get(url)
        self.assertEqual(response.status_code, 403)


class ViewTestCase(TestCase):
    fixtures = ['test_data', 'onlineforms/extra_test_data']
    slug_data = {'formgroup_slug': "comp-admins",
                'formsubmit_slug': "submission-comp-simple-form-2",
                'form_slug': "comp-simple-form",
                'sheet_slug': "initial-2",
                'field_slug': "favorite-color",
                'sheetsubmit_slug': "submission-initial-2",
                'secret_url': "b50d3a695edf877df2a2100376d493f1aec5c26a"}

    def test_no_arg_pages(self):
        client = log_in()
        views = ['manage_groups',
                        'new_group',
                        'admin_list_all',
                        'admin_assign_any',
                        'list_all',
                        'new_form',
                        'submissions_list_all_forms']
        self.run_basic_page_tests(client, views, {})

    def test_formgroup_pages(self):
        client = log_in()
        views = ['manage_group', 'add_group_member']
        args = {'formgroup_slug': self.slug_data["formgroup_slug"]}
        self.run_basic_page_tests(client, views, args)

    def test_form_pages(self):
        client = log_in()
        views = ['view_form', 'preview_form', 'edit_form', 'new_sheet', 'sheet_submission']
        args = {'form_slug': self.slug_data["form_slug"]}
        self.run_basic_page_tests(client, views, args)

    def test_sheet_pages(self):
        client = log_in()
        views = ['edit_sheet', 'edit_sheet_info', 'new_field']
        args = {'form_slug': self.slug_data["form_slug"], 'sheet_slug': self.slug_data["sheet_slug"]}
        self.run_basic_page_tests(client, views, args)

    def test_field_pages(self):
        client = log_in()
        views = ['edit_field']
        args = {'form_slug': self.slug_data["form_slug"],
                'sheet_slug': self.slug_data["sheet_slug"],
                'field_slug': self.slug_data["field_slug"]}
        self.run_basic_page_tests(client, views, args)

    def test_form_submission_pages(self):
        client = log_in()
        views = ['view_submission']
        args = {'formsubmit_slug': self.slug_data["formsubmit_slug"]}
        self.run_basic_page_tests(client, views, args)

    def test_secret_url_pages(self):
        client = log_in()
        views = ['sheet_submission_via_url']
        args = {'secret_url': self.slug_data["secret_url"]}
        self.run_basic_page_tests(client, views, args)

    def test_total_submission_pages(self):
        client = log_in()
        views = ['sheet_submission']
        args = {'form_slug': self.slug_data["form_slug"],
                'sheet_slug': self.slug_data["sheet_slug"],
                'formsubmit_slug': self.slug_data["formsubmit_slug"],
                'sheetsubmit_slug': self.slug_data["sheetsubmit_slug"]}
        self.run_basic_page_tests(client, views, args)

    def run_basic_page_tests(self, client, views, arguments):
        for view in views:
                try:
                    url = reverse('onlineforms.views.' + view, kwargs=arguments)
                    # response = client.get(url)
                    response = basic_page_tests(self, client, url)
                    self.assertEqual(response.status_code, 200)
                except:
                    print "with view==" + repr(view)
                    raise


class MiscTests(TestCase):
    fixtures = ['test_data', 'onlineforms/extra_test_data']

    def test_sheet_submission_get_url(self):
        # arrange
        slugs = {'sheetsubmit_slug': "submission-initial-2",
                'sheet_slug': "initial-2",
                'formsubmit_slug': "submission-comp-simple-form-2",
                'form_slug': "comp-simple-form"
        }
        form = Form.objects.get(slug=slugs['form_slug'])
        form_submission = FormSubmission.objects.get(form=form, slug=slugs['formsubmit_slug'])
        sheet = Sheet.objects.get(form=form, slug=slugs['sheet_slug'])
        sheet_submission = SheetSubmission.objects.get(sheet=sheet, form_submission=form_submission, slug=slugs['sheetsubmit_slug'])
        # act
        url = get_sheet_submission_url(sheet_submission)
        # assert, check that we get a full URL with all the slugs
        expected_url = reverse('onlineforms.views.sheet_submission', kwargs=slugs)
        self.assertEqual(url, expected_url)

    def test_sheet_submission_get_url_secret(self):
        # arrange
        key = "b50d3a695edf877df2a2100376d493f1aec5c26a"
        sheet_submission = SheetSubmissionSecretUrl.objects.get(key=key).sheet_submission
        # act
        url = get_sheet_submission_url(sheet_submission)
        # assert, check that we get a URL using the key, not all the slugs
        expected_url = reverse('onlineforms.views.sheet_submission_via_url', kwargs={'secret_url': key})
        self.assertEqual(url, expected_url)


class FieldTestCase(TestCase):
    fixtures = ['test_data']
    config = {"min_length": 1,
                "max_length": 10,
                "required": False,
                "help_text": "whatever",
                "label": "whatever",
                "min_responses": 1,
                "max_responses": 4}

    def setUp(self):
        self.unit = Unit.objects.get(label="COMP")

    def test_make_config_form(self):
        for (name, field_model) in FIELD_TYPE_MODELS.iteritems():
            instance = field_model(self.config)
            config_form = instance.make_config_form()
            # looks like a divider will return a bool false here, look into that
            # still checks for notimplemented error though
            if config_form:
                self.assertTrue(isinstance(config_form, DjangoForm))

    def test_make_entry_field(self):
        for (name, field_model) in FIELD_TYPE_MODELS.iteritems():
            instance = field_model(self.config)
            self.assertTrue(isinstance(instance.make_entry_field(), DjangoFormsField))

    def test_serialize_field(self):
        for (name, field_model) in FIELD_TYPE_MODELS.iteritems():
            instance = field_model(self.config)
            self.assertTrue(isinstance(instance.serialize_field("test data"), dict))

    def test_smltxt_field(self):
        client = log_in()
        fg = FormGroup.objects.create(name="Admin Test", unit=self.unit)
        form = Form.objects.create(title="Test Form", unit=self.unit, owner=fg, initiators="LOG")
        sheet = Sheet.objects.create(title="Initial Sheet", form=form, is_initial=True)
        field = Field.objects.create(label="F1", sheet=sheet, fieldtype="SMTX", config=self.config)

        test_input = "abacus"

        url = reverse('onlineforms.views.sheet_submission', kwargs={'form_slug': form.slug})
        post_data = {
            '0': test_input,
            'submit-mode': "Submit",
        }
        response = client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(FormSubmission.objects.filter(form=form)), 1)
        self.assertEqual(len(SheetSubmission.objects.filter(sheet=sheet)), 1)
        field_submissions = FieldSubmission.objects.filter(field=field)
        self.assertEqual(len(field_submissions), 1)
        field_submission = field_submissions[0]
        self.assertEqual(field_submission.data["info"], test_input)
