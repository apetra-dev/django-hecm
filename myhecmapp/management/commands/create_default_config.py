from django.core.management.base import BaseCommand
from myhecmapp.models.config import HECMConfig
from decimal import Decimal

class Command(BaseCommand):
    help = 'Creates a default HECM configuration if none exists'

    def handle(self, *args, **options):
        if not HECMConfig.objects.exists():
            config = HECMConfig.objects.create(
                effective_date="2025-01-01",
                fha_lending_limit=Decimal('1089300'),
                min_age=62,
                mip_rate=Decimal('0.02'),
                origination_fee_min=Decimal('2500'),
                origination_fee_cap=Decimal('6000'),
                first_tier_limit=Decimal('200000'),
                first_tier_rate=Decimal('0.02'),
                second_tier_rate=Decimal('0.01')
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully created config with ID {config.id}'))
        else:
            self.stdout.write(self.style.SUCCESS('Config already exists, no new config created'))