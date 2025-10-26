# Self-Hosting Backup and Restore

Protect your Census data with regular backups and disaster recovery procedures.

## Backup Strategy

A comprehensive backup strategy includes:

1. **Database backups** - Survey data, users, responses
2. **Media files** - Uploaded images, documents
3. **Configuration** - Environment variables, docker-compose files

## Database Backups

### Manual Backup

**With included PostgreSQL:**

```bash
# Create backup
docker compose exec db pg_dump -U census census > census-backup-$(date +%Y%m%d-%H%M%S).sql

# Compress backup
gzip census-backup-*.sql

# Verify backup
ls -lh census-backup-*.sql.gz
```

**With external database:**

```bash
# Direct backup
pg_dump postgresql://user:pass@external-host:5432/census > census-backup-$(date +%Y%m%d).sql

# Or using connection details
PGPASSWORD=yourpassword pg_dump \
  -h external-host \
  -U census \
  -d census \
  -F c \
  -f census-backup-$(date +%Y%m%d).backup
```

### Automated Backups

Create a backup script:

```bash
#!/bin/bash
# File: backup-census.sh

BACKUP_DIR="/var/backups/census"
DATE=$(date +%Y%m%d-%H%M%S)
KEEP_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
docker compose exec -T db pg_dump -U census census | gzip > "$BACKUP_DIR/db-$DATE.sql.gz"

# Backup media files  
docker compose cp web:/app/media "$BACKUP_DIR/media-$DATE"
tar czf "$BACKUP_DIR/media-$DATE.tar.gz" "$BACKUP_DIR/media-$DATE"
rm -rf "$BACKUP_DIR/media-$DATE"

# Backup configuration
cp .env "$BACKUP_DIR/env-$DATE"
cp docker-compose*.yml "$BACKUP_DIR/"

# Delete old backups
find $BACKUP_DIR -name "db-*.sql.gz" -mtime +$KEEP_DAYS -delete
find $BACKUP_DIR -name "media-*.tar.gz" -mtime +$KEEP_DAYS -delete
find $BACKUP_DIR -name "env-*" -mtime +$KEEP_DAYS -delete

# Log completion
echo "$(date): Backup completed - $BACKUP_DIR/db-$DATE.sql.gz"
```

Make it executable and schedule:

```bash
chmod +x backup-census.sh

# Add to crontab (daily at 2 AM)
(crontab -l; echo "0 2 * * * /path/to/backup-census.sh >> /var/log/census-backup.log 2>&1") | crontab -
```

### Cloud Storage Backup

**AWS S3:**

```bash
# Install AWS CLI
sudo apt-get install awscli

# Configure credentials
aws configure

# Add to backup script
aws s3 cp "$BACKUP_DIR/db-$DATE.sql.gz" s3://your-bucket/census-backups/
```

**Azure Blob Storage:**

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login
az login

# Upload backup
az storage blob upload \
  --account-name youraccount \
  --container-name census-backups \
  --name "db-$DATE.sql.gz" \
  --file "$BACKUP_DIR/db-$DATE.sql.gz"
```

## Media File Backups

Media files are stored in the `media_data` Docker volume:

```bash
# Backup media files
docker run --rm \
  -v census_media_data:/media \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/media-$(date +%Y%m%d).tar.gz /media

# List media volume contents
docker run --rm \
  -v census_media_data:/media \
  alpine ls -lah /media
```

## Restore Procedures

### Database Restore

**Complete restore from backup:**

```bash
# Stop the application
docker compose down

# Start only database
docker compose up -d db

# Wait for database to be ready
docker compose exec db pg_isready -U census

# Drop existing database (WARNING: destroys current data)
docker compose exec db psql -U census -c "DROP DATABASE IF EXISTS census;"
docker compose exec db psql -U census -c "CREATE DATABASE census;"

# Restore from backup
gunzip < census-backup-20250126.sql.gz | docker compose exec -T db psql -U census census

# Start application
docker compose up -d
```

**Partial restore (specific tables):**

```bash
# Restore only specific tables
pg_restore -U census -d census -t specific_table backup.dump
```

### Media Files Restore

```bash
# Extract media backup
docker run --rm \
  -v census_media_data:/media \
  -v $(pwd)/backups:/backup \
  alpine sh -c "rm -rf /media/* && tar xzf /backup/media-20250126.tar.gz -C /"

# Verify restoration
docker compose exec web ls -la /app/media
```

### Configuration Restore

```bash
# Restore .env file
cp backups/env-20250126 .env

# Restart services with restored config
docker compose down
docker compose up -d
```

## Disaster Recovery

### Complete System Recovery

Scenario: Server failure, need to restore on new server.

**Step 1: Install Prerequisites**

```bash
# Install Docker and Docker Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

**Step 2: Download Latest Census**

```bash
mkdir census && cd census
curl -O https://raw.githubusercontent.com/eatyourpeas/census/main/docker-compose.registry.yml
```

**Step 3: Restore Configuration**

```bash
# Copy backed-up .env
scp old-server:/backups/.env .

# Or download from cloud storage
aws s3 cp s3://your-bucket/census-backups/env-latest .env
```

**Step 4: Start Database**

```bash
docker compose up -d db
sleep 10  # Wait for database to initialize
```

**Step 5: Restore Database**

```bash
# Download backup
aws s3 cp s3://your-bucket/census-backups/db-latest.sql.gz .

# Restore
gunzip < db-latest.sql.gz | docker compose exec -T db psql -U census census
```

**Step 6: Restore Media Files**

```bash
# Download media backup
aws s3 cp s3://your-bucket/census-backups/media-latest.tar.gz .

# Restore to volume
docker run --rm \
  -v census_media_data:/media \
  -v $(pwd):/backup \
  alpine tar xzf /backup/media-latest.tar.gz -C /
```

**Step 7: Start Application**

```bash
docker compose up -d
docker compose logs -f web
```

### Point-in-Time Recovery

For external managed databases with point-in-time restore:

**AWS RDS:**

```bash
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier census-db \
  --target-db-instance-identifier census-db-restored \
  --restore-time 2025-01-26T10:00:00Z
```

**Azure:**

```bash
az postgres server restore \
  --resource-group census-rg \
  --name census-db-restored \
  --restore-point-in-time "2025-01-26T10:00:00Z" \
  --source-server census-db
```

## Backup Verification

Regularly test your backups:

```bash
#!/bin/bash
# File: verify-backup.sh

LATEST_BACKUP=$(ls -t backups/db-*.sql.gz | head -1)

echo "Testing backup: $LATEST_BACKUP"

# Create test database
docker compose exec db psql -U census -c "CREATE DATABASE census_test;"

# Restore to test database
gunzip < $LATEST_BACKUP | docker compose exec -T db psql -U census census_test

# Verify row counts
echo "Survey count:"
docker compose exec db psql -U census census_test -c "SELECT COUNT(*) FROM surveys_survey;"

echo "User count:"
docker compose exec db psql -U census census_test -c "SELECT COUNT(*) FROM core_user;"

# Cleanup
docker compose exec db psql -U census -c "DROP DATABASE census_test;"

echo "Backup verification complete!"
```

## Backup Best Practices

### Frequency

- **Small deployments:** Daily database backups, weekly media backups
- **Medium deployments:** Daily full backups, hourly incremental (if supported)
- **Large deployments:** Continuous replication to standby database

### Retention

- **Daily backups:** Keep 30 days
- **Weekly backups:** Keep 12 weeks (3 months)
- **Monthly backups:** Keep 12 months (1 year)

### Storage

- **3-2-1 Rule:**
  - 3 copies of data
  - 2 different storage types (local + cloud)
  - 1 offsite backup

### Security

- **Encrypt backups at rest:**

```bash
# Encrypt backup
gpg --symmetric --cipher-algo AES256 census-backup.sql.gz

# Decrypt when needed
gpg --decrypt census-backup.sql.gz.gpg > census-backup.sql.gz
```

- **Restrict access:**

```bash
chmod 600 backups/*
chown root:root backups/
```

### Monitoring

Create a monitoring script:

```bash
#!/bin/bash
# Check if backup was created today

BACKUP_DIR="/var/backups/census"
TODAY=$(date +%Y%m%d)

if ! ls $BACKUP_DIR/db-$TODAY-*.sql.gz 1> /dev/null 2>&1; then
    echo "ERROR: No backup found for today!"
    # Send alert email
    echo "No Census backup created on $TODAY" | mail -s "Backup Alert" admin@example.com
    exit 1
fi

echo "Backup OK: Found backup for $TODAY"
```

## Database Size Management

### Check Database Size

```bash
# Total database size
docker compose exec db psql -U census -c "
  SELECT pg_size_pretty(pg_database_size('census'));
"

# Table sizes
docker compose exec db psql -U census census -c "
  SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
  FROM pg_tables
  WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
  ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
  LIMIT 20;
"
```

### Archive Old Data

For very large databases, consider archiving:

```bash
# Export old survey responses (older than 1 year)
docker compose exec db psql -U census census -c "
  COPY (
    SELECT * FROM surveys_response 
    WHERE created_at < NOW() - INTERVAL '1 year'
  ) TO STDOUT CSV HEADER
" > archived-responses-$(date +%Y%m%d).csv

# Delete archived records (BE CAREFUL!)
# Only after verifying archive is complete
```

## Next Steps

- **[Database Options](self-hosting-database.md)** - Choose your database setup
- **[Production Setup](self-hosting-production.md)** - SSL and security
- **[Configuration](self-hosting-configuration.md)** - Customize your instance
