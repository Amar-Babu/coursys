# TODO: a QuestionMark model and the UI for TAs to enter marks
# TODO: delete Quiz?
# TODO: "copy course setup" should also copy quizzes

import datetime
import hashlib
import itertools
import json
from collections import namedtuple
from importlib import import_module
from typing import Optional, Tuple, List, Iterable, Any, Dict

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore as DatabaseSessionStore
from django.core.checks import Error
from django.db import models
from django.db.models import Max
from django.http import HttpRequest
from django.shortcuts import resolve_url
from django.utils.safestring import SafeText
from ipware import get_client_ip

from coredata.models import Member
from courselib.json_fields import JSONField, config_property
from courselib.markup import markup_to_html
from courselib.storage import UploadedFileStorage, upload_path
from grades.models import Activity
from quizzes import DEFAULT_QUIZ_MARKUP
from quizzes.types.file import FileAnswer
from quizzes.types.mc import MultipleChoice
from quizzes.types.text import ShortAnswer, LongAnswer, FormattedAnswer, NumericAnswer


QUESTION_TYPE_CHOICES = [
    ('MC', 'Multiple Choice'),
    ('SHOR', 'Short Answer'),
    ('LONG', 'Long Answer'),
    ('FMT', 'Long Answer with formatting'),
    ('NUM', 'Numeric Answer'),
    ('FILE', 'File Upload'),
]


QUESTION_CLASSES = {
    'MC': MultipleChoice,
    'SHOR': ShortAnswer,
    'LONG': LongAnswer,
    'FMT': FormattedAnswer,
    'NUM': NumericAnswer,
    'FILE': FileAnswer,
}


STATUS_CHOICES = [
    ('V', 'Visible'),
    ('D', 'Deleted'),
]


def string_hash(s: str, n_bytes: int = 8):
    """
    Create an n_bytes byte integer hash of the string
    """
    h = hashlib.sha256(s.encode('utf-8'))
    return int.from_bytes(h.digest()[:n_bytes], byteorder='big', signed=False)


class Randomizer(object):
    """
    A linear congruential generator (~= pseudorandom number generator). Custom implementation to ensure we can recreate
    a sequence of choices from a seed, regardless of Python's random implementation, etc.
    """
    # glibc parameters from
    # https://en.wikipedia.org/wiki/Linear_congruential_generator#Parameters_in_common_use
    def __init__(self, seed_str: str):
        seed = string_hash(seed_str, 7)
        self.m = 2 ** 31
        self.a = 1103515245
        self.c = 12345
        self.x = seed % self.m

    def next(self, n: Optional[int] = None):
        """
        Return the next random integer (optionally, mod n).
        """
        x = (self.a * self.x + self.c) % self.m
        self.x = x
        if n:
            return x % n
        else:
            return x

    def permute(self, lst: List[Any]) -> List[Any]:
        """
        Return a permuted copy of the list
        """
        result = []
        lst = lst.copy()
        while lst:
            elt = lst.pop(self.next(len(lst)))
            result.append(elt)
        return result


class Quiz(models.Model):
    class QuizStatusManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().select_related('activity', 'activity__offering').filter(status='V')

    activity = models.OneToOneField(Activity, on_delete=models.PROTECT)
    start = models.DateTimeField(help_text='Quiz will be visible to students after this time. Time format: HH:MM:SS, 24-hour time')
    end = models.DateTimeField(help_text='Quiz will be invisible to students and unsubmittable after this time. Time format: HH:MM:SS, 24-hour time')
    status = models.CharField(max_length=1, null=False, blank=False, default='V', choices=STATUS_CHOICES)
    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff:
    # .config['grace']: length of grace period at the end of the exam (in seconds)
    # .config['intro']: introductory text for the quiz
    # .config['markup']: markup language used: see courselib/markup.py
    # .config['math']: intro uses MathJax? (boolean)
    # .config['secret']: the "secret" used to seed the randomization for this quiz (integer)

    grace = config_property('grace', default=300)
    intro = config_property('intro', default='')
    markup = config_property('markup', default=DEFAULT_QUIZ_MARKUP)
    math = config_property('math', default=False)
    secret = config_property('secret', default='not a secret')

    class Meta:
        verbose_name_plural = 'Quizzes'

    objects = QuizStatusManager()

    def get_absolute_url(self):
        return resolve_url('offering:quiz:index', course_slug=self.activity.offering.slug, activity_slug=self.activity.slug)

    def save(self, *args, **kwargs):
        res = super().save(*args, **kwargs)
        if 'secret' not in self.config:
            # Ensure we are saved (so self.id is filled), and if the secret isn't there, fill it in.
            self.config['secret'] = string_hash(settings.SECRET_KEY) + self.id
            super().save(*args, **kwargs)
        return res

    def get_start_end(self, member: Optional[Member]) -> Tuple[datetime.datetime, datetime.datetime]:
        """
        Get the start and end times for this quiz.

        The start/end may have been overridden by the instructor for this student, but default to .start and .end if not
        """
        if not member:
            # in the generic case, use the defaults
            return self.start, self.end

        special_case = TimeSpecialCase.objects.filter(quiz=self, student=member).first()
        if not special_case:
            # no special case for this student
            return self.start, self.end
        else:
            # student has a special case
            return special_case.start, special_case.end

    def get_starts_ends(self, members: Iterable[Member]) -> Dict[Member, Tuple[datetime.datetime, datetime.datetime]]:
        """
        Get the start and end times for this quiz for each member.
        """
        special_cases = TimeSpecialCase.objects.filter(quiz=self, student__in=members).select_related('student')
        sc_lookup = {sc.student: sc for sc in special_cases}
        # stub so we can always get a TimeSpecialCase in the comprehension below
        default = TimeSpecialCase(start=self.start, end=self.end)
        return {m: (sc_lookup.get(m, default).start, sc_lookup.get(m, default).end) for m in members}

    def ongoing(self, member: Optional[Member] = None) -> bool:
        """
        Is the quiz currently in-progress?
        """
        start, end = self.get_start_end(member=member)
        if not start or not end:
            # newly created with start and end not yet filled
            return False
        now = datetime.datetime.now()
        return start <= now <= end

    def completed(self, member: Optional[Member] = None) -> bool:
        """
        Is the quiz over?
        """
        _, end = self.get_start_end(member=member)
        if not end:
            # newly created with end not yet filled
            return False
        now = datetime.datetime.now()
        return now > end

    def intro_html(self) -> SafeText:
        return markup_to_html(self.intro, markuplang=self.markup, math=self.math)

    def random_generator(self, seed: str) -> Randomizer:
        """
        Return a "random" value generator with given seed, which must be deterministic so we can reproduce the values.
        """
        seed_str = str(self.secret) + '--' + seed
        return Randomizer(seed_str)


class Question(models.Model):
    class QuestionStatusManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().select_related('quiz').prefetch_related('versions').filter(status='V')

    quiz = models.ForeignKey(Quiz, null=False, blank=False, on_delete=models.PROTECT)
    type = models.CharField(max_length=4, null=False, blank=False, choices=QUESTION_TYPE_CHOICES)
    status = models.CharField(max_length=1, null=False, blank=False, default='V', choices=STATUS_CHOICES)
    order = models.PositiveSmallIntegerField(null=False, blank=False)
    config = JSONField(null=False, blank=False, default=dict)
    # .config['points']: points the question is worth (positive integer)

    points = config_property('points', default=1)

    class Meta:
        ordering = ['order']

    objects = QuestionStatusManager()
    all_objects = models.Manager()

    def get_absolute_url(self):
        return resolve_url('offering:quiz:index', course_slug=self.quiz.activity.offering.slug,
                           activity_slug=self.quiz.activity.slug) + '#' + self.ident()

    def ident(self):
        """
        Unique identifier that can be used as a input name or HTML id value.
        """
        return 'q-%i' % (self.id,)

    def set_order(self):
        """
        If the question has no .order, set the .order value to the current max + 1
        """
        if self.order is not None:
            return

        current_max = Question.objects.filter(quiz=self.quiz).aggregate(Max('order'))['order__max']
        if not current_max:
            self.order = 1
        else:
            self.order = current_max + 1


class QuestionVersion(models.Model):
    class VersionStatusManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().select_related('question').filter(status='V')

    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name='versions')
    status = models.CharField(max_length=1, null=False, blank=False, default='V', choices=STATUS_CHOICES)
    created_at = models.DateTimeField(default=datetime.datetime.now, null=False, blank=False) # used for ordering
    config = JSONField(null=False, blank=False, default=dict)
    # .config['text']: question as (text, markup, math:bool)
    # others as set by the .question.type (and corresponding QuestionType)

    text = config_property('text', default=('', DEFAULT_QUIZ_MARKUP, False))

    objects = VersionStatusManager()

    class Meta:
        ordering = ['question', 'created_at', 'id']

    def helper(self, question: Optional['Question'] = None):
        return QUESTION_CLASSES[self.question.type](version=self, question=question)

    @classmethod
    def select(cls, quiz: Quiz, questions: Iterable[Question], student: Optional[Member],
               answers: Optional[Iterable['QuestionAnswer']]) -> List['QuestionVersion']:
        """
        Build a (reproducibly-random) set of question versions. Honour the versions already answered, if instructor
        has been fiddling with questions during the quiz.
        """
        assert (student is None and answers is None) or (student is not None and answers is not None), 'must give current answers if student is known.'
        if student:
            rand = quiz.random_generator(str(student.id))

        all_versions = QuestionVersion.objects.filter(question__in=questions)
        version_lookup = {
            q_id: list(vs)
            for q_id, vs in itertools.groupby(all_versions, key=lambda v: v.question_id)
        }
        if answers is not None:
            answers_lookup = {
                a.question_id: a
                for a in answers
            }

        versions = []
        for q in questions:
            vs = version_lookup[q.id]
            if student:
                # student: choose randomly unless they have already answered a version
                # We need to call rand.next() here to update the state of the LCG, even if we have something
                # in answers_lookup
                n = rand.next(len(vs))

                if q.id in answers_lookup:
                    ans = answers_lookup[q.id]
                    v = ans.question_version
                    try:
                        v.choice = vs.index(v) + 1
                    except ValueError:
                        # Happens if a student answers a version, but then the instructor deletes it. Hopefully never.
                        v.choice = 0
                else:
                    v = vs[n]
                    v.choice = n+1

            else:
                # instructor preview: choose the first
                v = vs[0]
                v.choice = 1

            v.n_versions = len(vs)
            #v.question_cached = True  # promise checks that we have the .question pre-fetched
            #v.question = q
            versions.append(v)

        return versions

    def question_html(self) -> SafeText:
        """
        Markup for the question itself
        """
        helper = self.helper()
        return helper.question_html()

    def question_preview_html(self) -> SafeText:
        """
        Markup for an instructor's preview of the question (e.g. question + MC options)
        """
        helper = self.helper()
        return helper.question_preview_html()

    def entry_field(self, student: Optional[Member], questionanswer: 'QuestionAnswer' = None):
        helper = self.helper()
        if questionanswer:
            assert questionanswer.question_version_id == self.id
        return helper.get_entry_field(questionanswer=questionanswer, student=student)


def file_upload_to(instance, filename):
    return upload_path(instance.question.quiz.activity.offering.slug, '_quizzes', filename)


class QuestionAnswer(models.Model):
    class AnswerStatusManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().select_related('question', 'question_version').filter(question__status='V')

    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    question_version = models.ForeignKey(QuestionVersion, on_delete=models.PROTECT)
    # Technically .question is redundant with .question_version.question, but keeping it for convenience
    # and the unique_together.
    student = models.ForeignKey(Member, on_delete=models.PROTECT)
    modified_at = models.DateTimeField(default=datetime.datetime.now, null=False, blank=False)
    # format of .answer determined by the corresponding QuestionHelper
    answer = JSONField(null=False, blank=False, default=dict)
    # .file used for file upload question types; null otherwise
    file = models.FileField(blank=True, null=True, storage=UploadedFileStorage, upload_to=file_upload_to, max_length=500)

    class Meta:
        unique_together = [['question_version', 'student']]

    objects = AnswerStatusManager()

    def save(self, *args, **kwargs):
        assert self.question_id == self.question_version.question_id  # ensure denormalized field stays consistent

        saving_file = False
        if '_file' in self.answer:
            if self.answer['_file'] is None:
                # keep current .file
                pass
            elif self.answer['_file'] is False:
                # user requested "clear"
                self.file = None
            else:
                # actually a file
                self.file = self.answer['_file']
                saving_file = True

            del self.answer['_file']

        if saving_file:
            # Inject the true save path into the .answer. Requires a double .save()
            super().save(*args, **kwargs)
            fn = self.file.name
            self.answer['filepath'] = fn

        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return resolve_url('offering:quiz:view_submission', course_slug=self.question.quiz.activity.offering.slug,
                           activity_slug=self.question.quiz.activity.slug,
                           userid=self.student.person.userid_or_emplid()) + '#' + self.question.ident()

    def answer_html(self) -> SafeText:
        helper = self.question_version.helper()
        return helper.to_html(self)


class QuizSubmission(models.Model):
    """
    Model to log everything we can think of about a quiz submission, for possibly later analysis.
    """
    quiz = models.ForeignKey(Quiz, null=False, blank=False, on_delete=models.PROTECT)
    student = models.ForeignKey(Member, null=False, blank=False, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=datetime.datetime.now, null=False, blank=False)
    ip_address = models.GenericIPAddressField(null=False, blank=False)
    config = JSONField(null=False, blank=False, default=dict)  # additional data about the submission:
    # .config['answers']: list of QuestionAnswer objects submitted (if changed from prev submission), as [(QuestionVersion.id, answer)]
    # .config['user_agent']: HTTP User-Agent header from submission
    # .config['session']: the session_key from the submission
    # .config['csrf_token']: the CSRF token being used for the submission
    # .config['fingerprint']: browser fingerprint provided by fingerprintjs2

    @classmethod
    def create(cls, request: HttpRequest, quiz: Quiz, student: Member, answers: List[QuestionAnswer], commit: bool = True) -> 'QuizSubmission':
        qs = cls(quiz=quiz, student=student)
        ip_addr, _ = get_client_ip(request)
        qs.ip_address = ip_addr
        qs.config['answers'] = [(a.question_version_id, a.answer) for a in answers]
        qs.config['session'] = request.session.session_key
        qs.config['csrf_token'] = request.META.get('CSRF_COOKIE')
        qs.config['user_agent'] = request.META.get('HTTP_USER_AGENT')
        try:
            qs.config['fingerprint'] = json.loads(request.POST['fingerprint'])
        except KeyError:
            qs.config['fingerprint'] = 'missing'
        except json.JSONDecodeError:
            qs.config['fingerprint'] = 'json-error'

        if commit:
            qs.save()
        return qs

    @classmethod
    def check(cls, **kwargs):
        """
        We use .session_key and CSRF_COOKIE above: check that they will be there, and fail fast if not.
        """
        errors = super().check(**kwargs)

        # Ensure we are using the database session store. (Other SessionStores may also have .session_key?)
        engine = import_module(settings.SESSION_ENGINE)
        store = engine.SessionStore
        if not issubclass(store, DatabaseSessionStore):
            errors.append(Error(
                "Quiz logging uses request.session.session_key, which likely implies "
                "SESSION_ENGINE = 'django.contrib.sessions.backends.db' in settings."
            ))

        if 'django.middleware.csrf.CsrfViewMiddleware' not in settings.MIDDLEWARE:
            errors.append(Error(
                "CsrfViewMiddleware is not enabled in settings: quiz logging uses CSRF_COOKIE and will fail without "
                "CSRF checking enabled. Also it should be enabled in general."
            ))

        return errors

    AnswerData = namedtuple('AnswerData', ['question', 'n', 'answer', 'answer_html'])

    def annotate_questions(self, questions: Iterable[Question], versions: Iterable[QuestionVersion]) -> None:
        """
        Annotate this object to combine .config['answers'] and questions for efficient display later.
        """
        answers = self.config['answers']
        question_lookup = {q.id: (q, i+1) for i,q in enumerate(questions)}
        version_lookup = {v.id: v for v in versions}
        answer_data = []
        for version_id, answer in answers:
            version = version_lookup[version_id]
            question, n = question_lookup[version.question_id]
            # temporarily reconstruct the QuestionAnswer so we can generate HTML
            qa = QuestionAnswer(question=question, question_version=version, student=self.student,
                                modified_at=self.created_at, answer=answer)
            answer_html = version.helper(question=question).to_html(qa)
            data = QuizSubmission.AnswerData(question=question, n=n, answer=answer, answer_html=answer_html)
            answer_data.append(data)

        self.answer_data = answer_data

    def session_fingerprint(self) -> str:
        """
        Return a hash of what we know about the user's session on submission.
        We could incorporate csrf_token here, but are we *sure* it only changes on login?
        """
        ident = self.config['session'] # + '--' + self.config['csrf_token']
        return '%08x' % (string_hash(ident, 4),)

    def browser_fingerprint(self) -> str:
        """
        Return a hash of what we know about the user's browser on submission.
        """
        # including user_agent is generally redundant, but not if the fingerprinting fails for some reason
        ident = self.config['user_agent'] + '--' + json.dumps(self.config['fingerprint'])
        return '%08x' % (string_hash(ident, 4),)


class TimeSpecialCase(models.Model):
    """
    Model to represent quiz start/end times that are unique to one student, to allow makeup quizzes, accessibility
    accommodations, etc.
    """
    quiz = models.ForeignKey(Quiz, null=False, blank=False, on_delete=models.PROTECT)
    student = models.ForeignKey(Member, on_delete=models.PROTECT)
    start = models.DateTimeField(help_text='Quiz will be visible to the student after this time. Time format: HH:MM:SS, 24-hour time')
    end = models.DateTimeField(help_text='Quiz will be invisible to the student and unsubmittable after this time. Time format: HH:MM:SS, 24-hour time')
    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff:

    class Meta:
        unique_together = [['quiz', 'student']]
