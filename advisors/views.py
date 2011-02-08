# Create your views here.
from advisors.models import *
from courselib.auth import requires_advisor
from django.db.models import Q
from coredata.models import Person, Member, Role
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse

from django.template import RequestContext
from django.template import Context, loader
from django.db.models import query
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import datetime

# --------------Search-----------------------------------
from django.template import RequestContext

@requires_advisor
#@login_required()
def index(request):
        username = request.user.username
        advisor = get_object_or_404(Person, userid = username)
   	return render_to_response("advisors/search_form.html",{'advisor':advisor},context_instance=RequestContext(request))

@requires_advisor
#@login_required()
def search(request):
    if 'index_text' in request.GET and request.GET['index_text']:
       query = request.GET['index_text']
       result = Person.objects.filter(Q(emplid__icontains=query)|Q(first_name__icontains=query)|Q(last_name__icontains=query)|Q(middle_name__icontains=query))   
       return render_to_response('advisors/view.html',{'results':result},context_instance=RequestContext(request)) 
    else:
       return HttpResponse('input error')

# --------------View and Add Notes------------------------

#Add Notes, only advisor can do it
@requires_advisor
def add_notes(request, userid):
#        
	notes = request.POST['NotesContent']
        
	user = get_object_or_404(Person, userid = userid)
	login_user = get_object_or_404(Person, userid = request.user.username)
	advisor = get_object_or_404(Role, person = login_user)

	added_notes = Notes(advisor = advisor, student = user, content = notes, created_date = datetime.now(), hidden = False)
	added_notes.save();

	messages.add_message(request, messages.SUCCESS, 'Submit successfully.')
      	return HttpResponseRedirect(reverse(view_notes, kwargs={'userid':userid}))
	#return render_to_response("advisors/success.html",{'notes':notes, 'userid': userid, 'user': user, 'created_date':datetime.now(), 'advisor':advisor}, context_instance=RequestContext(request))


#View Notes, students can read the notes of themselves, advisors can read all the notes for the choosen student
@login_required
def view_notes(request, userid):

	user_name = get_object_or_404(Person, userid = userid)
	login_user = get_object_or_404(Person, userid = request.user.username)
		
	notes = Notes.objects.filter(student = user_name).filter(hidden = False).order_by('created_date')
  
	return render_to_response("advisors/details.html",{'user_name':user_name, 'userid':userid, 'notes':notes},context_instance=RequestContext(request))

@requires_advisor
def delete_notes(request, userid, note_id):
	
	notes = Notes.objects.get(pk = note_id)
	notes.hidden = True
	notes.save()
	
	user = get_object_or_404(Person, userid = userid)
	notes = Notes.objects.filter(student = user).filter(hidden = False).order_by('created_date')
	messages.add_message(request, messages.SUCCESS, 'Comment deleted successfully.')
	return HttpResponseRedirect(reverse(view_notes, kwargs={'userid':userid}))
	#return render_to_response("advisors/details.html",{'user':user, 'userid':userid, 'notes':notes},context_instance=RequestContext(request))
	
# --------------------------------------------------------
 










