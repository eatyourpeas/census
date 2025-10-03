# Adding External Datasets

This guide shows you how to add new external datasets to the prefilled dropdown options feature.

## Overview

The external datasets system allows dropdown questions to load options from external APIs. The system is designed to be flexible and support multiple API providers with different response structures.

## Quick Start: Adding a Dataset from RCPCH API

If your dataset comes from the same RCPCH NHS Organisations API (`https://api.rcpch.ac.uk/nhs-organisations/v1`), you only need to update 3 places in `census_app/surveys/external_datasets.py`:

### 1. Add to AVAILABLE_DATASETS

```python
AVAILABLE_DATASETS = {
    # ... existing datasets ...
    "your_dataset_key": "Your Dataset Display Name",
}
```

### 2. Add Endpoint Mapping

```python
def _get_endpoint_for_dataset(dataset_key: str) -> str:
    endpoint_map = {
        # ... existing mappings ...
        "your_dataset_key": "/your/endpoint/",  # Note: include trailing slash
    }
    return endpoint_map.get(dataset_key, "")
```

### 3. Add Transformer Logic

Add a new `elif` block in `_transform_response_to_options()`:

```python
def _transform_response_to_options(dataset_key: str, data: Any) -> list[str]:
    # ... existing code ...

    elif dataset_key == "your_dataset_key":
        # Document the expected response format
        # Format: {"id": "123", "name": "Example", ...}
        for item in data:
            # Validate required fields exist
            if not isinstance(item, dict) or "name" not in item or "id" not in item:
                logger.warning(f"Skipping invalid item: {item}")
                continue

            # Format as "Name (Code)"
            options.append(f"{item['name']} ({item['id']})")
```

That's it! The dataset will automatically appear in the dropdown selector.

## Example: London Boroughs

Here's a complete example showing how London Boroughs were added:

**API Response:**
```json
[
  {
    "name": "Westminster",
    "gss_code": "E09000033",
    "hectares": 2203.005,
    "nonld_area": 54.308,
    "ons_inner": "T"
  }
]
```

**Implementation:**

```python
# 1. Add to AVAILABLE_DATASETS
AVAILABLE_DATASETS = {
    "london_boroughs": "London Boroughs",
}

# 2. Add endpoint
def _get_endpoint_for_dataset(dataset_key: str) -> str:
    endpoint_map = {
        "london_boroughs": "/london_boroughs/",
    }
    return endpoint_map.get(dataset_key, "")

# 3. Add transformer
def _transform_response_to_options(dataset_key: str, data: Any) -> list[str]:
    elif dataset_key == "london_boroughs":
        # Format: {"name": "Westminster", "gss_code": "E09000033", ...}
        for item in data:
            if not isinstance(item, dict) or "name" not in item or "gss_code" not in item:
                logger.warning(f"Skipping invalid London borough item: {item}")
                continue
            options.append(f"{item['name']} ({item['gss_code']})")
```

## Advanced: Using a Different API

For datasets from different API providers, configure `DATASET_CONFIGS`:

```python
DATASET_CONFIGS = {
    "custom_dataset": {
        "base_url": "https://different-api.example.com",
        "endpoint": "/custom/endpoint/",
        "api_key_setting": "CUSTOM_API_KEY",  # Optional: env var name for API key
    }
}
```

Then update the `fetch_dataset()` function to check `DATASET_CONFIGS` first (you'll need to modify the code to support this).

## Complex Response Structures

### Nested Data (e.g., Paediatric Diabetes Units)

For APIs that return nested objects, extract the relevant fields:

```python
elif dataset_key == "paediatric_diabetes_units":
    # Format: {"pz_code": "PZ215", "primary_organisation": {"name": "...", "ods_code": "..."}}
    for item in data:
        if not isinstance(item, dict) or "pz_code" not in item:
            logger.warning(f"Skipping invalid item: {item}")
            continue

        # Extract from nested structure
        name = None
        code = item["pz_code"]

        if "primary_organisation" in item and isinstance(item["primary_organisation"], dict):
            primary = item["primary_organisation"]
            if "name" in primary:
                name = primary["name"]
                if "ods_code" in primary:
                    code = primary["ods_code"]

        if name:
            options.append(f"{name} ({code})")
        else:
            # Fallback if no name found
            options.append(f"PDU {code}")
```

### Hierarchical Data (e.g., Welsh LHBs)

For hierarchical data, use indentation to show structure:

```python
elif dataset_key == "welsh_lhbs":
    for lhb in data:
        # Add parent
        options.append(f"{lhb['name']} ({lhb['ods_code']})")

        # Add children with indentation
        if "organisations" in lhb and isinstance(lhb["organisations"], list):
            for org in lhb["organisations"]:
                if isinstance(org, dict) and "name" in org and "ods_code" in org:
                    options.append(f"  {org['name']} ({org['ods_code']})")
```

## Testing Your New Dataset

### 1. Unit Tests

Add tests to `census_app/api/tests/test_dataset_api.py`:

```python
def get_mock_your_dataset_response():
    """Return realistic mock data matching the API structure."""
    return [
        {"id": "001", "name": "Example 1"},
        {"id": "002", "name": "Example 2"},
    ]

def test_get_your_dataset_success(self):
    """Test fetching your dataset returns transformed options."""
    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.json.return_value = get_mock_your_dataset_response()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        response = self.client.get("/api/datasets/your_dataset_key/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["dataset_key"], "your_dataset_key")
        self.assertIsInstance(data["options"], list)
        self.assertEqual(len(data["options"]), 2)
        self.assertEqual(data["options"][0], "Example 1 (001)")
```

### 2. Manual Testing

```python
# In Django shell
docker compose exec web python manage.py shell

from census_app.surveys.external_datasets import fetch_dataset

# Test your dataset
result = fetch_dataset('your_dataset_key')
print(f"Got {len(result)} options")
print("First 5:", result[:5])
```

### 3. Browser Testing

1. Navigate to survey builder
2. Create a dropdown question
3. Check "Use prefilled options"
4. Select your new dataset from the dropdown
5. Click "Load Options"
6. Verify options populate correctly

## Best Practices

### 1. Error Handling

Always validate required fields and log warnings for invalid items:

```python
if not isinstance(item, dict) or "required_field" not in item:
    logger.warning(f"Skipping invalid item: {item}")
    continue
```

### 2. Consistent Formatting

Use consistent format: `"Name (Code)"` for all datasets where possible:

```python
options.append(f"{item['name']} ({item['code']})")
```

### 3. Documentation

Document the expected API response structure in comments:

```python
elif dataset_key == "your_dataset":
    # Format: {"id": "123", "name": "Example", "active": true}
    # API endpoint: /your/endpoint/
    # Returns array of objects with id and name fields
```

### 4. Graceful Degradation

Provide fallbacks for optional fields:

```python
name = item.get("name", "Unknown")
code = item.get("code", item.get("id", "N/A"))
options.append(f"{name} ({code})")
```

## Troubleshooting

### Dataset Not Appearing in Dropdown

1. Check `AVAILABLE_DATASETS` includes your key and display name
2. Verify the key matches exactly in all three places
3. Hard refresh browser (Cmd+Shift+R) to clear cached JavaScript

### API Returns 404

1. Verify endpoint path is correct (including trailing slash!)
2. Test the full URL manually: `curl "https://api.rcpch.ac.uk/nhs-organisations/v1/your/endpoint/"`
3. Check `EXTERNAL_DATASET_API_URL` environment variable

### Options Not Transforming Correctly

1. Check response structure matches your transformer logic
2. Add debug logging: `print(f"DEBUG: item = {item}")`
3. Verify required fields exist in API response
4. Check for typos in field names (case-sensitive!)

### Caching Issues

Clear the Django cache to force fresh data:

```bash
docker compose exec web python manage.py shell -c "from django.core.cache import cache; cache.clear()"
```

## Current Available Datasets

| Dataset Key | Display Name | Endpoint | Format |
|------------|--------------|----------|--------|
| `hospitals_england_wales` | Hospitals (England & Wales) | `/organisations/limited/` | `name (ods_code)` |
| `nhs_trusts` | NHS Trusts | `/trusts/` | `name (ods_code)` |
| `welsh_lhbs` | Welsh Local Health Boards | `/local_health_boards/` | `name (ods_code)` (hierarchical) |
| `london_boroughs` | London Boroughs | `/london_boroughs/` | `name (gss_code)` |
| `nhs_england_regions` | NHS England Regions | `/nhs_england_regions/` | `name (region_code)` |
| `paediatric_diabetes_units` | Paediatric Diabetes Units | `/paediatric_diabetes_units/` | `name (ods_code)` |
| `integrated_care_boards` | Integrated Care Boards (ICBs) | `/integrated_care_boards/` | `name (ods_code)` |

## Related Documentation

- [Prefilled Datasets Setup](./prefilled-datasets-setup.md) - Configuration and API details
- [Prefilled Datasets Quick Start](./prefilled-datasets-quickstart.md) - User guide
- [Getting Started](./getting-started.md) - Environment variables

## Support

If you encounter issues or need help adding a dataset:

1. Check the [troubleshooting section](#troubleshooting) above
2. Review existing implementations in `external_datasets.py`
3. Test the API endpoint manually with `curl`
4. Check logs: `docker compose logs web --tail=50`
