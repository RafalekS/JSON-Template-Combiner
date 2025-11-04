#!/usr/bin/env python3
"""
Simple test script for JSON Template Combiner - ASCII version
"""

import sys
import os
import json
import traceback
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def test_basic_functionality():
    """Test basic functionality"""
    print("Testing basic functionality...")
    
    try:
        # Test imports
        import customtkinter as ctk
        import requests
        from utils import ConfigManager, JSONValidator, NetworkUtils, FileUtils, TemplateUtils, TemplateConverter
        from main import TemplateComparator, JSONTemplateApp
        print("+ All imports successful")
        
        # Test title normalization
        normalized = TemplateUtils.normalize_template_title("  Docker-Nginx Container  ")
        expected = "nginx"
        if normalized == expected:
            print(f"+ Title normalization works: '{normalized}'")
        else:
            print(f"- Title normalization failed: got '{normalized}', expected '{expected}'")
            return False
        
        # Test QNAP format conversion
        qnap_template = {
            "displayName": "Test QNAP App",
            "description": "Test QNAP description",
            "name": "test/app",
            "version": "latest",
            "arch": "amd64",
            "type": "ai"
        }
        
        converted = TemplateConverter.convert_to_portainer([qnap_template])
        if (converted.get('version') == '2' and 
            len(converted.get('templates', [])) == 1 and
            converted['templates'][0].get('title') == 'Test QNAP App'):
            print("+ QNAP format conversion works")
        else:
            print("- QNAP format conversion failed")
            return False
        
        # Test template comparison
        template1 = {
            "title": "Nginx Web Server",
            "description": "High-performance web server",
            "image": "nginx:latest"
        }
        
        template2 = {
            "title": "Nginx Web Server",
            "description": "High-performance web server and reverse proxy",
            "image": "nginx:alpine"
        }
        
        similarity = TemplateComparator.calculate_similarity(template1, template2)
        if 0.0 <= similarity <= 1.0:
            print(f"+ Template comparison works: {similarity:.2f}")
        else:
            print("- Template comparison failed")
            return False
        
        # Test manual template creation
        app_instance = JSONTemplateApp()
        
        # Simulate adding a manual template
        manual_template = {
            "title": "Test Manual Template",
            "description": "This is a manually created template",
            "image": "test:latest",
            "platform": "linux",
            "restart_policy": "unless-stopped",
            "categories": ["test"],
            "env": [{"name": "TEST_VAR", "default": "test_value"}],
            "ports": [{"WebUI": "8080/tcp"}],
            "volumes": [{"container": "/app", "bind": "!data/app"}]
        }
        
        app_instance.manual_templates.append(manual_template)
        
        if len(app_instance.manual_templates) == 1:
            print("+ Manual template creation works")
        else:
            print("- Manual template creation failed")
            return False
        
        # Test configuration loading
        config_test = app_instance.config.get('base_template.enabled', True)
        if isinstance(config_test, bool):
            print("+ Configuration management works")
        else:
            print("- Configuration management failed")
            return False
        
        # Test category extraction
        test_templates = {
            "version": "2",
            "templates": [
                {"title": "Test1", "categories": ["webserver", "test"]},
                {"title": "Test2", "categories": ["database"]}
            ]
        }
        app_instance.loaded_templates["test"] = test_templates
        categories = app_instance.extract_categories_from_templates()
        
        if "webserver" in categories and "database" in categories:
            print("+ Category extraction works")
        else:
            print("- Category extraction failed")
            return False
        
        # Test Docker Compose conversion
        from utils import DockerComposeConverter
        
        docker_compose_data = {
            "version": "3.8",
            "services": {
                "nginx": {
                    "image": "nginx:latest",
                    "ports": ["80:80"],
                    "volumes": ["./html:/usr/share/nginx/html"],
                    "restart": "unless-stopped",
                    "environment": ["NGINX_HOST=localhost"]
                },
                "mysql": {
                    "image": "mysql:8.0",
                    "ports": ["3306:3306"],
                    "environment": {
                        "MYSQL_ROOT_PASSWORD": "rootpass",
                        "MYSQL_DATABASE": "testdb"
                    },
                    "volumes": ["mysql_data:/var/lib/mysql"]
                }
            }
        }
        
        if DockerComposeConverter.is_docker_compose_data(docker_compose_data):
            print("+ Docker Compose format detection works")
        else:
            print("- Docker Compose format detection failed")
            return False
        
        converted_compose = DockerComposeConverter.convert_compose_to_portainer(docker_compose_data)
        if (converted_compose.get('version') == '2' and 
            len(converted_compose.get('templates', [])) == 2):
            print("+ Docker Compose conversion works")
        else:
            print("- Docker Compose conversion failed")
            return False
        
        print("+ All tests passed!")
        return True
        
    except Exception as e:
        print(f"- Test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("JSON Template Combiner - Simple Test")
    print("=" * 40)
    
    if test_basic_functionality():
        print("\n:) All core functionality works!")
        print("You can run the application with: python main.py")
        return True
    else:
        print("\nX Some functionality failed.")
        print("Please check the requirements and dependencies.")
        return False

if __name__ == "__main__":
    success = main()
    input("\nPress Enter to exit...")
    sys.exit(0 if success else 1)
