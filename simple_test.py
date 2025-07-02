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
