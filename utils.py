"""
Utility functions for JSON Template Combiner
"""

import json
import os
import requests
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import yaml


class ConfigManager:
    """Manages application configuration"""
    
    def __init__(self, config_file: str = "config/config.json"):
        self.config_file = config_file
        # Ensure config directory exists
        config_dir = os.path.dirname(self.config_file)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
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
            # Ensure config directory exists
            config_dir = os.path.dirname(self.config_file)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
            
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
            # Check for Docker Compose format
            if DockerComposeConverter.is_docker_compose_data(data):
                return 'docker_compose'
            # Check for Portainer format
            elif 'templates' in data and 'version' in data:
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
        elif format_type == 'docker_compose':
            return DockerComposeConverter.convert_compose_to_portainer(data)
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


class DockerComposeConverter:
    """Converts Docker Compose YAML files to Portainer template format"""
    
    @staticmethod
    def is_docker_compose_file(file_path: str) -> bool:
        """Check if file is a Docker Compose file based on extension and content"""
        if not file_path.lower().endswith(('.yml', '.yaml')):
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)
                
            # Check for Docker Compose indicators
            if isinstance(content, dict):
                # Check for version field or services field (common in docker-compose files)
                has_version = 'version' in content
                has_services = 'services' in content
                has_compose_fields = any(key in content for key in ['services', 'networks', 'volumes'])
                
                return has_services or (has_version and has_compose_fields)
        except:
            pass
        
        return False
    
    @staticmethod
    def is_docker_compose_data(data: Any) -> bool:
        """Check if data structure looks like Docker Compose"""
        if not isinstance(data, dict):
            return False
        
        # Check for Docker Compose structure
        has_services = 'services' in data and isinstance(data['services'], dict)
        has_version = 'version' in data
        has_compose_fields = any(key in data for key in ['services', 'networks', 'volumes'])
        
        return has_services or (has_version and has_compose_fields)
    
    @staticmethod
    def convert_compose_to_portainer(compose_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Docker Compose data to Portainer template format"""
        if not isinstance(compose_data, dict) or 'services' not in compose_data:
            raise ValueError("Invalid Docker Compose format: missing 'services' section")
        
        templates = []
        services = compose_data['services']
        
        if not isinstance(services, dict):
            raise ValueError("Invalid Docker Compose format: 'services' must be a dictionary")
        
        for service_name, service_config in services.items():
            if not isinstance(service_config, dict):
                continue
            
            template = DockerComposeConverter._convert_service_to_template(service_name, service_config)
            if template:
                templates.append(template)
        
        return {
            "version": "2",
            "templates": templates
        }
    
    @staticmethod
    def _convert_service_to_template(service_name: str, service_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert a single Docker Compose service to Portainer template"""
        if 'image' not in service_config:
            # Skip services without image (like build-only services)
            return None
        
        template = {
            "title": service_config.get('container_name', service_name).replace('_', ' ').title(),
            "image": service_config['image'],
            "platform": "linux",
            "restart_policy": DockerComposeConverter._map_restart_policy(service_config.get('restart', 'no'))
        }
        
        # Add description if available
        if 'labels' in service_config and isinstance(service_config['labels'], dict):
            description = service_config['labels'].get('description', 
                         service_config['labels'].get('traefik.frontend.rule', ''))
            if description:
                template['description'] = description
        
        if not template.get('description'):
            template['description'] = f"Container service: {service_name}"
        
        # Convert environment variables
        env_vars = DockerComposeConverter._convert_environment(service_config.get('environment', []))
        if env_vars:
            template['env'] = env_vars
        
        # Convert ports
        ports = DockerComposeConverter._convert_ports(service_config.get('ports', []))
        if ports:
            template['ports'] = ports
        
        # Convert volumes
        volumes = DockerComposeConverter._convert_volumes(service_config.get('volumes', []))
        if volumes:
            template['volumes'] = volumes
        
        # Add categories based on service name or image
        categories = DockerComposeConverter._detect_categories(service_name, service_config['image'])
        if categories:
            template['categories'] = categories
        
        # Add labels as note if present
        if 'labels' in service_config and isinstance(service_config['labels'], dict):
            notes = []
            for key, value in service_config['labels'].items():
                if key not in ['description']:  # Skip description as it's already used
                    notes.append(f"{key}: {value}")
            if notes:
                template['note'] = "Docker Compose labels: " + "; ".join(notes[:3])  # Limit to first 3
        
        return template
    
    @staticmethod
    def _map_restart_policy(restart: str) -> str:
        """Map Docker Compose restart policy to Portainer format"""
        restart_mapping = {
            'no': 'no',
            'always': 'always',
            'on-failure': 'on-failure',
            'unless-stopped': 'unless-stopped'
        }
        return restart_mapping.get(restart, 'unless-stopped')
    
    @staticmethod
    def _convert_environment(environment: Any) -> List[Dict[str, str]]:
        """Convert Docker Compose environment to Portainer format"""
        env_vars = []
        
        if isinstance(environment, list):
            for env in environment:
                if isinstance(env, str):
                    if '=' in env:
                        name, value = env.split('=', 1)
                        env_vars.append({"name": name, "default": value})
                    else:
                        env_vars.append({"name": env})
        elif isinstance(environment, dict):
            for name, value in environment.items():
                if value is not None:
                    env_vars.append({"name": name, "default": str(value)})
                else:
                    env_vars.append({"name": name})
        
        return env_vars
    
    @staticmethod
    def _convert_ports(ports: List) -> List[Dict[str, str]]:
        """Convert Docker Compose ports to Portainer format"""
        port_mappings = []
        
        for port in ports:
            if isinstance(port, str):
                # Handle "host:container" or "container" format
                if ':' in port:
                    host_port, container_port = port.split(':', 1)
                    # Handle protocol suffix
                    if '/' in container_port:
                        container_port, protocol = container_port.split('/')
                        port_str = f"{container_port}/{protocol}"
                    else:
                        port_str = f"{container_port}/tcp"
                    
                    label = f"Port {container_port}"
                else:
                    port_str = f"{port}/tcp"
                    label = f"Port {port}"
                
                port_mappings.append({label: port_str})
            elif isinstance(port, dict):
                # Handle expanded port format
                target = port.get('target', '')
                published = port.get('published', target)
                protocol = port.get('protocol', 'tcp')
                
                if target:
                    port_str = f"{target}/{protocol}"
                    label = f"Port {target}"
                    port_mappings.append({label: port_str})
        
        return port_mappings
    
    @staticmethod
    def _convert_volumes(volumes: List) -> List[Dict[str, str]]:
        """Convert Docker Compose volumes to Portainer format"""
        volume_mappings = []
        
        for volume in volumes:
            if isinstance(volume, str):
                # Handle "host:container" or "host:container:mode" format
                if ':' in volume:
                    parts = volume.split(':')
                    host_path = parts[0]
                    container_path = parts[1]
                    
                    # Convert relative paths and named volumes
                    if not host_path.startswith('/') and not host_path.startswith('.'):
                        # Probably a named volume
                        host_path = f"!data/{host_path}"
                    elif host_path.startswith('./'):
                        # Relative path
                        host_path = f"!data/{host_path[2:]}"
                    
                    volume_mappings.append({
                        "container": container_path,
                        "bind": host_path
                    })
            elif isinstance(volume, dict):
                # Handle expanded volume format
                source = volume.get('source', '')
                target = volume.get('target', '')
                
                if source and target:
                    # Handle named volumes
                    if not source.startswith('/') and not source.startswith('.'):
                        source = f"!data/{source}"
                    
                    volume_mappings.append({
                        "container": target,
                        "bind": source
                    })
        
        return volume_mappings
    
    @staticmethod
    def _detect_categories(service_name: str, image: str) -> List[str]:
        """Detect categories based on service name and image"""
        categories = []
        
        # Common service patterns
        service_patterns = {
            'database': ['mysql', 'postgres', 'mongodb', 'redis', 'mariadb', 'sqlite'],
            'webserver': ['nginx', 'apache', 'httpd', 'caddy'],
            'media': ['plex', 'jellyfin', 'emby', 'sonarr', 'radarr'],
            'networking': ['traefik', 'nginx-proxy', 'haproxy'],
            'monitoring': ['prometheus', 'grafana', 'influxdb', 'telegraf'],
            'development': ['node', 'python', 'php', 'ruby'],
            'storage': ['nextcloud', 'owncloud', 'seafile'],
            'communication': ['rocketchat', 'mattermost', 'discord'],
            'security': ['vault', 'keycloak', 'authelia']
        }
        
        service_lower = service_name.lower()
        image_lower = image.lower()
        
        for category, keywords in service_patterns.items():
            for keyword in keywords:
                if keyword in service_lower or keyword in image_lower:
                    categories.append(category)
                    break
        
        # Default category if none detected
        if not categories:
            categories.append('tools')
        
        return categories


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
