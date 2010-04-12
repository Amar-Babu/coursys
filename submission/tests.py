from django.test import TestCase
from django.test.client import Client
from submission.models import *
from submission.forms import *
from grades.models import NumericActivity
from coredata.tests import create_offering
from settings import CAS_SERVER_URL
from coredata.models import *
from courselib.testing import *
import gzip

import base64, StringIO
TGZ_FILE = base64.b64decode('H4sIAI7Wr0sAA+3OuxHCMBAE0CtFJUjoVw8BODfQP3bgGSKIcPResjO3G9w9/i9vRmt7ltnzZx6ilNrr7PVS9vscbUTKJ/wWr8fzuqYUy3pbvu1+9QAAAAAAAAAAAHCiNyHUDpAAKAAA')
GZ_FILE = base64.b64decode('H4sICIjWr0sAA2YAAwAAAAAAAAAAAA==')
ZIP_FILE = base64.b64decode('UEsDBAoAAAAAAMB6fDwAAAAAAAAAAAAAAAABABwAZlVUCQADiNavSzTYr0t1eAsAAQToAwAABOgDAABQSwECHgMKAAAAAADAenw8AAAAAAAAAAAAAAAAAQAYAAAAAAAAAAAApIEAAAAAZlVUBQADiNavS3V4CwABBOgDAAAE6AMAAFBLBQYAAAAAAQABAEcAAAA7AAAAAAA=')
RAR_FILE = base64.b64decode('UmFyIRoHAM+QcwAADQAAAAAAAABMpHQggCEACAAAAAAAAAADAAAAAMB6fDwdMwEApIEAAGYAv4hn9qn/1MQ9ewBABwA=')
PDF_FILE = base64.b64decode("""JVBERi0xLjQKJcfsj6IKNSAwIG9iago8PC9MZW5ndGggNiAwIFIvRmlsdGVyIC9GbGF0ZURlY29k
ZT4+CnN0cmVhbQp4nCtUMNAzVDAAQSidnMulH2SukF7MZaDgDsTpXIVchmAFClAqOVfBKQSoyELB
yEAhJI0Los9QwdxIwdQAKJLLpeGRmpOTr1CeX5SToqgZksXlGsIVCIQA1l0XrmVuZHN0cmVhbQpl
bmRvYmoKNiAwIG9iago5MgplbmRvYmoKNCAwIG9iago8PC9UeXBlL1BhZ2UvTWVkaWFCb3ggWzAg
MCA2MTIgNzkyXQovUm90YXRlIDAvUGFyZW50IDMgMCBSCi9SZXNvdXJjZXM8PC9Qcm9jU2V0Wy9Q
REYgL1RleHRdCi9FeHRHU3RhdGUgOSAwIFIKL0ZvbnQgMTAgMCBSCj4+Ci9Db250ZW50cyA1IDAg
Ugo+PgplbmRvYmoKMyAwIG9iago8PCAvVHlwZSAvUGFnZXMgL0tpZHMgWwo0IDAgUgpdIC9Db3Vu
dCAxCj4+CmVuZG9iagoxIDAgb2JqCjw8L1R5cGUgL0NhdGFsb2cgL1BhZ2VzIDMgMCBSCi9NZXRh
ZGF0YSAxMSAwIFIKPj4KZW5kb2JqCjcgMCBvYmoKPDwvVHlwZS9FeHRHU3RhdGUKL09QTSAxPj5l
bmRvYmoKOSAwIG9iago8PC9SNwo3IDAgUj4+CmVuZG9iagoxMCAwIG9iago8PC9SOAo4IDAgUj4+
CmVuZG9iago4IDAgb2JqCjw8L0Jhc2VGb250L0NvdXJpZXIvVHlwZS9Gb250Ci9TdWJ0eXBlL1R5
cGUxPj4KZW5kb2JqCjExIDAgb2JqCjw8L1R5cGUvTWV0YWRhdGEKL1N1YnR5cGUvWE1ML0xlbmd0
aCAxMzE5Pj5zdHJlYW0KPD94cGFja2V0IGJlZ2luPSfvu78nIGlkPSdXNU0wTXBDZWhpSHpyZVN6
TlRjemtjOWQnPz4KPD9hZG9iZS14YXAtZmlsdGVycyBlc2M9IkNSTEYiPz4KPHg6eG1wbWV0YSB4
bWxuczp4PSdhZG9iZTpuczptZXRhLycgeDp4bXB0az0nWE1QIHRvb2xraXQgMi45LjEtMTMsIGZy
YW1ld29yayAxLjYnPgo8cmRmOlJERiB4bWxuczpyZGY9J2h0dHA6Ly93d3cudzMub3JnLzE5OTkv
MDIvMjItcmRmLXN5bnRheC1ucyMnIHhtbG5zOmlYPSdodHRwOi8vbnMuYWRvYmUuY29tL2lYLzEu
MC8nPgo8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0nM2YzY2FmMmYtNzJkNy0xMWVhLTAwMDAt
NmVhZWMyYzJlNmZkJyB4bWxuczpwZGY9J2h0dHA6Ly9ucy5hZG9iZS5jb20vcGRmLzEuMy8nIHBk
ZjpQcm9kdWNlcj0nR1BMIEdob3N0c2NyaXB0IDguNzAnLz4KPHJkZjpEZXNjcmlwdGlvbiByZGY6
YWJvdXQ9JzNmM2NhZjJmLTcyZDctMTFlYS0wMDAwLTZlYWVjMmMyZTZmZCcgeG1sbnM6eG1wPSdo
dHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvJz48eG1wOk1vZGlmeURhdGU+MjAxMC0wMy0yOFQx
NTozODo1OC0wNzowMDwveG1wOk1vZGlmeURhdGU+Cjx4bXA6Q3JlYXRlRGF0ZT4yMDEwLTAzLTI4
VDE1OjM4OjU4LTA3OjAwPC94bXA6Q3JlYXRlRGF0ZT4KPHhtcDpDcmVhdG9yVG9vbD5Vbmtub3du
QXBwbGljYXRpb248L3htcDpDcmVhdG9yVG9vbD48L3JkZjpEZXNjcmlwdGlvbj4KPHJkZjpEZXNj
cmlwdGlvbiByZGY6YWJvdXQ9JzNmM2NhZjJmLTcyZDctMTFlYS0wMDAwLTZlYWVjMmMyZTZmZCcg
eG1sbnM6eGFwTU09J2h0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8nIHhhcE1NOkRvY3Vt
ZW50SUQ9JzNmM2NhZjJmLTcyZDctMTFlYS0wMDAwLTZlYWVjMmMyZTZmZCcvPgo8cmRmOkRlc2Ny
aXB0aW9uIHJkZjphYm91dD0nM2YzY2FmMmYtNzJkNy0xMWVhLTAwMDAtNmVhZWMyYzJlNmZkJyB4
bWxuczpkYz0naHR0cDovL3B1cmwub3JnL2RjL2VsZW1lbnRzLzEuMS8nIGRjOmZvcm1hdD0nYXBw
bGljYXRpb24vcGRmJz48ZGM6dGl0bGU+PHJkZjpBbHQ+PHJkZjpsaSB4bWw6bGFuZz0neC1kZWZh
dWx0Jz5VbnRpdGxlZDwvcmRmOmxpPjwvcmRmOkFsdD48L2RjOnRpdGxlPjwvcmRmOkRlc2NyaXB0
aW9uPgo8L3JkZjpSREY+CjwveDp4bXBtZXRhPgogICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgCjw/eHBhY2tldCBlbmQ9J3cnPz4KZW5kc3RyZWFtCmVuZG9iagoyIDAgb2JqCjw8L1Byb2R1
Y2VyKEdQTCBHaG9zdHNjcmlwdCA4LjcwKQovQ3JlYXRpb25EYXRlKEQ6MjAxMDAzMjgxNTM4NTgt
MDcnMDAnKQovTW9kRGF0ZShEOjIwMTAwMzI4MTUzODU4LTA3JzAwJyk+PmVuZG9iagp4cmVmCjAg
MTIKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwNDEzIDAwMDAwIG4gCjAwMDAwMDIwMzYgMDAw
MDAgbiAKMDAwMDAwMDM1NCAwMDAwMCBuIAowMDAwMDAwMTk1IDAwMDAwIG4gCjAwMDAwMDAwMTUg
MDAwMDAgbiAKMDAwMDAwMDE3NyAwMDAwMCBuIAowMDAwMDAwNDc4IDAwMDAwIG4gCjAwMDAwMDA1
NzggMDAwMDAgbiAKMDAwMDAwMDUxOSAwMDAwMCBuIAowMDAwMDAwNTQ4IDAwMDAwIG4gCjAwMDAw
MDA2NDAgMDAwMDAgbiAKdHJhaWxlcgo8PCAvU2l6ZSAxMiAvUm9vdCAxIDAgUiAvSW5mbyAyIDAg
UgovSUQgWzxFODIxMEZDNzI4OUJDM0Y5QzdCNEQxMjJDRjNCM0YwMD48RTgyMTBGQzcyODlCQzNG
OUM3QjREMTIyQ0YzQjNGMDA+XQo+PgpzdGFydHhyZWYKMjE1OQolJUVPRgo=""")

class SubmissionTest(TestCase):
    fixtures = ['test_data']
    
    def setUp(self):
        self.s, self.course = create_offering()
        self.a1 = NumericActivity(name="Assignment 1", short_name="A1", status="RLS", offering=self.course, position=2, max_grade=15, due_date="2010-04-01")
        self.a1.save()
        self.a2 = NumericActivity(name="Assignment 2", short_name="A2", status="RLS", offering=self.course, position=1, max_grade=15, due_date="2010-03-01")
        self.a2.save()
        
        p = Person.objects.get(userid="ggbaker")
        self.member = Member(person=p, offering=self.course, role="INST", career="NONS", added_reason="UNK")
        self.member.save()
        
        self.c1 = URL.Component(activity=self.a1, title="URL Link", position=8)
        self.c1.save()
        self.c2 = Archive.Component(activity=self.a1, title="Archive File", position=1, max_size=100000)
        self.c2.save()
        self.c3 = Code.Component(activity=self.a1, title="Code File", position=3, max_size=2000, allowed=".py")
        self.c3.save()

    def test_select_components(self):
        """
        Test submission component classes: subclasses, selection, sorting.
        """
        comps = select_all_components(self.a1)
        self.assertEqual(len(comps), 3)
        self.assertEqual(comps[0].title, 'Archive File') # make sure position=1 is first
        self.assertEqual(str(comps[1].Type), "courses.submission.models.code.Code")
        self.assertEqual(str(comps[2].Type), "courses.submission.models.url.URL")

    def test_component_view_page(self):
        client = Client()
        client.login(ticket="ggbaker", service=CAS_SERVER_URL)
        
        # When no component, should display error message
        url = reverse('submission.views.show_components', kwargs={'course_slug':self.course.slug, 'activity_slug':self.a2.slug})
        response = basic_page_tests(self, client, url)
        self.assertContains(response, 'No components configured.')
        # add component and test
        component = URL.Component(activity=self.a2, title="URL2", position=1)
        component.save()
        component = Archive.Component(activity=self.a2, title="Archive2", position=1, max_size=100)
        component.save()
        # should all appear
        response = basic_page_tests(self, client, url)
        self.assertContains(response, "URL2")
        self.assertContains(response, "Archive2")
        # make sure type displays
        self.assertContains(response, '<li class="view"><label>Type:</label>Archive</li>')
        # delete component
        self.assertRaises(NotImplementedError, component.delete)

    def test_magic(self):
        """
        Test file type inference function
        """
        ftype = filetype(StringIO.StringIO(TGZ_FILE))
        self.assertEqual(ftype, "TGZ")
        ftype = filetype(StringIO.StringIO(GZ_FILE))
        self.assertEqual(ftype, "GZIP")
        ftype = filetype(StringIO.StringIO(ZIP_FILE))
        self.assertEqual(ftype, "ZIP")
        ftype = filetype(StringIO.StringIO(RAR_FILE))
        self.assertEqual(ftype, "RAR")
        ftype = filetype(StringIO.StringIO(PDF_FILE))
        self.assertEqual(ftype, "PDF")





