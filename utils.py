"""
Utility functions for JSON Template Combiner
"""

import json
import os
import requests
from typing import Dict, Any, Optional
from urllib.parse import urlparse


class ConfigManager:
    """Manages application configuration"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")
        
        # Return default config if file doesn't exist or is invalid
        return self.get_default_config()
    
    def save_config(self) -> bool:
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "default_sources": {
                "urls": [
                    "https://templates-portainer.ibaraki.app"
                ],
                "files": []
            },
            "settings": {
                "similarity_threshold": 0.7,
                "request_timeout": 30,
                "default_output_filename": "templates.json",
                "auto_detect_architecture": True,
                "preserve_source_order": False
            },
            "ui_settings": {
                "theme": "System",
                "color_theme": "blue",
                "window_size": "900x700"
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value


class TemplateConverter:
    """Converts different template formats to Portainer format"""
    
    @staticmethod
    def detect_format(data: Any) -> str:
        """Detect the format of the JSON data"""
        if isinstance(data, dict):
            # Check for Portainer format
            if 'templates' in data and 'version' in data:
                return 'portainer'
            # Check for single template
            elif 'title' in data or 'image' in data:
                return 'portainer_single'
            # Check for QNAP format (single template)
            elif 'displayName' in data and 'name' in data:
                return 'qnap_single'
            else:
                return 'unknown'
        elif isinstance(data, list):
            if len(data) > 0 and isinstance(data[0], dict):
                first_item = data[0]
                # Check if it's QNAP format
                if 'displayName' in first_item and 'name' in first_item:
                    return 'qnap_array'
                # Check if it's Portainer template array
                elif 'title' in first_item or 'image' in first_item:
                    return 'portainer_array'
            return 'unknown'
        
        return 'unknown'
    
    @staticmethod
    def convert_to_portainer(data: Any) -> Dict[str, Any]:
        """Convert any supported format to Portainer format"""
        format_type = TemplateConverter.detect_format(data)
        
        if format_type == 'portainer':
            return data
        elif format_type == 'portainer_single':
            return {"version": "2", "templates": [data]}
        elif format_type == 'portainer_array':
            return {"version": "2", "templates": data}
        elif format_type == 'qnap_single':
            converted = TemplateConverter._convert_qnap_template(data)
            return {"version": "2", "templates": [converted]}
        elif format_type == 'qnap_array':
            converted_templates = [TemplateConverter._convert_qnap_template(item) for item in data]
            return {"version": "2", "templates": converted_templates}
        else:
            raise ValueError(f"Unsupported template format: {format_type}")
    
    @staticmethod
    def _convert_qnap_template(qnap_template: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a single QNAP template to Portainer format"""
        portainer_template = {}
        
        # Map basic fields
        if 'displayName' in qnap_template:
            portainer_template['title'] = qnap_template['displayName']
        
        if 'description' in qnap_template:
            portainer_template['description'] = qnap_template['description']
        
        # Create image field from name and version
        if 'name' in qnap_template:
            image = qnap_template['name']
            if 'version' in qnap_template:
                image += f":{qnap_template['version']}"
            portainer_template['image'] = image
        
        # Map icon to logo
        if 'icon' in qnap_template:
            portainer_template['logo'] = qnap_template['icon']
        
        # Map type to categories
        if 'type' in qnap_template:
            portainer_template['categories'] = [qnap_template['type']]
        
        # Map arch to platform
        if 'arch' in qnap_template:
            arch_mapping = {
                'amd64': 'linux',
                'arm64': 'linux',
                'arm': 'linux',
                '386': 'linux',
                'x86_64': 'linux'
            }
            portainer_template['platform'] = arch_mapping.get(qnap_template['arch'], 'linux')
            
            # If architecture is specific, add it to the title for differentiation
            if qnap_template['arch'] in ['arm64', 'arm', '386']:
                original_title = portainer_template.get('title', '')
                portainer_template['title'] = f"{original_title} ({qnap_template['arch']})"
        
        # Add location as note if available
        if 'location' in qnap_template:
            note_text = f"Source: {qnap_template['location']}"
            if 'qcsVersion' in qnap_template:
                note_text += f" (QCS Version: {qnap_template['qcsVersion']})"
            portainer_template['note'] = note_text
        
        # Set default restart policy
        portainer_template['restart_policy'] = 'unless-stopped'
        
        # Add repository info if it's dockerhub
        if qnap_template.get('repository') == 'dockerhub' and 'location' in qnap_template:
            portainer_template['repository'] = {
                'url': qnap_template['location'],
                'stackfile': ''
            }
        
        return portainer_template


class JSONValidator:
    """Validates JSON template structures"""
    
    @staticmethod
    def is_valid_template_structure(data: Any) -> bool:
        """Check if data has a valid template structure"""
        try:
            format_type = TemplateConverter.detect_format(data)
            return format_type != 'unknown'
        except:
            return False
    
    @staticmethod
    def extract_templates(data: Any) -> list:
        """Extract templates from various JSON structures"""
        try:
            # Convert to Portainer format first
            portainer_data = TemplateConverter.convert_to_portainer(data)
            return portainer_data.get('templates', [])
        except:
            # Fallback to old method
            if isinstance(data, dict):
                if 'templates' in data and isinstance(data['templates'], list):
                    return data['templates']
                elif 'title' in data or 'image' in data:
                    return [data]
            elif isinstance(data, list):
                return data
            
            return []
    
    @staticmethod
    def validate_template(template: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean a single template"""
        if not isinstance(template, dict):
            raise ValueError("Template must be a dictionary")
        
        # Check for required fields
        if 'title' not in template and 'image' not in template:
            raise ValueError("Template must have at least a 'title' or 'image' field")
        
        # Clean up the template
        cleaned = {}
        
        # Copy standard fields
        standard_fields = [
            'title', 'description', 'image', 'logo', 'categories', 'platform',
            'restart_policy', 'ports', 'volumes', 'env', 'labels', 'repository',
            'note', 'type', 'administrator_only', 'hostname'
        ]
        
        for field in standard_fields:
            if field in template:
                cleaned[field] = template[field]
        
        return cleaned


class NetworkUtils:
    """Network utility functions"""
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if URL is valid"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    @staticmethod
    def fetch_json(url: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """Fetch JSON from URL"""
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error: {str(e)}")


class FileUtils:
    """File utility functions"""
    
    @staticmethod
    def load_json_file(file_path: str) -> Dict[str, Any]:
        """Load JSON from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise Exception(f"File not found: {file_path}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON in file: {str(e)}")
        except Exception as e:
            raise Exception(f"Error reading file: {str(e)}")
    
    @staticmethod
    def save_json_file(data: Any, file_path: str) -> None:
        """Save data as JSON file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"Error saving file: {str(e)}")
    
    @staticmethod
    def ensure_json_extension(filename: str) -> str:
        """Ensure filename has .json extension"""
        if not filename.lower().endswith('.json'):
            return f"{filename}.json"
        return filename


class TemplateUtils:
    """Template processing utilities"""
    
    @staticmethod
    def normalize_template_title(title: str) -> str:
        """Normalize template title for comparison"""
        if not title:
            return ""
        
        # Remove extra whitespace and convert to lowercase
        normalized = ' '.join(title.strip().split()).lower()
        
        # Remove common prefixes/suffixes
        prefixes = ['docker-', 'container-']
        suffixes = ['-container', '-docker', ' container', ' docker']
        
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break
        
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
                break
        
        return normalized.strip()
    
    @staticmethod
    def extract_image_name(image: str) -> str:
        """Extract clean image name from Docker image string"""
        if not image:
            return ""
        
        # Remove registry and tag
        parts = image.split('/')
        image_name = parts[-1]  # Get the last part (image name)
        
        # Remove tag if present
        if ':' in image_name:
            image_name = image_name.split(':')[0]
        
        return image_name.lower()
    
    @staticmethod
    def get_template_quality_score(template: Dict[str, Any]) -> int:
        """Calculate quality score for template prioritization"""
        score = 0
        
        # Essential fields
        if template.get('title'):
            score += 20
        if template.get('description'):
            score += 15
        if template.get('image'):
            score += 25
        
        # Optional but valuable fields
        if template.get('logo'):
            score += 5
        if template.get('categories'):
            score += 5
        if template.get('platform'):
            score += 3
        
        # Configuration complexity (more is better)
        env_vars = template.get('env', [])
        if isinstance(env_vars, list):
            score += min(len(env_vars), 10)  # Cap at 10 points
        
        ports = template.get('ports', [])
        if isinstance(ports, list):
            score += min(len(ports) * 2, 10)  # Cap at 10 points
        
        volumes = template.get('volumes', [])
        if isinstance(volumes, list):
            score += min(len(volumes) * 2, 10)  # Cap at 10 points
        
        # Repository/compose content
        repo = template.get('repository')
        if repo and isinstance(repo, dict):
            if repo.get('stackfile'):
                score += 20
            if repo.get('url'):
                score += 5
        
        # Penalty for missing critical fields
        if not template.get('image'):
            score -= 30
        if not template.get('title'):
            score -= 20
        
        return max(score, 0)  # Ensure non-negative score
