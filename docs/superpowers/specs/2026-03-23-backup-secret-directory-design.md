# Backup Interface Enhancement: Include Secret Directory

**Date**: 2026-03-23
**Status**: Approved

## Overview

Extend the backup interface to include the secret directory (`.swe.secret` / `~/.copaw.secret/`) content alongside the working directory during backup upload and restore download operations.

## Background

Currently, the backup system only archives the working directory (`~/.copaw/{user_id}/`), which contains:
- `config.json`
- `sessions/`
- `memory/`
- `active_skills/`
- `customized_skills/`

However, sensitive configuration like API keys and provider settings are stored separately in the secret directory (`~/.copaw.secret/{user_id}/`), including:
- `envs.json`
- `providers.json`

This separation means a complete user restoration requires both directories. This design adds secret directory backup/restore to ensure data completeness.

## Design

### Approach: Nested Inclusion (Option C)

The secret directory contents will be included within the same zip file as a nested `.secret/` folder. This approach:
- Maintains simple S3 storage structure (one file per user)
- Keeps related data together
- Requires minimal changes to existing listing/retrieval logic
- Provides backward compatibility with old backups

### Zip Structure

**Note**: `.secret/` is at the **root level** of the zip archive, as a sibling to `config.json`.

```
backup_{user_id}.zip
├── config.json
├── sessions/
├── memory/
├── ... (other working dir contents)
└── .secret/
    ├── envs.json
    └── providers.json
```

### Implementation Changes

**File**: `src/copaw/app/backup/worker.py`

#### 0. Import Update

Add `get_secret_dir` to the imports from `copaw.constant`:

```python
from ...constant import DEFAULT_WORKING_DIR, get_secret_dir
```

#### 1. `_compress_user()` - Add secret directory compression

When compressing a user directory, also compress the corresponding secret directory contents into a `.secret/` folder within the zip.

**Logic**:
- Get secret directory via `get_secret_dir(user_id)` (from `copaw.constant`)
- If secret directory exists, iterate and add files under `.secret/` prefix
- Handle empty directories by writing directory entries (use same pattern as existing empty directory handling at lines 256-261)

#### 2. `_extract_zip()` - Handle `.secret/` extraction

Update the method signature to accept `user_id` for deriving the secret directory.

**Signature change**:
```python
async def _extract_zip(self, zip_path: Path, target_dir: Path, user_id: str) -> None
```

**Logic**:
- Derive `secret_dir` via `get_secret_dir(user_id)`
- Iterate zip file entries
- Entries starting with `.secret/` → extract to `secret_dir` (remove `.secret/` prefix)
- Other entries → extract to `target_dir` (existing behavior)
- **Security**: Validate resolved extraction paths are under target directories to prevent path traversal (use `Path.resolve()` and check parent chain)

#### 3. `_create_rollback_backup()` - Include secrets in rollback

Ensure rollback backups also capture secret directory state for complete rollback capability.

**Logic**:
- Get secret directory via `get_secret_dir(user_id)`
- If secret directory exists, iterate and add files under `.secret/` prefix
- Use same compression logic as `_compress_user`

#### 4. Update `_extract_zip()` call sites

Update all calls to `_extract_zip()` to pass the `user_id` parameter:

**In `run_restore_task()` (line ~204)**:
```python
await self._extract_zip(zip_path, user_dir, user_id)
```

**In `_rollback_all()` (line ~323)**:
```python
await self._extract_zip(path, user_dir, user_id)
```

### Edge Cases

| Scenario | Handling |
|----------|----------|
| Secret directory does not exist | Skip silently, continue backup |
| Secret directory is empty | Create empty `.secret/` entry in zip |
| Restoring old backup without `.secret/` | Only restore working directory contents |
| Permission errors on secret files | Log warning, continue with other files |
| Secret file path traversal | Validate extracted paths under target directory |

### Security Considerations

- Secret contents are backed up in the same zip file (compression level 6)
- **Note**: Zip compression is NOT encryption. Files are stored compressed but unencrypted within the zip.
- S3 transmission uses TLS encryption (handled by boto3)
- S3 storage encryption should be enabled at bucket level (user responsibility)
- No additional encryption layer added at application level
- Consider adding application-level encryption for secrets in future (see Future Considerations)

## Backward Compatibility

**Old backups → New system**: Restoration will detect absence of `.secret/` folder and only restore working directory. This is safe but incomplete (secrets must be reconfigured manually).

**New backups → Old system**: Not applicable (old system cannot read new format).

## Testing Strategy

1. **Unit tests**: Verify `_compress_user` includes `.secret/` folder
2. **Unit tests**: Verify `_extract_zip` routes `.secret/` entries correctly
3. **Integration tests**: Full backup/restore cycle with secret files
4. **Edge case tests**: Missing secret dir, empty secret dir, old backup restoration

## Future Considerations

- If selective backup/restore of secrets becomes needed, a query parameter could be added
- If encryption at rest is required beyond S3-level, consider encrypting `.secret/` contents with a user-provided passphrase

## Approval

Approved by: shixiangyi
Date: 2026-03-23
