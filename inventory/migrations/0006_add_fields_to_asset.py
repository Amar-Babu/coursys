# Generated by Django 2.0.3 on 2018-09-18 11:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0005_on_delete'),
    ]

    operations = [
        migrations.AddField(
            model_name='asset',
            name='account',
            field=models.CharField(blank=True, max_length=60, null=True, verbose_name='Account No.'),
        ),
        migrations.AddField(
            model_name='asset',
            name='po',
            field=models.CharField(blank=True, max_length=60, null=True, verbose_name='PR/PO No.'),
        ),
        migrations.AddField(
            model_name='asset',
            name='vendor',
            field=models.CharField(blank=True, max_length=400, null=True, verbose_name='Supplier/Vendor'),
        ),
        migrations.AlterField(
            model_name='asset',
            name='category',
            field=models.CharField(blank=True, choices=[('DISP', 'Display'), ('BROC', 'Brochures'), ('TECH', 'Tech Support'), ('GEN', 'General'), ('EVEN', 'Events'), ('SWAG', 'Swag'), ('OFF', 'Office Supplies'), ('TEAC', 'Teaching'), ('RESR', 'Research'), ('ADMN', 'Admin Support'), ('SURP', 'Surplus'), ('BANN', 'Banners')], default='GEN', max_length=4, null=True),
        ),
    ]
