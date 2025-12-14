# Schemas

This directory contains the formal contract for data interchange between ingestion scripts and the Obsidian plugin.

## Files

### `manifest.schema.json`
**The formal JSON Schema (Draft 7) definition.**

This schema strictly enforces the structure of manifest files that flow through the system. All ingestion scripts MUST generate JSON that validates against this schema, and the Obsidian plugin MUST validate incoming JSON before processing.

**Key Validation Rules:**
- `pack_id` must be a valid UUID (lowercase, hyphenated format)
- `file_type` must be lowercase alphanumeric only (no dots)
- `assets` array must contain at least 1 item
- `size_bytes` must be non-negative integer
- Tags must be unique within their arrays
- No additional properties allowed beyond those defined

### `example-manifest.json`
A valid example manifest demonstrating proper structure and typical metadata patterns.

## Validating Manifests

### Using Python
```python
import json
import jsonschema

# Load schema
with open('schemas/manifest.schema.json') as f:
    schema = json.load(f)

# Load manifest to validate
with open('output/my-pack.json') as f:
    manifest = json.load(f)

# Validate
try:
    jsonschema.validate(instance=manifest, schema=schema)
    print("✓ Valid manifest")
except jsonschema.ValidationError as e:
    print(f"✗ Validation failed: {e.message}")
```

**Install jsonschema:**
```bash
pip install jsonschema
```

### Using TypeScript/Node.js
```typescript
import Ajv from 'ajv';
import schema from './schemas/manifest.schema.json';
import manifest from './output/my-pack.json';

const ajv = new Ajv();
const validate = ajv.compile(schema);

if (validate(manifest)) {
  console.log('✓ Valid manifest');
} else {
  console.log('✗ Validation failed:', validate.errors);
}
```

**Install AJV:**
```bash
npm install ajv
```

### Using Online Validator
Visit [jsonschemavalidator.net](https://www.jsonschemavalidator.net/) and paste:
1. `manifest.schema.json` in the left panel
2. Your generated manifest JSON in the right panel

## Schema Versioning

**Current Version:** 1.0.0

When making breaking changes to the schema:
1. Increment the version in the schema's `$id` field
2. Update this README with migration notes
3. Ensure both ingestion scripts and plugin are updated accordingly

## Design Notes

### Why `additionalProperties: false`?
Strict validation prevents typos and ensures data integrity. If the plugin doesn't expect a field, it shouldn't be in the manifest.

### Why lowercase-only `file_type`?
Consistency for database queries and case-insensitive filesystems. Scripts should normalize extensions (e.g., `.PNG` → `png`).

### Why string values in `metadata`?
Flexibility. Different asset types have different metadata needs. Consumers can parse strings as needed (numbers, booleans, etc.).

### Why UUID pattern validation?
Ensures `pack_id` can be safely used as:
- SQLite primary key
- Markdown filename component
- Obsidian wikilink target

## Future Considerations

Potential schema enhancements (not yet implemented):
- Semantic versioning for manifest format itself
- Optional hash/checksum fields for asset integrity verification
- Standardized metadata field recommendations per file_type
- Support for asset dependencies/relationships
