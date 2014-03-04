from django.core.management.base import BaseCommand
from coredata.models import Unit, Role, Person
from faculty.models import CareerEvent, MemoTemplate, Memo, EventConfig, EVENT_TYPES
from datetime import date

def event_get_or_create(**kwargs):
    """
    CareerEvent.objects.get_or_create, but doesn't save and returns a Handler
    """
    try:
        e = CareerEvent.objects.get(**kwargs)
    except CareerEvent.DoesNotExist:
        e = CareerEvent(**kwargs)

    h = EVENT_TYPES[e.event_type](event=e)
    return e, h

def get_or_create_nosave(Model, **kwargs):
    try:
        m = Model.objects.get(**kwargs)
    except Model.DoesNotExist:
        m = Model(**kwargs)
    return m


class Command(BaseCommand):
    help = 'Build some test data for development.'

    def handle(self, *args, **options):
        self.global_data()
        self.department_data()
        self.personal_data()

    def global_data(self):
        univ, _ = Unit.objects.get_or_create(label='UNIV', name='Simon Fraser University', parent=None)
        fas, _ = Unit.objects.get_or_create(label='FAS', name='Faculty of Applied Sciences', parent=univ)
        cmpt, _ = Unit.objects.get_or_create(label='CMPT')
        cmpt.name = 'School of Computing Science'
        cmpt.parent = fas
        cmpt.save()
        ensc, _ = Unit.objects.get_or_create(label='ENSC')
        ensc.name = 'School of Engineering Science'
        ensc.parent = fas
        ensc.save()

        danyu = get_or_create_nosave(Person, userid='dzhao', first_name='Danyu', last_name='Zhao')
        danyu.emplid = 220000123
        danyu.save()

        greg = get_or_create_nosave(Person, userid='ggbaker', first_name='Gregory', last_name='Baker')
        greg.emplid = 220000124
        greg.save()

        diana = get_or_create_nosave(Person, userid='diana', first_name='Diana', last_name='Cukierman')
        diana.emplid = 220000125
        diana.save()

        tony = get_or_create_nosave(Person, userid='dixon', first_name='Anthony', last_name='Dixon')
        tony.emplid = 220000126
        tony.save()

    def department_data(self):
        danyu = Person.objects.get(userid='dzhao')
        cmpt = Unit.objects.get(slug='cmpt')
        mt, _ = MemoTemplate.objects.get_or_create(unit=cmpt, label='Welcome', event_type='APPOINT',
                subject='Appointment to faculty position', created_by=danyu)
        mt.template_text = ("We are pleased to appoint {{first_name}} {{last_name}} to a new job.\n\n" +
                "This memo will be taken as a formal welcoming, wherein the appointee waives {{ his_her}} right to " +
                "any kind of welcoming celebrations requiring a catering order.")
        mt.save()
        ec, _ = EventConfig.objects.get_or_create(unit=cmpt, event_type='FELLOW')
        ec.config = {'fellowships': [
            ('LIEF', 'Lief Chair'),
            ('BBYM', 'Burnaby Mountain Chair'),
            ('UNIR', 'University Research Chair')
        ]}
        ec.save()

    def personal_data(self):
        # get the objects that should already be there
        greg = Person.objects.get(userid='ggbaker')
        diana = Person.objects.get(userid='diana')
        tony = Person.objects.get(userid='dixon')
        danyu = Person.objects.get(userid='dzhao')
        editor = tony

        cmpt = Unit.objects.get(slug='cmpt')
        ensc = Unit.objects.get(slug='ensc')
        fas = Unit.objects.get(slug='fas')

        # create basic roles
        Role.objects.get_or_create(person=greg, unit=ensc, role='FAC')
        Role.objects.get_or_create(person=greg, unit=cmpt, role='FAC')
        Role.objects.get_or_create(person=diana, unit=cmpt, role='FAC')
        Role.objects.get_or_create(person=tony, unit=cmpt, role='FAC')
        Role.objects.get_or_create(person=tony, unit=cmpt, role='ADMN')
        Role.objects.get_or_create(person=danyu, unit=fas, role='ADMN')

        # create some events

        # appointment
        e, h = event_get_or_create(person=greg, unit=cmpt, event_type='APPOINT', start_date=date(2000,9,1),
                                status='A', title=EVENT_TYPES['APPOINT'].default_title())
        e.config = {'spousal_hire': False, 'leaving_reason': 'HERE'}
        h.save(editor=editor)
        appt = e

        # annual salary updates
        for person in [greg, diana, tony]:
            for year in range(2000, 2014):
                e, h = event_get_or_create(person=person, unit=cmpt, event_type='SALARY', start_date=date(year,9,1),
                                        status='A', title=EVENT_TYPES['SALARY'].default_title())
                e.config = {'step': year-1999,
                            'base_salary': 60000 + (year-2000)*2000,
                            'add_salary': 1000 if year>2005 else 0,
                            'add_pay': 500 if year<2005 else 0,
                            }
                h.save(editor=editor)

        # teaching credits
        e, h = event_get_or_create(person=greg, unit=cmpt, event_type='TEACHING', start_date=date(2012,9,1),
                                end_date=date(2012,12,31), status='A', title='Teaching credit because is good person')
        e.config = {'category': 'RELEASE', 'teaching_credits': '1', 'reason': "We just couldn't say no!"}
        h.save(editor=editor)

        e, h = event_get_or_create(person=greg, unit=cmpt, event_type='TEACHING', start_date=date(2013,9,1),
                                end_date=date(2014,4,30), status='A', title='Teaching buyout',
                                comments='Note that this is one teaching credit spread across two semesters.')
        e.config = {'category': 'BUYOUT', 'teaching_credits': '1/2', 'reason': "Somebody gave money."}
        h.save(editor=editor)

        # admin position
        e, h = event_get_or_create(person=greg, unit=cmpt, event_type='ADMINPOS', start_date=date(2008,9,1),
                                end_date=date(2010,8,31), status='A', title='Undergraduate Director')
        e.config = {'position': 'UGRAD_DIRECTOR', 'teaching_credit': '1/2'}
        h.save(editor=editor)

        # a memo
        mt = MemoTemplate.objects.filter(event_type='APPOINT')[0]
        m, _ = Memo.objects.get_or_create(career_event=appt, unit=cmpt, sent_date=date(1999,8,15), to_lines='Greg Baker',
                cc_lines='The FAS Dean\nVancouver Sun', from_person=tony, from_lines='Tony Dixon, CMPT',
                subject='Appointment as lecturer', template=mt, created_by=tony)
        m.memo_text = ("We are pleased to appoint Gregory Baker to a new job.\n\n" +
                "Because we are so excited to hire him, we will be throwing a party. Date to be announced.")
        m.save()










