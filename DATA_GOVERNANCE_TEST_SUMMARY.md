# Data Governance - Outstanding Tasks

## ✅ Completed Items

All core data governance features have been implemented and tested:

- ✅ **All 22 view tests passing** (was 9 passing, 13 skipped)
- ✅ **ExportService fixed** - Correct field mapping (question.text)
- ✅ **CSV export working** - Properly decrypted patient data
- ✅ **Permission enforcement** - All routes properly secured
- ✅ **Attestation requirement** - Users must confirm authorization
- ✅ **Token security** - Download links expire correctly
- ✅ **Dashboard integration** - Shows/hides based on permissions
- ✅ **Survey closure workflow** - Confirmation dialog implemented
- ✅ **Retention fields** - Automatically calculated on closure
- ✅ **Data governance models** - All 4 models implemented and tested
- ✅ **Service layer** - ExportService and RetentionService complete
- ✅ **Comprehensive documentation** - 7 detailed guides
- ✅ **Environment variables** - Configurable retention policies
- ✅ **UI improvements** - Empty state alerts, responsive design
- ✅ **Full test suite** - 536 tests passing

## ⏳ Outstanding Tasks

### 1. Email Notifications (HIGH PRIORITY)

The following email notifications need to be implemented per the data governance documentation:

#### A. Deletion Warning Emails ⏳
- **When:** At 30 days, 7 days, and 1 day before automatic deletion
- **To:** Survey owner
- **Content:** Warning about upcoming deletion, options to extend or export
- **Current status:** Placeholder in `RetentionService.send_deletion_warning()`
- **Documentation:** `docs/data-governance-overview.md` line 51

#### B. Data Export Notification 📧
- **When:** Any time survey data is downloaded
- **To:** Organization administrators (org owner + org admins)
- **Content:** Who downloaded, what survey, when, stated purpose
- **Current status:** Not implemented
- **Documentation:** `docs/data-governance-overview.md` line 64

#### C. Survey Closure Notification 📧
- **When:** Survey is closed
- **To:** Survey owner
- **Content:** Confirmation of closure, deletion date, retention period
- **Current status:** Not implemented
- **Why needed:** Confirms action, reminds about retention timeline

#### D. Custodian Assignment Notification 📧
- **When:** Data custodian role is granted
- **To:** The custodian being assigned
- **Content:** Role granted, survey details, responsibilities
- **Current status:** Not implemented
- **Documentation:** `docs/data-governance-overview.md` line 128

#### E. Ownership Transfer Notification 📧
- **When:** Survey ownership transfers (e.g., creator leaves organization)
- **To:** Both old owner and new owner
- **Content:** Transfer details, reason, new responsibilities
- **Current status:** Not implemented
- **Documentation:** `docs/data-governance-overview.md` line 128

#### F. Retention Extension Notification 📧
- **When:** Retention period is extended
- **To:** Survey owner and organization administrators
- **Content:** Who extended, new deletion date, reason provided
- **Current status:** Not implemented
- **Why needed:** Audit trail, transparency

#### G. Legal Hold Notifications 📧
- **When:** Legal hold is placed or removed
- **To:** Survey owner and organization owner
- **Content:** Legal hold status, reason, who placed/removed
- **Current status:** Not implemented
- **Why needed:** Legal compliance, documentation

### 2. Scheduled Deletion Processing (MEDIUM PRIORITY)

#### A. Automated Deletion Task ⏰
- **What:** Run `RetentionService.process_automatic_deletions()` daily
- **How:** Management command + scheduler (cron/Celery/Django-Q)
- **Current status:** Business logic complete, needs scheduling
- **Implementation options:**
  1. Django management command + system cron
  2. Celery periodic task
  3. Django-Q scheduled task
  4. Cloud scheduler (AWS EventBridge, Azure Functions Timer)

#### B. Management Command 🔧
- **Create:** `census_app/surveys/management/commands/process_deletions.py`
- **Purpose:** CLI interface to trigger deletion processing
- **Usage:** `python manage.py process_deletions`
- **Should include:**
  - Dry-run mode to preview deletions
  - Verbose output for logging
  - Error handling and reporting

### 3. Email Template Design (LOW PRIORITY)

All emails should use the existing branded email system (`census_app/core/email_utils.py`):

- Use `send_branded_email()` function
- Markdown content for email body
- Platform branding applied automatically
- Plain text fallback generated automatically

**Templates needed:**
- Deletion warning (3 variants: 30d, 7d, 1d)
- Export notification
- Closure confirmation
- Custodian assignment
- Ownership transfer
- Retention extension
- Legal hold placed/removed

## Implementation Priority

1. **Email Notifications** (2-4 hours)
   - Start with deletion warnings (most critical)
   - Then export notifications (audit requirement)
   - Then closure confirmation (user experience)
   - Finally other notifications (nice-to-have)

2. **Scheduled Deletion** (1-2 hours)
   - Create management command
   - Document deployment options
   - Test in development

3. **Production Deployment** (1-2 hours)
   - Set up scheduler (cron/Celery)
   - Configure email settings
   - Monitor first runs

## Files to Modify

### For Email Notifications:
- `census_app/surveys/services/retention_service.py` - Implement `send_deletion_warning()`
- `census_app/surveys/views_data_governance.py` - Add email calls to export/closure/etc.
- `census_app/surveys/models.py` - Add email calls to custodian/legal hold methods

### For Scheduled Deletion:
- Create: `census_app/surveys/management/commands/process_deletions.py`
- Update: Documentation for deployment

## Success Criteria

- [ ] All 7 email notification types implemented
- [ ] Emails use branded template system
- [ ] Management command created for deletions
- [ ] Documentation updated with deployment instructions
- [ ] Manual testing of all email notifications
- [ ] Dry-run testing of deletion processing
- [ ] Production deployment guide complete

## Notes

- Email infrastructure already exists (`census_app/core/email_utils.py`)
- All email sending uses `send_branded_email()` function
- Deletion logic is complete and tested
- Focus is on integration, not new business logic
