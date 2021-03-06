# Generated by Django 2.0.13 on 2019-04-04 13:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0006_add_fields_to_asset'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='assetchangerecord',
            name='event',
        ),
        migrations.AlterField(
            model_name='asset',
            name='category',
            field=models.CharField(blank=True, choices=[('SWAG', 'Swag'), ('DISP', 'Display'), ('EVEN', 'Events'), ('RESR', 'Research'), ('BROC', 'Brochures'), ('TEAC', 'Teaching'), ('TECH', 'Tech Support'), ('BANN', 'Banners'), ('OFF', 'Office Supplies'), ('SURP', 'Surplus'), ('ADMN', 'Admin Support'), ('GEN', 'General')], default='GEN', max_length=4, null=True),
        ),
    ]
