# JSON Template Combiner

A GUI application built with Python and CustomTkinter for combining multiple JSON template sources into a single `templates.json` file for Container Station or Portainer.

## Features

- **Multiple Source Support**: Load JSON data from URLs and local files
- **Docker Compose Support**: Convert Docker Compose YAML files to Portainer templates
- **Configurable Base Template**: Set custom base template URL or disable auto-loading
- **Manual Template Creation**: Create templates from scratch using a comprehensive form interface
- **Template Editing**: Edit individual templates from any loaded source
- **Smart Category Management**: Dropdown with categories extracted from loaded sources
- **Smart Deduplication**: Automatically detects and handles duplicate templates based on 70% similarity threshold
- **Architecture Detection**: Identifies different architectures (arm64, amd64, 386, linux) and creates variants
- **Template Validation**: Validates JSON structure and template completeness
- **User-Friendly GUI**: Intuitive tabbed interface with progress tracking
- **Preview Functionality**: Shows processing summary and final template before saving
- **Error Handling**: Comprehensive error handling with user feedback

## Requirements

- Python 3.7 or higher
- Internet connection (for loading URL sources)

## Installation

1. **Clone or download the project**:
   ```bash
   cd "C:\Users\r_sta\Downloads\projects\python\JSON Template Combiner"
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python main.py
   ```

## Usage

### 1. Sources Tab
- **Add URL Sources**: Enter JSON URLs (like GitHub raw content or API endpoints)
  - Example: `https://github.com/qnap-dev/container-apps/blob/2.0/ai.json`
- **Add Local Files**: Browse and select template files from your computer
  - **JSON files**: Standard Portainer templates or QNAP format
  - **YAML files**: Docker Compose files (docker-compose.yml, compose.yaml, etc.)
  - **Auto-detection**: Automatically detects and converts file formats
- **Manage Sources**: Remove unwanted sources from the lists
- **Base Template Configuration**: Configure custom base template URL or disable auto-loading
- **Load & Process**: Click to load all sources and extract templates

### 2. Manual Entry Tab
- **Create Templates**: Build templates from scratch using comprehensive form fields
- **Required Fields**: Title and Image are mandatory
- **Smart Categories**: Dropdown populated with categories from loaded sources
- **Optional Fields**: Description, Logo, Platform, Categories, Environment Variables, Ports, Volumes, Notes
- **Template Management**: Edit, delete, and organize manually created templates
- **Form Validation**: Ensures all required fields are completed before adding templates

### 3. Edit Templates Tab
- **Browse All Templates**: View templates from all loaded sources in one place
- **Filter and Search**: Find templates by title, image, description, or source
- **Edit Individual Templates**: Load any template into the manual entry form for editing
- **Clone Templates**: Create copies of existing templates with modifications
- **View JSON**: Inspect the raw JSON structure of any template
- **Source Identification**: See which source each template came from

### 4. Preview Tab
- **Processing Summary**: View how many templates were found from each source (including manual entries)
- **Generate Template**: Combine all templates with deduplication
- **Template Preview**: View the final JSON structure before saving

### 5. Save Tab
- **Choose Location**: Select where to save the final `templates.json`
- **Save Template**: Export the combined template file

## How It Works

### Template Comparison
The application compares templates using multiple criteria:
1. **Title similarity** (30% weight)
2. **Image similarity** (25% weight)
3. **Description similarity** (20% weight)
4. **Compose file content** (15% weight)
5. **Environment variables** (10% weight)

### Duplicate Handling
- Templates with 70%+ similarity are considered duplicates
- Different architectures are detected and saved as variants (e.g., `httpd-arm64`, `httpd-amd64`)
- For identical templates, the highest quality one is kept based on:
  - Completeness of required fields
  - Number of environment variables, ports, volumes
  - Presence of compose files

### Architecture Detection
The application detects architecture from:
- `platform` field in template
- Image tags (e.g., `nginx:latest-arm64`)
- Compose file content
- Defaults to `linux` if not detected

## Supported Source Formats

The application supports multiple file formats and automatically converts them to Portainer templates:

### JSON Formats

1. **Portainer Template Format**:
   ```json
   {
     "version": "2",
     "templates": [...]
   }
   ```

2. **QNAP Container Station Format**:
   ```json
   [
     {
       "displayName": "App Name",
       "name": "image/name",
       "version": "tag",
       "description": "Description"
     }
   ]
   ```

3. **Template Array Format**:
   ```json
   [
     { "title": "App1", ... },
     { "title": "App2", ... }
   ]
   ```

### YAML Formats

4. **Docker Compose Format**:
   ```yaml
   version: '3.8'
   services:
     nginx:
       image: nginx:latest
       ports:
         - "80:80"
       volumes:
         - ./html:/usr/share/nginx/html
       restart: unless-stopped
       environment:
         - NGINX_HOST=localhost
     mysql:
       image: mysql:8.0
       ports:
         - "3306:3306"
       environment:
         MYSQL_ROOT_PASSWORD: rootpass
         MYSQL_DATABASE: testdb
       volumes:
         - mysql_data:/var/lib/mysql
   ```

**Docker Compose Conversion Features**:
- Each service becomes a separate template
- Automatic category detection based on image name
- Port mapping conversion (host:container → Portainer format)
- Volume mapping conversion (including named volumes)
- Environment variable conversion
- Restart policy mapping
- Service name → template title conversion

## Example Sources

Pre-configured to work with:
- https://templates-portainer.ibaraki.app (base template)
- https://github.com/qnap-dev/container-apps/blob/2.0/ai.json
- https://github.com/qnap-dev/container-apps/blob/2.0/list.json
- https://github.com/qnap-dev/container-apps/blob/2.0/iot.json

## Error Handling

The application includes comprehensive error handling for:
- Network connectivity issues
- Invalid JSON format
- Missing required fields
- File access permissions
- URL accessibility

## Output Format

The generated `templates.json` follows the Portainer template specification:
```json
{
  "version": "2",
  "templates": [
    {
      "title": "Application Name",
      "description": "Application description",
      "image": "docker/image:tag",
      "categories": ["category1"],
      "platform": "linux",
      "ports": [...],
      "env": [...],
      "volumes": [...]
    }
  ]
}
```

## Troubleshooting

### Common Issues

1. **"Error loading URL"**: Check internet connection and URL accessibility
2. **"Invalid JSON format"**: Ensure source files are valid JSON
3. **"Permission denied"**: Run as administrator or check file permissions
4. **"Module not found"**: Install requirements with `pip install -r requirements.txt`

### Debug Mode
Check console output for detailed error messages and processing logs.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for improvements.

## License

This project is open source and available under the MIT License.
