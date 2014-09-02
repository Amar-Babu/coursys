from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import generics, views

from coredata.models import CourseOffering, Member
from coredata.serializers import CourseOfferingSerializer, ActivitySerializer
from courselib.rest import APIConsumerPermissions

class MyOfferings(generics.ListAPIView):
    """
    Return a list of course offering for the authenticated user.

    By default, all memberships known in the system are returned. Query string `relevant=yes` will give the list of
    offerings that are relevant to show the user in a menu: ones where there is some data in CourSys and are within a
    reasonable time span.
    """
    permission_classes = (APIConsumerPermissions,)
    consumer_permissions = set(['courses'])

    serializer_class = CourseOfferingSerializer

    def get_queryset(self):
        relevant = self.request.QUERY_PARAMS.get('relevant', None)
        if relevant == 'yes':
            memberships, _ = Member.get_memberships(self.request.user.username)
        else:
            memberships = Member.objects.exclude(role="DROP").exclude(offering__component="CAN") \
                    .filter(offering__graded=True, person__userid=self.request.user.username)

        offerings = [m.offering for m in memberships]
        return offerings

class OfferingInfo(generics.ListAPIView):
    permission_classes = (APIConsumerPermissions,)
    consumer_permissions = set(['courses', 'grades'])

    serializer_class = ActivitySerializer

    def get_queryset(self):
        offering = get_object_or_404(CourseOffering, ~Q(component='CAN'), slug=self.kwargs['course_slug'])
        qs = offering.activity_set.filter(deleted=False)

        member = get_object_or_404(Member, ~Q(role='DROP'), person__userid=self.request.user.username, offering=offering)
        if member.role == 'STUD':
            qs.exclude(status='INVI')

        return qs
