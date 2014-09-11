from rest_framework import serializers
from grades.models import Activity, NumericGrade
from grades.utils import generate_numeric_activity_stat, generate_letter_activity_stat
from courselib.rest import utc_datetime

class ActivitySerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField('get_url', help_text='URL for more info, if set by instructor')
    max_grade = serializers.SerializerMethodField('get_max_grade')
    is_numeric = serializers.Field(source='is_numeric')
    is_calculated = serializers.Field(source='is_calculated')

    class Meta:
        model = Activity
        fields = ('slug', 'name', 'short_name', 'due_date', 'percent', 'group', 'url', 'max_grade', 'is_numeric', 'is_calculated')

    def transform_due_date(self, obj, value):
        return utc_datetime(value)

    def get_url(self, a):
        return a.url() or None

    def get_max_grade(self, a):
        return getattr(a, 'max_grade', None)

class GradeMarkSerializer(serializers.Serializer):
    slug = serializers.SlugField(help_text='String that identifies this activity within the course offering')
    grade = serializers.SerializerMethodField('get_grade', help_text='Grade the student received, or null')
    max_grade = serializers.SerializerMethodField('get_max_grade', help_text='Maximum grade for numeric activities, or null for letter activities')

    def get_grade(self, a):
        return a.get_grade(self.context['view'].member.person)

    def get_max_grade(self, a):
        return getattr(a, 'max_grade', None)


class StatsSerializer(serializers.Serializer):
    slug = serializers.SlugField(help_text='String that identifies this activity within the course offering')
    count = serializers.SerializerMethodField('get_count', help_text='Grade count')
    min = serializers.SerializerMethodField('get_min', help_text='Minimum grade')
    max = serializers.SerializerMethodField('get_max', help_text='Maximum grade')
    average = serializers.SerializerMethodField('get_average', help_text='Average (mean) grade, or null for letter graded activities')
    median = serializers.SerializerMethodField('get_count', help_text='Median grade')
    histogram = serializers.SerializerMethodField('get_histo', help_text='Histogram data: list of label/count pairs, null if not available or disabled by instructor')
    missing_reason = serializers.CharField(help_text='Human-readable reason stats are missing (if relevant)')

    def to_native(self, a):
        # annotate the activity with its stats object before starting
        if a.is_numeric():
            a.stats, a.missing_reason = generate_numeric_activity_stat(a, self.context['view'].member.role)
        else:
            a.stats, a.missing_reason = generate_letter_activity_stat(a, self.context['view'].member.role)

        return super(StatsSerializer, self).to_native(a)

    def _get_or_none(self, a, attr):
        if a.stats:
            return getattr(a.stats, attr, None)
        else:
            return None

    def get_histo(self, a):
        if a.stats:
            return [(rng.grade_range, rng.stud_count) for rng in a.stats.grade_range_stat_list]
        else:
            return None

    def get_count(self, a):
        return self._get_or_none(a, 'count')
    def get_min(self, a):
        return self._get_or_none(a, 'min')
    def get_max(self, a):
        return self._get_or_none(a, 'max')
    def get_average(self, a):
        return self._get_or_none(a, 'average')
    def get_median(self, a):
        return self._get_or_none(a, 'median')
