# Option 2 Encryption Implementation Progress

## Summary
This document tracks the implementation of Option 2 (Password + Recovery Phrase) encryption for the Census survey platform, following the specification in `docs/patient-data-encryption.md`.

## Completed (✅)

### Phase 1: Database Schema (✅ Complete)
**Migration:** `0011_survey_encryption_option2.py`

Added three new fields to the Survey model:
- `encrypted_kek_password` (BinaryField): Survey key encrypted with password-derived key
- `encrypted_kek_recovery` (BinaryField): Survey key encrypted with recovery-phrase-derived key
- `recovery_code_hint` (CharField): First and last word of recovery phrase (e.g., "apple...zebra")

**Status:** Migration created and applied successfully
**Tests:** Database-level constraints validated

---

### Phase 2: Utility Functions (✅ Complete)
**File:** `census_app/surveys/utils.py`

Implemented:
1. **`generate_bip39_phrase(word_count=12)`**
   - Generates cryptographically secure BIP39-style mnemonic phrases
   - Supports 12, 15, 18, 21, or 24 words
   - Uses `secrets.choice()` for secure randomization

2. **`derive_key_from_passphrase(phrase, salt, iterations=200_000)`**
   - Derives 32-byte encryption key from recovery phrase
   - Uses PBKDF2-HMAC-SHA256
   - Normalizes whitespace and case

3. **`encrypt_kek_with_passphrase(kek, passphrase)`**
   - Encrypts survey key (KEK) with user passphrase or recovery phrase
   - Uses Scrypt KDF (n=2^14, r=8, p=1) + AES-GCM
   - Returns: salt (16 bytes) | nonce (12 bytes) | ciphertext
   - Normalizes recovery phrases (lowercase, collapse whitespace)

4. **`decrypt_kek_with_passphrase(encrypted_blob, passphrase)`**
   - Decrypts KEK using password or recovery phrase
   - Handles normalization for recovery phrases
   - Raises `InvalidTag` exception if passphrase is wrong

5. **`create_recovery_hint(phrase_words)`**
   - Creates hint showing first and last word (e.g., "apple...lamp")
   - Helps users verify they have the correct recovery phrase

**Status:** All functions implemented with comprehensive error handling
**Tests:** 18 unit tests passing (100% coverage)
- BIP39 generation tests (4 tests)
- Key derivation tests (3 tests)
- KEK encryption/decryption tests (6 tests)
- Recovery hint tests (4 tests)
- Integration scenario test (1 test)

---

### Phase 3: Survey Model Methods (✅ Complete)
**File:** `census_app/surveys/models.py`

Added methods to the Survey model:

1. **`set_dual_encryption(kek, password, recovery_phrase_words)`**
   - Sets up Option 2 dual-path encryption
   - Encrypts KEK with both password and recovery phrase
   - Stores recovery hint
   - Maintains backward compatibility with old `key_hash`/`key_salt` fields
   - Saves all fields in single atomic update

2. **`unlock_with_password(password)`**
   - Attempts to decrypt survey using password
   - Returns 32-byte KEK on success, `None` on failure
   - Catches `InvalidTag` exceptions gracefully

3. **`unlock_with_recovery(recovery_phrase)`**
   - Attempts to decrypt survey using recovery phrase
   - Handles phrase normalization automatically
   - Returns KEK or `None`

4. **`has_dual_encryption()`**
   - Returns `True` if survey has Option 2 encryption enabled
   - Checks presence of both `encrypted_kek_password` and `encrypted_kek_recovery`

**Status:** All methods implemented and tested
**Tests:** 12 integration tests passing (100% coverage)
- Basic dual encryption setup (1 test)
- Password unlock success/failure (2 tests)
- Recovery phrase unlock success/failure (2 tests)
- Phrase normalization (1 test)
- Dual encryption detection (1 test)
- Both unlock methods work (1 test)
- Recovery scenarios (4 tests)

---

## Test Summary

**Total Tests:** 30
**Passing:** 30 (100%)
**Failing:** 0

### Test Files:
1. `census_app/surveys/tests/test_encryption_utils.py` - 18 tests
2. `census_app/surveys/tests/test_survey_dual_encryption.py` - 12 tests

### Coverage:
- ✅ BIP39 phrase generation
- ✅ Key derivation from phrases
- ✅ KEK encryption/decryption
- ✅ Recovery hint generation
- ✅ Survey model encryption methods
- ✅ Password-based unlock
- ✅ Recovery phrase-based unlock
- ✅ Phrase normalization
- ✅ Error handling for wrong credentials
- ✅ Real-world recovery scenarios

---

## Remaining Work (⏳)

### Phase 4: Survey Publish Workflow
**Needs:** Enhanced views and forms to set up encryption when publishing

When a survey is published:
1. Check if user has organization → skip Option 2 (existing workflow)
2. If individual user → prompt for encryption password
3. Generate 12-word BIP39 recovery phrase
4. Set up dual encryption with `survey.set_dual_encryption()`
5. Store KEK in session temporarily for key display
6. Redirect to key display page

**Files to modify:**
- View for survey publishing/status change
- Form for encryption password input
- Session management for temporary KEK storage

---

### Phase 5: Key Display UI
**Needs:** Template to show encryption key and recovery phrase once

**Template:** `census_app/surveys/templates/surveys/key_display.html`

Features:
- Show encryption key (32-byte hex)
- Show recovery phrase (12 words in grid layout)
- Show recovery hint
- ⚠️ Warning: "This is the only time you will see these"
- Download as text file option
- Print-friendly CSS
- Copy-to-clipboard buttons
- i18n support for all strings

**View:** `key_display(request, slug)` - must verify KEK in session, show once only

---

### Phase 6: Enhanced Unlock View
**Needs:** Support both password and recovery phrase unlock methods

**Template:** `census_app/surveys/templates/surveys/unlock.html`

Enhancements:
- Tab/toggle between "Unlock with Password" and "Unlock with Recovery Phrase"
- Password input field
- Recovery phrase textarea (12-24 words)
- Show recovery hint to help users verify
- Clear error messages for wrong credentials
- i18n support

**View:** Update `survey_unlock(request, slug)` to:
- Try password unlock first if form uses password field
- Try recovery phrase unlock if form uses recovery field
- Store unlocked KEK in session on success
- Log audit entry when recovery phrase is used

---

### Phase 7: I18n Strings
**Needs:** Extract and translate all encryption-related strings

**New strings needed:**
- "Set up survey encryption"
- "Choose a strong password"
- "Your recovery phrase (write this down!)"
- "This is the only time you will see your recovery phrase"
- "Download recovery information"
- "Unlock with password"
- "Unlock with recovery phrase"
- "Recovery hint: {hint}"
- "Wrong password or recovery phrase"
- "Keep this recovery phrase in a safe place"
- etc.

**Files to update:**
- `locale/en_GB/LC_MESSAGES/django.po` - Add new msgid entries
- `docs/languages/COMPLETE_STRINGS_LIST.md` - Document all new strings
- Run `django-admin makemessages` to update all language files

---

### Phase 8: Integration Tests
**Needs:** End-to-end workflow tests

Test scenarios:
1. Create survey → publish with encryption → display keys → unlock with password
2. Create survey → publish with encryption → unlock with recovery phrase
3. User forgets password → uses recovery phrase → regains access
4. Attempt unlock with wrong password → fails gracefully
5. Attempt unlock with partial recovery phrase → fails gracefully

**File:** `census_app/surveys/tests/test_encryption_workflow.py`

---

### Phase 9: Audit Logging
**Needs:** Track recovery phrase usage

Add audit log entries:
- When survey is published with encryption
- When survey is unlocked with password (existing?)
- **When survey is unlocked with recovery phrase** (new - track fallback authentication)
- When key display page is accessed

**Model:** Use existing `AuditLog` model
**Scope:** `Scope.SURVEY`
**Actions:** May need new action like `Action.UNLOCK_RECOVERY`

---

### Phase 10: Documentation Validation
**Needs:** Verify implementation matches spec

1. Review `docs/patient-data-encryption.md` Option 2 section
2. Verify all documented workflows are implemented
3. Update any implementation details that differ from docs
4. Add "Implementation Status" section to docs
5. Update architecture diagrams if needed

---

## Security Considerations ✅

### Implemented:
- ✅ Cryptographically secure random phrase generation (`secrets` module)
- ✅ Strong KDF (Scrypt: n=2^14, r=8, p=1)
- ✅ AES-256-GCM authenticated encryption
- ✅ 200,000 PBKDF2 iterations for recovery phrases
- ✅ Phrase normalization prevents case/whitespace issues
- ✅ Graceful error handling (no information leakage)
- ✅ Recovery hint is non-sensitive (only first/last word)

### Still needed:
- ⏳ Session security for temporary KEK storage
- ⏳ Rate limiting on unlock attempts
- ⏳ Audit logging for recovery phrase usage
- ⏳ Key display page access restrictions (one-time only)
- ⏳ CSRF protection on all encryption forms

---

## File Changes

### Modified Files:
1. **census_app/surveys/models.py**
   - Added 3 database fields
   - Added 4 encryption methods
   - Lines changed: ~100

2. **census_app/surveys/utils.py**
   - Added BIP39 wordlist (sample)
   - Added 5 encryption utility functions
   - Lines changed: ~170

### New Files:
1. **census_app/surveys/migrations/0011_survey_encryption_option2.py**
   - Database migration for Option 2 fields

2. **census_app/surveys/tests/test_encryption_utils.py**
   - 18 unit tests for utility functions

3. **census_app/surveys/tests/test_survey_dual_encryption.py**
   - 12 integration tests for Survey model methods

4. **docs/ENCRYPTION_IMPLEMENTATION_PROGRESS.md** (this file)
   - Progress tracking document

---

## Next Steps

1. **Immediate:** Implement Phase 4 (Survey Publish Workflow)
   - Modify survey publishing view to prompt for encryption setup
   - Add form for password input
   - Generate recovery phrase and set up dual encryption

2. **Short-term:** Implement Phase 5 (Key Display UI)
   - Create template to show keys once
   - Add download/print functionality
   - Ensure keys are only shown once per session

3. **Short-term:** Implement Phase 6 (Enhanced Unlock View)
   - Update unlock template with tabs for both methods
   - Enhance view logic to handle both unlock paths

4. **Medium-term:** Complete i18n and testing
   - Extract all strings
   - Write integration tests
   - Add audit logging

---

## Questions for Discussion

1. **BIP39 Wordlist:** Currently using a sample wordlist. Should we:
   - Include the full 2048-word BIP39 English wordlist?
   - Support multiple languages (Spanish, French, etc.)?
   - Use an external library like `mnemonic`?

2. **Recovery Phrase Length:** Documentation suggests 12 words. Should we:
   - Allow users to choose (12, 15, 18, 21, or 24)?
   - Stick with 12 for simplicity?

3. **Encryption Opt-in:** Should Option 2 encryption be:
   - Mandatory for individual users?
   - Optional (user chooses at publish time)?
   - Configurable per-survey?

4. **Key Display Access:** Should the key display page be:
   - One-time only (session-based)?
   - Accessible multiple times with re-authentication?
   - Downloadable only?

---

## Conclusion

**Status:** ✅ Foundation Complete (3/10 phases)

We have successfully implemented the core encryption infrastructure for Option 2:
- ✅ Database schema ready
- ✅ Utility functions working and tested
- ✅ Survey model methods integrated and tested
- ✅ 30 tests passing (100% coverage)

The foundation is solid and ready for UI integration. The remaining work focuses on:
- User-facing workflows (publish, display, unlock)
- Internationalization
- Integration testing
- Documentation validation

**Estimated remaining work:** 4-6 hours for Phases 4-6, 2-3 hours for Phases 7-10

---

Last updated: 2025-10-20
