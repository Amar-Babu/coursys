import copy

# tool to create convenient getters and setters for .config fields
def getter_setter(field):
    def getter(self):
        return self.config[field] if field in self.config else copy.copy(self.defaults[field])
    def setter(self, val):
        self.config[field] = val
    return getter, setter

# for nested config fields
def getter_setter_2(field, subfield):
    def getter(self):
        return (self.config[field][subfield] 
                if field in self.config 
                else copy.copy(self.defaults[field][subfield]))
    def setter(self, val):
        self.config[field][subfield] = val
    return getter, setter

# better version of getter_setter
def config_property(field, default):
    def getter(self):
        return self.config[field] if field in self.config else copy.copy(default)
    def setter(self, val):
        self.config[field] = val
    return property(getter, setter)



from jsonfield.fields import JSONField as JSONFieldOriginal

class JSONField(JSONFieldOriginal):
    """
    override to allow null JSON to map to {}
    """
    def pre_init(self, value, obj):
        if value is None or value == '':
            return {}
        return super(JSONField, self).pre_init(value, obj)

from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^courselib\.json_fields\.JSONField$"])
