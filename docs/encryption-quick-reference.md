# Survey Encryption: Quick Reference

This guide helps you understand your encryption options when publishing a Census survey.

## Choose Your Encryption Method

Your encryption options depend on **how you sign in** and **whether you're in an organisation**.

### 🏢 Organisation Members with SSO (Google, Azure, Okta, etc.)

**Recommended**: **SSO + Organisation Encryption** (Automatic)

✅ **What you get:**
- Automatic encryption - no setup needed
- Auto-unlock when signed in via SSO
- Organisation admin can recover if you lose SSO access
- Nothing to remember or write down

✅ **Best for**: Most organisation users

[Learn more →](encryption-organisation-users.md)

---

### 🏢 Organisation Members with Username/Password

**Method**: **Password + Recovery Phrase + Organisation Encryption** (Automatic)

✅ **What you get:**
- Unlock with password OR recovery phrase
- Organisation admin can recover if you lose both
- Triple protection

⚠️ **You must remember**: Your password OR save your 12-word recovery phrase

[Learn more →](encryption-organisation-users.md)

---

### 👤 Individual Users with SSO (Google, Azure, etc.)

**You choose**: **SSO-Only** OR **SSO + Recovery Phrase**

#### Option A: SSO-Only Encryption (Recommended for most)

✅ **Pros:**
- Simple - nothing to remember
- Auto-unlock when signed in
- Fast setup

⚠️ **Cons:**
- If you lose SSO access permanently, data is gone
- No backup recovery method

👍 **Best for**: Low-medium sensitivity data, stable SSO account

#### Option B: SSO + Recovery Phrase (Maximum protection)

✅ **Pros:**
- Auto-unlock via SSO (convenient)
- Recovery phrase backup (safety)
- Can recover even if you lose SSO

⚠️ **Cons:**
- Must securely store 12-word recovery phrase

👍 **Best for**: High-sensitivity data, critical research, paranoid users

[Learn more →](encryption-individual-users.md)

---

### 👤 Individual Users with Username/Password

**Method**: **Password + Recovery Phrase** (Automatic)

✅ **What you get:**
- Unlock with password OR recovery phrase
- Complete control
- No organisation dependency

⚠️ **You must remember**: Your password OR save your 12-word recovery phrase

[Learn more →](encryption-individual-users.md)

---

## Quick Comparison Table

| Your Situation | Encryption Type | What to Remember | Recovery If You Lose Access |
|----------------|-----------------|------------------|----------------------------|
| **Org + SSO** | SSO + Org | Nothing! | Org admin recovers |
| **Org + Password** | Password + Recovery + Org | Password OR phrase | Password, phrase, or org admin |
| **Individual + SSO (Option A)** | SSO-Only | Nothing | None - data lost |
| **Individual + SSO (Option B)** | SSO + Recovery | Recovery phrase | SSO or phrase |
| **Individual + Password** | Password + Recovery | Password OR phrase | Password or phrase |

---

## Still Not Sure?

### For Organisation Members:
- **If you use SSO** → Use automatic SSO encryption (nothing to remember!)
- **If you use passwords** → Save your recovery phrase (backup if you forget password)

### For Individual Users:
- **Low-risk data + stable SSO** → Choose SSO-Only (simple!)
- **Critical data OR unstable SSO** → Choose SSO + Recovery Phrase (safe!)
- **Using passwords** → Save your recovery phrase (automatic)

---

## What Happens Next?

After you choose and set up encryption:

1. **Your survey is encrypted** - all responses are protected
2. **You unlock when needed** - automatic (SSO) or with password/phrase
3. **Survey stays unlocked** - for 30 minutes while you work
4. **Locks automatically** - when you're done or session expires

---

## Related Documentation

- [Encryption for Individual Users](encryption-individual-users.md) - Detailed guide for personal accounts
- [Encryption for Organisation Users](encryption-organisation-users.md) - Detailed guide for organisation members
- [Patient Data Encryption](patient-data-encryption.md) - Technical specification

---

## Questions?

- **Organisation members**: Contact your organisation admin
- **Individual users**: See the [FAQ sections](encryption-individual-users.md#frequently-asked-questions) in the detailed guides
- **Technical questions**: See [Patient Data Encryption](patient-data-encryption.md)
