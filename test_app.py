#!/usr/bin/env python3
"""
Test script for JSON Template Combiner
Run this to verify the application works correctly
"""

import sys
import os
import json
import traceback
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def test_imports():
    """Test if all required modules can be imported"""
    print("Testing imports...")
    
    try:
        import customtkinter as ctk
        print("+ customtkinter imported successfully")
    except ImportError as e:
        print(f"- Failed to import customtkinter: {e}")
        return False
    
    try:
        import requests
        print("+ requests imported successfully")
    except ImportError as e:
        print(f"- Failed to import requests: {e}")
        return False
    
    try:
        from utils import ConfigManager, JSONValidator, NetworkUtils, FileUtils, TemplateUtils
        print("+ utils module imported successfully")
    except ImportError as e:
        print(f"- Failed to import utils: {e}")
        return False
    
    try:
        from main import TemplateComparator, JSONTemplateApp
        print("+ main module imported successfully")
    except ImportError as e:
        print(f"- Failed to import main: {e}")
        return False
    
    return True

def test_config():
    """Test configuration loading"""
    print("\nTesting configuration...")
    
    try:
        from utils import ConfigManager
        config = ConfigManager()
        
        # Test getting values
        threshold = config.get('settings.similarity_threshold', 0.7)
        print(f"✓ Similarity threshold: {threshold}")
        
        timeout = config.get('settings.request_timeout', 30)
        print(f"✓ Request timeout: {timeout}")
        
        return True
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def test_json_validation():
    """Test JSON validation functions"""
    print("\nTesting JSON validation...")
    
    try:
        from utils import JSONValidator, TemplateConverter
        
        # Test valid template structure
        valid_template = {
            "title": "Test App",
            "description": "Test application",
            "image": "nginx:latest"
        }
        
        if JSONValidator.is_valid_template_structure(valid_template):
            print("✓ Valid template structure recognized")
        else:
            print("✗ Valid template structure not recognized")
            return False
        
        # Test template extraction
        portainer_format = {
            "version": "2",
            "templates": [valid_template]
        }
        
        extracted = JSONValidator.extract_templates(portainer_format)
        if len(extracted) == 1 and extracted[0]['title'] == 'Test App':
            print("✓ Template extraction works")
        else:
            print("✗ Template extraction failed")
            return False
        
        # Test QNAP format recognition
        qnap_format = [
            {
                "displayName": "QNAP App",
                "name": "qnap/app",
                "description": "QNAP application",
                "arch": "amd64"
            }
        ]
        
        if JSONValidator.is_valid_template_structure(qnap_format):
            print("✓ QNAP format recognized")
        else:
            print("✗ QNAP format not recognized")
            return False
        
        # Test QNAP template extraction with conversion
        extracted_qnap = JSONValidator.extract_templates(qnap_format)
        if (len(extracted_qnap) == 1 and 
            extracted_qnap[0].get('title') == 'QNAP App' and
            'image' in extracted_qnap[0]):
            print("✓ QNAP template extraction and conversion works")
        else:
            print("✗ QNAP template extraction failed")
            return False
        
        return True
    except Exception as e:
        print(f"✗ JSON validation test failed: {e}")
        return False

def test_template_comparison():
    """Test template comparison functionality"""
    print("\nTesting template comparison...")
    
    try:
        from main import TemplateComparator
        
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
        print(f"✓ Similarity calculation: {similarity:.2f}")
        
        if 0.0 <= similarity <= 1.0:
            print("✓ Similarity value is in valid range")
        else:
            print("✗ Similarity value is out of range")
            return False
        
        # Test architecture detection
        arch = TemplateComparator.detect_architecture(template1)
        print(f"✓ Architecture detection: {arch}")
        
        return True
    except Exception as e:
        print(f"✗ Template comparison test failed: {e}")
        return False

def test_network_utils():
    """Test network utility functions"""
    print("\nTesting network utilities...")
    
    try:
        from utils import NetworkUtils
        
        # Test URL validation
        if NetworkUtils.is_valid_url("https://example.com"):
            print("✓ Valid URL recognized")
        else:
            print("✗ Valid URL not recognized")
            return False
        
        if not NetworkUtils.is_valid_url("invalid-url"):
            print("✓ Invalid URL rejected")
        else:
            print("✗ Invalid URL accepted")
            return False
        
        print("✓ Network utilities working")
        return True
    except Exception as e:
        print(f"✗ Network utilities test failed: {e}")
        return False

def test_file_utils():
    """Test file utility functions"""
    print("\nTesting file utilities...")
    
    try:
        from utils import FileUtils
        
        # Test JSON extension handling
        filename = FileUtils.ensure_json_extension("test")
        if filename == "test.json":
            print("✓ JSON extension added correctly")
        else:
            print("✗ JSON extension not added correctly")
            return False
        
        filename = FileUtils.ensure_json_extension("test.json")
        if filename == "test.json":
            print("✓ Existing JSON extension preserved")
        else:
            print("✗ Existing JSON extension not preserved")
            return False
        
        return True
    except Exception as e:
        print(f"✗ File utilities test failed: {e}")
        return False

def test_template_utils():
    """Test template utility functions"""
    print("\nTesting template utilities...")
    
    try:
        from utils import TemplateUtils, TemplateConverter
        
        # Test title normalization
        normalized = TemplateUtils.normalize_template_title("  Docker-Nginx Container  ")
        expected = "nginx"
        if normalized == expected:
            print(f"✓ Title normalization: '{normalized}'")
        else:
            print(f"✗ Title normalization failed: got '{normalized}', expected '{expected}'")
            return False
        
        # Test image name extraction
        image_name = TemplateUtils.extract_image_name("registry.hub.docker.com/library/nginx:1.21-alpine")
        expected = "nginx"
        if image_name == expected:
            print(f"✓ Image name extraction: '{image_name}'")
        else:
            print(f"✗ Image name extraction failed: got '{image_name}', expected '{expected}'")
            return False
        
        # Test quality score
        template = {
            "title": "Test App",
            "description": "Test description",
            "image": "nginx:latest",
            "env": [{"name": "TEST", "value": "value"}]
        }
        score = TemplateUtils.get_template_quality_score(template)
        if score > 0:
            print(f"✓ Quality score calculation: {score}")
        else:
            print("✗ Quality score calculation failed")
            return False
        
        # Test QNAP format conversion
        qnap_template = {
            "displayName": "Test QNAP App",
            "description": "Test QNAP description",
            "name": "test/app",
            "version": "latest",
            "arch": "amd64",
            "type": "ai",
            "icon": "https://example.com/icon.png"
        }
        
        converted = TemplateConverter.convert_to_portainer([qnap_template])
        if (converted.get('version') == '2' and 
            len(converted.get('templates', [])) == 1 and
            converted['templates'][0].get('title') == 'Test QNAP App'):
            print("✓ QNAP format conversion successful")
        else:
            print("✗ QNAP format conversion failed")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Template utilities test failed: {e}")
        return False

def test_gui_initialization():
    """Test GUI can be initialized without errors"""
    print("\nTesting GUI initialization...")
    
    try:
        # Import without running the GUI
        import customtkinter as ctk
        
        # Test basic CTk initialization
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        print("✓ CustomTkinter configuration successful")
        
        # We can't fully test the GUI without displaying it,
        # but we can test that the main class can be imported
        from main import JSONTemplateApp
        print("✓ JSONTemplateApp class available")
        
        return True
    except Exception as e:
        print(f"✗ GUI initialization test failed: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("JSON Template Combiner - Test Suite")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Configuration Test", test_config),
        ("JSON Validation Test", test_json_validation),
        ("Template Comparison Test", test_template_comparison),
        ("Network Utils Test", test_network_utils),
        ("File Utils Test", test_file_utils),
        ("Template Utils Test", test_template_utils),
        ("GUI Initialization Test", test_gui_initialization),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} crashed: {e}")
            traceback.print_exc()
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The application should work correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the requirements and dependencies.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    
    if success:
        print("\nYou can now run the application with: python main.py")
    else:
        print("\nPlease fix the issues above before running the application.")
    
    input("\nPress Enter to exit...")
    sys.exit(0 if success else 1)
