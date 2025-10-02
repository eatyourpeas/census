"""
External dataset service for fetching prefilled dropdown options.

This module provides a service layer for fetching datasets from external APIs
(e.g., hospitals, NHS trusts) with caching to minimize external calls.
"""
import logging
from typing import Any

import requests
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

# Cache timeout: 24 hours for relatively stable datasets like hospital lists
DATASET_CACHE_TIMEOUT = 60 * 60 * 24

# Available dataset keys
AVAILABLE_DATASETS = {
    "hospitals_england": "Hospitals (England)",
    "hospitals_wales": "Hospitals (Wales)",
    "hospitals_england_wales": "Hospitals (England & Wales)",
    "nhs_trusts": "NHS Trusts",
    "welsh_lhbs": "Welsh Local Health Boards",
}


class DatasetFetchError(Exception):
    """Raised when external dataset fetch fails."""

    pass


def get_available_datasets() -> dict[str, str]:
    """Return dictionary of available dataset keys and display names."""
    return AVAILABLE_DATASETS.copy()


def _get_api_url() -> str:
    """Get the external dataset API URL from settings."""
    return getattr(
        settings,
        "EXTERNAL_DATASET_API_URL",
        "https://api.example.com/datasets",  # Replace with actual API
    )


def _get_api_key() -> str:
    """Get the external dataset API key from settings."""
    return getattr(settings, "EXTERNAL_DATASET_API_KEY", "")


def fetch_dataset(dataset_key: str) -> list[str]:
    """
    Fetch dataset options from external API with caching.

    Args:
        dataset_key: The key identifying which dataset to fetch

    Returns:
        List of option strings

    Raises:
        DatasetFetchError: If dataset key is invalid or fetch fails
    """
    if dataset_key not in AVAILABLE_DATASETS:
        raise DatasetFetchError(f"Unknown dataset key: {dataset_key}")

    # Check cache first
    cache_key = f"external_dataset:{dataset_key}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        logger.debug(f"Returning cached dataset: {dataset_key}")
        return cached_data

    # Fetch from external API
    try:
        api_url = _get_api_url()
        api_key = _get_api_key()

        url = f"{api_url}/{dataset_key}"
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        logger.info(f"Fetching dataset from external API: {dataset_key}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Extract options from response (adjust based on actual API structure)
        if isinstance(data, dict) and "options" in data:
            options = data["options"]
        elif isinstance(data, list):
            options = data
        else:
            raise DatasetFetchError(f"Unexpected response format for {dataset_key}")

        # Validate options are strings
        if not isinstance(options, list) or not all(
            isinstance(opt, str) for opt in options
        ):
            raise DatasetFetchError(f"Invalid options format for {dataset_key}")

        # Cache the result
        cache.set(cache_key, options, DATASET_CACHE_TIMEOUT)
        logger.info(f"Cached {len(options)} options for dataset: {dataset_key}")

        return options

    except requests.RequestException as e:
        logger.error(f"Failed to fetch dataset {dataset_key}: {e}")
        raise DatasetFetchError(f"Failed to fetch dataset: {str(e)}") from e
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Failed to parse dataset {dataset_key}: {e}")
        raise DatasetFetchError(f"Failed to parse dataset: {str(e)}") from e


def clear_dataset_cache(dataset_key: str | None = None) -> None:
    """
    Clear cached dataset(s).

    Args:
        dataset_key: If provided, clear only this dataset. Otherwise clear all.
    """
    if dataset_key:
        cache_key = f"external_dataset:{dataset_key}"
        cache.delete(cache_key)
        logger.info(f"Cleared cache for dataset: {dataset_key}")
    else:
        for key in AVAILABLE_DATASETS:
            cache_key = f"external_dataset:{key}"
            cache.delete(cache_key)
        logger.info("Cleared all dataset caches")
