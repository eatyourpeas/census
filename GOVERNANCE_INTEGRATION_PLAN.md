# Data Governance Integration Plan

## Current Situation - DUPLICATION DETECTED

### Existing Functionality (already in census_app/surveys/views.py):
1. **survey_close** - Line 2013: Sets `status = Survey.Status.CLOSED` in publish_settings
2. **survey_export_csv** - Line 4140: Exports responses as CSV (requires unlock)
3. **survey_delete** - Line 1848: Hard deletes survey with confirmation
4. **survey_dashboard** - Line 1597: Main dashboard for survey management

### New Data Governance Features (just created, NEED INTEGRATION):
- Data governance models (DataExport, LegalHold, DataCustodian, DataRetentionExtension)
- Services (ExportService, RetentionService)
- Permissions (14 functions for role-based access)
- New views in views_data_governance.py (DUPLICATE existing functionality!)

## Integration Strategy

### Option 1: Extend Existing Views (RECOMMENDED)
**Modify existing views to use new data governance features:**

1. **survey_close (in publish_settings)** 
   - When closing, call `survey.close_survey(user)` instead of just setting status
   - This triggers retention period and sets `closed_at`, `deletion_date`
   - Keep existing UI, add data governance info

2. **survey_export_csv**
   - Extend to use ExportService for audit logging
   - Create DataExport record with download tracking
   - Keep existing CSV generation, add governance layer

3. **survey_delete**
   - Modify to use soft delete by default (survey.soft_delete())
   - Add 30-day grace period
   - Check legal holds before deletion
   - Add separate hard delete for after grace period

4. **survey_dashboard**
   - Add data governance section showing:
     * Retention status (if closed)
     * Legal hold status
     * Active data custodians
     * Recent exports
   - Link to dedicated data governance page for details

### Option 2: Separate Data Governance Section (CURRENT - BUT DUPLICATES)
**Keep new views_data_governance.py separate**
- Pro: Clean separation of concerns
- **CON: Duplicates survey_close, survey_export, survey_delete**
- CON: Two places to manage same functionality
- CON: Confusing for users

## Recommendation

**GO WITH OPTION 1** - Integrate data governance into existing views:

1. **Delete** views_data_governance.py duplicate views
2. **Keep** data governance dashboard as overview page
3. **Extend** existing views:
   - Modify `survey_close` in publish_settings to call `survey.close_survey(user)`
   - Modify `survey_export_csv` to use ExportService for audit
   - Modify `survey_delete` to use soft_delete() with grace period
   - Add data governance widget to main survey_dashboard

4. **Create** new specialized views only for:
   - Extend retention (no duplicate)
   - Manage legal holds (no duplicate)
   - Manage data custodians (no duplicate)
   - Data governance dashboard (overview page)

This avoids duplication and keeps user experience consistent.
