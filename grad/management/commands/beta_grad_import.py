from django.core.management.base import BaseCommand
from coredata.models import Unit
from grad.importer import NEW_import_unit_grads
from optparse import make_option

class Command(BaseCommand):
    args = '<unit_slug>'
    help = 'Import data from SIMS into our system for one unit\'s grad students'

    option_list = BaseCommand.option_list + (
        make_option('--dry-run', '-n',
            dest='dryrun',
            action='store_true',
            default=False,
            help="Don't actually write changes"),
        )

    def handle(self, *args, **options):
        unit_slug = args[0]

        NEW_import_unit_grads(Unit.objects.get(slug=unit_slug), dry_run=options['dryrun'], verbosity=int(options['verbosity']))