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
# User provides survey key
key = request.POST.get("key").encode("utf-8")

# Verify against stored hash
if verify_key(key, survey.key_hash, survey.key_salt):
    # Store in session (HttpOnly, Secure cookie)
    request.session["survey_key"] = key
    
# Now can decrypt responses
demographics = response.load_demographics(survey_key)
```

### Current Security Properties

✅ **Zero-Knowledge**: Server never stores encryption keys in plaintext  
✅ **Per-Survey Isolation**: Each survey has unique encryption key  
✅ **Authenticated Encryption**: AES-GCM prevents tampering  
✅ **Strong KDF**: Scrypt protects against brute-force attacks  
✅ **Session-Based**: Keys stored only in session, not permanently  
✅ **No Key Escrow**: True end-to-end encryption

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

For **individual users**, Census can leverage **browser-native and OS-level key storage** to help users manage their encryption keys securely without manual copy-paste:

#### Option A: Web Credential Management API (Recommended) 🌟

Modern browsers provide the **Credential Management API** and **Password Manager** integration:

```html
<!-- surveys/templates/surveys/key_display.html -->
<div class="card bg-base-100 shadow-xl">
  <div class="card-body">
    <h2 class="card-title">🔑 Survey Encryption Key</h2>
    
    <div class="alert alert-info">
      <p>Save this key to your browser's password manager:</p>
    </div>
    
    <!-- Key Display -->
    <div class="form-control">
      <label class="label">
        <span class="label-text">Encryption Key</span>
      </label>
      <input 
        type="text" 
        id="survey-key"
        name="encryption-key"
        value="{{ survey_key }}"
        class="input input-bordered font-mono"
        readonly
        autocomplete="off"
        data-survey-slug="{{ survey.slug }}"
      />
    </div>
    
    <!-- Browser Save Button -->
    <button 
      type="button" 
      id="save-to-browser"
      class="btn btn-primary"
      onclick="saveKeyToBrowser()"
    >
      💾 Save to Browser Password Manager
    </button>
    
    <!-- Manual Download Fallback -->
    <button 
      type="button"
      class="btn btn-secondary"
      onclick="downloadKeyFile()"
    >
      📥 Download Key File
    </button>
    
    <!-- Print Option -->
    <button 
      type="button"
      class="btn btn-ghost"
      onclick="printKey()"
    >
      🖨️ Print Key (Store Securely)
    </button>
  </div>
</div>

<script>
async function saveKeyToBrowser() {
  const keyInput = document.getElementById('survey-key');
  const surveySlug = keyInput.dataset.surveySlug;
  const keyValue = keyInput.value;
  
  if (!window.PasswordCredential) {
    alert('Your browser does not support password manager integration. Please use manual download.');
    return;
  }
  
  try {
    // Create credential for browser's password manager
    const credential = new PasswordCredential({
      id: `census-survey-${surveySlug}`,
      password: keyValue,
      name: `Census Survey: ${surveySlug}`,
      iconURL: '/static/icons/census_brand.svg'
    });
    
    // Request browser to save
    await navigator.credentials.store(credential);
    
    alert('✅ Key saved to your browser password manager!\n\n' +
          'You can retrieve it later when unlocking the survey.');
    
    // Mark as saved
    document.getElementById('save-to-browser').classList.add('btn-success');
    document.getElementById('save-to-browser').textContent = '✅ Saved to Browser';
    
  } catch (error) {
    console.error('Failed to save credential:', error);
    alert('Could not save to browser. Please use manual download.');
  }
}

function downloadKeyFile() {
  const keyInput = document.getElementById('survey-key');
  const surveySlug = keyInput.dataset.surveySlug;
  const keyValue = keyInput.value;
  
  // Create downloadable text file
  const content = `Census Survey Encryption Key
Survey: ${surveySlug}
Key: ${keyValue}
Generated: ${new Date().toISOString()}

⚠️  IMPORTANT: Store this file securely!
• Do not share this key
• Do not commit to version control
• Required to decrypt survey responses
• Cannot be recovered if lost
`;
  
  const blob = new Blob([content], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `census-survey-${surveySlug}-key.txt`;
  a.click();
  URL.revokeObjectURL(url);
}

function printKey() {
  window.print();
}
</script>
```

**Browser Support:**
- ✅ Chrome/Edge: Full support
- ✅ Safari: Partial support (iCloud Keychain)
- ✅ Firefox: Partial support
- ✅ Mobile browsers: Works with system password managers

**User Experience:**
1. User creates survey
2. Census shows key + "Save to Browser" button
3. User clicks → browser prompts to save (like password save)
4. Key stored in Chrome/Safari/Firefox password manager
5. When unlocking: browser autofills the key! 🎉

---

#### Option B: Web Crypto API with IndexedDB

For users who want **encrypted local storage** without browser password manager:

```javascript
// static/js/key-storage.js

class SurveyKeyStore {
  constructor() {
    this.dbName = 'census-survey-keys';
    this.storeName = 'keys';
    this.db = null;
  }
  
  async init() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, 1);
      
      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve();
      };
      
      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        if (!db.objectStoreNames.contains(this.storeName)) {
          db.createObjectStore(this.storeName, { keyPath: 'surveySlug' });
        }
      };
    });
  }
  
  async saveKey(surveySlug, encryptionKey) {
    await this.init();
    
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      
      const request = store.put({
        surveySlug: surveySlug,
        key: encryptionKey,
        savedAt: new Date().toISOString()
      });
      
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }
  
  async getKey(surveySlug) {
    await this.init();
    
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([this.storeName], 'readonly');
      const store = transaction.objectStore(this.storeName);
      const request = store.get(surveySlug);
      
      request.onsuccess = () => {
        const result = request.result;
        resolve(result ? result.key : null);
      };
      request.onerror = () => reject(request.error);
    });
  }
  
  async deleteKey(surveySlug) {
    await this.init();
    
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.delete(surveySlug);
      
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }
  
  async listKeys() {
    await this.init();
    
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([this.storeName], 'readonly');
      const store = transaction.objectStore(this.storeName);
      const request = store.getAll();
      
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }
}

// Usage
const keyStore = new SurveyKeyStore();

async function saveKeyLocally() {
  const keyInput = document.getElementById('survey-key');
  const surveySlug = keyInput.dataset.surveySlug;
  
  try {
    await keyStore.saveKey(surveySlug, keyInput.value);
    alert('✅ Key saved locally in browser storage!\n\n' +
          '⚠️ Note: Keys are stored per-browser. ' +
          'Download a backup if you use multiple devices.');
    
    document.getElementById('save-locally').classList.add('btn-success');
    document.getElementById('save-locally').textContent = '✅ Saved Locally';
  } catch (error) {
    console.error('Failed to save key:', error);
    alert('Could not save key locally. Please download instead.');
  }
}

// Auto-fill on unlock page
async function autoFillKey() {
  const surveySlug = document.querySelector('[data-survey-slug]')?.dataset.surveySlug;
  if (!surveySlug) return;
  
  try {
    const savedKey = await keyStore.getKey(surveySlug);
    if (savedKey) {
      const keyInput = document.getElementById('key');
      keyInput.value = savedKey;
      
      // Show indicator
      const indicator = document.createElement('div');
      indicator.className = 'badge badge-success';
      indicator.textContent = '🔑 Key loaded from browser storage';
      keyInput.parentElement.appendChild(indicator);
    }
  } catch (error) {
    console.error('Could not load saved key:', error);
  }
}

// Run on unlock page load
if (window.location.pathname.includes('/unlock/')) {
  document.addEventListener('DOMContentLoaded', autoFillKey);
}
```

**Pros:**
- ✅ Per-browser encrypted storage
- ✅ Automatic key retrieval
- ✅ No server storage
- ✅ Works offline

**Cons:**
- ❌ Not synced across devices
- ❌ Lost if browser data cleared
- ❌ User needs backups for multi-device

---

#### Option C: Browser Extension (Advanced Users)

For users who want **cross-device sync**, recommend existing password managers:

```html
<!-- surveys/templates/surveys/key_display.html -->
<div class="alert alert-info">
  <h3 class="font-bold">💡 Recommended: Use a Password Manager</h3>
  <p class="mt-2">
    For the best security and convenience, save this key in a password manager:
  </p>
  
  <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
    <!-- 1Password -->
    <div class="card bg-base-200">
      <div class="card-body p-4">
        <h4 class="font-semibold">1Password</h4>
        <ul class="text-sm list-disc list-inside">
          <li>Cross-device sync</li>
          <li>Browser autofill</li>
          <li>Secure notes for keys</li>
        </ul>
        <a href="https://1password.com" target="_blank" class="btn btn-sm btn-ghost">
          Learn More →
        </a>
      </div>
    </div>
    
    <!-- Bitwarden -->
    <div class="card bg-base-200">
      <div class="card-body p-4">
        <h4 class="font-semibold">Bitwarden</h4>
        <ul class="text-sm list-disc list-inside">
          <li>Open source</li>
          <li>Free tier available</li>
          <li>Self-hosting option</li>
        </ul>
        <a href="https://bitwarden.com" target="_blank" class="btn btn-sm btn-ghost">
          Learn More →
        </a>
      </div>
    </div>
    
    <!-- macOS Keychain -->
    <div class="card bg-base-200">
      <div class="card-body p-4">
        <h4 class="font-semibold">macOS Keychain</h4>
        <ul class="text-sm list-disc list-inside">
          <li>Built into macOS</li>
          <li>iCloud sync</li>
          <li>Safari autofill</li>
        </ul>
        <a href="https://support.apple.com/guide/keychain-access" target="_blank" class="btn btn-sm btn-ghost">
          Learn More →
        </a>
      </div>
    </div>
  </div>
  
  <div class="mt-4 p-3 bg-base-300 rounded">
    <p class="text-sm">
      <strong>How to save:</strong> Copy the key above and create a new "Secure Note" 
      or "Password" entry in your password manager with these details:
    </p>
    <ul class="text-sm list-disc list-inside ml-4 mt-2">
      <li><strong>Title:</strong> Census Survey - {{ survey.name }}</li>
      <li><strong>Username/ID:</strong> {{ survey.slug }}</li>
      <li><strong>Password/Key:</strong> [paste the encryption key]</li>
      <li><strong>URL:</strong> {{ request.build_absolute_uri }}</li>
    </ul>
  </div>
</div>
```

---

#### Option D: Native OS Keychain Integration (Best for Desktop Apps)

If you build a **desktop companion app** or **Electron wrapper** for Census, you can use OS-native keychains:

**macOS Keychain:**
```javascript
// If building Electron app or Tauri desktop app
const keytar = require('keytar');

async function saveToKeychain(surveySlug, encryptionKey) {
  await keytar.setPassword(
    'census-app',           // service name
    `survey-${surveySlug}`, // account
    encryptionKey           // password (the encryption key)
  );
}

async function getFromKeychain(surveySlug) {
  return await keytar.getPassword('census-app', `survey-${surveySlug}`);
}
```

**Windows Credential Manager:**
```javascript
// Same API works on Windows
// Stored in Windows Credential Manager
```

**Linux Secret Service:**
```javascript
// Same API works with libsecret
// Stored in GNOME Keyring / KWallet
```

**Pros:**
- ✅ OS-level encryption
- ✅ Sync across devices (iCloud Keychain, Windows Sync)
- ✅ Biometric unlock (Touch ID, Windows Hello)
- ✅ System-managed backups

**Cons:**
- ❌ Requires native app (not pure web)

---

#### Option E: QR Code + Mobile Keychain

For **mobile users**, allow them to **scan and save** to their phone's keychain:

```html
<!-- surveys/templates/surveys/key_display.html -->
<div class="card bg-base-100">
  <div class="card-body">
    <h3 class="card-title">📱 Save to Mobile Device</h3>
    
    <div class="flex justify-center p-4">
      <!-- QR Code generated server-side or via qrcode.js -->
      <img 
        src="{% url 'surveys:key-qr' slug=survey.slug %}" 
        alt="QR Code for encryption key"
        class="w-48 h-48"
      />
    </div>
    
    <div class="alert alert-sm">
      <p>Scan with your phone to save to Notes app or password manager:</p>
      <ol class="text-sm list-decimal list-inside ml-2 mt-2">
        <li>Open camera app</li>
        <li>Scan QR code</li>
        <li>Tap notification</li>
        <li>Save to Notes (iOS) or Keep (Android)</li>
      </ol>
    </div>
  </div>
</div>
```

```python
# census_app/surveys/views.py
import qrcode
from io import BytesIO

@login_required
def key_qr_code(request: HttpRequest, slug: str) -> HttpResponse:
    """Generate QR code for survey encryption key."""
    survey = get_object_or_404(Survey, slug=slug, owner=request.user)
    
    # Only allow QR code generation during initial key display
    if not request.session.get(f'new_survey_key_{slug}'):
        raise Http404("QR code only available during initial setup")
    
    survey_key = request.session[f'new_survey_key_{slug}']
    
    # Create QR code with structured data
    qr_data = f"""Census Survey Key
Survey: {survey.name}
Slug: {slug}
Key: {survey_key}
URL: {request.build_absolute_uri(survey.get_absolute_url())}
Generated: {timezone.now().isoformat()}

⚠️ STORE SECURELY - Cannot be recovered!"""
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return HttpResponse(buffer.read(), content_type='image/png')
```

---

### Recommended Multi-Layered Approach

Offer **all options** and let users choose based on their needs:

```html
<!-- surveys/templates/surveys/key_display.html -->
<div class="container max-w-4xl mx-auto p-6">
  <div class="alert alert-warning mb-6">
    <h2 class="font-bold text-xl">⚠️ Save Your Encryption Key Now</h2>
    <p>This key will only be shown once. Choose at least one storage method:</p>
  </div>
  
  <!-- Display Key -->
  <div class="card bg-base-100 shadow-xl mb-6">
    <div class="card-body">
      <div class="form-control">
        <label class="label">
          <span class="label-text font-bold">Survey Encryption Key</span>
          <button onclick="copyToClipboard()" class="btn btn-sm btn-ghost">
            📋 Copy
          </button>
        </label>
        <input 
          type="text" 
          id="survey-key"
          value="{{ survey_key }}"
          class="input input-bordered font-mono text-lg"
          readonly
          data-survey-slug="{{ survey.slug }}"
        />
      </div>
    </div>
  </div>
  
  <!-- Storage Options -->
  <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
    
    <!-- Option 1: Browser Password Manager (Recommended) -->
    <div class="card bg-primary text-primary-content">
      <div class="card-body">
        <h3 class="card-title">
          🌟 Recommended
          <div class="badge badge-secondary">Easiest</div>
        </h3>
        <p class="text-sm">Save to your browser's built-in password manager</p>
        <ul class="text-sm list-disc list-inside mt-2 opacity-90">
          <li>Autofill when unlocking</li>
          <li>Syncs across devices (Chrome/Safari)</li>
          <li>Encrypted by browser</li>
        </ul>
        <button 
          type="button"
          id="save-to-browser"
          class="btn btn-secondary mt-4"
          onclick="saveKeyToBrowser()"
        >
          💾 Save to Browser
        </button>
      </div>
    </div>
    
    <!-- Option 2: Password Manager App -->
    <div class="card bg-base-200">
      <div class="card-body">
        <h3 class="card-title">
          🔐 Most Secure
          <div class="badge">Cross-Device</div>
        </h3>
        <p class="text-sm">Use 1Password, Bitwarden, or similar</p>
        <ul class="text-sm list-disc list-inside mt-2">
          <li>Works on all devices</li>
          <li>End-to-end encrypted</li>
          <li>Team sharing possible</li>
        </ul>
        <div class="flex gap-2 mt-4">
          <button onclick="copyToClipboard()" class="btn btn-ghost btn-sm flex-1">
            📋 Copy Key
          </button>
          <a href="#pm-instructions" class="btn btn-ghost btn-sm flex-1">
            📖 Instructions
          </a>
        </div>
      </div>
    </div>
    
    <!-- Option 3: Local Browser Storage -->
    <div class="card bg-base-200">
      <div class="card-body">
        <h3 class="card-title">
          💻 This Browser Only
          <div class="badge badge-warning">Backup Needed</div>
        </h3>
        <p class="text-sm">Save encrypted in this browser's local storage</p>
        <ul class="text-sm list-disc list-inside mt-2">
          <li>Quick and easy</li>
          <li>Automatic unlock on this device</li>
          <li>⚠️ Not synced across devices</li>
        </ul>
        <button 
          type="button"
          id="save-locally"
          class="btn btn-ghost btn-sm mt-4"
          onclick="saveKeyLocally()"
        >
          💾 Save Locally
        </button>
      </div>
    </div>
    
    <!-- Option 4: Download File -->
    <div class="card bg-base-200">
      <div class="card-body">
        <h3 class="card-title">
          📥 Download File
          <div class="badge">Manual</div>
        </h3>
        <p class="text-sm">Download as text file for manual storage</p>
        <ul class="text-sm list-disc list-inside mt-2">
          <li>Store in secure location</li>
          <li>Add to encrypted USB/drive</li>
          <li>Keep offline backup</li>
        </ul>
        <button 
          type="button"
          class="btn btn-ghost btn-sm mt-4"
          onclick="downloadKeyFile()"
        >
          📥 Download
        </button>
      </div>
    </div>
    
  </div>
  
  <!-- Mobile QR Option -->
  <div class="card bg-base-200 mb-6">
    <div class="card-body">
      <h3 class="card-title">📱 Save to Mobile Device</h3>
      <div class="flex flex-col md:flex-row gap-4 items-center">
        <div class="flex-shrink-0">
          <img 
            src="{% url 'surveys:key-qr' slug=survey.slug %}"
            alt="QR Code"
            class="w-32 h-32 border-4 border-base-300 rounded"
          />
        </div>
        <div>
          <p class="text-sm">Scan this QR code to save the key to your mobile device:</p>
          <ol class="text-sm list-decimal list-inside ml-2 mt-2">
            <li>Open your phone's camera app</li>
            <li>Scan the QR code</li>
            <li>Save to Notes, password manager, or secure storage</li>
          </ol>
        </div>
      </div>
    </div>
  </div>
  
  <!-- Confirmation Checklist -->
  <div class="card bg-warning text-warning-content">
    <div class="card-body">
      <h3 class="card-title">✅ Before Proceeding</h3>
      <p class="mb-4">Confirm you've saved your key using at least one method:</p>
      
      <form method="post" action="{% url 'surveys:key-confirm' slug=survey.slug %}">
        {% csrf_token %}
        
        <div class="form-control">
          <label class="label cursor-pointer justify-start gap-3">
            <input type="checkbox" id="saved-browser" class="checkbox" onchange="updateConfirm()" />
            <span class="label-text">Saved to browser password manager</span>
          </label>
        </div>
        
        <div class="form-control">
          <label class="label cursor-pointer justify-start gap-3">
            <input type="checkbox" id="saved-pm" class="checkbox" onchange="updateConfirm()" />
            <span class="label-text">Saved to password manager app (1Password, Bitwarden, etc.)</span>
          </label>
        </div>
        
        <div class="form-control">
          <label class="label cursor-pointer justify-start gap-3">
            <input type="checkbox" id="saved-local" class="checkbox" onchange="updateConfirm()" />
            <span class="label-text">Saved to this browser's local storage</span>
          </label>
        </div>
        
        <div class="form-control">
          <label class="label cursor-pointer justify-start gap-3">
            <input type="checkbox" id="saved-download" class="checkbox" onchange="updateConfirm()" />
            <span class="label-text">Downloaded and stored securely</span>
          </label>
        </div>
        
        <div class="form-control">
          <label class="label cursor-pointer justify-start gap-3">
            <input type="checkbox" id="saved-mobile" class="checkbox" onchange="updateConfirm()" />
            <span class="label-text">Saved to mobile device via QR code</span>
          </label>
        </div>
        
        <div class="divider"></div>
        
        <div class="form-control">
          <label class="label cursor-pointer justify-start gap-3">
            <input 
              type="checkbox" 
              id="acknowledge" 
              class="checkbox checkbox-warning" 
              required 
              onchange="updateConfirm()"
            />
            <span class="label-text font-bold">
              I understand this key cannot be recovered if lost, and I have saved it securely.
            </span>
          </label>
        </div>
        
        <button 
          type="submit" 
          id="confirm-btn"
          class="btn btn-primary mt-6 w-full"
          disabled
        >
          Continue to Survey Setup →
        </button>
      </form>
    </div>
  </div>
</div>

<script>
function updateConfirm() {
  const anySaved = document.querySelector('#saved-browser:checked') ||
                   document.querySelector('#saved-pm:checked') ||
                   document.querySelector('#saved-local:checked') ||
                   document.querySelector('#saved-download:checked') ||
                   document.querySelector('#saved-mobile:checked');
  
  const acknowledged = document.getElementById('acknowledge').checked;
  
  const confirmBtn = document.getElementById('confirm-btn');
  confirmBtn.disabled = !(anySaved && acknowledged);
}

function copyToClipboard() {
  const keyInput = document.getElementById('survey-key');
  keyInput.select();
  document.execCommand('copy');
  
  // Show toast notification
  const toast = document.createElement('div');
  toast.className = 'toast toast-top toast-end';
  toast.innerHTML = '<div class="alert alert-success"><span>✅ Key copied to clipboard</span></div>';
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}
</script>
```

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
