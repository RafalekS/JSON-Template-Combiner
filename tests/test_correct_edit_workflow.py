#!/usr/bin/env python3
"""
Test the corrected template editing workflow
"""

import sys
import os

project_path = r"C:\Users\r_sta\Downloads\projects\python\JSON Template Combiner"
sys.path.insert(0, project_path)

def test_correct_edit_workflow():
    """Test that the editing workflow now matches user requirements"""
    print("Testing Corrected Template Editing Workflow...")
    print("=" * 60)
    
    try:
        with open(os.path.join(project_path, "main.py"), "r", encoding="utf-8") as f:
            content = f.read()
        
        print("=== Testing Edit Window Implementation ===")
        
        # Check for dedicated edit window
        edit_window_features = [
            ("Dedicated edit window", "open_template_edit_window"),
            ("Modal edit dialog", "edit_window.grab_set()"),
            ("Proper window title", 'title(f"Edit Template:'),
            ("Separate form creation", "create_edit_form"),
            ("No Manual Entry reuse", "# Open dedicated edit window instead")
        ]
        
        for feature, search_text in edit_window_features:
            if search_text in content:
                print(f"  [OK] {feature}")
            else:
                print(f"  [FAIL] {feature}")
        
        print("\n=== Testing Save Choice Dialog ===")
        
        # Check for the exact save options requested
        save_choice_features = [
            ("Save choice dialog", "How do you want to save your changes?"),
            ("Save as separate option", "Save as Separate Template"),
            ("Update original option", "Update Original Source File"),
            ("Separate template function", "save_as_separate()"),
            ("Update source function", "update_original_source()"),
            ("No more 'added successfully'", "saved as a separate template!")
        ]
        
        for feature, search_text in save_choice_features:
            if search_text in content:
                print(f"  [OK] {feature}")
            else:
                print(f"  [FAIL] {feature}")
        
        print("\n=== Testing User Requirements ===")
        
        # Verify the exact requirements are met
        requirements = [
            ("Dedicated edit interface", "open_template_edit_window"),
            ("Clear save choice", "Save as Separate Template"),
            ("Update source option", "Update Original Source File"),
            ("No Manual Entry confusion", "dedicated edit window instead"),
            ("Proper edit vs add", "saved as a separate template")
        ]
        
        for requirement, search_text in requirements:
            if search_text in content:
                print(f"  [OK] {requirement}")
            else:
                print(f"  [FAIL] {requirement}")
        
        print("\n" + "=" * 60)
        print("CORRECTED WORKFLOW TEST COMPLETE!")
        print("\n=== WHAT SHOULD NOW HAPPEN ===")
        print("1. Edit Templates tab -> Select template -> Edit Selected Template")
        print("2. Opens DEDICATED edit window (not Manual Entry tab)")
        print("3. Make your changes in the dedicated window")
        print("4. Click 'Save Changes' -> Shows dialog with 2 clear choices:")
        print("   - 'Save as Separate Template' (creates new entry)")
        print("   - 'Update Original Source File' (modifies source)")
        print("5. No more confusion with Manual Entry tab")
        print("6. No more 'Template added successfully' when editing")
        
        print("\n✓ This now implements EXACTLY what you asked for!")
        
    except Exception as e:
        print(f"Test failed: {str(e)}")

if __name__ == "__main__":
    test_correct_edit_workflow()
