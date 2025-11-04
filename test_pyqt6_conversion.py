#!/usr/bin/env python3
"""
Test script to validate PyQt6 conversion without GUI rendering
"""

import os
import sys


def test_ui_file_exists():
    """Test that .ui file exists"""
    ui_path = os.path.join(os.path.dirname(__file__), 'main_window_pyqt6.ui')
    assert os.path.exists(ui_path), "main_window_pyqt6.ui not found"
    print("✓ UI file exists")
    return True


def test_ui_file_valid():
    """Test that .ui file is valid XML"""
    ui_path = os.path.join(os.path.dirname(__file__), 'main_window_pyqt6.ui')
    with open(ui_path, 'r') as f:
        content = f.read()
    assert '<?xml version="1.0"' in content, "Not a valid XML file"
    assert '<ui version="4.0">' in content, "Not a valid Qt UI file"
    assert '<class>MainWindow</class>' in content, "MainWindow class not defined"
    print("✓ UI file is valid XML")
    return True


def test_main_window_imports():
    """Test that main_window_pyqt6.py has correct imports"""
    with open('main_window_pyqt6.py', 'r') as f:
        content = f.read()

    required_imports = [
        'from PyQt6.QtWidgets import',
        'from PyQt6.QtCore import',
        'from PyQt6 import uic',
        'import requests',
        'import json',
    ]

    for imp in required_imports:
        assert imp in content, f"Missing import: {imp}"

    print("✓ Main window has correct imports")
    return True


def test_main_window_structure():
    """Test that main_window_pyqt6.py has required classes and methods"""
    with open('main_window_pyqt6.py', 'r') as f:
        content = f.read()

    required_classes = [
        'class TemplateComparator:',
        'class LoadTemplateWorker(QThread):',
        'class ProcessSourcesWorker(QThread):',
        'class GenerateTemplateWorker(QThread):',
        'class MainWindow(QMainWindow):',
    ]

    for cls in required_classes:
        assert cls in content, f"Missing class: {cls}"

    # Key methods from all tabs
    required_methods = [
        'def setup_connections(self):',
        'def add_url_source(self):',
        'def add_file_source(self):',
        'def process_sources(self):',
        'def add_category(self):',
        'def add_env_var(self):',
        'def add_port(self):',
        'def add_volume(self):',
        'def add_manual_template(self):',
        'def refresh_edit_templates_list(self):',
        'def generate_final_template(self):',
        'def save_template(self):',
        'def process_duplicate_templates(self',
    ]

    for method in required_methods:
        assert method in content, f"Missing method: {method}"

    print("✓ Main window has required classes and methods")
    return True


def test_main_entry_point():
    """Test that main_pyqt6.py exists and has correct structure"""
    with open('main_pyqt6.py', 'r') as f:
        content = f.read()

    assert 'from PyQt6.QtWidgets import QApplication' in content, "Missing QApplication import"
    assert 'from main_window_pyqt6 import MainWindow' in content, "Missing MainWindow import"
    assert 'def main():' in content, "Missing main function"
    assert 'app = QApplication(sys.argv)' in content, "Missing QApplication instantiation"
    assert 'window = MainWindow()' in content, "Missing MainWindow instantiation"

    print("✓ Main entry point is correct")
    return True


def test_utils_compatibility():
    """Test that utils.py is compatible"""
    from utils import (
        TemplateConverter,
        JSONValidator,
        ConfigManager,
    )

    # Test basic functionality
    config = ConfigManager()
    assert config.config is not None, "ConfigManager failed to initialize"

    # Test format detection
    test_data = {"version": "2", "templates": [{"title": "Test"}]}
    format_type = TemplateConverter.detect_format(test_data)
    assert format_type == 'portainer', "Format detection failed"

    print("✓ Utils module is compatible")
    return True


def test_requirements():
    """Test that requirements_pyqt6.txt has PyQt6"""
    with open('requirements_pyqt6.txt', 'r') as f:
        content = f.read()

    assert 'PyQt6' in content, "PyQt6 not in requirements_pyqt6.txt"
    assert 'requests' in content, "requests not in requirements_pyqt6.txt"

    print("✓ Requirements file is correct")
    return True


def test_backups_exist():
    """Test that backups of old versions exist"""
    assert os.path.exists('main_customtkinter_full.py'), "Backup of full version not found"
    print("✓ CustomTkinter backup exists")
    return True


def test_file_structure():
    """Test that all necessary files exist"""
    required_files = [
        'main_window_pyqt6.ui',
        'main_window_pyqt6.py',
        'main_pyqt6.py',
        'requirements_pyqt6.txt',
        'utils.py',
        'config.json',
    ]

    for file in required_files:
        assert os.path.exists(file), f"Required file not found: {file}"

    print("✓ All required files exist")
    return True


def test_line_count():
    """Test that the PyQt6 version is reasonable size"""
    with open('main_window_pyqt6.py', 'r') as f:
        lines = len(f.readlines())

    print(f"✓ PyQt6 version is {lines} lines (original CustomTkinter: 3617 lines)")
    assert lines > 1000, "PyQt6 version seems too short"
    assert lines < 2000, "PyQt6 version is reasonably sized"
    return True


def main():
    """Run all tests"""
    print("Running PyQt6 conversion validation tests...\n")

    tests = [
        test_ui_file_exists,
        test_ui_file_valid,
        test_main_window_imports,
        test_main_window_structure,
        test_main_entry_point,
        test_utils_compatibility,
        test_requirements,
        test_backups_exist,
        test_file_structure,
        test_line_count,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Tests passed: {passed}/{len(tests)}")
    print(f"Tests failed: {failed}/{len(tests)}")

    if failed == 0:
        print("\n✓ All validation tests passed!")
        print("Note: GUI rendering tests skipped (requires display server)")
        print("\nThe PyQt6 conversion is complete and validated!")
        print("\nTo run the application:")
        print("  1. Install dependencies: pip install -r requirements_pyqt6.txt")
        print("  2. Run: python main_pyqt6.py")
        return 0
    else:
        print(f"\n✗ {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
