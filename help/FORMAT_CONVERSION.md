# JSON Template Converter - QNAP Format Support

This document explains how the application handles different JSON template formats and converts them to the standard Portainer format.

## Supported Input Formats

### 1. Portainer Standard Format
```json
{
  "version": "2",
  "templates": [
    {
      "title": "Nginx",
      "description": "High performance web server",
      "image": "nginx:latest",
      "categories": ["webserver"],
      "platform": "linux"
    }
  ]
}
```

### 2. QNAP Container Station Format
```json
[
  {
    "description": "This is a photo recognition demo version generated using CAFFE deep learning framework.",
    "repository": "dockerhub",
    "arch": "amd64",
    "icon": "https://raw.githubusercontent.com/qnap-dev/container-apps/2.0/images/ai_default.png",
    "displayName": "CAFFE Demo - GPU",
    "name": "qnapnas/caffedemo",
    "version": "0.1beta-gpu",
    "location": "https://hub.docker.com/r/qnapnas/caffedemo/",
    "type": "ai",
    "qcsVersion": "2.0"
  }
]
```

## Conversion Mapping

When converting QNAP format to Portainer format, the following field mappings are applied:

| QNAP Field | Portainer Field | Notes |
|------------|-----------------|-------|
| `displayName` | `title` | Direct mapping |
| `description` | `description` | Direct mapping |
| `name` + `version` | `image` | Combined as `name:version` |
| `icon` | `logo` | Direct mapping |
| `type` | `categories` | Converted to array format |
| `arch` | `platform` | Mapped to "linux" with architecture noted in title if specific |
| `location` | `note` | Added as reference note |
| `repository` | `repository` | Only if dockerhub |

## Example Conversion

### Input (QNAP Format):
```json
{
  "description": "This is a photo recognition demo version generated using CAFFE deep learning framework.",
  "repository": "dockerhub",
  "arch": "amd64",
  "icon": "https://raw.githubusercontent.com/qnap-dev/container-apps/2.0/images/ai_default.png",
  "displayName": "CAFFE Demo - GPU",
  "name": "qnapnas/caffedemo",
  "version": "0.1beta-gpu",
  "location": "https://hub.docker.com/r/qnapnas/caffedemo/",
  "type": "ai",
  "qcsVersion": "2.0"
}
```

### Output (Portainer Format):
```json
{
  "title": "CAFFE Demo - GPU",
  "description": "This is a photo recognition demo version generated using CAFFE deep learning framework.",
  "image": "qnapnas/caffedemo:0.1beta-gpu",
  "logo": "https://raw.githubusercontent.com/qnap-dev/container-apps/2.0/images/ai_default.png",
  "categories": ["ai"],
  "platform": "linux",
  "restart_policy": "unless-stopped",
  "note": "Source: https://hub.docker.com/r/qnapnas/caffedemo/ (QCS Version: 2.0)",
  "repository": {
    "url": "https://hub.docker.com/r/qnapnas/caffedemo/",
    "stackfile": ""
  }
}
```

## Architecture Handling

For architecture-specific templates (arm64, arm, 386), the architecture is added to the title for differentiation:

### Input:
```json
{
  "displayName": "Nginx",
  "name": "nginx",
  "arch": "arm64"
}
```

### Output:
```json
{
  "title": "Nginx (arm64)",
  "image": "nginx",
  "platform": "linux"
}
```

## Error Handling

If conversion fails:
1. The application logs the conversion error
2. Attempts to store the original format
3. Uses fallback extraction methods
4. Continues processing other sources

## Supported Sources

The application can automatically detect and convert:
- QNAP Container Station JSON files
- Portainer template files
- Template arrays
- Single template objects
- Mixed format collections

This ensures compatibility with various container template repositories while maintaining the standard Portainer output format.
