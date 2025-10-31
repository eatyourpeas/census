# Quick Start - Prefilled Datasets

## What's Already Done ✅

1. **Service Layer**: `checktick_app/surveys/external_datasets.py`
   - Fetches data from RCPCH API
   - Transforms responses to formatted options
   - 24-hour caching

2. **API Endpoints**: `/api/datasets/` and `/api/datasets/{key}/`
   - Requires authentication
   - Returns formatted options

3. **Frontend UI**:
   - "Use prefilled options" checkbox (dropdown type only)
   - Dataset selector dropdown
   - "Load Options" button with spinner
   - Auto-populates options textarea

4. **Tests**: 24 passing tests covering all scenarios

## Configuration

Your `.env` file already has the right settings:

```bash
EXTERNAL_DATASET_API_URL=https://api.rcpch.ac.uk/nhs-organisations/v1
EXTERNAL_DATASET_API_KEY=  # Leave empty
```

## Try It Out

1. Log in to your CheckTick app
2. Create or edit a survey
3. Add a new question
4. Set type to **"Dropdown (single choice)"**
5. Check **"Use prefilled options"**
6. Select a dataset (e.g., "Hospitals (England & Wales)")
7. Click **"Load Options"**
8. Options will populate automatically!

## Available Datasets

- **Hospitals (England)** - Hospital list for England
- **Hospitals (Wales)** - Hospital list for Wales
- **Hospitals (England & Wales)** - Combined hospital list
- **NHS Trusts** - NHS Trust organizations
- **Welsh Local Health Boards** - Welsh LHBs with their constituent organizations

## Format

All options are formatted as: `NAME (ODS_CODE)`

Example:
- `ADDENBROOKE'S HOSPITAL (RGT01)`
- `AIREDALE NHS FOUNDATION TRUST (RCF)`

## Status

**All core functionality is complete!** ✅

The system now:
- ✅ Fetches data from RCPCH API
- ✅ Displays prefilled options (dropdown only)
- ✅ Shows spinner during loading
- ✅ Saves dataset selection with the question
- ✅ Restores dataset selection when editing

You're ready to test the complete flow end-to-end!

See `docs/prefilled-datasets-setup.md` for full details and `docs/prefilled-datasets-serialization.md` for implementation details.
