# Homepage Content Management Setup

## Overview

The CTO Dashboard homepage uses a modular content management system that allows easy updates through JSON configuration files or an optional admin interface.

## Content Structure

All homepage content is stored in `config/homepage_content.json` with the following sections:

- **Hero**: Main headline, subheadline, CTA button
- **Problem**: Challenge statements for target audience  
- **Solution**: Attention Engine explanation
- **Features**: Product feature cards with icons and descriptions
- **Daily Brief**: Example briefing items with status indicators
- **Pricing**: Pricing plans with features and CTAs
- **Footer**: Navigation links, social links, copyright

## Manual Content Updates

### Quick Updates
Edit `config/homepage_content.json` directly:

```bash
# Edit the configuration file
nano config/homepage_content.json

# Restart the application to pick up changes
./venv/bin/python integrated_dashboard.py
```

### Content Validation
The system automatically validates content structure to ensure the homepage remains functional. Required fields include:

- Hero: `headline`, `subheadline`, `cta_text`, `cta_link`
- Pricing: `plans` array with `name`, `price`, `description`, `features`, `cta`

## Admin Interface (Optional)

### Enable Admin Interface

Set environment variables:

```bash
# Enable the admin interface
export ENABLE_HOMEPAGE_ADMIN=true

# Set admin password (default: admin123)
export HOMEPAGE_ADMIN_PASSWORD=your_secure_password
```

### Access Admin Interface

1. Navigate to `/admin/homepage`
2. Login with the configured password
3. Edit content sections individually or use advanced JSON editor
4. Changes are automatically saved with backups

### Admin Interface Features

- **Section Editor**: Edit individual content sections with validation
- **Advanced Mode**: Direct JSON editing for power users
- **Content Export**: Download content as JSON backup
- **Auto-backup**: Automatic backup creation before updates
- **Validation**: Real-time JSON structure validation

### Disable Admin Interface

```bash
# Disable admin interface
export ENABLE_HOMEPAGE_ADMIN=false
# or simply omit the environment variable
```

When disabled:
- `/admin/homepage` returns 404
- Admin login routes are inaccessible
- Reduces attack surface for production deployments

## Integration with Flask App

Add homepage routes to your Flask application:

```python
# In integrated_dashboard.py or main app file
from routes.homepage_routes import homepage_bp

app.register_blueprint(homepage_bp)
```

## Content Management Service

The `HomepageService` class provides programmatic access:

```python
from services.homepage_service import homepage_service

# Get all content
content = homepage_service.get_content()

# Get specific section
hero_content = homepage_service.get_section('hero')

# Update section
new_hero = {
    "headline": "New headline",
    "subheadline": "New subheadline",
    "cta_text": "New CTA",
    "cta_link": "/new-link"
}
homepage_service.update_section('hero', new_hero)

# Update all content
homepage_service.update_content(full_content_dict)
```

## Responsive Design

The homepage template (`templates/homepage.html`) is fully responsive:

- **Mobile-first**: Optimized for mobile devices
- **Breakpoints**: Tailwind CSS responsive utilities
- **Touch-friendly**: Appropriate button sizes and spacing
- **Performance**: Optimized images and minimal JavaScript

## Security Considerations

### Admin Interface Security

- Simple password protection (enhance with proper auth as needed)
- Session-based authentication
- CSRF protection recommended for production
- Input validation and JSON structure checking

### Content Validation

- Prevents malicious JSON injection
- Validates required fields before saving
- Automatic backup and restore on failure
- File permission restrictions

## Production Deployment

### Recommended Settings

```bash
# Production environment variables
export ENABLE_HOMEPAGE_ADMIN=false  # Disable admin interface
export HOMEPAGE_ADMIN_PASSWORD=very_secure_password  # If enabled
```

### Content Updates in Production

1. **Manual Method**: Edit JSON file directly on server
2. **Deploy Method**: Update JSON in repository and redeploy
3. **Admin Interface**: Enable temporarily for updates, then disable

### Backup Strategy

- Automatic backups created before updates
- Export content regularly for version control
- Consider keeping JSON in repository for deployment consistency

## Troubleshooting

### Common Issues

1. **Invalid JSON**: Check syntax with JSON validator
2. **Missing Sections**: Ensure all required sections are present
3. **Failed Updates**: Check file permissions on config directory
4. **Admin Access**: Verify environment variables and password

### Recovery

If content becomes corrupted:

1. Restore from automatic backup (`config/homepage_content.json.backup`)
2. Use exported JSON backup
3. Reset to default content (service will create fallback)

### Logs

Check application logs for content update errors:

```bash
# View recent logs
tail -f logs/app.log | grep homepage
```

## Customization

### Adding New Sections

1. Update JSON structure with new section
2. Modify `templates/homepage.html` to render new section
3. Update validation in `HomepageService._validate_content()`
4. Add section info to `get_editable_sections()`

### Styling Changes

- Modify CSS in `templates/homepage.html` `<style>` section
- Adjust Tailwind classes for different appearance
- Update color schemes and animations as needed

### Content Schema

The JSON schema is flexible but follows this structure:

```json
{
  "section_name": {
    "title": "Section Title",
    "items": [...],
    "cta": {"text": "Button Text", "link": "/link"}
  }
}
```

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_HOMEPAGE_ADMIN` | `false` | Enable/disable admin interface |
| `HOMEPAGE_ADMIN_PASSWORD` | `admin123` | Password for admin access |

## File Structure

```
├── config/
│   ├── homepage_content.json      # Main content configuration
│   └── homepage_content.json.backup  # Automatic backup
├── services/
│   └── homepage_service.py        # Content management service
├── routes/
│   └── homepage_routes.py         # Flask routes and API endpoints
├── templates/
│   ├── homepage.html             # Main homepage template
│   ├── homepage_admin.html       # Admin interface template
│   └── admin_login.html          # Simple admin login
└── docs/
    └── HOMEPAGE-SETUP.md         # This documentation
```