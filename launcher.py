#!/usr/bin/env python3
"""
Launcher script for JSON Template Combiner
This script will automatically handle setup and launch the application
"""

import sys
import os
import subprocess
import importlib.util
from pathlib import Path

def check_python_version():
    """Check if Python version is supported"""
    if sys.version_info < (3, 7):
        print("Error: Python 3.7 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    return True

def check_and_install_requirements():
    """Check if required packages are installed, install if missing"""
    required_packages = [
        ('customtkinter', 'customtkinter>=5.2.0'),
        ('requests', 'requests>=2.31.0'),
        ('PIL', 'Pillow>=10.0.0')
    ]
    
    missing_packages = []
    
    for package_name, pip_name in required_packages:
        if importlib.util.find_spec(package_name) is None:
            missing_packages.append(pip_name)
    
    if missing_packages:
        print("Installing missing packages...")
        try:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install'
            ] + missing_packages)
            print("✓ All packages installed successfully")
        except subprocess.CalledProcessError:
            print("❌ Failed to install packages. Please run:")
            print(f"pip install {' '.join(missing_packages)}")
            return False
    else:
        print("✓ All required packages are installed")
    
    return True

def launch_application():
    """Launch the main application"""
    try:
        # Change to the script directory
        script_dir = Path(__file__).parent
        os.chdir(script_dir)
        
        # Import and run the application
        from main import main
        print("🚀 Launching JSON Template Combiner...")
        main()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure all files are in the same directory")
        return False
    except Exception as e:
        print(f"❌ Error launching application: {e}")
        return False
    
    return True

def main():
    """Main launcher function"""
    print("JSON Template Combiner - Launcher")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Check and install requirements
    if not check_and_install_requirements():
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Launch application
    if not launch_application():
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
