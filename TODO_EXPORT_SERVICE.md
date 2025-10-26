# TODO: Fix ExportService and Complete Test Coverage

## Critical Issues in ExportService

The `census_app/surveys/services/export_service.py` has several bugs that prevent proper CSV export generation:

### 1. Non-existent Field References

**Location:** `_generate_csv()` method (lines ~134-160)

**Problem:** The code references fields that don't exist on the `SurveyQuestion` model:
- `question.label` - doesn't exist (should use `question.text`)
- `question.field_name` - doesn't exist (should use `question.id` or similar)

**Current Code (BROKEN):**
```python
# Line ~145-150
for question in survey_questions:
    headers.append(question.label)  # ❌ Field doesn't exist
    field_names.append(question.field_name)  # ❌ Field doesn't exist
```

**Should Be:**
```python
# Use actual SurveyQuestion model fields
for question in survey_questions:
    headers.append(question.text)  # ✅ This field exists
    # For field_name, might need question.id or a generated identifier
```

### 2. Incorrect Query Filter

**Location:** `_generate_csv()` method (line ~134)

**Problem:** Query uses incorrect field name
```python
# FIXED (was questiongroup, now group)
survey_questions = SurveyQuestion.objects.filter(
    survey=survey
).select_related('group').order_by('order')
```

This has been fixed but needs testing.

### 3. Data Decryption Before CSV Generation

**Critical Requirement:** The export process must decrypt patient data before generating the CSV.

**Current Status:** Unknown - needs investigation

**Must Verify:**
- Where does decryption happen in the export flow?
- Is `enc_demographics` being decrypted before writing to CSV?
- Is `answers` field being decrypted if encrypted?
- Are all encrypted fields properly decrypted?

**Reference Models:**
- `SurveyResponse.enc_demographics` - encrypted demographics data
- `SurveyResponse.answers` - response data (may be encrypted?)

## Skipped Tests

The following test classes are currently skipped and need to be re-enabled after fixing ExportService:

### census_app/surveys/tests/test_data_governance_views.py

1. **TestSurveyExportCreateView:**
   - `test_export_create_post_creates_export` - Tests export creation
   - `test_export_create_requires_attestation` - Tests attestation validation

2. **TestSurveyExportDownloadView:** (entire class skipped)
   - `test_download_page_requires_login` - Token page requires auth
   - `test_download_page_shows_token_info` - Token page displays correctly
   - `test_download_page_accessible_by_owner` - Owner can access
   - `test_download_page_blocked_for_non_owners` - Non-owners blocked

3. **TestSurveyExportFileView:** (entire class skipped)
   - `test_file_download_requires_valid_token` - Token validation works
   - `test_file_download_fails_with_invalid_token` - Invalid tokens rejected
   - `test_file_download_fails_with_expired_token` - Expired tokens rejected
   - `test_file_download_contains_correct_data` - **CRITICAL: Tests data decryption**
   - `test_file_download_without_login` - Auth not required with valid token

4. **TestExportPermissionEnforcement:** (entire class skipped)
   - `test_export_routes_blocked_for_non_owners` - Non-owners can't export
   - `test_export_routes_allowed_for_owner` - Owners can export

**Total Skipped:** 13 tests

## Action Plan

### Phase 1: Fix ExportService (HIGH PRIORITY)

1. **Investigate SurveyQuestion Model:**
   - Read `census_app/surveys/models.py` to understand actual field structure
   - Document all fields on `SurveyQuestion`
   - Determine what should be used for CSV headers

2. **Fix _generate_csv() Method:**
   - Replace `question.label` with `question.text`
   - Replace `question.field_name` with appropriate identifier
   - Test that CSV generation works for basic survey

3. **Verify Decryption:**
   - Trace the export flow to find where decryption happens
   - Ensure `enc_demographics` is decrypted before CSV export
   - Ensure `answers` data is properly decrypted
   - Add explicit decryption step if missing

4. **Add Service Tests:**
   - Create `census_app/surveys/tests/test_export_service.py`
   - Test CSV generation with encrypted data
   - Test CSV headers match question text
   - Test CSV rows contain decrypted patient data
   - Test password protection works
   - Test token generation and expiry

### Phase 2: Enable View Tests (MEDIUM PRIORITY)

1. **Remove Skip Decorators:**
   - Remove `@pytest.mark.skip()` from all test classes/methods
   - Run tests individually to verify they pass

2. **Fix Any Remaining Issues:**
   - Tests may reveal additional ExportService bugs
   - Fix as needed

3. **Add Additional Test Cases:**
   - Test edge cases (empty surveys, missing data)
   - Test large exports
   - Test different question types

### Phase 3: Security Verification (HIGH PRIORITY)

**User's Original Requirement:**
> "I would like to be sure that only those users with permissions have access to the routes that download data, also that the data on download is appropriately decrypted"

**Must Verify:**
1. ✅ Permission enforcement (partially tested - basic tests passing)
2. ❌ Data decryption (NOT TESTED - needs ExportService fix)
3. ❌ Token security (NOT TESTED - needs ExportService fix)

## Current Test Status

**Passing (9 tests):**
- Dashboard widget visibility ✅
- Dashboard retention display ✅
- Survey close integration ✅
- Export create page access control ✅

**Skipped (13 tests):**
- All export creation/download/file download tests ⏸️
- Permission enforcement for export routes ⏸️

**Total:** 9 passing, 13 skipped (out of 22 tests)

## Files to Review/Modify

1. `census_app/surveys/services/export_service.py` - Fix field names, verify decryption
2. `census_app/surveys/models.py` - Understand SurveyQuestion structure
3. `census_app/surveys/tests/test_export_service.py` - CREATE NEW - test service directly
4. `census_app/surveys/tests/test_data_governance_views.py` - Re-enable skipped tests
5. `census_app/core/encryption.py` (?) - Understand decryption utilities

## Success Criteria

- [ ] ExportService._generate_csv() uses correct field names
- [ ] CSV export contains decrypted patient data
- [ ] All 22 view tests pass
- [ ] Service tests created and passing
- [ ] Full test suite (514+ tests) still passing
- [ ] Security requirements verified:
  - [ ] Only authorized users can download data
  - [ ] Downloaded data is properly decrypted
  - [ ] Download tokens expire correctly
  - [ ] Invalid tokens are rejected

## Notes

- This is a **security-critical feature** - data must be properly decrypted
- CSV exports contain sensitive patient data - must verify encryption/decryption flow
- Do not rush - thorough testing required before deployment
