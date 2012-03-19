import os, itertools, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')

# create "objs" by selecting all objects you want to serialize
from grad.models import *

objs = itertools.chain(Scholarship.objects.all())

# output the JSON: copy into test_data.json when you're sure it's right.
from django.core import serializers
data = serializers.serialize("json", objs, sort_keys=True, indent=1)
print data

