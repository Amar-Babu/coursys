from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent
from grad.models import Letter,LetterTemplate

@requires_role("GRAD")
def manage_letters(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug)
    letters = Letter.objects.filter(student=grad, removed=False)
    templates = LetterTemplate.objects.filter(unit=grad.program.unit, hidden=False)


    context = {
               'letters': letters,
               'templates': templates,
               'grad': grad,
               'can_edit': True,
               }
    return render(request, 'grad/manage_letters.html', context)
