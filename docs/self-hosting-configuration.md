# Self-Hosting Configuration

Complete configuration guide for customizing your CheckTick deployment.

## Environment Variables Reference

All configuration is done through environment variables in the `.env` file.

### Required Settings

#### Database

```bash
# For included PostgreSQL
POSTGRES_DB=checktick
POSTGRES_USER=checktick
POSTGRES_PASSWORD=your-secure-password

# For external database
DATABASE_URL=postgresql://user:password@host:5432/checktick
```

#### Security

```bash
# Generate with: openssl rand -base64 50
SECRET_KEY=your-very-long-random-secret-key-here

# Never use DEBUG=True in production
DEBUG=False

# Your domain(s), comma-separated
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,localhost

# HTTPS origins for CSRF protection
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Force HTTPS redirects (True for production)
SECURE_SSL_REDIRECT=True
```

#### Email

CheckTick requires email for user invitations and notifications:

```bash
DEFAULT_FROM_EMAIL=surveys@yourdomain.com
SERVER_EMAIL=server@yourdomain.com

# Email provider settings (see providers section below)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_TIMEOUT=10
```

### Optional Settings

#### Branding

Customize the appearance of your CheckTick instance:

```bash
# Site title (appears in browser tab and header)
BRAND_TITLE=Your Organization Surveys

# Theme name (currently only 'checktick' available)
BRAND_THEME=checktick

# Custom favicon
BRAND_ICON_URL=/static/your-logo.ico

# Custom fonts
BRAND_FONT_HEADING='Your Font', ui-sans-serif, system-ui
BRAND_FONT_BODY='Your Body Font', ui-serif, Georgia

# Google Fonts URL
BRAND_FONT_CSS_URL=https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap
```

#### Spam Protection

Add hCaptcha to prevent automated signup abuse:

```bash
# Get free keys from https://hcaptcha.com
HCAPTCHA_SITEKEY=your-site-key
HCAPTCHA_SECRET=your-secret-key
```

#### SSO Authentication

Enable Google or Microsoft 365 login for organization encryption features:

**Google:**

```bash
OIDC_RP_CLIENT_ID_GOOGLE=your-client-id.apps.googleusercontent.com
OIDC_RP_CLIENT_SECRET_GOOGLE=your-client-secret
OIDC_OP_JWKS_ENDPOINT_GOOGLE=https://www.googleapis.com/oauth2/v3/certs
```

**Microsoft 365 / Azure AD:**

```bash
OIDC_RP_CLIENT_ID_AZURE=your-application-id
OIDC_RP_CLIENT_SECRET_AZURE=your-client-secret
OIDC_OP_TENANT_ID_AZURE=your-tenant-id
OIDC_OP_JWKS_ENDPOINT_AZURE=https://login.microsoftonline.com/common/discovery/v2.0/keys
```

See [OIDC SSO Setup Guide](oidc-sso-setup.md) for detailed configuration.

#### External Datasets

**Required** for dropdown lists with NHS data (hospitals, trusts, etc.):

```bash
EXTERNAL_DATASET_API_URL=https://api.rcpch.ac.uk
EXTERNAL_DATASET_API_KEY=your-rcpch-api-key
```

Get your free API key from: https://api.rcpch.ac.uk

This provides access to:
- Hospitals (England & Wales)
- NHS Trusts
- Welsh Local Health Boards
- London Boroughs
- NHS England Regions
- Paediatric Diabetes Units
- Integrated Care Boards (ICBs)

#### Data Governance

Configure data retention and export policies for GDPR/healthcare compliance:

```bash
# Default retention period for survey data after closure (months)
# Range: 1-24 months
# Default: 6 months
CENSUS_DEFAULT_RETENTION_MONTHS=6

# Maximum retention period that can be set (months)
# Default: 24 months
CENSUS_MAX_RETENTION_MONTHS=24

# Number of days before export download links expire
# Default: 7 days
CENSUS_DOWNLOAD_LINK_EXPIRY_DAYS=7

# Days before deletion to send warning notifications
# Comma-separated list
# Default: 30,7,1 (warnings at 1 month, 1 week, and 1 day)
CENSUS_WARN_BEFORE_DELETION_DAYS=30,7,1
```

**Note:** These are optional settings with sensible defaults. Most deployments don't need to change these values. Adjust only if your organization has specific compliance requirements.

See the [Data Governance Overview](data-governance-overview.md) for details on how these settings affect survey lifecycle and data retention.

## Email Providers

### Gmail

1. **Enable 2-factor authentication** on your Google account
2. **Create an App Password:**
   - Visit: https://myaccount.google.com/apppasswords
   - Generate password for "Mail"
3. **Configure:**

```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-16-char-app-password
```

### Mailgun (Recommended for Production)

1. **Sign up** at https://www.mailgun.com
2. **Add and verify your domain**
3. **Get SMTP credentials** from domain settings
4. **Configure:**

```bash
EMAIL_HOST=smtp.eu.mailgun.org  # or smtp.mailgun.org for US
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=postmaster@mg.yourdomain.com
EMAIL_HOST_PASSWORD=your-mailgun-smtp-password
```

### SendGrid

```bash
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-api-key
```

### AWS SES

```bash
EMAIL_HOST=email-smtp.us-east-1.amazonaws.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-smtp-username
EMAIL_HOST_PASSWORD=your-smtp-password
```

### Office 365

```bash
EMAIL_HOST=smtp.office365.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@yourdomain.com
EMAIL_HOST_PASSWORD=your-password
```

### Custom SMTP

```bash
EMAIL_HOST=mail.yourdomain.com
EMAIL_PORT=587  # or 465 for SSL, 25 for unencrypted
EMAIL_USE_TLS=True  # False if using EMAIL_USE_SSL
EMAIL_USE_SSL=False  # True for port 465
EMAIL_HOST_USER=username
EMAIL_HOST_PASSWORD=password
```

## Testing Email Configuration

```bash
# Send test email
docker compose exec web python manage.py sendtestemail your@email.com

# Check logs for errors
docker compose logs web | grep -i email
```

## Branding Customization

### Custom Logo

1. **Add your logo** to a static files directory:

```bash
# Create custom static directory
mkdir -p custom-static

# Add your logo
cp your-logo.png custom-static/logo.png
```

2. **Mount in docker-compose:**

```yaml
services:
  web:
    volumes:
      - ./custom-static:/app/custom-static:ro
```

3. **Update .env:**

```bash
BRAND_ICON_URL=/custom-static/logo.png
```

### Custom Fonts

Use Google Fonts or self-hosted fonts:

**Google Fonts:**

```bash
BRAND_FONT_HEADING='Roboto', sans-serif
BRAND_FONT_BODY='Open Sans', sans-serif
BRAND_FONT_CSS_URL=https://fonts.googleapis.com/css2?family=Roboto:wght@700&family=Open+Sans&display=swap
```

**System Fonts:**

```bash
BRAND_FONT_HEADING=ui-sans-serif, system-ui
BRAND_FONT_BODY=ui-serif, Georgia
BRAND_FONT_CSS_URL=  # Leave empty
```

### Custom Theme

Currently only the default `checktick` theme is available. Custom themes coming in future releases.

## Performance Tuning

### Worker Processes

Adjust Gunicorn workers based on your server:

Edit `docker-compose.registry.yml`:

```yaml
services:
  web:
    command: >
      sh -c "python manage.py migrate --noinput &&
             python manage.py collectstatic --noinput &&
             gunicorn census_app.wsgi:application
             --bind 0.0.0.0:8000
             --workers 8
             --worker-class gthread
             --threads 4
             --timeout 120
             --max-requests 1000
             --max-requests-jitter 50"
```

**Workers calculation:**
- Formula: `(2 × CPU cores) + 1`
- Example: 4 core server = 9 workers
- Threads: 2-4 per worker for I/O-bound apps

### Memory Limits

Prevent runaway containers:

```yaml
services:
  web:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 512M
```

### Database Connection Pooling

For high-traffic sites, add connection pooling:

```yaml
services:
  pgbouncer:
    image: pgbouncer/pgbouncer
    environment:
      DATABASES_HOST: db
      DATABASES_PORT: 5432
      DATABASES_USER: checktick
      DATABASES_PASSWORD: your-password
      DATABASES_DBNAME: checktick
      PGBOUNCER_POOL_MODE: transaction
      PGBOUNCER_MAX_CLIENT_CONN: 1000
      PGBOUNCER_DEFAULT_POOL_SIZE: 25
```

Then update web service:

```bash
DATABASE_URL=postgresql://checktick:password@pgbouncer:6432/checktick
```

## Security Configuration

### File Upload Limits

Prevent abuse with upload size limits:

In `nginx/nginx.conf`:

```nginx
client_max_body_size 20M;  # Adjust as needed
```

### Rate Limiting

Already configured in nginx:

```nginx
# Authentication endpoints: 5 requests per minute
limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/m;

# General endpoints: 10 requests per second
limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
```

Adjust in `nginx/nginx.conf` as needed for your traffic.

### Password Requirements

CheckTick enforces Django's default password validators:
- Minimum 8 characters
- Cannot be too similar to username
- Cannot be entirely numeric
- Cannot be commonly used password

To customize, you'll need to modify Django settings (advanced).

## Monitoring and Logging

### Application Logs

```bash
# View real-time logs
docker compose logs -f web

# Search logs
docker compose logs web | grep ERROR

# Save logs to file
docker compose logs web > checktick-logs-$(date +%Y%m%d).log
```

### Database Logs

```bash
# PostgreSQL logs
docker compose logs db

# Query statistics
docker compose exec db psql -U checktick checktick -c "
  SELECT query, calls, total_time, mean_time
  FROM pg_stat_statements
  ORDER BY total_time DESC
  LIMIT 10;
"
```

### Resource Usage

```bash
# Container resource usage
docker stats

# Disk usage
docker system df -v

# Volume sizes
docker volume ls --format "{{.Name}}" | xargs docker volume inspect --format "{{.Name}}: {{.Mountpoint}}"
```

## Advanced Configuration

### Custom Domain for Different Services

Run multiple CheckTick instances on different domains:

```yaml
# checktick-main.yourdomain.com
services:
  web:
    environment:
      ALLOWED_HOSTS: checktick-main.yourdomain.com
      BRAND_TITLE: Main Surveys

# checktick-research.yourdomain.com
services:
  web:
    environment:
      ALLOWED_HOSTS: checktick-research.yourdomain.com
      BRAND_TITLE: Research Surveys
```

### Read-Only Replicas

For very high-traffic deployments:

1. Set up PostgreSQL replication
2. Add read-only database connection
3. Configure Django database router (advanced)

## Configuration Validation

Check your configuration:

```bash
# Verify environment variables loaded
docker compose config

# Check Django configuration
docker compose exec web python manage.py check

# Test database connection
docker compose exec web python manage.py dbshell
```

## Troubleshooting

### Static Files Not Loading

```bash
# Collect static files
docker compose exec web python manage.py collectstatic --noinput

# Verify static files exist
docker compose exec web ls -la /app/staticfiles
```

### CSRF Errors

Ensure `CSRF_TRUSTED_ORIGINS` includes your domain with `https://`:

```bash
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Email Not Sending

```bash
# Test email configuration
docker compose exec web python manage.py shell

>>> from django.core.mail import send_mail
>>> send_mail('Test', 'Message', 'from@example.com', ['to@example.com'])
```

## Next Steps

- **[Production Setup](self-hosting-production.md)** - SSL and nginx configuration
- **[Database Options](self-hosting-database.md)** - Choose your database
- **[Backup & Restore](self-hosting-backup.md)** - Protect your data
- **[Quick Start](self-hosting-quickstart.md)** - Get started quickly
