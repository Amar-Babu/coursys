from django.core.exceptions import ValidationError
from models import Alert, AlertType 
from coredata.models import Role, Person, Unit
import coredata.validate_rest
import json
import datetime

# 
#   Here's an example of a valid JSON request: 
#
#    {
#        "person": "classam", 
#        "unit": "FAS"
#        "secret": "23456...",  
#        "alerts": [
#            {
#                "code": "IMMEDIATE RETAKE", 
#                "emplid": 200000561, 
#                "description": "Immediate retake detected: CMPT 125", 
#                "unique_id": "CMPT:125", 
#                "details": {
#                    "COURSE_DESCRIPTION": "Something something CMPT", 
#                    "COURSE_NAME": "CMPT", 
#                    "COURSE_NUMBER": "125"
#                }
#            }, 
#            {
#                "code": "IMMEDIATE RETAKE", 
#                "emplid": 200000251, 
#                "description": "Immediate retake detected: MACM 101", 
#                "unique_id": "MACM:101", 
#                "details": {
#                    "COURSE_DESCRIPTION": "Blah blah MACM", 
#                    "COURSE_NAME": "MACM", 
#                    "COURSE_NUMBER": "101"
#                }
#            }, 
#            {
#                "code": "IMMEDIATE RETAKE", 
#                "emplid": 200000181, 
#                "description": "Immediate retake detected: CMPT 300", 
#                "unique_id": "CMPT:300", 
#                "details": {
#                    "COURSE_DESCRIPTION": "Hurf durf more CMPT", 
#                    "COURSE_NAME": "CMPT", 
#                    "COURSE_NUMBER": "300"
#                }
#            }
#        ] 
#    }

def _create_alerts(data, person, unit):
    print "Creating alerts!"
    try:
        alerts = data['alerts']
        if not isinstance(alerts, (list, tuple)):
            raise ValidationError("Problems not in list format")
        if len(alerts) is 0:
            raise ValidationError("No problems present")
    except KeyError:
        raise ValidationError("No problems present")
            

    errors = []
    
    for alert in alerts:
        comments = None
        try:
            emplid = alert['emplid']
            code = alert['code']
            description = alert['description']
            unique_id = alert['unique_id']
        except KeyError:
            raise ValidationError("Necessary fields not present in alert: " + str(alert) )
            
        try:
            if not isinstance(emplid, int):
                raise ValidationError("Alert emplid:'%s' must be integer" % str(emplid) )
            try:
                student = Person.objects.get(emplid=emplid)
            except Person.DoesNotExist:
                raise ValidationError("Emplid '%d' doesn't exist" % emplid)
            
            if not isinstance(code, basestring) or not isinstance(description, basestring):
                raise ValidationError("Alert code & description must be strings")
            if len(code) >= 30:
                raise ValidationError("Alert code must be less than or equal to 30 characters")

            try: 
                details = alert['details']
            except KeyError:
                details = {}
            
            try:
                alertType = AlertType.objects.get(code=code)
            except AlertType.DoesNotExist:
                # If the AlertType doesn't exist, try to create one. 
                # This requires that the User has provided a unit at the 
                # base level of the JSON
                alertType = AlertType()
                alertType.code = code
                alertType.unit = unit
                alertType.description = "Not set."
                alertType.save() 
            
            alert = Alert()
            alert.person = student
            alert.alerttype = alertType
            alert.description = description
            alert.details = details

            alert.safe_create(unique_id)

        except ValidationError as e:
            print e
            errors.append(str(e))

def new_alerts(post_data):
    """
    Parses the JSON post data, validates, and save the advisor notes
    """
    data = json.loads(post_data) # throws ValueError on bad JSON, UnicodeDecodeError on bad UTF-8
    
    person, unit, key = coredata.validate_rest.validate_credentials(data)
    _create_alerts(data, person, unit)
    
