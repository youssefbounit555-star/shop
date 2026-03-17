from django.core.management.base import BaseCommand

from analytics.insights import generate_insights

class Command(BaseCommand):
    help = 'Generates insights from analytics data.'

    def handle(self, *args, **options):
        days = int(options.get('days') or 7)
        self.stdout.write(f'Generating insights for the last {days} days...')
        created = generate_insights(days=days)
        self.stdout.write(self.style.SUCCESS(f'Successfully generated {created} insights.'))

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to analyze (default: 7).',
        )
