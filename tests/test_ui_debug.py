#!/usr/bin/env python3
"""
Quick test to launch the app and see debug output
"""

import sys
import os

# Add the project path
project_path = r"C:\Users\r_sta\Downloads\projects\python\JSON Template Combiner"
sys.path.insert(0, project_path)

def test_app_launch():
    """Test launching the app with debug output"""
    print("=" * 60)
    print("LAUNCHING JSON TEMPLATE COMBINER WITH DEBUGGING")
    print("=" * 60)
    print("Watch console for debug output:")
    print("- 'DEBUG: Creating Ports section' - should show when UI is built")
    print("- 'DEBUG: Creating Volumes section' - should show when UI is built")  
    print("- 'DEBUG: Port Add button created' - should show buttons are made")
    print("- 'DEBUG: Volume Add button created' - should show buttons are made")
    print("=" * 60)
    
    try:
        # Import and run the application
        from main import JSONTemplateApp
        app = JSONTemplateApp()
        
        print("\n[INFO] Application created successfully")
        print("[INFO] Go to Manual Entry tab and check if Ports/Volumes buttons are visible")
        print("[INFO] Try adding environmental variables and saving to test data persistence")
        print("[INFO] Watch console for any DEBUG messages\n")
        
        app.run()
        
    except ImportError as e:
        print(f"[ERROR] Import error: {e}")
        print("Make sure you're in the correct directory and dependencies are installed")
        return False
    except Exception as e:
        print(f"[ERROR] Error launching application: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_app_launch()
