from rest_framework import generics

from coredata.models import CourseOffering, Member
from coredata.serializers import ShortCourseOfferingSerializer, CourseOfferingSerializer
from courselib.rest import APIConsumerPermissions, IsOfferingMember

class MyOfferings(generics.ListAPIView):
    """
    Course offering for the authenticated user.

    By default, all offerings that are relevant to show the user in a menu: ones where there is some data in CourSys
    and are within a reasonable time span. This should be used to build a menu of courses for a user.

    Query string `all=yes` will give the complete list of known offerings where the user was a member.
    """
    permission_classes = (APIConsumerPermissions,)
    consumer_permissions = set(['courses'])

    serializer_class = ShortCourseOfferingSerializer

    def get_queryset(self):
        all = self.request.QUERY_PARAMS.get('all', None)
        if all == 'yes':
            memberships = Member.objects.exclude(role="DROP").exclude(offering__component="CAN") \
                    .filter(offering__graded=True, person__userid=self.request.user.username)
        else:
            memberships, _ = Member.get_memberships(self.request.user.username)

        offerings = [m.offering for m in memberships]
        return offerings

class OfferingInfo(generics.RetrieveAPIView):
    """
    Detailed information on one course offering.
    """
    permission_classes = (APIConsumerPermissions, IsOfferingMember,)
    consumer_permissions = set(['courses'])

    serializer_class = CourseOfferingSerializer
    lookup_field = 'slug'
    lookup_url_kwarg = 'course_slug'

    queryset = CourseOffering.objects.exclude(component='CAN')