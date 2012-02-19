from django import template
from django import forms
from django.utils.safestring import mark_safe
from django.utils.html import escape
register = template.Library()

@register.filter
def as_dl(form, safe=False):
    """
    Output a Form as a nice <dl>
    """
    out = []
    out.append(unicode(form.non_field_errors()))
    if form.hidden_fields():
        out.append('<div style="display:none">')
        for field in form.hidden_fields():
            out.append(unicode(field))
        out.append('</div>')
        
    out.append('<dl class="dlform">')
    reqcount = 0
    for field in form.visible_fields():
        reqtext = ''
        if field.field.required:
            reqtext = ' <span class="required">*</span>'
            reqcount += 1
        out.append('<dt><label for="id_%s">%s:%s</label></dt><dd>' % (field.name, escape(field.label), reqtext))
        out.append(unicode(field.errors))
        if isinstance(field.field.widget, forms.widgets.RadioSelect):
            out.append('<div class="field radio">%s</div>' % (unicode(field)))
        else:
            out.append('<div class="field">%s</div>' % (unicode(field)))
        if field.help_text:
            if safe:
                out.append('<div class="helptext">%s</div>' % (field.help_text))
            else:
                out.append('<div class="helptext">%s</div>' % (escape(field.help_text)))
        out.append('</dd>')
    
    out.append('</dl>')
    if reqcount > 0:
        out.append('<p class="helptext"><span class="required">*</span> This field is required.</p>')
    return mark_safe('\n'.join(out))

@register.filter
def as_dl_2(form, safe=False):
    """
    Output a Form as a nice <dl>
    """
    out = []
    out.append(unicode(form.non_field_errors()))
    if form.hidden_fields():
        out.append('<div style="display:none">')
        for field in form.hidden_fields():
            out.append(unicode(field))
        out.append('</div>')
        
    out.append('<dl class="dlform">')
    reqcount = 0
    for field in form.visible_fields():
        reqtext = ''
        if field.field.required:
            reqtext = ' <span class="required">*</span>'
            reqcount += 1
        out.append('<dt><label for="id_%s">%s:%s</label></dt><dd>' % (field.name, escape(field.label), reqtext))
        out.append('<div class="field">%s</div>' % (unicode(field)))
        if field.help_text:
            if safe:
                out.append('<div class="helptext">%s</div>' % (field.help_text))
            else:
                out.append('<div class="helptext">%s</div>' % (escape(field.help_text)))
        if field.errors:
            out.append(unicode(field.errors))
        out.append('</dd>')
    
    out.append('</dl>')
    if reqcount > 0:
        out.append('<p class="helptext"><span class="required">*</span> This field is required.</p>')
    return mark_safe('\n'.join(out))

@register.filter
def as_dl_safe(form):
    """
    Like as_dl, but assumes helptext is a safe string
    """
    return as_dl(form, safe=True)

