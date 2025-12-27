"""JSON Schema validation for asset pack manifests.

This module loads the formal JSON Schema and validates manifests before output.
"""

import json
from pathlib import Path
from typing import Any

import jsonschema
from jsonschema import ValidationError

from .types import Manifest

# Path to the schema file (relative to this module)
# ingestion/src/game_asset_tracker_ingestion/core/validator.py -> game-asset-tracker/schemas/
SCHEMA_PATH = Path(__file__).parent.parent.parent.parent.parent / "schemas" / "manifest.schema.json"


def load_schema() -> dict[str, Any]:
    """Load the JSON schema from disk.

    Returns:
        Dictionary containing the JSON Schema.

    Raises:
        FileNotFoundError: If schema file doesn't exist
        json.JSONDecodeError: If schema is invalid JSON
    """
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")

    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def validate_manifest(manifest: Manifest) -> None:
    """Validate a manifest against the JSON Schema.

    Args:
        manifest: The manifest dictionary to validate

    Raises:
        ValidationError: If the manifest doesn't conform to the schema
        FileNotFoundError: If schema file is missing
        json.JSONDecodeError: If schema is invalid
    """
    schema = load_schema()
    jsonschema.validate(instance=manifest, schema=schema)


def validate_manifest_with_error_details(manifest: Manifest) -> tuple[bool, str | None]:
    """Validate a manifest and return detailed error information.

    This is a convenience wrapper that catches validation errors and
    returns user-friendly error messages.

    Args:
        manifest: The manifest dictionary to validate

    Returns:
        Tuple of (is_valid, error_message). error_message is None if valid.
    """
    try:
        validate_manifest(manifest)
        return True, None
    except ValidationError as e:
        # Build a detailed error message
        error_path = " -> ".join(str(p) for p in e.path) if e.path else "root"
        error_msg = f"Validation error at {error_path}: {e.message}"

        # Add context if available
        if e.instance:
            error_msg += f"\nInvalid value: {e.instance}"

        return False, error_msg
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return False, f"Schema error: {e}"
