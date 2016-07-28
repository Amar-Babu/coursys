"""
A module written for inventory control of any type of asset we may want.
"""


from coredata.models import Unit
from autoslug import AutoSlugField
from django.db import models
from django.utils import timezone
from django.db.models import Q
from courselib.slugs import make_slug

CATEGORY_CHOICES = {
    ('SWAG', 'Swag'),
    ('DISP', 'Display'),
    ('BANN', 'Banners'),
    ('BROC', 'Brochures'),
    ('EVEN', 'Events'),
    ('GEN', 'General'),
}

class AssetQuerySet(models.QuerySet):
    """
    Only see visible items, in this case also limited by accessible units.
    """
    def visible(self, units):
        return self.filter(hidden=False, unit__in=units)


class Asset(models.Model):
    name = models.CharField(max_length=150, null=False, blank=False)
    unit = models.ForeignKey(Unit, blank=False, null=False, help_text='Unit to which this asset belongs')
    brand = models.CharField(max_length=60, null=True, blank=True)
    description = models.CharField(max_length=400, blank=True, null=True)
    serial = models.CharField("Serial Number", max_length=60, null=True, blank=True)
    tag = models.CharField("Asset Tag Number", max_length=60, null=True, blank=True, help_text="SFU Asset Tag number, "
                                                                                               "if it exists")
    quantity = models.PositiveIntegerField(blank=True, null=True)
    min_qty = models.PositiveIntegerField("Minimum re-order quantity", blank=True, null=True,
                                          help_text="The minimum quantity that should be in stock before having to "
                                                    "re-order")
    qty_ordered = models.PositiveIntegerField("Quantity on order", blank=True, null=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    category = models.CharField(max_length=4, choices=CATEGORY_CHOICES, null=True, blank=True, default='GEN')
    location = models.CharField(max_length=150, null=True, blank=True)
    notes = models.CharField(max_length=400, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    last_modified = models.DateTimeField(editable=False, blank=False, null=False)
    hidden = models.BooleanField(default=False, null=False, blank=False, editable=False)

    objects = AssetQuerySet.as_manager()

    def autoslug(self):
        return make_slug(self.unit.slug + '-' + self.name)

    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)

    def __unicode__(self):
        return u"%s - %s" % (self.name, self.unit.label)

    def save(self, *args, **kwargs):
        self.last_modified = timezone.now()
        super(Asset, self).save(*args, **kwargs)

    def delete(self):
        """
        Like most of our objects, never actually delete them, just hide them.
        """
        self.hidden = True
        self.save()

    #  Some helper methods to display things with a color code in the index list.
    def out_of_stock(self):
        return self.quantity is not None and self.quantity == 0

    def needs_reorder(self):
        return self.quantity is not None and self.min_qty is not None and self.quantity <= self.min_qty

    def in_stock(self):
        return self.quantity is not None and self.min_qty is not None and self.quantity > self.min_qty
