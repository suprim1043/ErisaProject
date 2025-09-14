import csv
import json
import os
from decimal import Decimal
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from ErisaApp.models import Claim, ClaimDetail


class Command(BaseCommand):
    help = 'Load claim records from CSV or JSON files with support for overwrite/append modes'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Path to the CSV or JSON file containing claim data'
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['csv', 'json'],
            help='File format (auto-detected if not specified)'
        )
        parser.add_argument(
            '--mode',
            type=str,
            choices=['append', 'overwrite', 'clear'],
            default='append',
            help='Data loading mode: append (default), overwrite existing records, or clear all data first'
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing records with new data (only in append mode)'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        file_format = options.get('format')
        mode = options.get('mode', 'append')
        update_existing = options.get('update_existing', False)

        if not os.path.exists(file_path):
            raise CommandError(f'File "{file_path}" does not exist.')

        # Auto-detect format if not specified
        if not file_format:
            if file_path.lower().endswith('.csv'):
                file_format = 'csv'
            elif file_path.lower().endswith('.json'):
                file_format = 'json'
            else:
                raise CommandError('Cannot detect file format. Please specify --format.')

        self.stdout.write(f'Loading {file_format.upper()} file: {file_path}')
        self.stdout.write(f'Mode: {mode.upper()}')
        if update_existing and mode == 'append':
            self.stdout.write('Update existing records: YES')

        # Handle different modes
        if mode == 'clear':
            self.stdout.write('Clearing all existing data...')
            with transaction.atomic():
                ClaimDetail.objects.all().delete()
                Claim.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('All existing data cleared.'))

        try:
            with transaction.atomic():
                if file_format == 'csv':
                    self._load_csv(file_path, mode, update_existing)
                else:
                    self._load_json(file_path, mode, update_existing)
        except Exception as e:
            raise CommandError(f'Error loading data: {str(e)}')

        self.stdout.write(self.style.SUCCESS('Data loaded successfully!'))

    def _load_csv(self, file_path, mode, update_existing):
        claims_created = 0
        claims_updated = 0
        claims_skipped = 0
        details_created = 0
        details_updated = 0
        details_skipped = 0
        
        # Auto-detect delimiter
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            sample = csvfile.read(1024)
            csvfile.seek(0)
            
            # Check for pipe delimiter
            if '|' in sample and sample.count('|') > sample.count(','):
                delimiter = '|'
            else:
                delimiter = ','
                
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            fieldnames = reader.fieldnames
            
            self.stdout.write(f'Detected delimiter: "{delimiter}"')
            self.stdout.write(f'Field names: {fieldnames}')
            
            # Check if this looks like a claims file or details file
            if 'patient_name' in fieldnames:
                # This is a claims file
                self.stdout.write('Processing as claims file...')
                for row in reader:
                    result = self._process_claim_from_dict(dict(row), mode, update_existing)
                    if result == 'created':
                        claims_created += 1
                    elif result == 'updated':
                        claims_updated += 1
                    elif result == 'skipped':
                        claims_skipped += 1
                        
            elif 'claim_id' in fieldnames and ('cpt_code' in fieldnames or 'cpt_codes' in fieldnames or 'denial_reason' in fieldnames):
                # This is a details file
                self.stdout.write('Processing as details file...')
                for row in reader:
                    result = self._process_detail_from_dict(dict(row), mode, update_existing)
                    if result == 'created':
                        details_created += 1
                    elif result == 'updated':
                        details_updated += 1
                    elif result == 'skipped':
                        details_skipped += 1
            else:
                raise CommandError(f'CSV file format not recognized. Expected either claims or details format.\nFound fields: {fieldnames}')
                
        self._print_summary(claims_created, claims_updated, claims_skipped, 
                           details_created, details_updated, details_skipped)

    def _load_json(self, file_path, mode, update_existing):
        with open(file_path, 'r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)
            
        claims_created = 0
        claims_updated = 0
        claims_skipped = 0
        details_created = 0
        details_updated = 0
        details_skipped = 0
        
        # Handle different JSON structures
        if isinstance(data, list):
            # Array of records
            for record in data:
                if 'patient_name' in record:
                    result = self._process_claim_from_dict(record, mode, update_existing)
                    if result == 'created':
                        claims_created += 1
                    elif result == 'updated':
                        claims_updated += 1
                    elif result == 'skipped':
                        claims_skipped += 1
                elif 'claim_id' in record and ('cpt_code' in record or 'cpt_codes' in record):
                    result = self._process_detail_from_dict(record, mode, update_existing)
                    if result == 'created':
                        details_created += 1
                    elif result == 'updated':
                        details_updated += 1
                    elif result == 'skipped':
                        details_skipped += 1
                        
        elif isinstance(data, dict):
            # Check if it has separate claims and details sections
            if 'claims' in data:
                for record in data['claims']:
                    result = self._process_claim_from_dict(record, mode, update_existing)
                    if result == 'created':
                        claims_created += 1
                    elif result == 'updated':
                        claims_updated += 1
                    elif result == 'skipped':
                        claims_skipped += 1
                        
            if 'claim_details' in data:
                for record in data['claim_details']:
                    result = self._process_detail_from_dict(record, mode, update_existing)
                    if result == 'created':
                        details_created += 1
                    elif result == 'updated':
                        details_updated += 1
                    elif result == 'skipped':
                        details_skipped += 1
                        
        self._print_summary(claims_created, claims_updated, claims_skipped, 
                           details_created, details_updated, details_skipped)

    def _process_claim_from_dict(self, data, mode, update_existing):
        try:
            claim_id = int(data.get('id', data.get('claim_id', 0)))
            
            # Parse discharge date
            discharge_date = timezone.now().date()
            if 'discharge_date' in data and data['discharge_date']:
                try:
                    discharge_date = datetime.strptime(data['discharge_date'], '%Y-%m-%d').date()
                except ValueError:
                    try:
                        discharge_date = datetime.strptime(data['discharge_date'], '%m/%d/%Y').date()
                    except ValueError:
                        self.stdout.write(self.style.WARNING(f'Invalid discharge_date format: {data["discharge_date"]}'))

            claim_data = {
                'patient_name': data.get('patient_name', ''),
                'billed_amount': Decimal(str(data.get('billed_amount', 0))),
                'paid_amount': Decimal(str(data.get('paid_amount', 0))),
                'status': data.get('status', 'pending'),
                'insurer_name': data.get('insurer_name', ''),
                'discharge_date': discharge_date,
            }

            try:
                existing_claim = Claim.objects.get(claim_id=claim_id)
                
                if mode == 'overwrite' or (mode == 'append' and update_existing):
                    # Update existing record
                    for field, value in claim_data.items():
                        setattr(existing_claim, field, value)
                    existing_claim.save()
                    return 'updated'
                else:
                    # Skip existing record
                    return 'skipped'
                    
            except Claim.DoesNotExist:
                # Create new record
                claim = Claim.objects.create(claim_id=claim_id, **claim_data)
                return 'created'
                
        except (ValueError, KeyError) as e:
            self.stdout.write(self.style.ERROR(f'Error processing claim from data {data}: {str(e)}'))
            return 'error'

    def _process_detail_from_dict(self, data, mode, update_existing):
        try:
            claim_id = int(data.get('claim_id', 0))
            
            try:
                claim = Claim.objects.get(claim_id=claim_id)
            except Claim.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Claim {claim_id} not found for detail record'))
                return 'error'

            # Handle both cpt_code and cpt_codes fields
            cpt_codes_raw = data.get('cpt_codes', data.get('cpt_code', ''))
            denial_reason = data.get('denial_reason', '')
            
            # If cpt_codes contains multiple codes separated by commas, create multiple detail records
            if cpt_codes_raw:
                cpt_codes = [code.strip() for code in str(cpt_codes_raw).split(',') if code.strip()]
            else:
                cpt_codes = ['']  # Create one record with empty cpt_code
            
            results = []
            for cpt_code in cpt_codes:
                # Check if detail already exists (same claim + cpt_code combination)
                try:
                    existing_detail = ClaimDetail.objects.get(claim=claim, cpt_code=cpt_code)
                    
                    if mode == 'overwrite' or (mode == 'append' and update_existing):
                        # Update existing detail
                        existing_detail.denial_reason = denial_reason
                        existing_detail.save()
                        results.append('updated')
                    else:
                        # Skip existing detail
                        results.append('skipped')
                        
                except ClaimDetail.DoesNotExist:
                    # Create new detail
                    ClaimDetail.objects.create(
                        claim=claim,
                        cpt_code=cpt_code,
                        denial_reason=denial_reason
                    )
                    results.append('created')
            
            # Return the most common result, or 'created' if mixed
            if results:
                return max(set(results), key=results.count) if len(set(results)) == 1 else 'created'
            else:
                return 'error'
                
        except (ValueError, KeyError) as e:
            self.stdout.write(self.style.ERROR(f'Error processing detail from data {data}: {str(e)}'))
            return 'error'

    def _print_summary(self, claims_created, claims_updated, claims_skipped, 
                      details_created, details_updated, details_skipped):
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('IMPORT SUMMARY'))
        self.stdout.write('='*50)
        
        self.stdout.write(f'Claims:')
        self.stdout.write(f'  ✓ Created: {claims_created}')
        self.stdout.write(f'  ↻ Updated: {claims_updated}')
        self.stdout.write(f'  ⊝ Skipped: {claims_skipped}')
        
        self.stdout.write(f'\nClaim Details:')
        self.stdout.write(f'  ✓ Created: {details_created}')
        self.stdout.write(f'  ↻ Updated: {details_updated}')
        self.stdout.write(f'  ⊝ Skipped: {details_skipped}')
        
        total_processed = (claims_created + claims_updated + claims_skipped + 
                          details_created + details_updated + details_skipped)
        self.stdout.write(f'\nTotal records processed: {total_processed}')
        self.stdout.write('='*50) 