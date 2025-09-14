# ERISA Recovery System

A comprehensive Django-based system for managing insurance claim recovery with data ingestion, claims management, and user-generated annotations.

### Core Functionality

- **Claims Management**: View, search, and filter insurance claims
- **Advanced Data Ingestion**: Load claim data from CSV or JSON files with re-upload support
- **CSV Re-upload Support**: Append, overwrite, or update existing records with new data
- **Data Overwrite/Append Logic**: Multiple modes for handling duplicate records
- **Claim Details**: Detailed view with CPT codes and denial reasons
- **User Annotations**: Add flags and notes to claims for review tracking

## Setup Instructions

### 1. Environment Setup

```bash
# Activate virtual environment
source virtual/bin/activate

# Navigate to project directory
cd ErisaProject

# Apply database migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser
```

### 2. Load Sample Data

```bash
# Load sample claims from CSV
python manage.py load_claims path/to/file.csv

# Load sample claim details from CSV
python manage.py load_claims .path/to/file.csv

# Load sample data from JSON (includes both claims and details)
python manage.py load_claims path/to/file.json

# Clear existing data and load new data
python manage.py load_claims path/to/file.csv --clear
```

### 3. Run the Server

```bash
python manage.py runserver
```

Visit `http://localhost:8000` to access the application.

## Data Ingestion

### Supported Formats

- **CSV Files**: Separate files for claims and claim details
- **JSON Files**: Single file with both claims and claim details

### CSV Format

#### Claims CSV

```csv
id|patient_name|billed_amount|paid_amount|status|insurer_name|discharge_date
1001|John Smith|15000.00|12000.00,paid|Blue Cross Blue Shield|2024-01-15
```

#### Claim Details CSV

```csv
claim_id|cpt_code|denial_reason
1001|99213|
1002|99214|Prior authorization required
```

### JSON Format

```json
{
  "claims": [
    {
      "id": 30001,
      "patient_name": "Virginia Rhodes",
      "billed_amount": 639787.37,
      "paid_amount": 16001.57,
      "status": "Denied",
      "insurer_name": "United Healthcare",
      "discharge_date": "2022-12-19"
    }
  ],
  "claim_details": [
    {
      "claim_id": 30001,
      "denial_reason": "Policy terminated before service date",
      "cpt_codes": "99204,82947,99406"
    }
  ]
}
```

### Management Command Options

#### Basic Usage

```bash
# Auto-detect file format (default: append mode)
python manage.py load_claims path/to/file.csv

# Specify format explicitly
python manage.py load_claims path/to/file.json --format json
```

#### Data Loading Modes

```bash
# APPEND MODE (default) - Skip existing records, add new ones
python manage.py load_claims path/to/file.csv --mode append

# APPEND MODE with updates - Update existing records with new data
python manage.py load_claims path/to/file.csv --mode append --update-existing

# OVERWRITE MODE - Replace existing records with new data
python manage.py load_claims path/to/file.csv --mode overwrite

# CLEAR MODE - Delete all existing data first, then load new data
python manage.py load_claims path/to/file.csv --mode clear
```

#### CSV Re-upload Support

```bash
# First upload
python manage.py load_claims claims_v1.csv
# Output: ✓ Created: 100 claims

# Re-upload same file (default behavior - skip duplicates)
python manage.py load_claims claims_v1.csv
# Output: ⊝ Skipped: 100 claims

# Re-upload with updates to existing records
python manage.py load_claims claims_v2.csv --update-existing
# Output: ↻ Updated: 50 claims, ✓ Created: 25 claims

# Complete data replacement
python manage.py load_claims new_claims.csv --mode overwrite
# Output: ↻ Updated: 75 claims, ✓ Created: 25 claims
```
