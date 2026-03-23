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

#### 1. `_compress_user()` - Add secret directory compression

When compressing a user directory, also compress the corresponding secret directory contents into a `.secret/` folder within the zip.

**Logic**:
- Get secret directory via `get_secret_dir(user_id)`
- If secret directory exists, iterate and add files under `.secret/` prefix
- Handle empty directories by writing directory entries

#### 2. `_extract_zip()` - Handle `.secret/` extraction

When extracting a backup zip, detect files under `.secret/` prefix and route them to the secret directory instead of the working directory.

**Logic**:
- Parse zip file entries
- Entries starting with `.secret/` → extract to `secret_dir`
- Other entries → extract to `user_dir` (existing behavior)
- Remove `.secret/` prefix when extracting to maintain internal structure

#### 3. `_create_rollback_backup()` - Include secrets in rollback

Ensure rollback backups also capture secret directory state for complete rollback capability.

#### 4. Helper Addition

Add `_get_secret_dir(user_id)` helper method to resolve secret directory paths consistently.

### Edge Cases

| Scenario | Handling |
|----------|----------|
| Secret directory does not exist | Skip silently, continue backup |
| Secret directory is empty | Create empty `.secret/` entry in zip |
| Restoring old backup without `.secret/` | Only restore working directory contents |
| Permission errors on secret files | Log warning, continue with other files |
| Secret file path traversal | Validate extracted paths under target directory |

### Security Considerations

- Secret contents are backed up in the same encrypted zip (zip compression level 6)
- S3 transmission uses TLS encryption (handled by boto3)
- S3 storage encryption should be enabled at bucket level (user responsibility)
- No additional encryption layer added at application level

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
