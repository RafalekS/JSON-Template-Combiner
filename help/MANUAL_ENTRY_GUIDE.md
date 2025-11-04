# Manual Template Entry Guide

The Manual Entry tab allows you to create container templates from scratch without needing external JSON sources. This is perfect for creating custom templates or adding unique configurations to your template collection.

## Getting Started

1. **Navigate to Manual Entry Tab**: Click on the "Manual Entry" tab in the application
2. **Fill Required Fields**: At minimum, provide a Title and Image
3. **Add Optional Configuration**: Customize with additional fields as needed
4. **Add Template**: Click "Add Template" to save your creation

## Field Reference

### Required Fields

#### Title*
- **Purpose**: Display name for the template
- **Example**: `Nginx Web Server`, `Custom Database`, `My Application`
- **Guidelines**: Keep it descriptive and unique

#### Image*
- **Purpose**: Docker image to use for the container
- **Example**: `nginx:latest`, `postgres:13`, `myregistry/myapp:v1.0`
- **Guidelines**: Use full image names with tags when possible

### Basic Information

#### Description
- **Purpose**: Brief explanation of what the application does
- **Example**: `High-performance web server and reverse proxy`
- **Guidelines**: Keep it concise but informative

#### Logo URL
- **Purpose**: Icon displayed in Container Station/Portainer
- **Example**: `https://example.com/logos/nginx.png`
- **Guidelines**: Use public URLs, PNG/SVG preferred

#### Platform
- **Options**: `linux` (default), `windows`
- **Purpose**: Target operating system for the container

#### Restart Policy
- **Options**: `unless-stopped` (default), `always`, `no`, `on-failure`
- **Purpose**: When to restart the container automatically

### Configuration Arrays

#### Categories
- **Purpose**: Group templates by type/function
- **Examples**: `webserver`, `database`, `monitoring`, `media`
- **How to Add**: Type category name and click "Add"
- **Guidelines**: Use lowercase, single words when possible

#### Environment Variables
- **Purpose**: Configure application settings
- **Format**: Name = Value
- **Examples**: 
  - `MYSQL_ROOT_PASSWORD` = `mysecretpassword`
  - `NODE_ENV` = `production`
  - `DEBUG` = `true`
- **Guidelines**: Use descriptive variable names

#### Ports
- **Purpose**: Expose container ports to host
- **Format**: Label: Port/Protocol
- **Examples**:
  - `WebUI: 80/tcp`
  - `Database: 5432/tcp`
  - `SSH: 22/tcp`
- **Guidelines**: Use descriptive labels

#### Volumes
- **Purpose**: Persist data and share files between host and container
- **Format**: Container Path -> Host/Bind Path
- **Examples**:
  - `/var/www/html` -> `!data/nginx`
  - `/var/lib/mysql` -> `!data/mysql`
  - `/app/config` -> `!config/app`
- **Guidelines**: Use `!data/` prefix for data directories

### Additional Options

#### Note
- **Purpose**: Additional instructions or important information
- **Example**: `Make sure to set a strong password for MYSQL_ROOT_PASSWORD`
- **Guidelines**: Include setup tips or warnings

#### Administrator Only
- **Purpose**: Restrict template to admin users only
- **When to Use**: For system-level services or sensitive applications

## Step-by-Step Examples

### Example 1: Simple Web Server

1. **Basic Info**:
   - Title: `My Web Server`
   - Description: `Custom web server for my website`
   - Image: `nginx:alpine`

2. **Add Category**:
   - Type `webserver` and click "Add"

3. **Add Port**:
   - Label: `WebUI`
   - Port: `80/tcp`
   - Click "Add"

4. **Add Volume**:
   - Container: `/usr/share/nginx/html`
   - Bind: `!data/website`
   - Click "Add"

5. **Click "Add Template"**

### Example 2: Database with Configuration

1. **Basic Info**:
   - Title: `PostgreSQL Database`
   - Description: `PostgreSQL database server`
   - Image: `postgres:13`

2. **Add Categories**:
   - `database`
   - `postgres`

3. **Add Environment Variables**:
   - `POSTGRES_DB` = `myapp`
   - `POSTGRES_USER` = `admin`
   - `POSTGRES_PASSWORD` = `changeme`

4. **Add Port**:
   - Label: `Database`
   - Port: `5432/tcp`

5. **Add Volume**:
   - Container: `/var/lib/postgresql/data`
   - Bind: `!data/postgres`

6. **Add Note**: `Remember to change the default password`

7. **Click "Add Template"**

## Template Management

### Editing Templates
1. Select a template from "Created Templates" list
2. Click "Edit Selected"
3. Form will populate with existing values
4. Make your changes
5. Click "Add Template" to save changes

### Deleting Templates
1. Select a template from "Created Templates" list
2. Click "Delete Selected"
3. Confirm deletion in the dialog

### Clearing the Form
- Click "Clear Form" to reset all fields to defaults
- Useful when starting a new template from scratch

## Best Practices

### Naming Conventions
- **Templates**: Use descriptive titles (`Nginx Web Server` not `nginx`)
- **Categories**: Use lowercase, standardized terms (`webserver`, `database`)
- **Environment Variables**: Use UPPERCASE with underscores (`MY_APP_CONFIG`)
- **Port Labels**: Use descriptive names (`WebUI`, `Database`, `Admin Panel`)

### Security Considerations
- Never use default passwords in production
- Use environment variables for sensitive configuration
- Enable "Administrator Only" for system services
- Include security notes in the Note field

### Organization Tips
- Group related templates with consistent categories
- Use consistent naming patterns within your organization
- Document custom configurations in the Note field
- Test templates in a development environment first

## Integration with Other Sources

Manual templates are combined with loaded sources during the generation process:

1. **Processing Order**: Manual templates are processed first
2. **Deduplication**: Manual templates participate in similarity checking
3. **Priority**: Manual templates are treated equally with loaded templates
4. **Final Output**: All templates (manual + loaded) are combined into one file

## Validation and Error Handling

The application validates manual templates:

- **Required Fields**: Title and Image must be provided
- **Format Checking**: URLs and values are validated where possible
- **Duplicate Prevention**: Similar templates will be flagged during generation
- **Error Messages**: Clear feedback for validation failures

## Tips for Advanced Users

### Custom Images
- Use private registries: `myregistry.com/myapp:latest`
- Tag specific versions: `nginx:1.21-alpine`
- Include digests for security: `nginx@sha256:abc123...`

### Advanced Port Configurations
- Multiple protocols: `8080/tcp`, `53/udp`
- Port ranges: `8000-8100/tcp`
- Host-specific bindings: `127.0.0.1:8080:80/tcp`

### Complex Volume Mappings
- Named volumes: `myvolume:/data`
- Read-only mounts: `/config:ro`
- Temporary filesystems: `tmpfs:/tmp`

### Environment Variable Patterns
- Configuration files: `CONFIG_FILE=/app/config.yml`
- Feature flags: `ENABLE_LOGGING=true`
- Service endpoints: `DATABASE_URL=postgres://user:pass@host:port/db`

## Troubleshooting

### Common Issues

**Template not appearing in final output**
- Check that you clicked "Add Template" after filling the form
- Verify the template appears in "Created Templates" list
- Ensure you clicked "Generate Final Template" in Preview tab

**Validation errors**
- Title and Image are required fields
- Check for special characters in field values
- Ensure URLs are properly formatted

**Duplicate templates**
- Manual templates are subject to deduplication rules
- Check the 70% similarity threshold in Preview tab
- Consider using different architectures or versions to differentiate

### Getting Help

If you encounter issues with manual template creation:

1. Check the application logs/console for error messages
2. Verify all required fields are completed
3. Test with a simple template first (just Title and Image)
4. Review this guide for proper field formats
5. Check the main README.md for general troubleshooting

---

The Manual Entry feature makes the JSON Template Combiner a complete solution for both importing existing templates and creating custom ones from scratch. Whether you're adapting existing applications or building entirely new container configurations, this interface provides the flexibility you need.
