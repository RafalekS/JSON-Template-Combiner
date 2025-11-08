# JSON Template Combiner

A professional GUI application built with PyQt6 for combining multiple JSON template sources into a single `templates.json` file for Container Station or Portainer. Features a clean Qt Designer-based interface with full functionality for template management, editing, and export.

## Features

- **Multiple Source Support**: Load JSON data from URLs and local files
- **Manual Template Entry**: Create or import individual templates through an intuitive form interface
- **Template Editing**: Edit existing templates with a comprehensive editor
- **Smart Deduplication**: Automatically detects and handles duplicate templates based on 70% similarity threshold
- **Architecture Detection**: Identifies different architectures (arm64, amd64, 386, linux) and creates variants
- **Template Validation**: Validates JSON structure and template completeness
- **Format Conversion**: Supports JSON, YAML, and Docker Compose formats
- **Preview Functionality**: Shows processing summary and final template before saving
- **Modern GUI**: PyQt6-based interface with .ui file separation for easy customization
- **Asynchronous Processing**: Worker threads for non-blocking operations
- **Error Handling**: Comprehensive error handling with user feedback

## Architecture

This application uses a modern PyQt6 architecture with clear separation of concerns:

- **PyQt6 Framework**: Modern Qt6 bindings for Python
- **UI/Logic Separation**: GUI defined in XML .ui files (Qt Designer compatible)
- **Worker Threads**: QThread-based async operations for responsive UI
- **Signal/Slot Pattern**: Event-driven communication between components
- **Config Management**: Centralized configuration in `config/` directory

## Requirements

- Python 3.7 or higher
- PyQt6 6.6.0 or higher
- Internet connection (for loading URL sources)

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/RafalekS/JSON-Template-Combiner.git
   cd JSON-Template-Combiner
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python main.py
   ```

## Usage Guide

### 1. Sources Tab

The Sources tab allows you to manage and load templates from multiple sources.

**URL Sources:**
- Add JSON template URLs (GitHub raw content, APIs, etc.)
- Example: `https://raw.githubusercontent.com/qnap-dev/container-apps/2.0/ai.json`
- Remove unwanted URLs from the list
- Bulk load all URL sources with one click

**Local File Sources:**
- Browse and add local JSON files from your computer
- Support for multiple file selection
- Remove unwanted files from the list
- Direct file path validation

**Loading & Processing:**
- "Load Templates" button: Fetches and processes all sources
- Progress indication during loading
- Error handling for failed sources
- Automatic template extraction and parsing
- Results displayed with count per source

### 2. Manual Entry Tab

Create or import individual templates through a comprehensive form interface.

**Template Information:**
- **Title**: Application name (required)
- **Description**: Detailed description of the application
- **Image**: Docker image name and tag (e.g., `nginx:latest`)
- **Platform**: Target architecture (linux, arm64, amd64, 386)
- **Logo**: URL to application logo/icon
- **Categories**: Comma-separated list (e.g., "Web Server, Proxy")
- **Note**: Additional notes or warnings

**Container Configuration:**
- **Ports**: Port mappings in format `host:container/protocol`
  - Example: `8080:80/tcp`
- **Environment Variables**: Key-value pairs for container environment
  - Name, Label, Default value, Description, Presets
- **Volumes**: Volume mount definitions
  - Container path and bind (host path)
- **Restart Policy**: Container restart behavior

**Docker Compose Support:**
- Import compose file content directly
- Repository URL and stackfile path
- Automatic parsing of compose configurations

**Actions:**
- **Add to Templates**: Validates and adds template to collection
- **Import from JSON**: Import a complete template from JSON file
- **Clear Form**: Reset all fields

### 3. Edit Templates Tab

Comprehensive template editing interface for modifying existing templates.

**Template Selection:**
- Dropdown list of all loaded templates
- Quick search and filter capabilities
- Load template into editor for modification

**Edit Capabilities:**
- All fields editable (same as Manual Entry tab)
- Real-time validation
- Preserve or modify existing configurations
- Update existing template in collection

**Template Management:**
- **Update Template**: Save changes to selected template
- **Delete Template**: Remove template from collection
- **Duplicate Template**: Create a copy for modification
- Undo/redo functionality

### 4. Preview Tab

View and analyze the combined template collection before saving.

**Processing Summary:**
- Total templates loaded from all sources
- Breakdown by source (URLs and local files)
- Count of templates from each source
- Duplicate detection statistics

**Template Generation:**
- "Generate Template" button: Combines all templates with smart deduplication
- Architecture variant detection and separation
- Similarity-based duplicate handling (70% threshold)
- Quality-based template selection

**Template Preview:**
- JSON preview of final combined template
- Formatted and syntax-highlighted display
- Scroll through entire template structure
- Verify before saving

**Deduplication Details:**
- Number of duplicates found and merged
- Architecture variants created (e.g., httpd-arm64, httpd-amd64)
- Quality scoring for duplicate resolution

### 5. Save Tab

Export the final combined template to a file.

**Save Options:**
- **Output Location**: Choose directory for `templates.json`
- **File Format**: JSON (Portainer format)
- **Validation**: Pre-save validation of template structure
- **Overwrite Protection**: Confirmation for existing files

**Save Actions:**
- "Choose Save Location" button: Browse for output directory
- "Save Template" button: Writes final template to file
- Success confirmation with file path
- Error handling for permission issues

## How It Works

### Template Comparison Algorithm

The application uses a sophisticated multi-factor comparison system:

1. **Title Similarity** (30% weight): Compares application titles using difflib sequence matching
2. **Image Similarity** (25% weight): Compares Docker image names and tags
3. **Description Similarity** (20% weight): Analyzes description text similarity
4. **Compose Content** (15% weight): Compares Docker Compose file content if available
5. **Environment Variables** (10% weight): Matches environment variable names and configurations

**Duplicate Threshold:** Templates with 70% or higher similarity are considered duplicates.

### Duplicate Handling Strategy

When duplicates are detected:

1. **Architecture Variants**: Different architectures are preserved as separate templates
   - Example: `nginx-arm64`, `nginx-amd64`, `nginx-linux`

2. **Quality Scoring**: For identical templates across architectures, quality is determined by:
   - Completeness of required fields (title, description, image)
   - Number and quality of environment variables
   - Port and volume configurations
   - Presence of Docker Compose files
   - Logo and category information

3. **Merge Strategy**:
   - Higher quality template is kept
   - Unique information from duplicates is preserved
   - Categories and notes are combined

### Architecture Detection

The application intelligently detects target architectures from:

- **Platform field**: Explicit platform specification in template
- **Image tags**: Parsing of architecture suffixes (e.g., `-arm64`, `-amd64`)
- **Compose content**: Architecture specifications in Docker Compose files
- **Default**: Falls back to `linux` if no architecture is detected

### Supported Source Formats

**1. Portainer Template Format:**
```json
{
  "version": "2",
  "templates": [
    {
      "title": "Application Name",
      "description": "Description",
      "image": "docker/image:tag",
      "categories": ["category1"],
      "platform": "linux",
      "ports": ["8080:80/tcp"],
      "env": [
        {
          "name": "VARIABLE_NAME",
          "label": "Variable Label",
          "default": "default_value"
        }
      ],
      "volumes": [
        {
          "container": "/data",
          "bind": "/host/path"
        }
      ]
    }
  ]
}
```

**2. Template Array Format:**
```json
[
  {
    "title": "App1",
    "image": "app1:latest",
    ...
  },
  {
    "title": "App2",
    "image": "app2:latest",
    ...
  }
]
```

**3. Docker Compose Format:**
```yaml
version: '3'
services:
  app:
    image: nginx:latest
    ports:
      - "8080:80"
    environment:
      - VAR=value
```

## Configuration

Configuration files are stored in the `config/` directory:

- **config.json**: Application settings and preferences
- **templates.json**: Saved template database
- **example_output.json**: Example output format reference
- **main_window_pyqt6.ui**: Qt Designer UI definition (XML)

### Theming

The application includes a professional theming system with multiple color schemes:

**Available Themes:**
- **Dark Theme**: VS Code-inspired dark theme with blue accents (default)
- **Light Theme**: Modern Windows-style light theme with blue accents

**Changing Themes:**
1. Open the application
2. Click **View** → **Theme** in the menu bar
3. Select your preferred theme (Dark or Light)
4. Theme choice is automatically saved and persists across sessions

**Theme Files:**
Themes are stored as QSS (Qt Style Sheets) files in the `themes/` directory:
- `themes/dark.qss` - Dark theme stylesheet
- `themes/light.qss` - Light theme stylesheet

**Creating Custom Themes:**
You can create your own themes by:
1. Copying an existing `.qss` file in the `themes/` directory
2. Modifying colors, fonts, and styling using QSS syntax (similar to CSS)
3. Saving with a new name (e.g., `custom.qss`)
4. Adding the theme name to `ThemeManager.AVAILABLE_THEMES` in `utils.py`

### Customizing the Interface

The GUI is defined in `config/main_window_pyqt6.ui` and can be edited with:
- **Qt Designer**: Visual editor for Qt interfaces
- **Direct XML editing**: Manual modifications to the .ui file

After modifying the .ui file, simply restart the application to see changes.

## Example Sources

Pre-configured to work with popular template repositories:

- `https://templates-portainer.ibaraki.app` (Community templates)
- `https://raw.githubusercontent.com/qnap-dev/container-apps/2.0/ai.json` (AI applications)
- `https://raw.githubusercontent.com/qnap-dev/container-apps/2.0/list.json` (General apps)
- `https://raw.githubusercontent.com/qnap-dev/container-apps/2.0/iot.json` (IoT applications)

## Error Handling

Comprehensive error handling for common issues:

- **Network Issues**: Timeout handling, retry logic, connection error messages
- **Invalid JSON**: Syntax validation, structure verification, helpful error messages
- **Missing Fields**: Template validation, required field checking
- **File Operations**: Permission checking, file access validation
- **URL Issues**: Reachability tests, redirect handling, HTTPS validation

## Output Format

The generated `templates.json` follows the Portainer v2 template specification:

```json
{
  "version": "2",
  "templates": [
    {
      "type": 1,
      "title": "Application Name",
      "description": "Application description",
      "image": "docker/image:tag",
      "categories": ["category1", "category2"],
      "platform": "linux",
      "logo": "https://example.com/logo.png",
      "ports": [
        "8080:80/tcp"
      ],
      "env": [
        {
          "name": "VARIABLE_NAME",
          "label": "Variable Label",
          "default": "default_value",
          "description": "Variable description"
        }
      ],
      "volumes": [
        {
          "container": "/data",
          "bind": "/host/path"
        }
      ],
      "restart_policy": "unless-stopped",
      "repository": {
        "url": "https://github.com/user/repo",
        "stackfile": "docker-compose.yml"
      }
    }
  ]
}
```

## Technical Details

### Project Structure

```
JSON-Template-Combiner/
├── config/                          # Configuration directory
│   ├── config.json                  # Application settings
│   ├── templates.json               # Template database
│   ├── example_output.json          # Example output
│   └── main_window_pyqt6.ui         # Qt Designer UI file
├── main.py                          # Application entry point
├── main_window.py                   # Main window class (1431 lines)
├── utils.py                         # Business logic utilities
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

### Key Components

**MainWindow Class (main_window.py)**
- 71 methods handling all application functionality
- Tab-based interface management
- Signal/slot connections for event handling
- Worker thread coordination

**Worker Threads:**
- `LoadTemplateWorker`: Asynchronous source loading
- `ProcessSourcesWorker`: Template extraction and processing
- `GenerateTemplateWorker`: Template combination and deduplication

**Utility Classes (utils.py):**
- `ConfigManager`: Settings persistence
- `TemplateConverter`: Format conversion (JSON/YAML/Compose)
- `JSONValidator`: Template structure validation
- `TemplateComparator`: Similarity calculation

## Troubleshooting

### Common Issues

**"Error loading URL"**
- Check internet connection
- Verify URL is accessible (try in browser)
- Check for firewall or proxy issues
- Ensure URL points to raw JSON content

**"Invalid JSON format"**
- Validate JSON syntax using online validator
- Check for trailing commas, missing brackets
- Ensure proper encoding (UTF-8)

**"Permission denied" (Windows)**
- Run as administrator if saving to protected directories
- Check antivirus isn't blocking file operations
- Verify write permissions on target directory

**"Module not found" error**
- Ensure all dependencies installed: `pip install -r requirements.txt`
- Check Python version (3.7+)
- Verify PyQt6 installation: `python -c "import PyQt6"`

**Application doesn't start**
- Check console for error messages
- Verify `config/main_window_pyqt6.ui` exists
- Ensure all Python files are in the same directory
- Try: `python -m py_compile main.py` to check syntax

### Debug Mode

Enable detailed logging by running:
```bash
python main.py --verbose
```

Console output includes:
- Source loading progress
- Template parsing details
- Similarity calculations
- Deduplication decisions
- Error stack traces

## Development

### Requirements
- Python 3.7+
- PyQt6 6.6.0+
- Qt Designer (optional, for UI editing)

### Modifying the UI
1. Open `config/main_window_pyqt6.ui` in Qt Designer
2. Make visual changes
3. Save the file
4. Restart the application

### Adding Features
1. Add business logic to `utils.py`
2. Add UI handlers to `main_window.py`
3. Update `config/main_window_pyqt6.ui` if needed
4. Test thoroughly with various template sources

### Theme Editor Tool

The project includes a **Visual Theme Editor** for creating and modifying themes without manually editing QSS code.

**Running the Theme Editor:**
```bash
python theme_editor.py
```

**Features:**
- **Visual Color Scheme Editor**: Click color buttons to choose colors with a color picker
- **Live Preview**: See your theme applied to sample widgets in real-time
- **QSS Code Editor**: View and edit the raw QSS code directly
- **Load/Save**: Open existing themes or create new ones
- **Auto-Generate**: Generate complete QSS from your color choices

**How to Use:**
1. Run `python theme_editor.py`
2. Load an existing theme from the dropdown (dark or light)
3. **Option A - Visual Editing:**
   - Click color buttons to change colors (Background, Primary, Border, etc.)
   - Click "Generate QSS from Colors" to create stylesheet
   - Click "Apply to Preview" to see changes in the preview panel
4. **Option B - Code Editing:**
   - Edit the QSS code directly in the text editor
   - Click "Apply to Preview" to see changes
5. Save your theme with File → Save or Save As

**Creating New Themes:**
1. Click "New Theme" button
2. Edit colors or QSS code
3. Save with a descriptive name (e.g., `my_theme.qss`)
4. Add theme name to `ThemeManager.AVAILABLE_THEMES` in `utils.py`
5. Restart the main application to use your new theme

**Tips:**
- Start by loading an existing theme (dark or light) as a base
- Use the color picker for consistent color schemes
- Test your theme in the preview panel before saving
- QSS syntax is similar to CSS for web pages

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is open source and available under the MIT License.

## Acknowledgments

- Built with PyQt6 for modern cross-platform GUI
- Template format based on Portainer specification
- Supports community template repositories

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing issues for solutions
- Provide detailed error messages and logs

---

**Version**: 2.0 (PyQt6 Edition)
**Last Updated**: 2025-11-04
