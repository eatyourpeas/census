# Nginx Configuration

This directory contains nginx configuration for production CheckTick deployments.

## Documentation

See the full documentation at:
- [Self-Hosting Production Setup](../docs/self-hosting-production.md)
- [Self-Hosting Quick Start](../docs/self-hosting-quickstart.md)

## Quick Reference

- **nginx.conf** - Main nginx configuration file
- **ssl/** - Place your SSL certificates here (fullchain.pem and privkey.pem)

## Usage

```bash
# Start with nginx
docker compose -f docker-compose.registry.yml -f docker-compose.nginx.yml up -d

# Check configuration
docker compose exec nginx nginx -t
```
