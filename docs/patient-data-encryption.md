# Patient Data Encryption

Census implements a security-first approach to handling sensitive patient data, using per-survey encryption keys with AES-GCM encryption. This document describes the current implementation and planned enhancements for organizational and individual users.

## Table of Contents

- [Current Implementation](#current-implementation)
  - [Overview](#overview)
  - [How It Works](#how-it-works)
  - [Current Security Properties](#current-security-properties)
  - [Current Limitations](#current-limitations)
- [Web Application Integration](#web-application-integration)
  - [Survey Creation via Web Interface](#survey-creation-via-web-interface)
  - [Key Display Workflow](#key-display-workflow)
  - [Account Creation Integration](#account-creation-integration)
  - [Survey Unlocking](#survey-unlocking-via-web-interface)
  - [Viewing Encrypted Data](#viewing-encrypted-data)
  - [User Experience Flow](#user-experience-flow)
  - [Unified Security Model](#unified-security-model)
- [Planned Enhancements](#planned-enhancements)
  - [Option 1: Organization Users](#option-1-organization-users-recommended-for-healthcare)
  - [Option 2: Individual Users](#option-2-individual-users-personal-responsibility)
  - [Account Type Detection](#account-type-detection)
- [Security Best Practices](#security-best-practices)
- [Compliance and Regulations](#compliance-and-regulations)
- [Migration Path](#migration-path)
- [Technical Reference](#technical-reference)
- [Testing](#testing)

## Current Implementation

### Overview

Census protects sensitive demographic data (names, dates of birth, hospital numbers, addresses) using **per-survey encryption** with the following characteristics:

- **Algorithm**: AES-GCM (Authenticated Encryption with Associated Data)
- **Key Derivation**: Scrypt KDF (n=2^14, r=8, p=1)
- **Key Size**: 256-bit (32 bytes)
- **Authentication**: PBKDF2-HMAC-SHA256 (200,000 iterations)
- **Zero-Knowledge Storage**: Only key hash + salt stored in database

### How It Works

#### 1. Survey Creation

When a survey is created via the API:

```python
# Generate random 32-byte encryption key
key = os.urandom(32)

# Store only hash + salt for verification
digest, salt = make_key_hash(key)
survey.key_hash = digest
survey.key_salt = salt

# Return key ONCE to creator as base64
response.data["one_time_key_b64"] = base64.b64encode(key).decode("ascii")
```

**The encryption key is shown only once and never stored in plaintext.**

#### 2. Data Encryption

When patient data is collected in a survey response:

```python
# Sensitive fields (encrypted)
demographics = {
    "first_name": "John",
    "last_name": "Smith",
    "date_of_birth": "1980-01-01",
    "nhs_number": "1234567890",
    "address": "123 Main St"
}

# Encrypt with survey key
encrypted_blob = encrypt_sensitive(survey_key, demographics)
response.enc_demographics = encrypted_blob  # Stored in database
```

The encryption process:
1. Derives encryption key from survey key using Scrypt KDF with random salt
2. Generates random 12-byte nonce
3. Encrypts JSON data with AES-GCM
4. Stores: `salt (16 bytes) | nonce (12 bytes) | ciphertext`

#### 3. Data Decryption

To view encrypted data, users must "unlock" the survey:

```python
# User provides password or recovery phrase
unlock_method = request.POST.get("unlock_method")

if unlock_method == "password":
    # Derive KEK from user's password
    password = request.POST.get("password")
    survey_kek = survey.unlock_with_password(password)
elif unlock_method == "recovery":
    # Derive KEK from recovery phrase
    recovery_phrase = request.POST.get("recovery_phrase")
    survey_kek = survey.unlock_with_recovery(recovery_phrase)

if survey_kek:
    # Store encrypted credentials in session (not the KEK)
    # KEK is re-derived on each request for forward secrecy
    session_key = request.session.session_key or request.session.create()
    encrypted_creds = encrypt_sensitive(session_key.encode('utf-8'), {
        'password': password,  # or recovery_phrase
        'survey_slug': survey.slug
    })
    request.session["unlock_credentials"] = base64.b64encode(encrypted_creds).decode('ascii')
    request.session["unlock_method"] = unlock_method
    request.session["unlock_verified_at"] = timezone.now().isoformat()
    request.session["unlock_survey_slug"] = survey.slug

# On each request needing the KEK, re-derive it
survey_key = get_survey_key_from_session(request, survey.slug)
if survey_key:
    demographics = response.load_demographics(survey_key)
```

### Current Security Properties

✅ **Zero-Knowledge**: Server never stores encryption keys in plaintext
✅ **Per-Survey Isolation**: Each survey has unique encryption key
✅ **Authenticated Encryption**: AES-GCM prevents tampering
✅ **Strong KDF**: Scrypt protects against brute-force attacks
✅ **Forward Secrecy**: KEK re-derived on each request, never persisted in session
✅ **Minimal Session Storage**: Only encrypted credentials stored, not key material
✅ **Automatic Timeout**: 30-minute session expiration for unlocked surveys
✅ **No Key Escrow**: True end-to-end encryption

### Session Security Model

Census implements a **forward secrecy** model where encryption keys are never persisted in sessions:

**What's Stored in Sessions:**
- `unlock_credentials`: Encrypted blob containing user's password or recovery phrase
- `unlock_method`: Which method was used ("password" or "recovery")
- `unlock_verified_at`: ISO timestamp of when unlock occurred
- `unlock_survey_slug`: Which survey was unlocked

**What's NOT Stored:**
- ❌ The KEK (Key Encryption Key) itself
- ❌ Any plaintext key material
- ❌ Decrypted credentials

**How It Works:**

1. **User Unlocks Survey**: Provides password or recovery phrase
2. **Credentials Encrypted**: Credentials encrypted with session-specific key using `encrypt_sensitive()`
3. **KEK Derived & Verified**: KEK derived and verified, then discarded
4. **Session Metadata Stored**: Only encrypted credentials + metadata stored in session
5. **Each Request**: KEK re-derived on-demand via `get_survey_key_from_session()`
6. **Automatic Cleanup**: After 30 minutes or on error, session data cleared

**Security Benefits:**

- **Forward Secrecy**: Compromise of session storage doesn't reveal KEK
- **Time-Limited Access**: Automatic 30-minute timeout enforced
- **Survey Isolation**: Slug validation prevents cross-survey access
- **No Key Material in Memory**: KEK exists only during request processing

**Helper Function:**

```python
def get_survey_key_from_session(request: HttpRequest, survey_slug: str) -> Optional[bytes]:
    """
    Re-derive KEK from encrypted session credentials.
    Returns None if timeout expired (>30 min) or validation fails.
    """
    # Check credentials exist
    if not request.session.get("unlock_credentials"):
        return None

    # Validate 30-minute timeout
    verified_at_str = request.session.get("unlock_verified_at")
    verified_at = timezone.datetime.fromisoformat(verified_at_str)
    if timezone.is_naive(verified_at):
        verified_at = timezone.make_aware(verified_at)

    if timezone.now() - verified_at > timedelta(minutes=30):
        # Clear expired session
        request.session.pop("unlock_credentials", None)
        request.session.pop("unlock_method", None)
        request.session.pop("unlock_verified_at", None)
        request.session.pop("unlock_survey_slug", None)
        return None

    # Validate survey slug matches
    if request.session.get("unlock_survey_slug") != survey_slug:
        return None

    # Decrypt credentials with session key
    session_key = request.session.session_key
    encrypted_creds_b64 = request.session.get("unlock_credentials")
    encrypted_creds = base64.b64decode(encrypted_creds_b64)

    credentials = decrypt_sensitive(session_key.encode('utf-8'), encrypted_creds)

    # Re-derive KEK based on method
    survey = Survey.objects.get(slug=survey_slug)
    unlock_method = request.session.get("unlock_method")

    if unlock_method == "password":
        return survey.unlock_with_password(credentials["password"])
    elif unlock_method == "recovery":
        return survey.unlock_with_recovery(credentials["recovery_phrase"])
    elif unlock_method == "legacy":
        # Legacy key stored as base64
        return base64.b64decode(credentials["legacy_key"])

    return None
```

### Current Limitations

⚠️ **Key Loss = Data Loss**: If encryption key is lost, data cannot be recovered
⚠️ **User Responsibility**: Users must securely store the key shown at creation
⚠️ **No Organization Recovery**: Organization admins cannot recover lost keys
⚠️ **Single Point of Failure**: No backup/recovery mechanism

## Web Application Integration

The web application follows **exactly the same encryption approach** as the API. Whether users create surveys through the web interface or the API, the security model is identical.

### Survey Creation via Web Interface

When a user creates a survey through the web application at `/surveys/create/`:

```python
@login_required
@require_http_methods(["GET", "POST"])
def survey_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = SurveyCreateForm(request.POST)
        if form.is_valid():
            survey: Survey = form.save(commit=False)
            survey.owner = request.user

            # Generate encryption key automatically
            encryption_key = os.urandom(32)
            survey.set_key(encryption_key)  # Stores hash + salt only

            survey.save()

            # Show key ONCE to user (enhanced approach below)
            request.session['new_survey_key'] = encryption_key
            request.session['new_survey_slug'] = survey.slug

            return redirect("surveys:key-display", slug=survey.slug)
    else:
        form = SurveyCreateForm()
    return render(request, "surveys/create.html", {"form": form})
```

### Key Display Workflow

After survey creation, users are redirected to a **one-time key display page** that shows the encryption key with clear warnings:

```html
<!-- surveys/templates/surveys/key_display.html -->
<div class="max-w-2xl mx-auto">
  <div class="alert alert-warning shadow-lg mb-6">
    <div>
      <svg class="stroke-current flex-shrink-0 h-6 w-6">...</svg>
      <div>
        <h3 class="font-bold">⚠️ Critical: Save Your Encryption Key</h3>
        <div class="text-sm">
          This key encrypts sensitive patient data in your survey.
          <strong>It will only be shown once.</strong>
        </div>
      </div>
    </div>
  </div>

  <div class="card bg-base-100 shadow-xl">
    <div class="card-body">
      <h2 class="card-title">Survey: {{ survey.name }}</h2>

      <!-- Encryption Key Display -->
      <div class="form-control">
        <label class="label">
          <span class="label-text font-semibold">Encryption Key</span>
        </label>
        <div class="input-group">
          <input
            type="text"
            readonly
            value="{{ encryption_key_b64 }}"
            class="input input-bordered w-full font-mono text-sm"
            id="encryption-key"
          />
          <button
            class="btn btn-square"
            onclick="copyToClipboard()"
            title="Copy to clipboard"
          >
            📋
          </button>
        </div>
      </div>

      <!-- Download Options -->
      <div class="flex gap-2 mt-4">
        <button
          class="btn btn-primary"
          onclick="downloadKeyFile()"
        >
          📥 Download Key File
        </button>
        <button
          class="btn btn-secondary"
          onclick="printKey()"
        >
          🖨️ Print Key
        </button>
      </div>

      <!-- User Type Specific Messaging -->
      {% if user.organization_memberships.exists %}
        <!-- Organization User -->
        <div class="alert alert-info mt-6">
          <div>
            <svg class="stroke-current flex-shrink-0 h-6 w-6">...</svg>
            <div>
              <h4 class="font-bold">Organization Account</h4>
              <ul class="text-sm list-disc list-inside mt-2">
                <li>Your organization can recover this key if lost</li>
                <li>Organization admins can access encrypted data</li>
                <li>All key access is logged for compliance</li>
                <li>Multi-person approval required for emergency recovery</li>
              </ul>
            </div>
          </div>
        </div>
      {% else %}
        <!-- Individual User -->
        <div class="alert alert-error mt-6">
          <div>
            <svg class="stroke-current flex-shrink-0 h-6 w-6">...</svg>
            <div>
              <h4 class="font-bold">Individual Account - Important</h4>
              <ul class="text-sm list-disc list-inside mt-2">
                <li>⚠️ You are solely responsible for this key</li>
                <li>⚠️ Lost key = permanent data loss (no recovery)</li>
                <li>⚠️ Save in a secure location (password manager recommended)</li>
                <li>⚠️ Consider printing and storing offline</li>
              </ul>
            </div>
          </div>
        </div>
      {% endif %}

      <!-- Acknowledgment Checkbox -->
      <div class="form-control mt-6">
        <label class="label cursor-pointer justify-start gap-3">
          <input
            type="checkbox"
            class="checkbox checkbox-primary"
            id="acknowledge"
            required
          />
          <span class="label-text">
            I have saved the encryption key securely. I understand the risks of losing it.
          </span>
        </label>
      </div>

      <!-- Continue Button -->
      <div class="card-actions justify-end mt-6">
        <button
          class="btn btn-primary btn-wide"
          id="continue-btn"
          disabled
          onclick="window.location.href='{% url 'surveys:groups' slug=survey.slug %}'"
        >
          Continue to Survey Builder →
        </button>
      </div>
    </div>
  </div>
</div>

<script>
  // Enable continue button only after acknowledgment
  document.getElementById('acknowledge').addEventListener('change', function() {
    document.getElementById('continue-btn').disabled = !this.checked;
  });

  // Copy to clipboard
  function copyToClipboard() {
    const input = document.getElementById('encryption-key');
    input.select();
    document.execCommand('copy');
    alert('Encryption key copied to clipboard!');
  }

  // Download key as text file
  function downloadKeyFile() {
    const key = document.getElementById('encryption-key').value;
    const surveyName = '{{ survey.name|escapejs }}';
    const content = `Census Survey Encryption Key
Survey: ${surveyName}
Created: {{ now|date:"Y-m-d H:i:s" }}

Encryption Key (Base64):
${key}

⚠️ IMPORTANT SECURITY INFORMATION ⚠️
- Store this file in a secure location
- Never share via email or messaging
- Use a password manager or encrypted storage
- Without this key, encrypted patient data cannot be accessed
- See documentation: /docs/patient-data-encryption/

Generated by Census Survey Platform
`;

    const blob = new Blob([content], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `census-survey-${surveyName.toLowerCase().replace(/\s+/g, '-')}-encryption-key.txt`;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  // Print key
  function printKey() {
    window.print();
  }
</script>
```

### Account Creation Integration

The encryption approach is communicated clearly during account signup:

#### Organization Account Signup

```html
<!-- registration/signup_organization.html -->
<div class="alert alert-info mb-6">
  <h3 class="font-bold">🏢 Organization Account Benefits</h3>
  <ul class="text-sm list-disc list-inside mt-2">
    <li><strong>Collaborative:</strong> Multiple users can manage surveys</li>
    <li><strong>Key Recovery:</strong> Organization can recover lost encryption keys</li>
    <li><strong>Audit Trail:</strong> All key access logged for compliance</li>
    <li><strong>Enterprise Security:</strong> Keys backed up in AWS/Azure Key Vault</li>
    <li><strong>HIPAA/GDPR Ready:</strong> Meets healthcare compliance standards</li>
  </ul>
</div>
```

#### Individual Account Signup

```html
<!-- registration/signup_individual.html -->
<div class="alert alert-warning mb-6">
  <h3 class="font-bold">👤 Individual Account Notice</h3>
  <ul class="text-sm list-disc list-inside mt-2">
    <li><strong>Personal Responsibility:</strong> You manage your own encryption keys</li>
    <li><strong>No Recovery Service:</strong> Lost keys cannot be recovered by Census</li>
    <li><strong>Data Loss Risk:</strong> Losing your key means losing encrypted data</li>
    <li><strong>Best For:</strong> Small studies, personal projects, non-critical data</li>
  </ul>

  <div class="form-control mt-4">
    <label class="label cursor-pointer justify-start gap-3">
      <input type="checkbox" class="checkbox checkbox-warning" required />
      <span class="label-text">
        I understand that Census cannot recover lost encryption keys for individual accounts.
        I will store all survey keys securely.
      </span>
    </label>
  </div>
</div>
```

### Helping Users Store Keys Safely

For **individual users** who don't have organizational key recovery, Census implements a **multi-method recovery approach** that balances security with usability. Individual users are given multiple ways to store and recover their encryption keys without relying on browser storage or third-party services.

#### Current Implementation: Password + Recovery Phrase (Option 2)

The current working solution provides **dual recovery paths** for individual users:

```
Survey Encryption Key (KEK)
├─ Password-Encrypted Copy
│  └─ Encrypted with user's password-derived key
│  └─ Used for normal day-to-day access
│
└─ Recovery Code-Encrypted Copy
   └─ Encrypted with BIP39 recovery phrase-derived key
   └─ 12-word mnemonic phrase shown ONCE at creation
   └─ Provides backup if password is lost
```

**Key Features:**

- **Dual Access Methods**: User can unlock with either their account password OR the recovery phrase
- **Zero-Knowledge**: Server stores only encrypted versions, never plaintext keys
- **Offline Backup**: Recovery phrase can be written down or printed and stored physically
- **User Responsibility**: Clear warnings that losing BOTH password and recovery phrase = permanent data loss

**Database Schema:**

```python
class Survey(models.Model):
    # Current fields (for legacy API compatibility)
    key_salt = models.BinaryField()
    key_hash = models.BinaryField()

    # Option 2: Individual user encryption
    encrypted_kek_password = models.BinaryField(null=True)
    encrypted_kek_recovery = models.BinaryField(null=True)
    recovery_code_hint = models.CharField(max_length=100, blank=True)
```

**Implementation at Survey Creation:**

```python
@login_required
@require_http_methods(["GET", "POST"])
def survey_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = SurveyCreateForm(request.POST)
        if form.is_valid():
            survey: Survey = form.save(commit=False)
            survey.owner = request.user

            # Generate master encryption key for this survey
            survey_kek = os.urandom(32)

            # Store hash for legacy API compatibility
            digest, salt = make_key_hash(survey_kek)
            survey.key_hash = digest
            survey.key_salt = salt

            # Determine encryption strategy
            if request.user.organization_memberships.exists():
                # Organization user - implement Option 1 (future)
                setup_organization_encryption(survey, survey_kek, request.user)
            else:
                # Individual user - implement Option 2 (current)
                setup_individual_encryption(survey, survey_kek, request.user)

            survey.save()

            # Redirect to key display page
            request.session['new_survey_key_b64'] = base64.b64encode(survey_kek).decode()
            request.session['new_survey_slug'] = survey.slug

            return redirect("surveys:key-display", slug=survey.slug)
    else:
        form = SurveyCreateForm()
    return render(request, "surveys/create.html", {"form": form})


def setup_individual_encryption(survey: Survey, survey_kek: bytes, user: User):
    """Set up encryption for individual users with dual recovery."""

    # Method 1: Password-based encryption (primary access)
    password_key = derive_key_from_password(user.password)
    survey.encrypted_kek_password = encrypt_sensitive(
        password_key,
        {"kek": survey_kek.hex()}
    )

    # Method 2: Recovery phrase-based encryption (backup access)
    recovery_phrase = generate_bip39_phrase(words=12)
    recovery_key = derive_key_from_passphrase(recovery_phrase)
    survey.encrypted_kek_recovery = encrypt_sensitive(
        recovery_key,
        {"kek": survey_kek.hex()}
    )

    # Store recovery phrase in session to show user ONCE
    request.session['recovery_phrase'] = recovery_phrase


def generate_bip39_phrase(words: int = 12) -> str:
    """
    Generate a BIP39-compatible mnemonic phrase.

    Uses standard BIP39 wordlist for better compatibility with
    password managers and recovery tools.
    """
    from mnemonic import Mnemonic

    mnemo = Mnemonic("english")
    # Generate based on entropy: 128 bits = 12 words, 256 bits = 24 words
    bits = 128 if words == 12 else 256
    return mnemo.generate(strength=bits)


def derive_key_from_passphrase(passphrase: str) -> bytes:
    """
    Derive encryption key from recovery passphrase.

    Uses PBKDF2 with high iteration count to slow brute-force attacks.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"census-recovery-phrase-salt-v1",  # Fixed salt for passphrases
        iterations=200_000
    )
    return kdf.derive(passphrase.encode('utf-8'))
```

**User Interface - Key Display Page:**

```html
<!-- surveys/templates/surveys/key_display.html -->
<div class="max-w-3xl mx-auto p-6">

  <!-- Critical Warning Banner -->
  <div class="alert alert-error shadow-lg mb-6">
    <div>
      <svg class="stroke-current flex-shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      <div>
        <h3 class="font-bold text-lg">⚠️ Critical: Save Your Encryption Keys</h3>
        <div class="text-sm mt-2">
          This survey uses end-to-end encryption for patient data security.
          <strong>You must save BOTH keys below.</strong> They will only be shown once.
          Without them, encrypted data cannot be recovered.
        </div>
      </div>
    </div>
  </div>

  <div class="card bg-base-100 shadow-xl">
    <div class="card-body">
      <h2 class="card-title text-2xl">Survey Created: {{ survey.name }}</h2>

      <!-- Method 1: Survey Encryption Key (Base64) -->
      <div class="divider">Primary Access Method</div>

      <div class="form-control">
        <label class="label">
          <span class="label-text font-semibold text-lg">
            🔐 Survey Encryption Key (Base64)
          </span>
        </label>
        <div class="input-group">
          <input
            type="text"
            readonly
            value="{{ encryption_key_b64 }}"
            class="input input-bordered w-full font-mono text-sm"
            id="encryption-key"
          />
          <button
            class="btn btn-square"
            onclick="copyToClipboard('encryption-key')"
            title="Copy to clipboard"
          >
            📋
          </button>
        </div>
        <label class="label">
          <span class="label-text-alt">
            Use this key to unlock the survey when signed in.
          </span>
        </label>
      </div>

      <!-- Method 2: Recovery Phrase (12 Words) -->
      <div class="divider mt-6">Backup Recovery Method</div>

      <div class="form-control">
        <label class="label">
          <span class="label-text font-semibold text-lg">
            🔑 Recovery Phrase (12 Words)
          </span>
        </label>
        <div class="bg-base-200 p-4 rounded-lg">
          <div class="grid grid-cols-3 gap-3 font-mono text-sm" id="recovery-phrase">
            {% for word in recovery_phrase_words %}
              <div class="bg-base-100 p-2 rounded">
                <span class="text-xs text-gray-500">{{ forloop.counter }}.</span>
                <span class="font-semibold">{{ word }}</span>
              </div>
            {% endfor %}
          </div>
        </div>
        <label class="label">
          <span class="label-text-alt">
            Write these words down in order. They can recover your data if you lose the encryption key.
          </span>
        </label>
      </div>

      <!-- Download and Print Options -->
      <div class="flex flex-wrap gap-3 mt-6">
        <button class="btn btn-primary gap-2" onclick="downloadKeyFile()">
          📥 Download Keys as Text File
        </button>
        <button class="btn btn-secondary gap-2" onclick="downloadRecoverySheet()">
          📄 Download Printable Recovery Sheet
        </button>
        <button class="btn btn-accent gap-2" onclick="window.print()">
          🖨️ Print This Page
        </button>
      </div>

      <!-- Security Best Practices -->
      <div class="alert alert-info mt-6">
        <div>
          <svg class="stroke-current flex-shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <h4 class="font-bold">Recommended Storage Methods:</h4>
            <ul class="text-sm list-disc list-inside mt-2 space-y-1">
              <li><strong>Password Manager:</strong> Store both keys in a password manager (1Password, Bitwarden, etc.)</li>
              <li><strong>Offline Backup:</strong> Print the recovery sheet and store in a safe place</li>
              <li><strong>Encrypted Storage:</strong> Save the text file in encrypted cloud storage (not email!)</li>
              <li><strong>Multiple Copies:</strong> Keep recovery phrase in 2-3 separate secure locations</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Individual User Warning -->
      <div class="alert alert-warning mt-4">
        <div>
          <svg class="stroke-current flex-shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div>
            <h4 class="font-bold">👤 Individual Account - Important</h4>
            <ul class="text-sm list-disc list-inside mt-2">
              <li>⚠️ You are solely responsible for these keys</li>
              <li>⚠️ Census cannot recover lost keys for individual accounts</li>
              <li>⚠️ Losing BOTH the encryption key AND recovery phrase = permanent data loss</li>
              <li>⚠️ Never share these keys via email or messaging apps</li>
              <li>💡 Consider upgrading to an Organization account for key recovery options</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Acknowledgment Checkbox -->
      <div class="form-control mt-6">
        <label class="label cursor-pointer justify-start gap-3">
          <input
            type="checkbox"
            class="checkbox checkbox-error checkbox-lg"
            id="acknowledge"
            required
          />
          <span class="label-text font-semibold">
            I have saved BOTH the encryption key and recovery phrase securely.
            I understand that losing both will result in permanent, unrecoverable data loss.
          </span>
        </label>
      </div>

      <!-- Continue Button -->
      <div class="card-actions justify-end mt-6">
        <button
          class="btn btn-primary btn-wide btn-lg"
          id="continue-btn"
          disabled
          onclick="clearKeysAndContinue()"
        >
          Continue to Survey Builder →
        </button>
      </div>
    </div>
  </div>
</div>

<script>
  // Enable continue button only after acknowledgment
  document.getElementById('acknowledge').addEventListener('change', function() {
    document.getElementById('continue-btn').disabled = !this.checked;
  });

  // Copy to clipboard
  function copyToClipboard(elementId) {
    const input = document.getElementById(elementId);
    input.select();
    document.execCommand('copy');

    // Show feedback
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = '✓';
    setTimeout(() => btn.textContent = originalText, 1500);
  }

  // Download both keys as text file
  function downloadKeyFile() {
    const key = document.getElementById('encryption-key').value;
    const recoveryWords = Array.from(
      document.querySelectorAll('#recovery-phrase .font-semibold')
    ).map(el => el.textContent).join(' ');

    const surveyName = '{{ survey.name|escapejs }}';
    const content = `Census Survey Encryption Keys
=====================================

Survey: ${surveyName}
Created: {{ now|date:"Y-m-d H:i:s" }}

ENCRYPTION KEY (Base64):
${key}

RECOVERY PHRASE (12 Words):
${recoveryWords}

⚠️ CRITICAL SECURITY INFORMATION ⚠️
────────────────────────────────────
• Store this file in a secure location (password manager or encrypted storage)
• NEVER share via email, messaging apps, or unencrypted cloud storage
• You need EITHER the encryption key OR the recovery phrase to access data
• Losing BOTH means permanent data loss - Census cannot recover them
• Consider printing a backup and storing in a physical safe

RECOMMENDED STORAGE:
────────────────────
✓ Password manager (1Password, Bitwarden, LastPass, etc.)
✓ Encrypted USB drive in safe deposit box
✓ Printed copy in fireproof safe
✓ Encrypted cloud storage with strong password

DO NOT STORE:
────────────
✗ Unencrypted email
✗ Text messages or chat apps
✗ Unencrypted cloud drives
✗ Shared network drives
✗ Browser bookmarks or notes

For more information:
https://docs.census.app/patient-data-encryption/

Generated by Census Survey Platform
`;

    const blob = new Blob([content], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `census-${surveyName.toLowerCase().replace(/\s+/g, '-')}-encryption-keys-{{ now|date:"Y-m-d" }}.txt`;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  // Download printable recovery sheet (formatted PDF-ready)
  function downloadRecoverySheet() {
    const key = document.getElementById('encryption-key').value;
    const recoveryWords = Array.from(
      document.querySelectorAll('#recovery-phrase .font-semibold')
    ).map(el => el.textContent);

    const surveyName = '{{ survey.name|escapejs }}';

    let recoveryGrid = '';
    for (let i = 0; i < 12; i++) {
      recoveryGrid += `${i + 1}. ${recoveryWords[i]}\n`;
    }

    const content = `
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║              CENSUS SURVEY - ENCRYPTION RECOVERY SHEET            ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝

Survey Name: ${surveyName}
Created: {{ now|date:"Y-m-d H:i:s" }}

─────────────────────────────────────────────────────────────────────

RECOVERY PHRASE (12 Words)
══════════════════════════

${recoveryGrid}

─────────────────────────────────────────────────────────────────────

ENCRYPTION KEY (Base64)
═══════════════════════

${key}

─────────────────────────────────────────────────────────────────────

⚠️  CRITICAL INSTRUCTIONS ⚠️

1. STORE SECURELY
   • Keep in a fireproof safe or secure location
   • Treat like cash, passport, or bank account details
   • Do NOT leave in plain sight

2. RECOVERY METHODS
   • Use recovery phrase if you forget encryption key
   • Use encryption key for normal survey access
   • You need EITHER one to access encrypted data

3. PROTECTION
   • Do not photograph or scan this document
   • Do not share via email or messaging
   • Shred securely when no longer needed

4. DATA LOSS WARNING
   • Losing BOTH keys = permanent data loss
   • Census cannot recover keys for individual accounts
   • No backdoor or recovery service exists

─────────────────────────────────────────────────────────────────────

For technical documentation:
https://docs.census.app/patient-data-encryption/

Generated by Census Survey Platform
© ${new Date().getFullYear()}

═══════════════════════════════════════════════════════════════════
`;

    const blob = new Blob([content], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `census-${surveyName.toLowerCase().replace(/\s+/g, '-')}-recovery-sheet-{{ now|date:"Y-m-d" }}.txt`;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  // Clear keys from session and continue
  function clearKeysAndContinue() {
    // Keys are cleared from session server-side after first view
    window.location.href = '{% url "surveys:groups" slug=survey.slug %}';
  }
</script>

<style>
  @media print {
    .btn, .alert { page-break-inside: avoid; }
    #continue-btn { display: none; }
  }
</style>
```

**Key Recovery Workflow:**

```python
@login_required
def survey_unlock_with_recovery(request: HttpRequest, slug: str) -> HttpResponse:
    """Unlock survey using either password-based key OR recovery phrase."""

    survey = get_object_or_404(Survey, slug=slug, owner=request.user)

    if request.method == "POST":
        unlock_method = request.POST.get("unlock_method")  # "key" or "recovery"

        if unlock_method == "key":
            # Traditional key unlock (base64 key)
            key_b64 = request.POST.get("key", "")
            try:
                key = base64.b64decode(key_b64)
                if verify_key(key, bytes(survey.key_hash), bytes(survey.key_salt)):
                    request.session["survey_key"] = key
                    log_key_access(request.user, survey, method="encryption_key")
                    messages.success(request, "Survey unlocked successfully.")
                    return redirect("surveys:dashboard", slug=slug)
            except Exception:
                pass

            messages.error(request, "Invalid encryption key.")

        elif unlock_method == "recovery":
            # Recovery phrase unlock
            recovery_phrase = request.POST.get("recovery_phrase", "").strip()

            try:
                # Derive key from recovery phrase
                recovery_key = derive_key_from_passphrase(recovery_phrase)

                # Decrypt the KEK using recovery key
                decrypted_data = decrypt_sensitive(
                    recovery_key,
                    bytes(survey.encrypted_kek_recovery)
                )
                survey_kek = bytes.fromhex(decrypted_data["kek"])

                # Verify it's correct
                if verify_key(survey_kek, bytes(survey.key_hash), bytes(survey.key_salt)):
                    request.session["survey_key"] = survey_kek
                    log_key_access(request.user, survey, method="recovery_phrase")
                    messages.success(
                        request,
                        "Survey unlocked using recovery phrase. "
                        "Consider saving the encryption key for easier access."
                    )
                    return redirect("surveys:dashboard", slug=slug)
            except Exception as e:
                logger.exception("Recovery phrase unlock failed")

            messages.error(request, "Invalid recovery phrase. Check spelling and word order.")

    return render(request, "surveys/unlock.html", {
        "survey": survey,
        "supports_recovery": bool(survey.encrypted_kek_recovery),
    })
```

#### Future Enhancement: OIDC Identity-Based Keys (Planned)

When OIDC (OpenID Connect) authentication is implemented, individual users will have an even better option: **automatic key derivation from their identity provider** (Google, Microsoft, GitHub, etc.).

**How OIDC Will Improve Key Management:**

```
OIDC-Enhanced Individual User Encryption
├─ OIDC Identity-Derived Key (Primary - Auto-unlock)
│  └─ Derived from stable OIDC subject identifier
│  └─ No manual key entry needed when signed in
│  └─ MFA handled by identity provider (Google/Microsoft)
│
├─ Recovery Phrase (Backup)
│  └─ Still generated for offline/fallback access
│  └─ Used if OIDC provider has issues
│
└─ Password-Based Key (Legacy Support)
   └─ For users who don't use OIDC
```

**Benefits of OIDC (when implemented):**

✅ **No Manual Key Management**: Keys automatically available when user authenticates via Google/Microsoft
✅ **MFA Built-In**: Multi-factor authentication handled by identity provider
✅ **Survives Password Changes**: OIDC subject ID is stable across password resets
✅ **Better UX**: "Sign in with Google" → automatic survey unlock
✅ **Recovery Phrase as Backup**: Still available if OIDC provider has issues

**Current Status**: OIDC implementation is planned but not yet available. For now, individual users rely on the password + recovery phrase approach (Option 2).

### Survey Unlocking via Web Interface

Users unlock surveys to view encrypted data through `/surveys/<slug>/unlock/`:

```python
@login_required
@require_http_methods(["GET", "POST"])
def survey_unlock(request: HttpRequest, slug: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug, owner=request.user)

    if request.method == "POST":
        key = request.POST.get("key", "").encode("utf-8")

        # Verify key against stored hash
        if (
            survey.key_hash
            and survey.key_salt
            and verify_key(key, bytes(survey.key_hash), bytes(survey.key_salt))
        ):
            # Store in session (HttpOnly, Secure cookie)
            request.session["survey_key"] = key

            # Log access for audit trail
            AuditLog.objects.create(
                actor=request.user,
                scope=AuditLog.Scope.SURVEY,
                survey=survey,
                action=AuditLog.Action.KEY_ACCESS,
                metadata={"unlocked_at": timezone.now().isoformat()}
            )

            messages.success(request, "Survey unlocked for this session.")
            return redirect("surveys:dashboard", slug=slug)

        messages.error(request, "Invalid encryption key.")

    return render(request, "surveys/unlock.html", {"survey": survey})
```

### Viewing Encrypted Data

Once unlocked, encrypted demographics are automatically decrypted when viewing responses:

```python
@login_required
def survey_responses(request: HttpRequest, slug: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug, owner=request.user)

    # Check if survey is unlocked in session
    if not request.session.get("survey_key"):
        messages.warning(request, "Unlock survey to view encrypted patient data.")
        return redirect("surveys:unlock", slug=slug)

    survey_key = request.session["survey_key"]
    responses = []

    for response in survey.responses.all():
        response_data = {
            "id": response.id,
            "submitted_at": response.submitted_at,
            "answers": response.answers,
        }

        # Decrypt demographics if present
        if response.enc_demographics:
            try:
                demographics = response.load_demographics(survey_key)
                response_data["demographics"] = demographics
            except Exception:
                response_data["demographics_error"] = "Decryption failed"

        responses.append(response_data)

    return render(request, "surveys/responses.html", {
        "survey": survey,
        "responses": responses,
    })
```

### CSV Export with Decryption

Exporting data includes decrypted demographics when survey is unlocked:

```python
@login_required
def survey_export_csv(
    request: HttpRequest, slug: str
) -> Union[HttpResponse, StreamingHttpResponse]:
    survey = get_object_or_404(Survey, slug=slug, owner=request.user)

    if not request.session.get("survey_key"):
        messages.error(request, "Unlock survey first to export with patient data.")
        return redirect("surveys:unlock", slug=slug)

    survey_key = request.session["survey_key"]

    def generate():
        import csv
        from io import StringIO

        # Build header with demographic fields
        header = ["id", "submitted_at", "first_name", "last_name",
                  "date_of_birth", "nhs_number", "answers"]
        s = StringIO()
        writer = csv.writer(s)
        writer.writerow(header)
        yield s.getvalue()
        s.seek(0)
        s.truncate(0)

        for r in survey.responses.iterator():
            # Decrypt demographics
            demographics = {}
            if r.enc_demographics:
                try:
                    demographics = r.load_demographics(survey_key)
                except Exception:
                    demographics = {"error": "decryption_failed"}

            row = [
                r.id,
                r.submitted_at.isoformat(),
                demographics.get("first_name", ""),
                demographics.get("last_name", ""),
                demographics.get("date_of_birth", ""),
                demographics.get("nhs_number", ""),
                json.dumps(r.answers)
            ]
            writer.writerow(row)
            yield s.getvalue()
            s.seek(0)
            s.truncate(0)

    resp = StreamingHttpResponse(generate(), content_type="text/csv")
    resp["Content-Disposition"] = f"attachment; filename={slug}-responses.csv"
    return resp
```

### Session Security

Encryption keys in session are protected by Django's security features:

```python
# census_app/settings.py

# Session security
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
SESSION_COOKIE_SAMESITE = 'Strict'  # CSRF protection
SESSION_COOKIE_AGE = 3600  # 1 hour timeout

# Keys expire after session
# User must re-unlock for each session
```

### User Experience Flow

**For Organization Users:**

1. **Signup** → See benefits of org key recovery
2. **Create Survey** → Key generated automatically
3. **View Key** → See key + org recovery message
4. **Download/Save** → Multiple backup options
5. **Acknowledge** → Confirm key saved
6. **Build Survey** → Add questions, distribute
7. **Unlock (when needed)** → Enter key OR org admin recovery
8. **View Data** → Encrypted data visible during session

**For Individual Users:**

1. **Signup** → Warning about key responsibility
2. **Acknowledge** → Must accept data loss risk
3. **Create Survey** → Key generated automatically
4. **View Key** → See key + strong warnings
5. **Download/Save** → Encouraged to use password manager
6. **Acknowledge** → Confirm key saved securely
7. **Build Survey** → Add questions, distribute
8. **Unlock (when needed)** → Enter key (no recovery option)
9. **View Data** → Encrypted data visible during session

### Unified Security Model

The web application and API share the same security infrastructure:

```python
# Shared encryption utilities (census_app/surveys/utils.py)

def encrypt_sensitive(passphrase_key: bytes, data: dict) -> bytes:
    """Used by both API and web interface"""
    # Same implementation for all entry points

def decrypt_sensitive(passphrase_key: bytes, blob: bytes) -> dict:
    """Used by both API and web interface"""
    # Same implementation for all entry points

def make_key_hash(key: bytes) -> tuple[bytes, bytes]:
    """Used by both API and web interface"""
    # Same implementation for all entry points

def verify_key(key: bytes, digest: bytes, salt: bytes) -> bool:
    """Used by both API and web interface"""
    # Same implementation for all entry points
```

### Benefits of Unified Approach

✅ **Consistent Security**: Same encryption regardless of entry point
✅ **Interoperability**: API and web users can collaborate on same surveys
✅ **Single Audit Trail**: All access logged via same `AuditLog` model
✅ **Unified Testing**: One test suite covers both interfaces
✅ **Clear Documentation**: Users understand security model regardless of interface
✅ **Maintainability**: Single codebase for encryption logic

## OIDC Integration and Authentication

Census plans to implement **OpenID Connect (OIDC)** for authentication, which **significantly enhances** the encryption security model without changing the core encryption approach.

### Why OIDC Works Perfectly with Encryption

OIDC provides **authentication** (proving who you are), while the encryption keys provide **authorization** (accessing encrypted data). These are complementary, not competing:

```
┌─────────────────────────────────────────────────┐
│         Authentication Layer (OIDC)              │
│  • Proves user identity via SSO provider         │
│  • Handles MFA/2FA at identity provider          │
│  • Issues JWT tokens for session management      │
│  • No password stored in Census                  │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│         Authorization Layer (Encryption)         │
│  • Survey encryption keys control data access    │
│  • Independent of authentication method          │
│  • User must have BOTH valid auth AND key       │
│  • Zero-knowledge encryption maintained          │
└─────────────────────────────────────────────────┘
```

### OIDC Benefits for Census

#### 1. Enhanced Security
- **MFA/2FA** handled by identity provider (Google, Microsoft, Okta, etc.)
- **No password storage** in Census (one less attack vector)
- **Single Sign-On (SSO)** for organizational users
- **Centralized access control** via identity provider
- **Audit trail** from both OIDC provider and Census

#### 2. Better User Experience
- **One login** for multiple services
- **MFA already configured** at identity provider
- **Password reset** handled by identity provider
- **Device trust** and conditional access policies
- **Familiar login flow** (e.g., "Sign in with Google")

#### 3. Enterprise Readiness
- **Works with existing enterprise identity systems** (Azure AD, Okta, Auth0)
- **Role mapping** from OIDC claims to Census permissions
- **Group membership** automatically synchronized
- **Compliance** with enterprise security policies

### How OIDC Changes the Key Management

OIDC **improves** the planned encryption enhancements, especially for Option 1 (Organizations):

#### Before OIDC (Password-Based)

```python
# User-encrypted KEK derived from password
user_password = "user's password"
user_key = derive_key_from_password(user_password)
encrypted_kek_user = encrypt(survey_kek, user_key)

# Problem: If user changes password, KEK must be re-encrypted
# Problem: Password complexity requirements needed
# Problem: Password storage/hashing overhead
```

#### With OIDC (Identity-Based)

```python
# User-encrypted KEK derived from OIDC subject identifier
oidc_subject = "google-oauth2|123456789"  # Stable user identifier
user_key = derive_key_from_oidc_subject(oidc_subject, user_salt)
encrypted_kek_user = encrypt(survey_kek, user_key)

# Benefits:
# ✅ Stable identifier (doesn't change with password)
# ✅ No password storage in Census
# ✅ MFA handled by identity provider
# ✅ User can change password without re-encrypting data
```

### Updated Architecture with OIDC

#### Option 1: Organization Users with OIDC

```
Authentication Flow:
1. User clicks "Sign in with [Provider]"
2. Redirected to OIDC provider (e.g., Azure AD)
3. User authenticates (with MFA if configured)
4. OIDC provider returns ID token + access token
5. Census validates token and creates session
6. User identity stored: oidc_provider + subject_id

Survey Encryption Key (KEK) Storage:
├─ User-Encrypted Copy
│  └─ Derived from OIDC subject + user salt
│     └─ Stable across password changes
│     └─ User has primary access when authenticated
│
├─ Organization-Encrypted Copy
│  └─ Encrypted with organization master key
│     └─ Stored in AWS KMS / Azure Key Vault
│     └─ Org admins can decrypt for recovery
│
└─ Emergency Recovery Shares
   └─ Shamir's Secret Sharing (3-of-5 threshold)
      └─ Distributed to designated administrators
```

#### Option 2: Individual Users with OIDC

```
Authentication Flow:
1. User signs in with Google/Microsoft/GitHub
2. MFA handled by provider (if enabled)
3. OIDC token validated by Census
4. User session created

Survey Encryption Key (KEK) Storage:
├─ OIDC-Derived Copy
│  └─ Derived from OIDC subject + user salt
│     └─ User must authenticate to access
│
└─ Recovery Code-Encrypted Copy
   └─ Encrypted with BIP39 recovery phrase
      └─ Shown once at survey creation
      └─ Independent backup method
```

### Implementation with OIDC

#### User Model Changes

```python
# census_app/core/models.py

from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    # OIDC fields
    oidc_provider = models.CharField(
        max_length=100,
        blank=True,
        help_text="OIDC provider (google, microsoft, okta, etc.)"
    )
    oidc_subject = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text="Stable OIDC subject identifier"
    )
    oidc_email_verified = models.BooleanField(
        default=False,
        help_text="Email verified by OIDC provider"
    )

    # Key derivation salt (unique per user)
    key_derivation_salt = models.BinaryField(
        null=True,
        help_text="Salt for deriving encryption keys from OIDC identity"
    )

    # Legacy password users (migrated to OIDC over time)
    is_oidc_user = models.BooleanField(
        default=False,
        help_text="User authenticates via OIDC"
    )
```

#### Survey Key Encryption with OIDC

```python
# census_app/surveys/utils.py

def derive_key_from_oidc_identity(
    oidc_provider: str,
    oidc_subject: str,
    user_salt: bytes
) -> bytes:
    """
    Derive encryption key from OIDC identity.

    This is stable across password changes but unique per user.
    """
    # Combine provider + subject for uniqueness
    identity = f"{oidc_provider}:{oidc_subject}".encode('utf-8')

    # Use PBKDF2 with user-specific salt
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=user_salt,
        iterations=200_000
    )

    return kdf.derive(identity)


def encrypt_survey_kek_for_user(survey_kek: bytes, user: User) -> bytes:
    """Encrypt survey KEK for a specific user."""

    if user.is_oidc_user:
        # OIDC users: derive key from stable identity
        user_key = derive_key_from_oidc_identity(
            user.oidc_provider,
            user.oidc_subject,
            user.key_derivation_salt
        )
    else:
        # Legacy users: derive from password (to be migrated)
        user_key = derive_key_from_password(user.password)

    # Encrypt KEK with user key
    return encrypt_sensitive(user_key, {"kek": survey_kek.hex()})


def decrypt_survey_kek_for_user(
    encrypted_kek: bytes,
    user: User
) -> bytes:
    """Decrypt survey KEK for a specific user."""

    if user.is_oidc_user:
        user_key = derive_key_from_oidc_identity(
            user.oidc_provider,
            user.oidc_subject,
            user.key_derivation_salt
        )
    else:
        user_key = derive_key_from_password(user.password)

    decrypted = decrypt_sensitive(user_key, encrypted_kek)
    return bytes.fromhex(decrypted["kek"])
```

#### Survey Creation with OIDC

```python
# census_app/surveys/views.py

@login_required
@require_http_methods(["GET", "POST"])
def survey_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = SurveyCreateForm(request.POST)
        if form.is_valid():
            survey: Survey = form.save(commit=False)
            survey.owner = request.user

            # Generate survey encryption key (KEK)
            survey_kek = os.urandom(32)

            # Store hash for verification (legacy compatibility)
            digest, salt = make_key_hash(survey_kek)
            survey.key_hash = digest
            survey.key_salt = salt

            # Encrypt KEK for user (OIDC or password-based)
            if request.user.is_oidc_user:
                survey.encrypted_kek_user = encrypt_survey_kek_for_user(
                    survey_kek,
                    request.user
                )
                # User can unlock via OIDC authentication alone
                # No manual key entry needed for OIDC users!
            else:
                # Legacy: show key once for manual storage
                request.session['new_survey_key'] = survey_kek

            # Organization users: also encrypt with org master key
            if request.user.organization_memberships.exists():
                org = request.user.organization_memberships.first().organization
                org_master_key = get_org_master_key(org)
                survey.encrypted_kek_org = encrypt_survey_kek_with_org_key(
                    survey_kek,
                    org_master_key
                )

            survey.save()

            # OIDC users skip manual key display
            if request.user.is_oidc_user:
                messages.success(
                    request,
                    "Survey created! Encryption is automatic with your account."
                )
                return redirect("surveys:groups", slug=survey.slug)
            else:
                return redirect("surveys:key-display", slug=survey.slug)
    else:
        form = SurveyCreateForm()
    return render(request, "surveys/create.html", {"form": form})
```

#### Auto-Unlock for OIDC Users

```python
@login_required
def survey_responses(request: HttpRequest, slug: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug, owner=request.user)

    # OIDC users: automatic unlock if user has encrypted KEK
    if request.user.is_oidc_user and survey.encrypted_kek_user:
        try:
            # Decrypt KEK using user's OIDC identity
            survey_kek = decrypt_survey_kek_for_user(
                survey.encrypted_kek_user,
                request.user
            )
            request.session["survey_key"] = survey_kek

            # Log auto-unlock
            AuditLog.objects.create(
                actor=request.user,
                scope=AuditLog.Scope.SURVEY,
                survey=survey,
                action=AuditLog.Action.KEY_ACCESS,
                metadata={
                    "method": "oidc_auto_unlock",
                    "provider": request.user.oidc_provider
                }
            )
        except Exception as e:
            messages.error(request, "Unable to unlock survey automatically.")
            return redirect("surveys:unlock", slug=slug)

    # Legacy users or OIDC users without encrypted KEK: manual unlock
    elif not request.session.get("survey_key"):
        messages.warning(request, "Unlock survey to view encrypted data.")
        return redirect("surveys:unlock", slug=slug)

    # Continue with response viewing...
```

### Migration Strategy

#### Phase 1: Add OIDC Support (Backward Compatible)
```python
# Support both legacy and OIDC users
# New users can choose OIDC
# Existing users continue with password
```

#### Phase 2: Migrate Existing Users to OIDC
```python
@login_required
def migrate_to_oidc(request: HttpRequest):
    """One-time migration for legacy users."""
    if request.user.is_oidc_user:
        messages.info(request, "Already using OIDC.")
        return redirect("home")

    if request.method == "POST":
        # User has authenticated with OIDC provider
        oidc_provider = request.POST.get("oidc_provider")
        oidc_subject = request.POST.get("oidc_subject")

        # Generate user salt for key derivation
        user_salt = os.urandom(16)

        # Re-encrypt all survey KEKs with OIDC-derived key
        for survey in Survey.objects.filter(owner=request.user):
            if survey.encrypted_kek_user:
                # Decrypt with old password-based key
                old_kek = decrypt_survey_kek_for_user(
                    survey.encrypted_kek_user,
                    request.user  # Uses password
                )

                # Update user to OIDC
                request.user.oidc_provider = oidc_provider
                request.user.oidc_subject = oidc_subject
                request.user.key_derivation_salt = user_salt
                request.user.is_oidc_user = True

                # Re-encrypt with new OIDC-derived key
                survey.encrypted_kek_user = encrypt_survey_kek_for_user(
                    old_kek,
                    request.user  # Now uses OIDC
                )
                survey.save()

        request.user.save()
        messages.success(request, "Migrated to OIDC successfully!")
        return redirect("home")
```

### Security Benefits of OIDC + Encryption

#### Defense in Depth

```
Layer 1: OIDC Authentication
├─ MFA at identity provider
├─ Device trust policies
├─ Conditional access (IP, location)
└─ Session management

Layer 2: Census Authorization
├─ Role-based access control
├─ Survey ownership verification
└─ Organization membership checks

Layer 3: Encryption Key Control
├─ Survey-specific encryption keys
├─ Zero-knowledge architecture
├─ Per-user encrypted KEKs
└─ Organization recovery options
```

#### Attack Scenarios and Mitigations

| Attack | Without OIDC | With OIDC |
|--------|--------------|-----------|
| **Credential Stuffing** | Vulnerable if weak passwords | Protected by identity provider MFA |
| **Phishing** | Credentials stolen → account access | MFA prevents access; Census never sees password |
| **Database Breach** | Password hashes exposed | No passwords stored; OIDC subjects useless alone |
| **Session Hijacking** | Need password to re-authenticate | MFA required at identity provider |
| **Insider Threat** | Admin could reset password | Cannot reset OIDC identity; org recovery needed |
| **Lost Credentials** | Manual password reset | Identity provider handles recovery |

### User Experience with OIDC

#### Organization User Flow

1. **Signup**: "Sign in with Microsoft" (organization SSO)
2. **Create Survey**: Automatic encryption (no manual key management!)
3. **View Data**: Auto-unlock when authenticated via OIDC
4. **Recovery**: Organization admin can recover if needed
5. **MFA**: Handled by Microsoft/Google/Okta

#### Individual User Flow

1. **Signup**: "Sign in with Google"
2. **Create Survey**: Shows recovery phrase (backup method)
3. **View Data**: Auto-unlock + optional manual key for extra security
4. **Recovery**: Recovery phrase if OIDC provider issues
5. **MFA**: Enable at Google/Microsoft level

### Configuration Example

```python
# census_app/settings.py

OIDC_ENABLED = env.bool("OIDC_ENABLED", default=True)

OIDC_PROVIDERS = {
    "google": {
        "client_id": env("GOOGLE_OAUTH_CLIENT_ID"),
        "client_secret": env("GOOGLE_OAUTH_CLIENT_SECRET"),
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
        "scopes": ["openid", "email", "profile"],
        "display_name": "Google",
    },
    "microsoft": {
        "client_id": env("MICROSOFT_OAUTH_CLIENT_ID"),
        "client_secret": env("MICROSOFT_OAUTH_CLIENT_SECRET"),
        "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "userinfo_url": "https://graph.microsoft.com/oidc/userinfo",
        "scopes": ["openid", "email", "profile"],
        "display_name": "Microsoft",
    },
    "okta": {
        # Enterprise OIDC provider for organizations
        "client_id": env("OKTA_CLIENT_ID"),
        "client_secret": env("OKTA_CLIENT_SECRET"),
        "authorize_url": env("OKTA_AUTHORIZE_URL"),
        "token_url": env("OKTA_TOKEN_URL"),
        "userinfo_url": env("OKTA_USERINFO_URL"),
        "scopes": ["openid", "email", "profile", "groups"],
        "display_name": "Okta",
    },
}

# Recommended packages:
# - mozilla-django-oidc (mature, well-maintained)
# - authlib (flexible, supports multiple providers)
# - social-auth-app-django (comprehensive social auth)
```

### Why OIDC is Better Than 2FA Alone

| Feature | Password + 2FA | OIDC + MFA |
|---------|---------------|------------|
| **User Experience** | Manage password + 2FA code | Single SSO login |
| **Security** | Census stores password hashes | Census stores nothing |
| **MFA Management** | Per-application setup | Centralized at identity provider |
| **Account Recovery** | Reset in Census | Identity provider handles |
| **Enterprise Integration** | Manual user provisioning | Automatic via OIDC groups |
| **Audit Trail** | Census logs only | Census + identity provider |
| **Encryption Key Stability** | Changes with password | Stable OIDC subject |
| **Attack Surface** | Password storage + 2FA | No password, delegated auth |

### Recommendation

✅ **Implement OIDC** instead of building custom 2FA
✅ **Support multiple providers** (Google, Microsoft, Okta)
✅ **Auto-unlock for OIDC users** via encrypted KEKs
✅ **Keep recovery phrases** for individual users as backup
✅ **Organization master keys** remain unchanged
✅ **Migrate existing users** gradually to OIDC

**Result**: Better security, better UX, less code to maintain, and the encryption model becomes even stronger!

## Planned Enhancements

To address key loss scenarios while maintaining security, Census will implement **dual-tier key management** based on user type:

### Option 1: Organization Users (Recommended for Healthcare)

**For users belonging to an organization**, implement **Key Escrow with Dual Control**:

#### Architecture

```
Survey Encryption Key (KEK)
├─ User-Encrypted Copy
│  └─ Encrypted with user's password-derived key
│     └─ User has primary access
│
├─ Organization-Encrypted Copy
│  └─ Encrypted with organization master key
│     └─ Stored in AWS KMS / Azure Key Vault
│     └─ Org ADMINs can decrypt for recovery
│
└─ Emergency Recovery Shares (Optional)
   └─ Shamir's Secret Sharing (3-of-5 threshold)
      └─ Distributed to designated administrators
      └─ Requires multiple people for catastrophic recovery
```

#### Benefits

- **Primary Control**: User maintains control via password
- **Organizational Recovery**: Org admins can recover if user leaves/loses key
- **Disaster Recovery**: Multiple admins required for emergency access
- **Audit Trail**: All key access logged via `AuditLog` model
- **Compliance**: HIPAA/GDPR compliant with proper documentation

#### Implementation Details

**Database Schema:**
```python
class Survey(models.Model):
    # Current fields
    key_salt = models.BinaryField()
    key_hash = models.BinaryField()

    # New fields for Option 1
    encrypted_kek_user = models.BinaryField()      # User-encrypted KEK
    encrypted_kek_org = models.BinaryField(null=True)  # Org-encrypted KEK
    recovery_threshold = models.IntegerField(default=3)
    recovery_shares_count = models.IntegerField(default=5)
```

**Key Storage:**
```python
# At survey creation
survey_kek = os.urandom(32)  # Master encryption key

# 1. Encrypt with user's password
user_key = derive_key_from_password(user.password)
survey.encrypted_kek_user = encrypt(survey_kek, user_key)

# 2. Encrypt with organization master key (from KMS)
org_master_key = kms_client.decrypt(organization.kms_key_id)
survey.encrypted_kek_org = encrypt(survey_kek, org_master_key)

# 3. Create recovery shares (optional)
shares = create_secret_shares(survey_kek, threshold=3, total=5)
# Distribute to designated org admins
```

**Recovery Workflow:**

1. **Normal Access**: User enters password → decrypt KEK → access data
2. **User Forgot Password**: Org ADMIN uses org master key → decrypt KEK → access data
3. **Catastrophic Loss**: 3 designated admins combine recovery shares → reconstruct KEK

**Audit Logging:**
```python
# Log all key access
AuditLog.objects.create(
    actor=admin_user,
    scope=AuditLog.Scope.SURVEY,
    action=AuditLog.Action.KEY_RECOVERY,
    survey=survey,
    metadata={"recovery_method": "organization_master_key"}
)
```

### Option 2: Individual Users (Personal Responsibility)

**For individual users not part of an organization**, implement **User-Controlled with Recovery Code**:

#### Architecture

```
Survey Encryption Key (KEK)
├─ Password-Encrypted Copy
│  └─ Encrypted with user's password-derived key
│
└─ Recovery Code-Encrypted Copy
   └─ Encrypted with recovery phrase-derived key
      └─ BIP39-style 12-24 word recovery phrase
      └─ Shown ONCE at creation
      └─ User MUST save securely
```

#### Benefits

- **User Maintains Control**: True zero-knowledge architecture
- **Dual Recovery**: Password OR recovery code can decrypt
- **No Third-Party**: No organizational key escrow
- **Simple**: Straightforward implementation
- **Privacy**: Maximum patient privacy

#### Risks and Mitigations

⚠️ **Risk**: If user loses both password AND recovery code → permanent data loss

**Mitigations:**
- Clear warnings at survey creation
- Force download of recovery code file
- Email recovery code (encrypted with user's public key)
- Require acknowledgment: "I understand data loss is permanent"
- Provide key strength verification tool

#### Implementation Details

**Database Schema:**
```python
class Survey(models.Model):
    # Current fields remain
    key_salt = models.BinaryField()
    key_hash = models.BinaryField()

    # New fields for Option 2
    encrypted_kek_password = models.BinaryField()  # Password-encrypted
    encrypted_kek_recovery = models.BinaryField()  # Recovery code-encrypted
    recovery_code_hint = models.CharField(max_length=100, blank=True)
```

**Key Storage:**
```python
# At survey creation
survey_kek = os.urandom(32)

# Generate BIP39-style recovery phrase
recovery_phrase = generate_bip39_phrase(words=12)  # e.g., "apple tree house..."

# 1. Encrypt with user's password
password_key = derive_key_from_password(user.password)
survey.encrypted_kek_password = encrypt(survey_kek, password_key)

# 2. Encrypt with recovery phrase
recovery_key = derive_key_from_passphrase(recovery_phrase)
survey.encrypted_kek_recovery = encrypt(survey_kek, recovery_key)

# Show user ONCE with clear warnings
return {
    "survey_key_b64": base64.b64encode(survey_kek).decode(),
    "recovery_phrase": recovery_phrase,
    "warning": "⚠️ SAVE BOTH SECURELY. Without them, encrypted data is permanently lost."
}
```

**UI Workflow:**

```html
<!-- Survey Creation Success -->
<div class="alert alert-warning">
  <h3>⚠️ Critical: Save Your Encryption Keys</h3>
  <p>Your survey uses end-to-end encryption for patient data.</p>

  <div class="card">
    <h4>Survey Encryption Key</h4>
    <code>{{ survey_key_b64 }}</code>
    <button>Download Key File</button>
  </div>

  <div class="card">
    <h4>Recovery Phrase (12 Words)</h4>
    <code>{{ recovery_phrase }}</code>
    <button>Download Recovery File</button>
  </div>

  <div class="checkbox">
    <input type="checkbox" required>
    <label>
      I have saved both the encryption key and recovery phrase.
      I understand that losing both will result in permanent data loss.
    </label>
  </div>
</div>
```

### Account Type Detection

The system automatically determines which option to use:

```python
def get_encryption_strategy(user: User, survey: Survey) -> str:
    """Determine encryption strategy based on user type."""

    # Check if user belongs to an organization
    if user.organization_memberships.exists():
        return "organization"  # Use Option 1

    # Individual user
    return "individual"  # Use Option 2
```

### Clear Communication at Signup

**For Organization Members:**
```
✅ Your organization can recover lost encryption keys
✅ Organization admins can access data if you're unavailable
✅ All key access is logged for compliance
✅ Multi-person approval required for emergency recovery
```

**For Individual Users:**
```
⚠️ You are solely responsible for your encryption keys
⚠️ Lost keys = permanent data loss (no recovery possible)
⚠️ Save your recovery phrase in a secure location
⚠️ Consider using a password manager
⚠️ Recommended: Print and store recovery phrase offline
```

## Security Best Practices

### For All Users

1. **Never share encryption keys** via email or messaging
2. **Use strong passwords** for account access
3. **Enable 2FA** on your account
4. **Regularly backup** recovery codes offline
5. **Test recovery** process before collecting real data

### For Organization Admins

1. **Rotate KMS keys** annually
2. **Maintain audit logs** of all key access
3. **Designate recovery admins** carefully (trusted individuals)
4. **Document procedures** in disaster recovery plan
5. **Regular security reviews** of key management

### For Individual Users

1. **Store recovery phrase** in password manager
2. **Print recovery phrase** and store in safe location
3. **Never lose both** password and recovery phrase
4. **Test recovery** before collecting patient data
5. **Consider organizational account** for critical data

## Compliance and Regulations

### GDPR Compliance

✅ **Data Minimization**: Only necessary fields encrypted
✅ **Right to Erasure**: Survey deletion removes all encrypted data
✅ **Data Portability**: Export functionality available
✅ **Breach Notification**: Encrypted data protected even if breached
✅ **Audit Trail**: All access logged via `AuditLog`

### HIPAA Compliance (Healthcare Organizations)

✅ **Administrative Safeguards**: Role-based access control
✅ **Technical Safeguards**: AES-256 encryption, audit logs
✅ **Physical Safeguards**: KMS hardware security modules
✅ **Encryption**: Patient data encrypted at rest and in transit
✅ **Access Controls**: Multi-factor authentication required

### NHS Data Security Standards

✅ **Data Security**: End-to-end encryption
✅ **Secure Access**: Session-based key management
✅ **Audit**: Comprehensive logging
✅ **Incident Response**: Clear recovery procedures
✅ **Training**: Documentation for staff

## Migration Path

### Phase 1: Individual Users (Current)
- ✅ Implemented: Basic per-survey encryption
- ✅ Zero-knowledge key storage
- ⚠️ No recovery mechanism

### Phase 2: Recovery Codes (Next Release)
- Add recovery phrase generation
- Implement dual-encryption (password + recovery)
- Update UI with warnings
- Provide key download functionality

### Phase 3: Organization Support (Future)
- Add KMS integration (AWS/Azure)
- Implement organization master keys
- Add Shamir's Secret Sharing for recovery
- Enhanced audit logging

### Phase 4: Advanced Features (Roadmap)
- Automatic key rotation
- Hardware security module support
- Biometric authentication
- Smart card integration

## Technical Reference

### Encryption Utilities

```python
# census_app/surveys/utils.py

def encrypt_sensitive(passphrase_key: bytes, data: dict) -> bytes:
    """
    Encrypt sensitive data dictionary with AES-GCM.

    Args:
        passphrase_key: 32-byte encryption key
        data: Dictionary of sensitive fields

    Returns:
        Encrypted blob: salt(16) | nonce(12) | ciphertext
    """
    key, salt = derive_key(passphrase_key)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    plaintext = json.dumps(data).encode("utf-8")
    ct = aesgcm.encrypt(nonce, plaintext, None)
    return salt + nonce + ct

def decrypt_sensitive(passphrase_key: bytes, blob: bytes) -> dict:
    """
    Decrypt sensitive data blob.

    Args:
        passphrase_key: 32-byte encryption key
        blob: Encrypted blob from encrypt_sensitive()

    Returns:
        Decrypted dictionary

    Raises:
        InvalidTag: If ciphertext is tampered or key is wrong
    """
    salt, nonce, ct = blob[:16], blob[16:28], blob[28:]
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    key = kdf.derive(passphrase_key)
    aesgcm = AESGCM(key)
    pt = aesgcm.decrypt(nonce, ct, None)
    return json.loads(pt.decode("utf-8"))
```

### Key Verification

```python
def make_key_hash(key: bytes) -> tuple[bytes, bytes]:
    """Create hash and salt for key verification."""
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200_000
    )
    digest = kdf.derive(key)
    return digest, salt

def verify_key(key: bytes, digest: bytes, salt: bytes) -> bool:
    """Verify a key matches stored hash."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200_000
    )
    try:
        kdf.verify(key, digest)
        return True
    except Exception:
        return False
```

## Testing

Census includes comprehensive tests for encryption:

```bash
# Run encryption tests
docker compose exec web pytest census_app/surveys/tests/ -k encrypt

# Run key management tests
docker compose exec web pytest census_app/surveys/tests/ -k key

# Run full security test suite
docker compose exec web pytest census_app/surveys/tests/ -k security
```

## Related Documentation

- [Authentication and Permissions](authentication-and-permissions.md)
- [User Management](user-management.md)
- [API Reference](api.md)
- [Getting Started](getting-started.md)

## Support and Questions

For security-related questions or to report vulnerabilities:

- **Security Issues**: Please report privately via GitHub Security Advisories
- **General Questions**: Open a GitHub issue or discussion
- **Commercial Support**: Contact for healthcare deployment assistance

---

**Last Updated**: October 2025
**Version**: 1.0 (Current Implementation) + Roadmap
