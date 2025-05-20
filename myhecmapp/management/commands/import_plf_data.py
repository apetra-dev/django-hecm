from django.core.management.base import BaseCommand
from django.db import transaction
from myhecmapp.models.tables import PLFTable
from myhecmapp.models.config import HECMConfig
import os
import pandas as pd
from decimal import Decimal


class Command(BaseCommand):
    help = 'Import PLF data from CSV file into database'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, help='Path to the CSV file')
        parser.add_argument('--clear', action='store_true', help='Clear existing PLF data before import')

    def handle(self, *args, **options):
        file_path = options.get('file')
        clear_existing = options.get('clear', False)

        if not file_path:
            # Default path - adjust as needed
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            file_path = os.path.join(base_dir, 'data', 'consolidated_2017_plfs copy.csv')

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return

        try:
            # Load CSV file
            self.stdout.write(f'Loading data from {file_path}...')
            df = pd.read_csv(file_path)
            self.stdout.write(f'Found {len(df)} entries in the CSV file')

            # Get current config (or create a default one)
            try:
                # Try to get the latest config by ID (assuming latest has highest ID)
                config = HECMConfig.objects.latest('id')
                self.stdout.write(f'Using existing HECMConfig with ID: {config.id}')
            except HECMConfig.DoesNotExist:
                # Create a default config if none exists
                config = HECMConfig.objects.create(
                    fha_lending_limit=Decimal('970800.00'),  # 2022 limit, update as needed
                    mip_rate=Decimal('0.02'),
                    first_tier_limit=Decimal('200000.00'),
                    first_tier_rate=Decimal('0.02'),
                    second_tier_rate=Decimal('0.01'),
                    origination_fee_min=Decimal('2500.00'),
                    origination_fee_cap=Decimal('6000.00'),
                )
                self.stdout.write(self.style.WARNING('Created new HECMConfig as none existed'))

            # Import data in batches to avoid memory issues
            batch_size = 1000
            num_created = 0

            with transaction.atomic():
                # First, clear existing data if requested
                if clear_existing:
                    count = PLFTable.objects.filter(config=config).delete()[0]
                    self.stdout.write(f'Cleared {count} existing PLF table entries')

                # Process in batches
                for i in range(0, len(df), batch_size):
                    batch = df.iloc[i:i + batch_size]
                    plf_objects = []

                    for _, row in batch.iterrows():
                        # Check if this entry already exists
                        exists = PLFTable.objects.filter(
                            config=config,
                            age=int(row['Age']),
                            interest_rate=Decimal(str(row['Rate']))
                        ).exists()

                        if not exists:
                            plf_objects.append(PLFTable(
                                config=config,
                                age=int(row['Age']),
                                interest_rate=Decimal(str(row['Rate'])),
                                factor=Decimal(str(row['PLF']))
                            ))

                    if plf_objects:
                        PLFTable.objects.bulk_create(plf_objects)
                        num_created += len(plf_objects)
                        self.stdout.write(f'Imported {num_created} entries so far...')
                    else:
                        self.stdout.write(f'Skipping batch starting at index {i} (all entries already exist)')

            self.stdout.write(self.style.SUCCESS(f'Successfully imported {num_created} PLF entries'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error importing data: {str(e)}'))