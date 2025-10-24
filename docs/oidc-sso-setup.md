# OIDC SSO Setup for Healthcare Organizations

This guide provides step-by-step instructions for setting up Single Sign-On (SSO) authentication for healthcare organizations using Google OAuth and Microsoft Azure AD.

## Overview

Census supports healthcare SSO through:
- **Google OAuth**: For healthcare workers with personal Google accounts
- **Microsoft Azure AD**: For hospital staff with organizational Microsoft 365 accounts
- **Multi-provider support**: Users can authenticate via either method

## Prerequisites

Before starting, ensure you have:

- Administrator access to your Azure AD tenant (for Azure setup)
- Owner/Editor access to a Google Cloud Project (for Google setup)
- Census deployment with HTTPS enabled (required for production)
- Access to your Census environment variables

## Environment Variables

Add these variables to your `.env` file:

```bash
# Azure AD Configuration
OIDC_RP_CLIENT_ID_AZURE=your-azure-client-id
OIDC_RP_CLIENT_SECRET_AZURE=your-azure-client-secret
OIDC_OP_TENANT_ID_AZURE=your-azure-tenant-id

# Google OAuth Configuration
OIDC_RP_CLIENT_ID_GOOGLE=your-google-client-id
OIDC_RP_CLIENT_SECRET_GOOGLE=your-google-client-secret

# OIDC Protocol Configuration (required)
OIDC_RP_SIGN_ALGO=RS256
OIDC_OP_JWKS_ENDPOINT_GOOGLE=https://www.googleapis.com/oauth2/v3/certs
OIDC_OP_JWKS_ENDPOINT_AZURE=https://login.microsoftonline.com/common/discovery/v2.0/keys
```

## Azure AD Setup (Microsoft 365 Organizations)

### Step 1: Register Application in Azure Portal

1. Navigate to [Azure Portal](https://portal.azure.com/)
2. Go to **Azure Active Directory** > **App registrations**
3. Click **New registration**
4. Configure:
   - **Name**: `Census Healthcare Platform`
   - **Supported account types**:
     - **Multitenant**: "Accounts in any organizational directory" (for multiple hospitals)
     - **Single tenant**: "Accounts in this organizational directory only" (for single organization)
   - **Redirect URI**:
     - **Type**: Web
     - **URL**: `https://your-census-domain.com/oidc/callback/`
     - **Development**: Also add `http://localhost:8000/oidc/callback/`

### Step 2: Configure Application Settings

1. **Authentication** tab:
   - Under **Redirect URIs**, ensure your callback URLs are listed
   - **Front-channel logout URL**: `https://your-census-domain.com/accounts/logout/`
   - **Implicit grant and hybrid flows**: Leave unchecked (Census uses authorization code flow)

2. **Certificates & secrets** tab:
   - Click **New client secret**
   - **Description**: `Census OIDC Secret`
   - **Expires**: Choose appropriate duration (24 months recommended)
   - **Copy the secret value** (this is your `OIDC_RP_CLIENT_SECRET_AZURE`)

3. **API permissions** tab:
   - Ensure these permissions are present:
     - `openid` (OpenID Connect sign-in)
     - `profile` (View users' basic profile)
     - `email` (View users' email address)
     - `User.Read` (Read user profiles)
   - Click **Grant admin consent** if you have admin rights

### Step 3: Note Configuration Values

From the **Overview** tab, copy:

- **Application (client) ID** → `OIDC_RP_CLIENT_ID_AZURE`
- **Directory (tenant) ID** → `OIDC_OP_TENANT_ID_AZURE`

### Step 4: Configure External User Access (Optional)

For guest users (external healthcare workers):

1. Go to **Azure AD** > **External Identities** > **External collaboration settings**
2. Under **Guest user access**, ensure appropriate permissions
3. Under **Guest invite settings**, configure as needed

## Google Cloud Setup (Personal Google Accounts)

### Step 1: Create Google Cloud Project

1. Navigate to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing:
   - **Project name**: `Census Healthcare SSO`
   - **Organization**: Your healthcare organization (if applicable)

### Step 2: Enable APIs

1. Go to **APIs & Services** > **Library**
2. Search and enable:
   - **Google+ API** (or **People API**)
   - **OpenID Connect API**

### Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** > **OAuth consent screen**
2. Choose **External** (unless using Google Workspace)
3. Configure:
   - **App name**: `Census Healthcare Platform`
   - **User support email**: Your healthcare IT support email
   - **App domain**: Your Census domain
   - **Authorized domains**: Add your Census domain
   - **Developer contact**: Your IT contact email
4. **Scopes**: Add `openid`, `email`, `profile`
5. **Test users**: Add healthcare worker emails for testing

### Step 4: Create OAuth Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth 2.0 Client IDs**
3. Configure:
   - **Application type**: Web application
   - **Name**: `Census Healthcare SSO`
   - **Authorized redirect URIs**:
     - Production: `https://your-census-domain.com/oidc/callback/`
     - Development: `http://localhost:8000/oidc/callback/`

### Step 5: Note Configuration Values

Copy the generated:

- **Client ID** → `OIDC_RP_CLIENT_ID_GOOGLE`
- **Client Secret** → `OIDC_RP_CLIENT_SECRET_GOOGLE`

## Deployment Configuration

### Update Environment Variables

1. Add all OIDC variables to your production `.env` file
2. Restart your Census application:

   ```bash
   docker compose restart web
   ```

### Verify Configuration

1. Navigate to your Census login page
2. You should see:
   - "Sign in with Google" button
   - "Sign in with Microsoft" button
   - Traditional email/password login

### Test Authentication

1. **Test Google SSO**:
   - Click "Sign in with Google"
   - Authenticate with a Google account
   - Verify user creation and login

2. **Test Azure SSO**:
   - Click "Sign in with Microsoft"
   - Authenticate with a Microsoft 365 account
   - Verify user creation and login

## Security Considerations

### Production Requirements

- **HTTPS Required**: SSO only works with HTTPS in production
- **Secure Cookies**: Ensure `SECURE_SSL_REDIRECT=True`
- **CSRF Protection**: Census automatically handles CSRF for SSO flows

### Redirect URI Security

- Always use exact redirect URIs (avoid wildcards)
- Use different OAuth apps for development vs production
- Regularly rotate client secrets

### User Account Linking

- Users are automatically linked via email address
- Same user can authenticate via multiple methods
- Encryption keys preserved across authentication methods

## Troubleshooting

### Common Issues

1. **"Redirect URI mismatch"**:
   - Verify exact callback URLs in cloud consoles
   - Check for trailing slashes and HTTP vs HTTPS

2. **"Invalid client"**:
   - Verify client ID and secret in environment variables
   - Check for extra spaces or quotes

3. **"Access denied"**:
   - Verify API permissions in Azure AD
   - Check OAuth consent screen configuration in Google

4. **"Email not found"**:
   - Ensure `email` scope is requested
   - For Azure: verify `User.Read` permission

### Log Analysis

Enable debug logging to troubleshoot:

```bash
# In .env
DEBUG=True

# Check logs
docker compose logs web --follow
```

Look for:

- `CustomOIDCAuthenticationBackend.authenticate called`
- `Got userinfo:` with user data
- `Extracted email from UPN:` for Azure external users

### Development Testing

For local development:

```bash
# Use HTTP callback URLs
OIDC_CALLBACK_URL=http://localhost:8000/oidc/callback/

# Test with ngrok for HTTPS
ngrok http 8000
# Update cloud console redirect URIs with ngrok HTTPS URL
```

## Support

For additional help:

- Check Census logs: `docker compose logs web`
- Review Azure AD sign-in logs in Azure Portal
- Check Google Cloud audit logs
- Contact your Census administrator

## Example Production Configuration

```bash
# Production .env example
DEBUG=False
ALLOWED_HOSTS=census.hospital.org
SECURE_SSL_REDIRECT=True
CSRF_TRUSTED_ORIGINS=https://census.hospital.org

# Azure AD for hospital staff
OIDC_RP_CLIENT_ID_AZURE=a1b2c3d4-e5f6-7890-abcd-ef1234567890
OIDC_RP_CLIENT_SECRET_AZURE=your-secret-from-azure
OIDC_OP_TENANT_ID_AZURE=hospital-tenant-id

# Google OAuth for external healthcare workers
OIDC_RP_CLIENT_ID_GOOGLE=123456789-abcdef.apps.googleusercontent.com
OIDC_RP_CLIENT_SECRET_GOOGLE=your-secret-from-google

# Protocol configuration (unchanged)
OIDC_RP_SIGN_ALGO=RS256
OIDC_OP_JWKS_ENDPOINT_GOOGLE=https://www.googleapis.com/oauth2/v3/certs
OIDC_OP_JWKS_ENDPOINT_AZURE=https://login.microsoftonline.com/common/discovery/v2.0/keys
```
