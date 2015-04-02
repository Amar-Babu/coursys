
Grad Students
=============

A significant portion of the system is devoted to the management and administration of Grad Students. 

Unlike with the undergrad modules, the Grad Students are not offered direct access to the Grad Student
data - instead, their interactions with the Grad System are mediated by Grad Student, TA, and RA administrators, 
using the following applications: 

    /grad
    /tacontracts
    /ta
    /ra

While, of course, it is possible for students who are not Our Grad Students to accept TA and RA posts in FAS
departments, the TA and RA systems are both at least aware of the Grad Student system, because we want to keep 
track of the money that we are paying FAS Grad Students. 

grad
----
The application for managing Grad Students and Programs. The key models are GradProgram and GradStudent.

One important thing to note is that a GradStudent record is not unique to a Student - an individual student
can have multiple GradStudent records, a topic so complicated that I think it deserves its own subheader.

### Multiple GradStudent Records

Yeah, there it is. 

Each student interaction with our department, as a single start-to-finish run, gets one GradStudent object.

Let's imagine two students. Al and Bette. 

Al applies for a CMPT PhD. His application is denied. This creates and closes one GradStudent record. 

Al applies for a CMPT Masters, and is accepted. This creates another GradStudent record.

Al completes the CMPT Masters, graduates, and leaves the university. This closes the previous GradStudent record.

Al applies for a CMPT PhD, is accepted, and graduates. This creates and closes another GradStudent record.

Bette applies for a CMPT Masters, and is accepted. This creates a GradStudent record. 

Bette transfers into CMPT PhD. This changes the program of the existing GradStudent record, and creates a
GradProgramHistory entry in that GradStudent record to record the move. 

Bette completes her CMPT PhD, graduates, and leaves the university. This closes her GradStudent record.

After all of these machinations, both Al and Bette have a CMPT PhD - but Al has three GradStudent records
where Bette only has one.

### Importing Grad Students

Grad records are created/updated daily as part of the regular import: [grad.importer](../grad/importer/) has the guts
and effort has been made to comment it as well as possible.

So, here's a strange thing that you probably need to know: CMPT manually keeps its grad students up to date, but 
ENSC and MSE use a system that (mostly works and) just updates GradStudent status from SIMS.

ta and tacontracts
------------------
The `/ta` and `/tacontracts` applications both manage TA Contracts for a semester.  

_"Why are there two different applications, both offering up what appears to be exactly the same set of functionality?"_

Good question, disembodied voice!

The original `/ta` application was designed to replace the _entire TA workflow_ for the CMPT department - posting a 
CMPT TA Job Application, collecting applicant data, ranking applicants, creating contracts for successful applicants, 
and creating TUGS for those successful applicants. 

While this was 
stupendously useful for CMPT, getting the `/ta` application working for other departments proved difficult, as each 
department had a completely different TA hiring workflow that would need to be respected by the application. 

ENSC and MSE still wanted a way to keep track of Grad Contracts, but not one that was tied to the hiring policies of
CMPT. `/tacontracts` was designed to fill that need, with `/forms` suggested as the solution for complicated hiring
form management. `/tacontracts` was designed to be as department-neutral as possible - it only deals with the problem
of creating and tracking TA Contracts, and leaves the hiring procedure out. 

_"Couldn't you adapt the CMPT system to use the new, simplified TA Contracts system, without pulling out their hiring
and ranking logic? That way you'd only have one set of TAContracts to manage."_ 

The hiring and ranking logic in `/ta` is pretty deeply attached to the contracts logic. It would require taking
the application completely apart, which would mean months of fixing bugs. 

Honestly, I think that a better solution would be to migrate all departments to use `/forms` for hiring and
`/tacontracts` for contracts, and shutter the older system - but that's way in the future. First we have to get
ENSC and MSE to the point where they are happy using `/forms` for hiring.

### TUGS

_"So, both `/ta` and `/tacontracts` use the TUG model from `/ta`. That doesn't seem like very good system architecture.
You should have refactored TUGS out into its own application."_

I totally agree. I should have. 

ra
--

I... don't have a lot to say about the RA part of the app. It manages Research Associate posts. Works fine. Not a lot
of strange gotchas have appeared, here, yet. 
