#!/bin/sh
# Data Governance Cron Job Entrypoint
# Used by Northflank scheduled job

set -e

echo "Starting data governance processing..."
python manage.py process_data_governance
echo "Data governance processing complete"
