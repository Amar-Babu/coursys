# TODO: documentation for the markup flavours available
# TODO: write better help_text
# TODO: onlineforms ExplanationTextField is creole only
# TODO: the way discuss/models.py and discuss/forms.py uses the creole object should be purged/simplified
# TODO: ta module uses creole for offer_text
# TODO: discipline module uses textile
# TODO: ta TAContactForm uses textile
# TODO: dashboard NewsItem uses textile
# TODO: cache markup_to_html intelligently

from django.core.cache import cache
from django.db import models
from django.utils.safestring import mark_safe
from django.conf import settings

from grades.models import Activity

import re, os, subprocess
import pytz
import creoleparser
import bleach


MARKUP_CHOICES = [
    ('creole', 'WikiCreole'),
    ('markdown', 'Markdown'),
    ('html', 'HTML'),
]
MARKUP_CHOICES_WYSIWYG = MARKUP_CHOICES + [('html-wysiwyg', 'HTML editor')]

allowed_tags_restricted = bleach.sanitizer.ALLOWED_TAGS + [ # allowed in discussion
    'h3', 'h4', 'pre', 'p', 'dl', 'dt', 'dd', 'dfn', 'q', 'del', 'ins', 'sub', 'sup',
]
allowed_tags = allowed_tags_restricted + [ # allowed on pages
    'h2', 'img',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
]
allowed_attributes = bleach.sanitizer.ALLOWED_ATTRIBUTES
allowed_attributes['pre'] = ['lang']


def sanitize_html(html, restricted=False):
    """
    Sanitize HTML we got from the user so it's safe to include in the page
    """
    # TODO: document the HTML subset allowed (particularly <pre lang="python">)
    allowed = allowed_tags_restricted if restricted else allowed_tags
    return bleach.clean(html, tags=allowed, attributes=allowed_attributes, strip=True)


def markdown_to_html(markup):
    sub = subprocess.Popen([os.path.join(settings.BASE_DIR, 'courselib', 'markdown2html.rb')], stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE)
    stdoutdata, stderrdata = sub.communicate(input=markup)
    ret = sub.wait()
    if ret != 0:
        raise RuntimeError('markdown2html.rb did not return successfully')
    return stdoutdata


def markup_to_html(markup, markuplang, offering=None, pageversion=None, html_already_safe=False, restricted=False):
    """
    Master function to convert one of our markup languages to HTML (safely).

    :param markup: the markup code
    :param markuplang: the markup language, from MARKUP_CHOICES
    :param offering: the course offering we're converting for
    :param pageversion: the PageVersion we're converting for
    :param html_already_safe: markuplang=='html' and markup has already been through sanitize_html()
    :param restricted: use the restricted HTML subset for discussion (preventing format bombs)
    :return: HTML markup
    """
    if markuplang == 'creole':
        if offering:
            Creole = ParserFor(offering, pageversion)
        else:
            Creole = ParserFor(pageversion.page.offering, pageversion)
        html = Creole.text2html(markup)
        if restricted:
            html = sanitize_html(html, restricted=True)

    elif markuplang == 'markdown':
        # TODO: the due_date etc tricks that are available in wikicreole
        html = markdown_to_html(markup)
        if restricted:
            html = sanitize_html(html, restricted=True)

    elif markuplang == 'html':
        # TODO: the due_date etc tricks that are available in wikicreole
        if html_already_safe:
            # caller promises sanitize_html() has already been called on the input
            html = markup
        else:
            html = sanitize_html(markup, restricted=restricted)

    else:
        raise NotImplementedError()

    return mark_safe(html.strip())




# custom form field

from django import forms


class MarkupContentWidget(forms.MultiWidget):
    def __init__(self):
        widgets = (
            forms.Textarea(attrs={'cols': 70, 'rows': 20}),
            forms.Select(),
            forms.CheckboxInput(),
        )
        super(MarkupContentWidget, self).__init__(widgets)

    def format_output(self, rendered_widgets):
        return '<div class="markup-content">%s<br/>Markup language: %s Use MathJax? %s</div>' % tuple(rendered_widgets)

    def decompress(self, value):
        if value is None:
            return ['', 'creole', False]
        return value


class MarkupContentField(forms.MultiValueField):
    widget = MarkupContentWidget

    def __init__(self, with_wysiwyg=False, rows=20, *args, **kwargs):
        choices = MARKUP_CHOICES_WYSIWYG if with_wysiwyg else MARKUP_CHOICES
        fields = [
            forms.CharField(required=True),
            forms.ChoiceField(choices=choices, required=True),
            forms.BooleanField(required=False),
        ]
        super(MarkupContentField, self).__init__(fields, required=False,
            help_text=mark_safe('Markup language used in the content, and should <a href="http://www.mathjax.org/">MathJax</a> be used for displaying TeX formulas?'),
            *args, **kwargs)

        self.fields[0].required = True
        self.widget.widgets[0].attrs['rows'] = rows
        self.fields[1].required = True
        self.widget.widgets[1].choices = choices

    def compress(self, data_list):
        return data_list

    def clean(self, value):
        content, markup, math = super(MarkupContentField, self).clean(value)
        if markup == 'html-wysiwyg':
            # the editor is a UI nicety only
            markup = 'html'
        return content, markup, math


# custom creoleparser Parser class

from genshi.core import Markup

brushre = r"[\w\-#]+"


class AbbrAcronym(creoleparser.elements.InlineElement):
    # handles a subset of the abbreviation/acronym extension
    # http://www.wikicreole.org/wiki/AbbreviationAndAcronyms
    def __init__(self):
        super(AbbrAcronym, self).__init__('abbr', ['^', '^'])

    def _build(self, mo, element_store, environ):
        try:
            abbr, title = mo.group(1).split(":", 1)
        except ValueError:
            abbr = mo.group(1)
            title = None
        return creoleparser.core.bldr.tag.__getattr__('abbr')(
            creoleparser.core.fragmentize(abbr,
                                          self.child_elements,
                                          element_store, environ), title=title)


class HTMLEntity(creoleparser.elements.InlineElement):
    # Allows HTML elements to be passed through
    def __init__(self):
        super(HTMLEntity, self).__init__('span', ['&', ';'])
        self.regexp = re.compile(self.re_string())

    def re_string(self):
        return '&([A-Za-z]\w{1,24}|#\d{2,7}|#[Xx][0-9a-zA-Z]{2,6});'

    def _build(self, mo, element_store, environ):
        content = mo.group(1)
        return creoleparser.core.bldr.tag.__getattr__('span')(Markup('&' + content + ';'))


class CodeBlock(creoleparser.elements.BlockElement):
    """
    A block of code that gets syntax-highlited
    """

    def __init__(self):
        super(CodeBlock, self).__init__('pre', ['{{{', '}}}'])
        self.regexp = re.compile(self.re_string(), re.DOTALL + re.MULTILINE)
        self.regexp2 = re.compile(self.re_string2(), re.MULTILINE)

    def re_string(self):
        start = '^\{\{\{\s*\[(' + brushre + ')\]\s*\n'
        content = r'(.+?\n)'
        end = r'\}\}\}\s*?$'
        return start + content + end

    def re_string2(self):
        """Finds a closing token with a space at the start of the line."""
        return r'^ (\s*?\}\]\s*?\n)'

    def _build(self, mo, element_store, environ):
        lang = mo.group(1)
        code = mo.group(2).rstrip()

        return creoleparser.core.bldr.tag.__getattr__(self.tag)(
            creoleparser.core.fragmentize(code, self.child_elements,
                                          element_store, environ, remove_escapes=False),
            class_="highlight lang-" + lang)


def _find_activity(offering, arg_string):
    """
    Find activity from the arg_string from a macro. Return error message string if it can't be found.
    """
    act_name = arg_string.strip()
    attrs = {}
    acts = Activity.objects.filter(offering=offering, deleted=False).filter(
        models.Q(name=act_name) | models.Q(short_name=act_name))
    if len(acts) == 0:
        return u'[No activity "%s"]' % (act_name)
    elif len(acts) > 1:
        return u'[There is both a name and short name "%s"]' % (act_name)
    else:
        return acts[0]
        due = act.due_date


local_tz = pytz.timezone(settings.TIME_ZONE)


def _duedate(offering, dateformat, macro, environ, *act_name):
    """
    creoleparser macro for due datetimes

    Must be created in a closure by ParserFor with offering set (since that
    doesn't come from the parser).
    """
    act = _find_activity(offering, macro['arg_string'])
    attrs = {}
    if isinstance(act, Activity):
        due = act.due_date
        if due:
            iso8601 = local_tz.localize(due).isoformat()
            text = act.due_date.strftime(dateformat)
            attrs['title'] = iso8601
        else:
            text = u'["%s" has no due date specified]' % (act.name)
            attrs['class'] = 'empty'
    else:
        # error
        text = act
        attrs['class'] = 'empty'

    return creoleparser.core.bldr.tag.__getattr__('span')(text, **attrs)


def _activitylink(offering, macro, environ, *act_name):
    act = _find_activity(offering, macro['arg_string'])
    attrs = {}
    if isinstance(act, Activity):
        text = act.name
        attrs['href'] = act.get_absolute_url()
    else:
        # error
        text = act
        attrs['class'] = 'empty'

    return creoleparser.core.bldr.tag.__getattr__('a')(text, **attrs)


def _pagelist(offering, pageversion, macro, environ, prefix=None):
    # all pages [with the given prefix] for this offering
    from pages.models import Page
    if prefix:
        pages = Page.objects.filter(offering=offering, label__startswith=prefix)
    else:
        pages = Page.objects.filter(offering=offering)

    # ... except this page (if known)
    if pageversion:
        pages = pages.exclude(id=pageversion.page_id)

    elements = []
    for p in pages:
        link = creoleparser.core.bldr.tag.__getattr__('a')(p.current_version().title or p.label, href=p.label)
        li = creoleparser.core.bldr.tag.__getattr__('li')(link)
        elements.append(li)
    return creoleparser.core.bldr.tag.__getattr__('ul')(elements, **{'class': 'filelist'})


class ParserFor(object):
    """
    Class to hold the creoleparser objects for a particular CourseOffering.

    (Needs to be specific to the offering so we can select the right activities/pages in macros.)
    """

    def __init__(self, offering, pageversion=None):
        self.offering = offering
        self.pageversion = pageversion

        def duedate_macro(macro, environ, *act_name):
            return _duedate(self.offering, '%A %B %d %Y', macro, environ, *act_name)

        def duedatetime_macro(macro, environ, *act_name):
            return _duedate(self.offering, '%A %B %d %Y, %H:%M', macro, environ, *act_name)

        def activitylink_macro(macro, environ, *act_name):
            return _activitylink(self.offering, macro, environ, *act_name)

        def pagelist_macro(macro, environ, prefix=None):
            return _pagelist(self.offering, self.pageversion, macro, environ, prefix)

        if self.offering:
            nb_macros = {
                'duedate': duedate_macro,
                'duedatetime': duedatetime_macro,
                'pagelist': pagelist_macro,
                'activitylink': activitylink_macro,
            }
        else:
            nb_macros = None
        CreoleBase = creoleparser.creole11_base(non_bodied_macros=nb_macros, add_heading_ids='h-')

        class CreoleDialect(CreoleBase):
            codeblock = CodeBlock()
            abbracronym = AbbrAcronym()
            htmlentity = HTMLEntity()
            strikethrough = creoleparser.elements.InlineElement('del', '--')

            def __init__(self):
                self.custom_elements = [self.abbracronym, self.strikethrough]
                super(CreoleDialect, self).__init__()

            @property
            def inline_elements(self):
                inline = super(CreoleDialect, self).inline_elements
                inline.append(self.abbracronym)
                inline.append(self.strikethrough)
                inline.append(self.htmlentity)
                return inline

            @property
            def block_elements(self):
                blocks = super(CreoleDialect, self).block_elements
                blocks.insert(0, self.codeblock)
                return blocks

        self.parser = creoleparser.core.Parser(CreoleDialect)
        self.text2html = self.parser.render
