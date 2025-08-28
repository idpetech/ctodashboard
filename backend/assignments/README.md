# Assignment Configuration Files

This directory contains JSON configuration files for each assignment/project.

## File Structure
- `{assignment-id}.json` - Active assignments
- `archived/` - Archived assignments (moved here when projects end)

## Adding New Assignments
1. Copy `template.json` to `{new-assignment-id}.json`
2. Update all fields with actual values
3. Configure metrics_config for the platforms you want to track
4. Restart backend or it will auto-reload

## Template Fields
- `id`: Unique identifier (used in URLs)
- `name`: Display name
- `status`: "active" or "archived"  
- `metrics_config`: Configure which platforms to integrate with
- `team`: Team composition and tech stack

## Environment Variables Required
See `.env.example` for required API tokens for each service.

## Migration to Database
These JSON files will be migrated to SQLite database in future versions while maintaining the same structure.