# Self-Hosting: Scheduled Tasks

Census requires scheduled tasks to process data governance operations including deletion warnings and automatic data cleanup. This guide explains how to set up these tasks on different hosting platforms.

## Overview

The `process_data_governance` management command runs daily to:

1. **Send deletion warnings** - Email notifications 30 days, 7 days, and 1 day before automatic deletion
2. **Soft-delete expired surveys** - Automatically soft-delete surveys that have reached their retention period
3. **Hard-delete surveys** - Permanently delete surveys 30 days after soft deletion

**Legal Requirement**: These tasks are required for GDPR compliance. Failure to run them may result in data being retained longer than legally allowed.

## Prerequisites

- Census deployed and running
- Email configured (for sending deletion warnings)
- Access to your hosting platform's scheduling features

---

## Platform-Specific Setup

### Northflank (Recommended)

Northflank provides native cron job support, making this the simplest option.

#### 1. Create a Cron Job Service

1. Go to your Northflank project
2. Click **"Add Service"** → **"Cron Job"**
3. Configure the job:
   - **Name**: `census-data-governance`
   - **Docker Image**: Use the same image as your web service (e.g., `ghcr.io/eatyourpeas/census:latest`)
   - **Schedule**: `0 2 * * *` (runs at 2 AM UTC daily)
   - **Command**: `python manage.py process_data_governance`

#### 2. Copy Environment Variables

The cron job needs the same environment variables as your web service:

1. In Northflank, go to your web service → **Environment**
2. Copy all environment variables
3. Go to your cron job service → **Environment**
4. Paste the variables

**Critical variables needed:**
- `DATABASE_URL`
- `SECRET_KEY`
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
- `DEFAULT_FROM_EMAIL`
- `SITE_URL` (for email links)

#### 3. Deploy and Test

1. Deploy the cron job service
2. Test it manually via Northflank dashboard: **Jobs** → **Run Now**
3. Check logs to verify successful execution
4. Monitor the **History** tab for scheduled runs

**Northflank Advantages:**
- ✅ No extra containers running 24/7
- ✅ Easy manual testing via UI
- ✅ Built-in logging and monitoring
- ✅ No additional cost (same compute as web service, but only active for ~1-2 minutes daily)

---

### Docker Compose (Local/VPS)

If you're self-hosting with Docker Compose on a VPS or dedicated server, use the system's cron.

#### 1. Create a Cron Script

Create `/usr/local/bin/census-data-governance.sh`:

```bash
#!/bin/bash
# Census Data Governance Cron Job
# Runs daily at 2 AM UTC

# Set working directory
cd /path/to/your/census-app

# Run the management command
docker compose exec -T web python manage.py process_data_governance >> /var/log/census/data-governance.log 2>&1

# Exit with the command's exit code
exit $?
```

Make it executable:

```bash
chmod +x /usr/local/bin/census-data-governance.sh
```

#### 2. Add to System Crontab

```bash
sudo crontab -e
```

Add this line:

```cron
# Census Data Governance - Daily at 2 AM UTC
0 2 * * * /usr/local/bin/census-data-governance.sh
```

#### 3. Create Log Directory

```bash
sudo mkdir -p /var/log/census
sudo chown $USER:$USER /var/log/census
```

#### 4. Test the Script

```bash
# Test manually
/usr/local/bin/census-data-governance.sh

# Check logs
tail -f /var/log/census/data-governance.log
```

---

### Kubernetes

If you're running Census in Kubernetes, use a CronJob resource.

#### Create a CronJob manifest:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: census-data-governance
  namespace: census
spec:
  schedule: "0 2 * * *"  # 2 AM UTC daily
  concurrencyPolicy: Forbid  # Don't run if previous job still running
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: data-governance
            image: ghcr.io/eatyourpeas/census:latest
            command:
            - python
            - manage.py
            - process_data_governance
            envFrom:
            - configMapRef:
                name: census-config
            - secretRef:
                name: census-secrets
            resources:
              requests:
                memory: "256Mi"
                cpu: "100m"
              limits:
                memory: "512Mi"
                cpu: "500m"
```

Apply the manifest:

```bash
kubectl apply -f census-cronjob.yaml
```

Test manually:

```bash
# Trigger a manual run
kubectl create job --from=cronjob/census-data-governance manual-test-1

# Check logs
kubectl logs -l job-name=manual-test-1
```

---

### AWS ECS/Fargate

Use AWS EventBridge (CloudWatch Events) to trigger scheduled ECS tasks.

#### 1. Create EventBridge Rule

```bash
aws events put-rule \
  --name census-data-governance-daily \
  --schedule-expression "cron(0 2 * * ? *)" \
  --description "Run Census data governance tasks daily at 2 AM UTC"
```

#### 2. Add ECS Task as Target

```bash
aws events put-targets \
  --rule census-data-governance-daily \
  --targets "Id"="1","Arn"="arn:aws:ecs:region:account:cluster/census-cluster","RoleArn"="arn:aws:iam::account:role/ecsEventsRole","EcsParameters"="{TaskDefinitionArn=arn:aws:ecs:region:account:task-definition/census-web:latest,LaunchType=FARGATE,NetworkConfiguration={awsvpcConfiguration={Subnets=[subnet-xxx],SecurityGroups=[sg-xxx],AssignPublicIp=ENABLED}},TaskCount=1,PlatformVersion=LATEST}"
```

#### 3. Override Task Command

In your task definition, set the command override:

```json
{
  "overrides": {
    "containerOverrides": [
      {
        "name": "census-web",
        "command": ["python", "manage.py", "process_data_governance"]
      }
    ]
  }
}
```

---

### Heroku

Heroku provides the **Scheduler** add-on for running periodic tasks.

#### 1. Add Scheduler Add-on

```bash
heroku addons:create scheduler:standard
```

#### 2. Configure Job

```bash
heroku addons:open scheduler
```

In the web interface:
- **Command**: `python manage.py process_data_governance`
- **Frequency**: Daily at 2:00 AM (UTC)

---

### Railway

Railway doesn't have native cron support, so use an external service or run a background worker.

#### Option 1: Use GitHub Actions (Recommended)

Create `.github/workflows/data-governance-cron.yml`:

```yaml
name: Data Governance Cron

on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC daily
  workflow_dispatch:  # Allow manual trigger

jobs:
  run-data-governance:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Railway Command
        run: |
          curl -X POST \
            -H "Authorization: Bearer ${{ secrets.RAILWAY_API_TOKEN }}" \
            -H "Content-Type: application/json" \
            -d '{"command": "python manage.py process_data_governance"}' \
            https://backboard.railway.app/graphql/v2
```

#### Option 2: Use EasyCron or Similar Service

1. Sign up for [EasyCron](https://www.easycron.com/) or similar
2. Create a webhook endpoint in your Census app
3. Schedule the webhook to run daily

---

## Command Reference

### Basic Usage

```bash
# Run data governance tasks
python manage.py process_data_governance

# Dry-run mode (show what would be done without making changes)
python manage.py process_data_governance --dry-run

# Verbose output (detailed logging)
python manage.py process_data_governance --verbose
```

### Example Output

```
Starting data governance processing at 2024-10-26 02:00:00

--- Deletion Warnings ---
Sent 3 deletion warnings:
  - 30-day warnings: 2
  - 7-day warnings: 1
  - 1-day warnings: 0

--- Automatic Deletions ---
Soft deleted: 1 surveys
Hard deleted: 0 surveys

⚠️  1 surveys were deleted. Check audit logs for details.

Data governance processing completed at 2024-10-26 02:00:15
```

---

## Testing

### Test in Development

```bash
# Test with dry-run (safe, no changes)
docker compose exec web python manage.py process_data_governance --dry-run --verbose

# Test for real (only if you have test data)
docker compose exec web python manage.py process_data_governance --verbose
```

### Test in Production

1. **First, use dry-run mode:**
   ```bash
   python manage.py process_data_governance --dry-run --verbose
   ```

2. **Review the output** - it will show what surveys would be affected

3. **Run for real** (on your scheduled platform)

4. **Monitor logs** after the first scheduled run

---

## Monitoring

### Check Execution Logs

**Northflank:**
- Go to your cron job service → **History** → View logs

**Docker Compose:**
```bash
tail -f /var/log/census/data-governance.log
```

**Kubernetes:**
```bash
kubectl logs -l job-name=census-data-governance --tail=100
```

### Audit Trail

All deletions are logged in the database. Check via Django admin:

```python
# In Django shell
python manage.py shell

from census_app.surveys.models import Survey
from django.utils import timezone
from datetime import timedelta

# Check recently soft-deleted surveys
Survey.objects.filter(
    deleted_at__gte=timezone.now() - timedelta(days=7)
).values('name', 'deleted_at', 'deletion_date')

# Check surveys due for deletion soon
Survey.objects.filter(
    deletion_date__lte=timezone.now() + timedelta(days=7),
    deleted_at__isnull=True
).values('name', 'deletion_date', 'retention_months')
```

---

## Troubleshooting

### No Emails Being Sent

**Check email configuration:**
```bash
# Test email from Django shell
python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail('Test', 'Testing', 'from@example.com', ['to@example.com'])
```

**Common issues:**
- Missing `EMAIL_HOST` or `EMAIL_PORT` environment variables
- Incorrect SMTP credentials
- Missing `SITE_URL` (emails include survey links)

### Surveys Not Being Deleted

**Check for legal holds:**
```python
from census_app.surveys.models import Survey, LegalHold

# Find surveys with active legal holds
Survey.objects.filter(legal_hold__removed_at__isnull=True)
```

Surveys with active legal holds are **intentionally skipped** from automatic deletion.

### Command Fails Silently

**Run with verbose output:**
```bash
python manage.py process_data_governance --verbose
```

**Check Python errors:**
- Database connection issues
- Missing environment variables
- Permissions problems

---

## Security Considerations

### Environment Variables

The cron job needs access to:
- **Database credentials** (via `DATABASE_URL`)
- **Email credentials** (for sending notifications)
- **Django SECRET_KEY** (for encryption/signing)

**Never log sensitive environment variables!**

### Execution Isolation

- Cron jobs should run in the same network as your database
- Use read-only database credentials if possible for reporting
- Consider separate logging for scheduled tasks

---

## FAQ

**Q: What happens if the cron job fails?**

A: The next day's run will process any missed deletions. Surveys won't be deleted prematurely - only those past their `deletion_date`.

**Q: Can I change the schedule?**

A: Yes, but **daily at 2 AM UTC is recommended** for:
- Off-peak hours (less load)
- Predictable timing for users
- Allows overnight processing before business hours

**Q: What timezone does the schedule use?**

A: All schedules use **UTC**. Django's `deletion_date` is also stored in UTC, so the system is timezone-aware.

**Q: How long does the command take to run?**

A: Typically **30-60 seconds** for most deployments. Scales with:
- Number of surveys approaching deletion
- Email sending speed
- Database query performance

**Q: Can I disable automatic deletion?**

A: No - automatic deletion is **required for GDPR compliance**. However, you can:
- Apply legal holds to prevent specific surveys from being deleted
- Extend retention periods (up to 24 months)
- Export data before deletion

---

## Next Steps

- [Data Governance Overview](./data-governance-overview.md) - Understand the retention policy
- [Data Governance Retention](./data-governance-retention.md) - Learn about retention periods
- [Self-Hosting Backup](./self-hosting-backup.md) - Set up automated backups
- [Email Notifications](./email-notifications.md) - Configure email delivery
