# Data Governance Integration - Correction Plan

## Analysis: What We Built vs. What Was Planned

### ✅ CORRECT - What Matches the Plan:
1. **Models** - All 4 models created correctly (DataExport, LegalHold, DataCustodian, DataRetentionExtension)
2. **Services** - ExportService and RetentionService implemented correctly
3. **Permissions** - All 14 permission functions implemented
4. **Tests** - Comprehensive test suite (97 tests passing)

### ❌ INCORRECT - What Diverged from Plan:
1. **Created separate views_data_governance.py** - Plan says integrate into existing views
2. **Created separate dashboard** - Plan says add to existing survey dashboard
3. **Created duplicate close/export/delete views** - Should extend existing ones
4. **Wrong UI flow** - Should be buttons on dashboard, not separate pages

## What the Plan Actually Says

### UI Integration (from data-governance-export.md):

**Survey Dashboard Should Have:**
1. "Close Survey" button (existing) - should call `survey.close_survey(user)`
2. **"Download Data" button** - ONLY visible after survey closed, ONLY to authorized users
3. Export button opens **Download Disclaimer Modal** (React component)
4. Modal handles attestation, then generates export

### File Locations (from data-governance-implementation.md):

```
User Interface Layer:
  - Survey Dashboard (existing) → Add export button widget
  - Download Disclaimer Modal (NEW React component)
  - Retention warnings (in dashboard if approaching deletion)

Views/API Layer:
  - Extend existing views (survey_dashboard, survey_close)
  - Add NEW API endpoints (POST /api/surveys/{id}/export/)
  
Services:
  - ExportService ✅ (done)
  - RetentionService ✅ (done)
  
Models:
  - Survey extensions ✅ (done)
  - DataExport ✅ (done)
  - LegalHold ✅ (done)
  - DataCustodian ✅ (done)
```

## Correct Implementation Plan

### Phase 1: Modify Existing Views (TODAY)

1. **Modify `survey_close` in `publish_settings` view:**
   ```python
   # When action == "close"
   survey.close_survey(request.user)  # Instead of just setting status
   # This triggers: closed_at, retention_months, deletion_date
   ```

2. **Add export button to `survey_dashboard` template:**
   ```django
   {% if survey.is_closed and permissions.can_export %}
     <a href="{% url 'surveys:data_export' survey.slug %}" class="btn btn-primary">
       Download Survey Data
     </a>
   {% endif %}
   ```

3. **Add retention status widget to `survey_dashboard` template:**
   ```django
   {% if survey.is_closed %}
     <div class="alert alert-info">
       Retention: {{ survey.retention_months }} months
       Deletion date: {{ survey.deletion_date|date:"Y-m-d" }}
       Days remaining: {{ survey.days_until_deletion }}
     </div>
   {% endif %}
   ```

### Phase 2: Create Export Flow (TODAY)

1. **Keep ONLY these NEW views from views_data_governance.py:**
   - `data_export_disclaimer` - Show disclaimer form
   - `data_export_create` - Generate export (POST)
   - `data_export_download` - Download file with token
   - `extend_retention` - Extension form
   - `legal_hold_manage` - Legal hold UI
   - `custodian_manage` - Custodian UI

2. **Delete duplicate views:**
   - ❌ Remove `survey_close` (duplicate of publish_settings)
   - ❌ Remove `data_governance_dashboard` (integrate into survey_dashboard)
   - ❌ Remove `survey_soft_delete` (modify existing survey_delete)

### Phase 3: URL Structure

```python
# census_app/surveys/urls.py

urlpatterns = [
    # Existing (keep as-is)
    path('<slug:slug>/dashboard/', views.survey_dashboard, name='dashboard'),
    path('<slug:slug>/delete/', views.survey_delete, name='delete'),
    
    # Data Governance (NEW - from views_data_governance.py)
    path('<slug:slug>/export/', gov_views.data_export_disclaimer, name='data_export'),
    path('<slug:slug>/export/create/', gov_views.data_export_create, name='data_export_create'),
    path('<slug:slug>/export/<uuid:export_id>/<str:token>/', gov_views.data_export_download, name='data_export_download'),
    path('<slug:slug>/retention/extend/', gov_views.extend_retention, name='extend_retention'),
    path('<slug:slug>/legal-hold/', gov_views.legal_hold_manage, name='legal_hold'),
    path('<slug:slug>/custodians/', gov_views.custodian_manage, name='custodians'),
]
```

### Phase 4: Template Integration

**Modify existing dashboard.html:**
```django
<!-- Add after existing stats -->
{% if survey.is_closed %}
  <div class="card bg-base-100 shadow-xl">
    <div class="card-body">
      <h2 class="card-title">Data Governance</h2>
      
      <div class="stats">
        <div class="stat">
          <div class="stat-title">Retention Period</div>
          <div class="stat-value">{{ survey.retention_months }} months</div>
          <div class="stat-desc">Deletion: {{ survey.deletion_date|date:"Y-m-d" }}</div>
        </div>
      </div>
      
      <div class="card-actions">
        {% if permissions.can_export %}
          <a href="{% url 'surveys:data_export' survey.slug %}" class="btn btn-primary">
            Download Data
          </a>
        {% endif %}
        
        {% if permissions.can_extend_retention %}
          <a href="{% url 'surveys:extend_retention' survey.slug %}" class="btn btn-secondary">
            Extend Retention
          </a>
        {% endif %}
      </div>
    </div>
  </div>
{% endif %}
```

## Action Items (Priority Order)

### HIGH PRIORITY (Do Now):
1. ✅ Delete duplicate views from views_data_governance.py
2. ✅ Keep only export/retention/legal-hold/custodian views
3. ✅ Modify existing `survey_close` to call `survey.close_survey(user)`
4. ✅ Add export button to existing dashboard template
5. ✅ Add retention widget to existing dashboard template

### MEDIUM PRIORITY (Next):
6. Modify existing `survey_delete` to use `soft_delete()` instead of hard delete
7. Add breadcrumbs to all new templates (follow existing pattern)
8. Test full workflow: close → export → download

### LOW PRIORITY (Later):
9. Add React modal for download disclaimer (optional - can use Django forms first)
10. Add Celery tasks for deletion warnings
11. Add email notifications

## Files to Modify Today

1. **census_app/surveys/views_data_governance.py** - Remove duplicates, keep only new views
2. **census_app/surveys/views.py** - Modify `survey_close` (line ~2013)
3. **census_app/surveys/templates/surveys/dashboard.html** - Add export button + retention widget
4. **census_app/surveys/urls.py** - Update URL patterns
5. **All new templates** - Add proper breadcrumbs

## Success Criteria

After this refactor:
- ✅ No duplicate views (close/export/delete)
- ✅ Export button appears on dashboard ONLY when survey closed
- ✅ Export button ONLY visible to authorized users
- ✅ Retention status visible on dashboard
- ✅ Breadcrumbs on all templates
- ✅ All tests still passing
