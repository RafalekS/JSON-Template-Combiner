#!/usr/bin/env python3
"""
JSON Template Combiner
A GUI application for combining multiple JSON template sources into one templates.json file
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import requests
import json
import threading
from typing import List, Dict, Any, Tuple
import difflib
from urllib.parse import urlparse
import os
import re
from datetime import datetime

# Configure customtkinter
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class TemplateComparator:
    """Handles comparison and similarity checking of templates"""
    
    @staticmethod
    def calculate_similarity(template1: Dict, template2: Dict) -> float:
        """Calculate similarity percentage between two templates"""
        # Compare key fields in order of importance
        title_sim = TemplateComparator._text_similarity(
            template1.get('title', ''), template2.get('title', '')
        )
        
        image_sim = TemplateComparator._text_similarity(
            template1.get('image', ''), template2.get('image', '')
        )
        
        desc_sim = TemplateComparator._text_similarity(
            template1.get('description', ''), template2.get('description', '')
        )
        
        # Compare compose file content if exists
        compose_sim = 0.0
        if 'repository' in template1 and 'repository' in template2:
            if 'stackfile' in template1['repository'] and 'stackfile' in template2['repository']:
                compose_sim = TemplateComparator._text_similarity(
                    template1['repository']['stackfile'], 
                    template2['repository']['stackfile']
                )
        
        # Compare environment variables
        env_sim = TemplateComparator._compare_env_vars(
            template1.get('env', []), template2.get('env', [])
        )
        
        # Weighted average (title and image are most important)
        total_sim = (title_sim * 0.3 + image_sim * 0.25 + desc_sim * 0.2 + 
                    compose_sim * 0.15 + env_sim * 0.1)
        
        return total_sim
    
    @staticmethod
    def _text_similarity(text1: str, text2: str) -> float:
        """Calculate text similarity using difflib"""
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0
        
        return difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    @staticmethod
    def _compare_env_vars(env1: List, env2: List) -> float:
        """Compare environment variable lists"""
        if not env1 and not env2:
            return 1.0
        if not env1 or not env2:
            return 0.0
        
        # Create sets of env var names for comparison
        env1_names = {var.get('name', '') for var in env1 if isinstance(var, dict)}
        env2_names = {var.get('name', '') for var in env2 if isinstance(var, dict)}
        
        if not env1_names and not env2_names:
            return 1.0
        
        intersection = len(env1_names.intersection(env2_names))
        union = len(env1_names.union(env2_names))
        
        return intersection / union if union > 0 else 0.0
    
    @staticmethod
    def detect_architecture(template: Dict) -> str:
        """Detect architecture from template data"""
        # Check platform field
        platform = template.get('platform', '').lower()
        if platform:
            return platform
        
        # Check image tag for architecture hints
        image = template.get('image', '').lower()
        if 'arm64' in image or 'aarch64' in image:
            return 'arm64'
        elif 'arm' in image:
            return 'arm'
        elif 'amd64' in image or 'x86_64' in image:
            return 'amd64'
        elif '386' in image or 'i386' in image:
            return '386'
        
        # Check in repository or other fields
        repo = template.get('repository', {})
        if isinstance(repo, dict):
            stackfile = repo.get('stackfile', '').lower()
            if 'arm64' in stackfile:
                return 'arm64'
            elif 'amd64' in stackfile:
                return 'amd64'
        
        return 'linux'  # default


class JSONTemplateApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("JSON Template Combiner")
        self.root.geometry("1400x1000")
        
        # Data storage
        self.url_sources = []
        self.file_sources = []
        self.loaded_templates = {}
        self.manual_templates = []  # Store manually created templates
        self.all_categories = set()  # Store all unique categories from sources
        self.all_templates_for_editing = []  # Store all templates for editing tab
        self.final_template = {"version": "2", "templates": []}
        self.current_editing_context = None  # For tracking template edits
        
        # Configuration
        from utils import ConfigManager
        self.config = ConfigManager()
        
        # Initialize base template from configuration
        self.base_template_enabled = self.config.get('base_template.enabled', True)
        self.base_template_url = self.config.get('base_template.url', 'https://templates-portainer.ibaraki.app')
        self.base_template_auto_load = self.config.get('base_template.auto_load', True)
        
        self.setup_ui()
        if self.base_template_enabled and self.base_template_auto_load:
            self.load_base_template()
        
    def setup_ui(self):
        """Set up the user interface"""
        # Create notebook for tabs
        self.notebook = ctk.CTkTabview(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create tabs
        self.setup_sources_tab()
        self.setup_manual_entry_tab()
        self.setup_edit_templates_tab()
        self.setup_preview_tab()
        self.setup_save_tab()
        
    def setup_sources_tab(self):
        """Set up the sources management tab"""
        tab1 = self.notebook.add("Sources")
        
        # URL Sources section
        url_frame = ctk.CTkFrame(tab1)
        url_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(url_frame, text="URL Sources", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)
        
        # URL input frame
        url_input_frame = ctk.CTkFrame(url_frame)
        url_input_frame.pack(fill="x", padx=10, pady=5)
        
        self.url_entry = ctk.CTkEntry(url_input_frame, placeholder_text="Enter JSON URL...")
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.add_url_btn = ctk.CTkButton(url_input_frame, text="Add URL", 
                                        command=self.add_url_source, width=100)
        self.add_url_btn.pack(side="right")
        
        # URL list
        self.url_listbox = tk.Listbox(url_frame, height=6)
        self.url_listbox.pack(fill="x", padx=10, pady=5)
        
        self.remove_url_btn = ctk.CTkButton(url_frame, text="Remove Selected URL", 
                                           command=self.remove_url_source)
        self.remove_url_btn.pack(pady=5)
        
        # File Sources section
        file_frame = ctk.CTkFrame(tab1)
        file_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(file_frame, text="Local File Sources", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)
        
        self.add_file_btn = ctk.CTkButton(file_frame, text="Add Template File (JSON/YAML/Compose)", 
                                         command=self.add_file_source)
        self.add_file_btn.pack(pady=5)
        
        # File list
        self.file_listbox = tk.Listbox(file_frame, height=6)
        self.file_listbox.pack(fill="x", padx=10, pady=5)
        
        self.remove_file_btn = ctk.CTkButton(file_frame, text="Remove Selected File", 
                                            command=self.remove_file_source)
        self.remove_file_btn.pack(pady=5)
        
        # Base Template Configuration section
        base_frame = ctk.CTkFrame(tab1)
        base_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(base_frame, text="Base Template Configuration", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)
        
        # Enable base template checkbox
        base_config_frame = ctk.CTkFrame(base_frame)
        base_config_frame.pack(fill="x", padx=10, pady=5)
        
        self.base_template_enabled_var = ctk.BooleanVar(value=self.base_template_enabled)
        self.base_template_checkbox = ctk.CTkCheckBox(base_config_frame, text="Load Base Template", 
                                                     variable=self.base_template_enabled_var,
                                                     command=self.toggle_base_template)
        self.base_template_checkbox.pack(side="left", padx=10)
        
        # Base template URL configuration
        base_url_frame = ctk.CTkFrame(base_frame)
        base_url_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(base_url_frame, text="Base Template URL:", width=120).pack(side="left", padx=(10, 5))
        self.base_template_entry = ctk.CTkEntry(base_url_frame, width=400)
        self.base_template_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.base_template_entry.insert(0, self.base_template_url)
        
        self.update_base_url_btn = ctk.CTkButton(base_url_frame, text="Update URL", 
                                                command=self.update_base_template_url, width=100)
        self.update_base_url_btn.pack(side="right", padx=5)
        
        self.load_base_btn = ctk.CTkButton(base_frame, text="Load Base Template Now", 
                                          command=self.load_base_template)
        self.load_base_btn.pack(pady=5)
        
        self.clear_base_btn = ctk.CTkButton(base_frame, text="Clear Base Template", 
                                           command=self.clear_base_template)
        self.clear_base_btn.pack(pady=(0, 5))
        
        # Load and Process button
        self.process_btn = ctk.CTkButton(tab1, text="Load & Process Sources →", 
                                        command=self.process_sources,
                                        font=ctk.CTkFont(size=14, weight="bold"))
        self.process_btn.pack(pady=20)
        
        # Progress bar
        self.progress = ctk.CTkProgressBar(tab1)
        self.progress.pack(fill="x", padx=10, pady=5)
        self.progress.set(0)
        
        # Status label
        self.status_label = ctk.CTkLabel(tab1, text="Ready")
        self.status_label.pack(pady=5)
    
    def setup_preview_tab(self):
        """Set up the preview tab"""
        tab2 = self.notebook.add("Preview")
        
        # Summary section
        summary_frame = ctk.CTkFrame(tab2)
        summary_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(summary_frame, text="Processing Summary", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)
        
        self.summary_text = ctk.CTkTextbox(summary_frame, height=150)
        self.summary_text.pack(fill="x", padx=10, pady=5)
        
        # Generate template button
        self.generate_btn = ctk.CTkButton(tab2, text="Generate Final Template →", 
                                         command=self.generate_final_template,
                                         font=ctk.CTkFont(size=14, weight="bold"))
        self.generate_btn.pack(pady=10)
        
        # Template preview section
        preview_frame = ctk.CTkFrame(tab2)
        preview_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        ctk.CTkLabel(preview_frame, text="Generated Template Preview", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)
        
        self.preview_text = ctk.CTkTextbox(preview_frame)
        self.preview_text.pack(fill="both", expand=True, padx=10, pady=5)
    
    def setup_save_tab(self):
        """Set up the save tab"""
        tab3 = self.notebook.add("Save")
        
        # Save location section
        location_frame = ctk.CTkFrame(tab3)
        location_frame.pack(fill="x", padx=10, pady=20)
        
        ctk.CTkLabel(location_frame, text="Save Location", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)
        
        path_frame = ctk.CTkFrame(location_frame)
        path_frame.pack(fill="x", padx=10, pady=5)
        
        self.save_path_entry = ctk.CTkEntry(path_frame, placeholder_text="templates.json")
        self.save_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.save_path_entry.insert(0, "templates.json")
        
        self.browse_btn = ctk.CTkButton(path_frame, text="Browse", 
                                       command=self.browse_save_location, width=100)
        self.browse_btn.pack(side="right")
        
        # Save button
        self.save_btn = ctk.CTkButton(tab3, text="Save Template File", 
                                     command=self.save_template,
                                     font=ctk.CTkFont(size=14, weight="bold"))
        self.save_btn.pack(pady=30)
        
        # Save status
        self.save_status = ctk.CTkLabel(tab3, text="")
        self.save_status.pack(pady=10)
    
    def setup_manual_entry_tab(self):
        """Set up the manual template entry tab"""
        tab_manual = self.notebook.add("Manual Entry")
        
        # Create main container with proper grid configuration
        main_container = ctk.CTkFrame(tab_manual)
        main_container.pack(fill="both", expand=True, padx=5, pady=5)
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_columnconfigure(1, weight=1)
        main_container.grid_rowconfigure(0, weight=1)
        
        # Left panel for form
        left_panel = ctk.CTkScrollableFrame(main_container)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(5, 2), pady=5)
        
        # Right panel for lists and management
        right_panel = ctk.CTkScrollableFrame(main_container)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(2, 5), pady=5)
        
        # Title
        title_label = ctk.CTkLabel(left_panel, text="Create Template Manually", 
                                  font=ctk.CTkFont(size=16, weight="bold"))
        title_label.pack(pady=(0, 15))
        
        # Basic Information Section
        basic_frame = ctk.CTkFrame(left_panel)
        basic_frame.pack(fill="x", padx=2, pady=3)
        
        ctk.CTkLabel(basic_frame, text="Basic Information", 
                    font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(5, 8))
        
        # Create a grid layout for compact form
        form_grid = ctk.CTkFrame(basic_frame)
        form_grid.pack(fill="x", padx=8, pady=(0, 8))
        form_grid.grid_columnconfigure(1, weight=1)
        
        # Title (required) - Row 0
        ctk.CTkLabel(form_grid, text="Title*:", width=80, anchor="w").grid(row=0, column=0, sticky="w", padx=(5, 8), pady=3)
        self.manual_title = ctk.CTkEntry(form_grid, placeholder_text="e.g., Nginx Web Server", height=32)
        self.manual_title.grid(row=0, column=1, sticky="ew", padx=(0, 5), pady=3)
        
        # Image (required) - Row 1
        ctk.CTkLabel(form_grid, text="Image*:", width=80, anchor="w").grid(row=1, column=0, sticky="w", padx=(5, 8), pady=3)
        self.manual_image = ctk.CTkEntry(form_grid, placeholder_text="e.g., nginx:latest", height=32)
        self.manual_image.grid(row=1, column=1, sticky="ew", padx=(0, 5), pady=3)
        
        # Description - Row 2
        ctk.CTkLabel(form_grid, text="Description:", width=80, anchor="w").grid(row=2, column=0, sticky="w", padx=(5, 8), pady=3)
        self.manual_description = ctk.CTkEntry(form_grid, placeholder_text="Brief description", height=32)
        self.manual_description.grid(row=2, column=1, sticky="ew", padx=(0, 5), pady=3)
        
        # Logo URL - Row 3
        ctk.CTkLabel(form_grid, text="Logo URL:", width=80, anchor="w").grid(row=3, column=0, sticky="w", padx=(5, 8), pady=3)
        self.manual_logo = ctk.CTkEntry(form_grid, placeholder_text="https://example.com/logo.png", height=32)
        self.manual_logo.grid(row=3, column=1, sticky="ew", padx=(0, 5), pady=3)
        
        # Platform and Restart Policy - Row 4 (side by side)
        config_frame = ctk.CTkFrame(form_grid)
        config_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=5, pady=3)
        config_frame.grid_columnconfigure(1, weight=1)
        config_frame.grid_columnconfigure(3, weight=1)
        
        ctk.CTkLabel(config_frame, text="Platform:", width=70, anchor="w").grid(row=0, column=0, sticky="w", padx=(5, 5))
        self.manual_platform = ctk.CTkComboBox(config_frame, values=["linux", "windows"], width=100, height=32)
        self.manual_platform.grid(row=0, column=1, sticky="w", padx=(0, 15))
        self.manual_platform.set("linux")
        
        ctk.CTkLabel(config_frame, text="Restart:", width=70, anchor="w").grid(row=0, column=2, sticky="w", padx=(5, 5))
        self.manual_restart = ctk.CTkComboBox(config_frame, values=["unless-stopped", "always", "no", "on-failure"], width=130, height=32)
        self.manual_restart.grid(row=0, column=3, sticky="w", padx=(0, 5))
        self.manual_restart.set("unless-stopped")
        
        # Note - Row 5 (Large multiline text area)
        ctk.CTkLabel(form_grid, text="Note:", width=80, anchor="nw").grid(row=5, column=0, sticky="nw", padx=(5, 8), pady=(8, 3))
        
        # Create large textbox directly in the grid
        self.manual_note = ctk.CTkTextbox(form_grid, height=150, wrap="word", font=ctk.CTkFont(size=11))
        self.manual_note.grid(row=5, column=1, sticky="ew", padx=(0, 5), pady=3)
        
        # Add placeholder text functionality with better messaging
        self.manual_note_placeholder = """Enter additional information about this template.
You can use multiple lines and include helpful details like:
• Setup instructions
• Important notes  
• Links to documentation
• HTML tags (will be stored as text for Container Station)"""
        
        self.manual_note.insert("1.0", self.manual_note_placeholder)
        self.manual_note.configure(text_color="gray")
        
        def on_note_focus_in(event):
            current_text = self.manual_note.get("1.0", "end-1c")
            if current_text == self.manual_note_placeholder:
                self.manual_note.delete("1.0", tk.END)
                self.manual_note.configure(text_color=("gray10", "gray90"))
        
        def on_note_focus_out(event):
            current_text = self.manual_note.get("1.0", "end-1c").strip()
            if not current_text:
                self.manual_note.insert("1.0", self.manual_note_placeholder)
                self.manual_note.configure(text_color="gray")
        
        self.manual_note.bind("<FocusIn>", on_note_focus_in)
        self.manual_note.bind("<FocusOut>", on_note_focus_out)
        
        # Administrator Only - Row 6
        admin_frame = ctk.CTkFrame(form_grid)
        admin_frame.grid(row=6, column=0, columnspan=2, sticky="w", padx=5, pady=(3, 8))
        self.manual_admin_only = ctk.CTkCheckBox(admin_frame, text="Administrator Only")
        self.manual_admin_only.pack(side="left", padx=5)
        
        # Action Buttons
        action_frame = ctk.CTkFrame(left_panel)
        action_frame.pack(fill="x", padx=2, pady=3)
        
        button_container = ctk.CTkFrame(action_frame)
        button_container.pack(pady=8)
        
        self.clear_form_btn = ctk.CTkButton(button_container, text="Clear Form", 
                                           command=self.clear_manual_form, width=100, height=35)
        self.clear_form_btn.pack(side="left", padx=5)
        
        self.add_template_btn = ctk.CTkButton(button_container, text="Add Template", 
                                             command=self.add_manual_template, width=100, height=35,
                                             font=ctk.CTkFont(weight="bold"))
        self.add_template_btn.pack(side="left", padx=5)
        
        # Debug button for troubleshooting
        self.debug_btn = ctk.CTkButton(button_container, text="Debug UI", 
                                      command=self.debug_ui_elements, width=80, height=35)
        self.debug_btn.pack(side="left", padx=5)
        
        # === RIGHT PANEL - Configuration Lists ===
        
        # Categories Section
        categories_frame = ctk.CTkFrame(right_panel)
        categories_frame.pack(fill="x", padx=2, pady=3)
        
        cat_header = ctk.CTkFrame(categories_frame)
        cat_header.pack(fill="x", padx=5, pady=(5, 3))
        
        ctk.CTkLabel(cat_header, text="Categories", 
                    font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        
        ctk.CTkButton(cat_header, text="🔄", command=self.refresh_categories, 
                     width=25, height=25, font=ctk.CTkFont(size=12)).pack(side="right")
        
        # Category input
        cat_input_frame = ctk.CTkFrame(categories_frame)
        cat_input_frame.pack(fill="x", padx=5, pady=3)
        cat_input_frame.grid_columnconfigure(1, weight=1)
        
        self.manual_category_combo = ctk.CTkComboBox(cat_input_frame, values=["webserver", "database", "media", "networking", "tools"], 
                                                    width=120, height=28, command=self.on_category_selected)
        self.manual_category_combo.grid(row=0, column=0, sticky="w", padx=(5, 5))
        self.manual_category_combo.set("Select...")
        
        self.manual_category_entry = ctk.CTkEntry(cat_input_frame, placeholder_text="or type custom", height=28)
        self.manual_category_entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        
        ctk.CTkButton(cat_input_frame, text="Add", command=self.add_category, width=50, height=28).grid(row=0, column=2, padx=(0, 5))
        
        # Categories list with scrollbar
        cat_list_frame = ctk.CTkFrame(categories_frame)
        cat_list_frame.pack(fill="x", padx=5, pady=3)
        
        self.categories_listbox = tk.Listbox(cat_list_frame, height=3, font=("Segoe UI", 9))
        self.categories_listbox.pack(fill="x", pady=(0, 3))
        self.categories_listbox.bind("<Double-Button-1>", self.edit_category)
        
        cat_buttons = ctk.CTkFrame(cat_list_frame)
        cat_buttons.pack(fill="x")
        
        ctk.CTkButton(cat_buttons, text="Edit", command=self.edit_category, width=60, height=25).pack(side="left", padx=(5, 2))
        ctk.CTkButton(cat_buttons, text="Remove", command=self.remove_category, width=60, height=25).pack(side="left", padx=2)
        
        
        # Environment Variables Section
        env_frame = ctk.CTkFrame(right_panel)
        env_frame.pack(fill="x", padx=2, pady=3)
        
        ctk.CTkLabel(env_frame, text="Environment Variables", 
                    font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(5, 3))
        
        # Environment input
        env_input_frame = ctk.CTkFrame(env_frame)
        env_input_frame.pack(fill="x", padx=5, pady=3)
        env_input_frame.grid_columnconfigure(1, weight=1)
        env_input_frame.grid_columnconfigure(3, weight=1)
        
        ctk.CTkLabel(env_input_frame, text="Name:", width=50, anchor="w").grid(row=0, column=0, sticky="w", padx=(5, 2))
        self.manual_env_name = ctk.CTkEntry(env_input_frame, placeholder_text="VAR_NAME", width=100, height=28)
        self.manual_env_name.grid(row=0, column=1, sticky="w", padx=2)
        
        ctk.CTkLabel(env_input_frame, text="Value:", width=50, anchor="w").grid(row=0, column=2, sticky="w", padx=(8, 2))
        self.manual_env_value = ctk.CTkEntry(env_input_frame, placeholder_text="default_value", height=28)
        self.manual_env_value.grid(row=0, column=3, sticky="ew", padx=2)
        
        ctk.CTkButton(env_input_frame, text="Add", command=self.add_env_var, width=50, height=28).grid(row=0, column=4, padx=(5, 5))
        
        # Environment list with edit capability
        env_list_frame = ctk.CTkFrame(env_frame)
        env_list_frame.pack(fill="x", padx=5, pady=3)
        
        self.env_listbox = tk.Listbox(env_list_frame, height=4, font=("Segoe UI", 9))
        self.env_listbox.pack(fill="x", pady=(0, 3))
        self.env_listbox.bind("<Double-Button-1>", self.edit_env_var)
        
        env_buttons = ctk.CTkFrame(env_list_frame)
        env_buttons.pack(fill="x")
        
        ctk.CTkButton(env_buttons, text="Edit", command=self.edit_env_var, width=60, height=25).pack(side="left", padx=(5, 2))
        ctk.CTkButton(env_buttons, text="Remove", command=self.remove_env_var, width=60, height=25).pack(side="left", padx=2)
        
        
        # Ports Section - AGGRESSIVE FIX: Complete rewrite with standard tkinter
        ports_frame = ctk.CTkFrame(right_panel)
        ports_frame.pack(fill="x", padx=2, pady=3)
        
        print("DEBUG: Creating Ports section - AGGRESSIVE LAYOUT FIX")
        
        ctk.CTkLabel(ports_frame, text="Ports", 
                    font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(5, 3))
        
        # COMPLETELY NEW APPROACH: Use tkinter Frame inside CustomTkinter
        ports_tk_frame = tk.Frame(ports_frame, bg='white', relief='solid', bd=1)
        ports_tk_frame.pack(fill="x", padx=5, pady=5)
        
        # Port input using standard tkinter widgets
        port_input_tk_frame = tk.Frame(ports_tk_frame, bg='white')
        port_input_tk_frame.pack(fill="x", padx=5, pady=5)
        
        tk.Label(port_input_tk_frame, text="Label:", bg='white', width=8).pack(side="left", padx=(0, 5))
        self.manual_port_label = tk.Entry(port_input_tk_frame, width=12)
        self.manual_port_label.pack(side="left", padx=2)
        self.manual_port_label.insert(0, "WebUI")
        
        tk.Label(port_input_tk_frame, text="Port:", bg='white', width=6).pack(side="left", padx=(5, 5))
        self.manual_port_number = tk.Entry(port_input_tk_frame, width=12)
        self.manual_port_number.pack(side="left", padx=2)
        self.manual_port_number.insert(0, "80/tcp")
        
        # FORCE VISIBLE BUTTON with tkinter
        port_add_btn = tk.Button(port_input_tk_frame, text="Add", command=self.add_port, 
                                bg='#1f6aa5', fg='white', width=8, relief='flat')
        port_add_btn.pack(side="left", padx=(10, 5))
        print("DEBUG: Port Add button FORCED VISIBLE with tkinter")
        
        # Ports list
        self.ports_listbox = tk.Listbox(ports_tk_frame, height=3, font=("Segoe UI", 9))
        self.ports_listbox.pack(fill="x", padx=5, pady=5)
        self.ports_listbox.bind("<Double-Button-1>", self.edit_port)
        
        # FORCE VISIBLE EDIT/REMOVE BUTTONS
        port_buttons_tk = tk.Frame(ports_tk_frame, bg='white')
        port_buttons_tk.pack(fill="x", padx=5, pady=5)
        
        port_edit_btn = tk.Button(port_buttons_tk, text="Edit", command=self.edit_port, 
                                 bg='#1f6aa5', fg='white', width=8, relief='flat')
        port_edit_btn.pack(side="left", padx=(5, 2))
        
        port_remove_btn = tk.Button(port_buttons_tk, text="Remove", command=self.remove_port, 
                                   bg='#dc3545', fg='white', width=8, relief='flat')
        port_remove_btn.pack(side="left", padx=2)
        
        print("DEBUG: Ports section FORCED VISIBLE with tkinter widgets")
        
        
        # Volumes Section - AGGRESSIVE FIX: Complete rewrite with standard tkinter
        volumes_frame = ctk.CTkFrame(right_panel)
        volumes_frame.pack(fill="x", padx=2, pady=3)
        
        print("DEBUG: Creating Volumes section - AGGRESSIVE LAYOUT FIX")
        
        ctk.CTkLabel(volumes_frame, text="Volumes", 
                    font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(5, 3))
        
        # COMPLETELY NEW APPROACH: Use tkinter Frame inside CustomTkinter
        volumes_tk_frame = tk.Frame(volumes_frame, bg='white', relief='solid', bd=1)
        volumes_tk_frame.pack(fill="x", padx=5, pady=5)
        
        # Volume input using standard tkinter widgets
        volume_input_tk_frame = tk.Frame(volumes_tk_frame, bg='white')
        volume_input_tk_frame.pack(fill="x", padx=5, pady=5)
        
        tk.Label(volume_input_tk_frame, text="Container:", bg='white', width=10).pack(side="left", padx=(0, 5))
        self.manual_volume_container = tk.Entry(volume_input_tk_frame, width=15)
        self.manual_volume_container.pack(side="left", padx=2)
        self.manual_volume_container.insert(0, "/app/data")
        
        tk.Label(volume_input_tk_frame, text="Bind:", bg='white', width=6).pack(side="left", padx=(5, 5))
        self.manual_volume_bind = tk.Entry(volume_input_tk_frame, width=15)
        self.manual_volume_bind.pack(side="left", padx=2)
        self.manual_volume_bind.insert(0, "!data/app")
        
        # FORCE VISIBLE BUTTON with tkinter
        volume_add_btn = tk.Button(volume_input_tk_frame, text="Add", command=self.add_volume, 
                                  bg='#1f6aa5', fg='white', width=8, relief='flat')
        volume_add_btn.pack(side="left", padx=(10, 5))
        print("DEBUG: Volume Add button FORCED VISIBLE with tkinter")
        
        # Volumes list
        self.volumes_listbox = tk.Listbox(volumes_tk_frame, height=3, font=("Segoe UI", 9))
        self.volumes_listbox.pack(fill="x", padx=5, pady=5)
        self.volumes_listbox.bind("<Double-Button-1>", self.edit_volume)
        
        # FORCE VISIBLE EDIT/REMOVE BUTTONS
        volume_buttons_tk = tk.Frame(volumes_tk_frame, bg='white')
        volume_buttons_tk.pack(fill="x", padx=5, pady=5)
        
        volume_edit_btn = tk.Button(volume_buttons_tk, text="Edit", command=self.edit_volume, 
                                   bg='#1f6aa5', fg='white', width=8, relief='flat')
        volume_edit_btn.pack(side="left", padx=(5, 2))
        
        volume_remove_btn = tk.Button(volume_buttons_tk, text="Remove", command=self.remove_volume, 
                                     bg='#dc3545', fg='white', width=8, relief='flat')
        volume_remove_btn.pack(side="left", padx=2)
        
        print("DEBUG: Volumes section FORCED VISIBLE with tkinter widgets")
        
        # Manual Templates List (bottom of right panel)
        list_frame = ctk.CTkFrame(right_panel)
        list_frame.pack(fill="x", padx=2, pady=(10, 3))
        
        ctk.CTkLabel(list_frame, text="Created Templates", 
                    font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(5, 3))
        
        self.manual_templates_listbox = tk.Listbox(list_frame, height=4, font=("Segoe UI", 9))
        self.manual_templates_listbox.pack(fill="x", padx=5, pady=(0, 3))
        
        manual_buttons_frame = ctk.CTkFrame(list_frame)
        manual_buttons_frame.pack(pady=(0, 5))
        
        self.edit_manual_btn = ctk.CTkButton(manual_buttons_frame, text="Edit", 
                                            command=self.edit_manual_template, width=80, height=28)
        self.edit_manual_btn.pack(side="left", padx=2)
        
        self.delete_manual_btn = ctk.CTkButton(manual_buttons_frame, text="Delete", 
                                              command=self.delete_manual_template, width=80, height=28)
        self.delete_manual_btn.pack(side="left", padx=2)
    
    def setup_edit_templates_tab(self):
        """Set up the template editing tab"""
        tab_edit = self.notebook.add("Edit Templates")
        
        # Instructions
        instructions_frame = ctk.CTkFrame(tab_edit)
        instructions_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(instructions_frame, text="Edit Individual Templates", 
                    font=ctk.CTkFont(size=18, weight="bold")).pack(pady=5)
        
        ctk.CTkLabel(instructions_frame, 
                    text="Select templates from loaded sources to edit. Changes will be saved as new manual templates.",
                    font=ctk.CTkFont(size=12)).pack(pady=(0, 5))
        
        # Template list and controls
        list_control_frame = ctk.CTkFrame(tab_edit)
        list_control_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Filter and search
        filter_frame = ctk.CTkFrame(list_control_frame)
        filter_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(filter_frame, text="Filter:", width=60).pack(side="left", padx=(10, 5))
        self.edit_filter_entry = ctk.CTkEntry(filter_frame, placeholder_text="Search templates by title or image...")
        self.edit_filter_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.edit_filter_entry.bind("<KeyRelease>", self.filter_edit_templates)
        
        ctk.CTkButton(filter_frame, text="Refresh List", command=self.refresh_edit_templates_list, 
                     width=100).pack(side="right", padx=5)
        
        # Source filter
        source_filter_frame = ctk.CTkFrame(list_control_frame)
        source_filter_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(source_filter_frame, text="Source:", width=60).pack(side="left", padx=(10, 5))
        self.source_filter_combo = ctk.CTkComboBox(source_filter_frame, values=["All Sources"], 
                                                  command=self.filter_by_source, width=200)
        self.source_filter_combo.pack(side="left", padx=5)
        self.source_filter_combo.set("All Sources")
        
        # Templates list with scrollbars
        listbox_frame = ctk.CTkFrame(list_control_frame)
        listbox_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create listbox with scrollbars
        self.edit_templates_listbox = tk.Listbox(listbox_frame, height=15)
        self.edit_templates_listbox.pack(side="left", fill="both", expand=True)
        self.edit_templates_listbox.bind("<Double-Button-1>", self.edit_selected_template)
        
        # Vertical scrollbar
        v_scrollbar = tk.Scrollbar(listbox_frame, orient="vertical", command=self.edit_templates_listbox.yview)
        v_scrollbar.pack(side="right", fill="y")
        self.edit_templates_listbox.configure(yscrollcommand=v_scrollbar.set)
        
        # Horizontal scrollbar
        h_scrollbar_frame = ctk.CTkFrame(list_control_frame)
        h_scrollbar_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        h_scrollbar = tk.Scrollbar(h_scrollbar_frame, orient="horizontal", command=self.edit_templates_listbox.xview)
        h_scrollbar.pack(fill="x")
        self.edit_templates_listbox.configure(xscrollcommand=h_scrollbar.set)
        
        # Action buttons
        action_frame = ctk.CTkFrame(list_control_frame)
        action_frame.pack(fill="x", padx=10, pady=5)
        
        self.edit_template_btn = ctk.CTkButton(action_frame, text="Edit Selected Template", 
                                              command=self.edit_selected_template, width=150,
                                              font=ctk.CTkFont(weight="bold"))
        self.edit_template_btn.pack(side="left", padx=5)
        
        self.clone_template_btn = ctk.CTkButton(action_frame, text="Clone Template", 
                                               command=self.clone_selected_template, width=120)
        self.clone_template_btn.pack(side="left", padx=5)
        
        self.view_template_btn = ctk.CTkButton(action_frame, text="View JSON", 
                                              command=self.view_template_json, width=100)
        self.view_template_btn.pack(side="left", padx=5)
        
        # Status
        self.edit_status_label = ctk.CTkLabel(tab_edit, text="Load templates from Sources tab to begin editing")
        self.edit_status_label.pack(pady=5)
    
    def load_base_template(self):
        """Load the base template from configured URL"""
        if not self.base_template_enabled:
            self.update_status("Base template is disabled")
            return
            
        def load_thread():
            try:
                self.update_status("Loading base template...")
                response = requests.get(self.base_template_url, timeout=30)
                response.raise_for_status()
                
                base_data = response.json()
                
                # Convert to Portainer format if needed
                from utils import TemplateConverter
                try:
                    converted_data = TemplateConverter.convert_to_portainer(base_data)
                    # Store with special key to distinguish from URL sources
                    self.loaded_templates[f"BASE_TEMPLATE:{self.base_template_url}"] = converted_data
                except ValueError as e:
                    self.update_status(f"Base template format conversion error: {str(e)}")
                    # Store as-is if conversion fails
                    self.loaded_templates[f"BASE_TEMPLATE:{self.base_template_url}"] = base_data
                
                # DO NOT add to URL sources - base template is separate!
                self.update_status("Base template loaded successfully")
            except Exception as e:
                self.update_status(f"Error loading base template: {str(e)}")
        
        threading.Thread(target=load_thread, daemon=True).start()
    
    def add_url_source(self):
        """Add a URL source"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a URL")
            return
        
        if url in self.url_sources:
            messagebox.showwarning("Warning", "URL already added")
            return
        
        # Validate URL
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                raise ValueError("Invalid URL")
        except:
            messagebox.showerror("Error", "Invalid URL format")
            return
        
        self.url_sources.append(url)
        self.url_listbox.insert(tk.END, url)
        self.url_entry.delete(0, tk.END)
    
    def remove_url_source(self):
        """Remove selected URL source"""
        selection = self.url_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a URL to remove")
            return
        
        index = selection[0]
        url = self.url_sources[index]
        
        # Remove from sources and UI
        del self.url_sources[index]
        self.url_listbox.delete(index)
        
        # Remove from loaded templates if exists
        if url in self.loaded_templates:
            del self.loaded_templates[url]
        
        self.update_status(f"Removed URL source: {url}")
    
    def add_file_source(self):
        """Add a local file source"""
        file_path = filedialog.askopenfilename(
            title="Select Template File",
            filetypes=[
                ("Template files", "*.json;*.yml;*.yaml"),
                ("JSON files", "*.json"), 
                ("YAML files", "*.yml;*.yaml"),
                ("Docker Compose", "docker-compose*.yml;docker-compose*.yaml;compose*.yml;compose*.yaml"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        if file_path in self.file_sources:
            messagebox.showwarning("Warning", "File already added")
            return
        
        self.file_sources.append(file_path)
        self.file_listbox.insert(tk.END, os.path.basename(file_path))
    
    def remove_file_source(self):
        """Remove selected file source"""
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a file to remove")
            return
        
        index = selection[0]
        file_path = self.file_sources[index]
        
        del self.file_sources[index]
        self.file_listbox.delete(index)
        
        # Remove from loaded templates if exists
        if file_path in self.loaded_templates:
            del self.loaded_templates[file_path]
    
    def process_sources(self):
        """Process all sources and load JSON data"""
        if not self.url_sources and not self.file_sources:
            messagebox.showwarning("Warning", "Please add at least one source")
            return
        
        def process_thread():
            try:
                total_sources = len(self.url_sources) + len(self.file_sources)
                current = 0
                
                # Process URL sources
                for url in self.url_sources:
                    if url not in self.loaded_templates:  # Skip if already loaded
                        self.update_status(f"Loading URL: {url}")
                        try:
                            response = requests.get(url, timeout=30)
                            response.raise_for_status()
                            data = response.json()
                            
                            # Convert to Portainer format if needed
                            from utils import TemplateConverter
                            try:
                                converted_data = TemplateConverter.convert_to_portainer(data)
                                self.loaded_templates[url] = converted_data
                            except ValueError as e:
                                self.update_status(f"Format conversion error for {url}: {str(e)}")
                                # Try to store as-is if conversion fails
                                self.loaded_templates[url] = data
                                
                        except Exception as e:
                            self.update_status(f"Error loading {url}: {str(e)}")
                    
                    current += 1
                    self.progress.set(current / total_sources)
                
                # Process file sources
                for file_path in self.file_sources:
                    if file_path not in self.loaded_templates:  # Skip if already loaded
                        self.update_status(f"Loading file: {os.path.basename(file_path)}")
                        try:
                            # Determine file type and load accordingly
                            file_extension = file_path.lower().split('.')[-1]
                            
                            if file_extension in ['yml', 'yaml']:
                                # Load YAML file
                                import yaml
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    data = yaml.safe_load(f)
                            else:
                                # Load JSON file
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    data = json.load(f)
                            
                            # Convert to Portainer format if needed
                            from utils import TemplateConverter
                            try:
                                converted_data = TemplateConverter.convert_to_portainer(data)
                                self.loaded_templates[file_path] = converted_data
                                
                                # Determine what type of conversion was done
                                format_type = TemplateConverter.detect_format(data)
                                if format_type == 'docker_compose':
                                    self.update_status(f"Loaded Docker Compose file: {os.path.basename(file_path)}")
                                elif file_extension in ['yml', 'yaml']:
                                    self.update_status(f"Loaded YAML file: {os.path.basename(file_path)}")
                                else:
                                    self.update_status(f"Loaded JSON file: {os.path.basename(file_path)}")
                                    
                            except ValueError as e:
                                self.update_status(f"Format conversion error for {file_path}: {str(e)}")
                                # Try to store as-is if conversion fails
                                self.loaded_templates[file_path] = data
                                
                        except Exception as e:
                            self.update_status(f"Error loading {file_path}: {str(e)}")
                    
                    current += 1
                    self.progress.set(current / total_sources)
                
                self.update_status("All sources processed successfully")
                self.generate_summary()
                
                # Refresh categories and edit templates list
                self.refresh_categories()
                self.refresh_edit_templates_list()
                
            except Exception as e:
                self.update_status(f"Error processing sources: {str(e)}")
        
        threading.Thread(target=process_thread, daemon=True).start()
    
    def generate_summary(self):
        """Generate processing summary"""
        summary = []
        total_templates = 0
        source_count = 0
        
        # Include manual templates in summary
        if self.manual_templates:
            manual_count = len(self.manual_templates)
            total_templates += manual_count
            source_count += 1
            summary.append(f"✓ Manual Entry: {manual_count} templates")
        
        # Separate base template from other sources
        base_template_count = 0
        
        for source, data in self.loaded_templates.items():
            # Check if this is the base template
            if source.startswith("BASE_TEMPLATE:"):
                base_url = source.replace("BASE_TEMPLATE:", "")
                base_name = f"Base Template ({base_url.split('/')[-1] if '/' in base_url else base_url})"
                
                if isinstance(data, dict):
                    if 'templates' in data and isinstance(data['templates'], list):
                        template_count = len(data['templates'])
                        total_templates += template_count
                        base_template_count = template_count
                        summary.insert(0, f"✓ {base_name}: {template_count} templates")
                        source_count += 1
                continue
            
            # Handle regular sources
            source_name = os.path.basename(source) if os.path.exists(source) else source
            
            # Shorten long URLs for display
            if not os.path.exists(source) and len(source_name) > 50:
                source_name = f"...{source_name[-40:]}"
            
            if isinstance(data, dict):
                if 'templates' in data and isinstance(data['templates'], list):
                    template_count = len(data['templates'])
                    total_templates += template_count
                    source_count += 1
                    summary.append(f"✓ {source_name}: {template_count} templates")
                elif isinstance(data, list):
                    template_count = len(data)
                    total_templates += template_count
                    source_count += 1
                    summary.append(f"✓ {source_name}: {template_count} templates")
                else:
                    # Try to extract using the new converter
                    try:
                        from utils import JSONValidator
                        extracted = JSONValidator.extract_templates(data)
                        template_count = len(extracted)
                        total_templates += template_count
                        source_count += 1
                        summary.append(f"✓ {source_name}: {template_count} templates (converted)")
                    except:
                        summary.append(f"? {source_name}: Unknown format")
            else:
                summary.append(f"✗ {source_name}: Invalid JSON format")
        
        # Add totals at the top
        summary.insert(0, f"Total sources processed: {source_count}")
        summary.insert(1, f"Total templates found: {total_templates}")
        summary.append("")
        summary.append("Click 'Generate Final Template' to combine and deduplicate templates.")
        summary.append("Manual templates will be included in the final output.")
        if base_template_count > 0:
            summary.append("Base template is loaded separately from URL sources.")
        
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert("1.0", "\n".join(summary))
        
        # Switch to preview tab
        self.notebook.set("Preview")
    
    def generate_final_template(self):
        """Generate the final combined template"""
        def generate_thread():
            try:
                self.update_status("Generating final template...")
                
                all_templates = []
                
                # Include manually created templates
                for template in self.manual_templates:
                    # Add source info for tracking
                    template_copy = template.copy()
                    template_copy['_source'] = 'manual_entry'
                    all_templates.append(template_copy)
                
                # Collect all templates from all sources
                for source, data in self.loaded_templates.items():
                    # Use the updated extraction method
                    from utils import JSONValidator
                    try:
                        templates = JSONValidator.extract_templates(data)
                    except:
                        # Fallback to old method
                        if isinstance(data, dict) and 'templates' in data:
                            templates = data['templates']
                        elif isinstance(data, list):
                            templates = data
                        else:
                            continue
                    
                    for template in templates:
                        if isinstance(template, dict):
                            # Add source info for tracking
                            template['_source'] = source
                            all_templates.append(template)
                
                # Process templates for duplicates and architecture
                processed_templates = self.process_duplicate_templates(all_templates)
                
                # Create final template structure
                self.final_template = {
                    "version": "2",
                    "templates": processed_templates
                }
                
                # Update preview
                self.preview_text.delete("1.0", tk.END)
                self.preview_text.insert("1.0", json.dumps(self.final_template, indent=2))
                
                self.update_status(f"Final template generated with {len(processed_templates)} templates")
                
                # Update summary with deduplication info
                self.update_summary_with_dedup_info(len(all_templates), len(processed_templates))
                
            except Exception as e:
                self.update_status(f"Error generating template: {str(e)}")
        
        threading.Thread(target=generate_thread, daemon=True).start()
    
    def process_duplicate_templates(self, templates: List[Dict]) -> List[Dict]:
        """Process templates to handle duplicates and architecture variants"""
        processed = []
        template_groups = {}
        
        # Group templates by name/title
        for template in templates:
            title = template.get('title', '').strip()
            if not title:
                continue
            
            if title not in template_groups:
                template_groups[title] = []
            template_groups[title].append(template)
        
        # Process each group
        for title, group in template_groups.items():
            if len(group) == 1:
                # Single template, just clean and add
                clean_template = self.clean_template(group[0])
                processed.append(clean_template)
            else:
                # Multiple templates with same title
                processed.extend(self.handle_duplicate_group(title, group))
        
        return processed
    
    def handle_duplicate_group(self, title: str, group: List[Dict]) -> List[Dict]:
        """Handle a group of templates with the same title"""
        result = []
        
        # Compare all templates in the group
        unique_templates = []
        architecture_variants = {}
        
        for template in group:
            is_duplicate = False
            arch = TemplateComparator.detect_architecture(template)
            
            # Check similarity with existing unique templates
            for existing in unique_templates:
                similarity = TemplateComparator.calculate_similarity(template, existing)
                
                if similarity >= 0.7:  # 70% similarity threshold
                    is_duplicate = True
                    existing_arch = TemplateComparator.detect_architecture(existing)
                    
                    # If architectures are different, keep both with architecture suffix
                    if arch != existing_arch:
                        if arch not in architecture_variants:
                            architecture_variants[arch] = template
                        if existing_arch not in architecture_variants:
                            architecture_variants[existing_arch] = existing
                    else:
                        # Same architecture, pick the best one
                        if self.is_better_template(template, existing):
                            # Replace existing with current
                            unique_templates[unique_templates.index(existing)] = template
                    break
            
            if not is_duplicate:
                unique_templates.append(template)
        
        # Handle architecture variants
        if architecture_variants:
            for arch, template in architecture_variants.items():
                clean_template = self.clean_template(template)
                clean_template['title'] = f"{title}-{arch}"
                result.append(clean_template)
            
            # Remove any templates that became architecture variants from unique_templates
            for template in architecture_variants.values():
                if template in unique_templates:
                    unique_templates.remove(template)
        
        # Add remaining unique templates
        for template in unique_templates:
            clean_template = self.clean_template(template)
            result.append(clean_template)
        
        return result
    
    def is_better_template(self, template1: Dict, template2: Dict) -> bool:
        """Determine which template is better based on completeness and quality"""
        score1 = self.calculate_template_score(template1)
        score2 = self.calculate_template_score(template2)
        return score1 > score2
    
    def calculate_template_score(self, template: Dict) -> int:
        """Calculate a quality score for a template"""
        score = 0
        
        # Check for required fields
        if template.get('title'): score += 10
        if template.get('description'): score += 8
        if template.get('image'): score += 10
        
        # Check for optional but useful fields
        if template.get('categories'): score += 5
        if template.get('platform'): score += 3
        if template.get('logo'): score += 2
        if template.get('env'): score += len(template['env'])
        if template.get('ports'): score += len(template['ports']) * 2
        if template.get('volumes'): score += len(template['volumes']) * 2
        
        # Check repository/compose content
        if template.get('repository'):
            repo = template['repository']
            if repo.get('stackfile'): score += 15
            if repo.get('url'): score += 5
        
        # Penalize templates with missing critical info
        if not template.get('image'): score -= 20
        if not template.get('description'): score -= 10
        
        return score
    
    def clean_template(self, template: Dict) -> Dict:
        """Clean template by removing internal fields"""
        clean = template.copy()
        
        # Remove internal tracking fields
        if '_source' in clean:
            del clean['_source']
        
        return clean
    
    def update_summary_with_dedup_info(self, original_count: int, final_count: int):
        """Update summary with deduplication information"""
        current_text = self.summary_text.get("1.0", tk.END)
        
        dedup_info = f"\n--- Processing Complete ---\n"
        dedup_info += f"Original templates: {original_count}\n"
        dedup_info += f"Final templates: {final_count}\n"
        dedup_info += f"Duplicates removed: {original_count - final_count}\n"
        
        self.summary_text.insert(tk.END, dedup_info)
    
    def browse_save_location(self):
        """Browse for save location"""
        file_path = filedialog.asksaveasfilename(
            title="Save Template File",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="templates.json"
        )
        
        if file_path:
            self.save_path_entry.delete(0, tk.END)
            self.save_path_entry.insert(0, file_path)
    
    def save_template(self):
        """Save the final template to file"""
        if not self.final_template.get('templates'):
            messagebox.showwarning("Warning", "No template generated yet. Please generate a template first.")
            return
        
        save_path = self.save_path_entry.get().strip()
        if not save_path:
            messagebox.showwarning("Warning", "Please specify a save location")
            return
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            
            # Save the file
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(self.final_template, f, indent=2, ensure_ascii=False)
            
            self.save_status.configure(text=f"✓ Template saved successfully to: {save_path}")
            messagebox.showinfo("Success", f"Template saved successfully!\n\nLocation: {save_path}\nTemplates: {len(self.final_template['templates'])}")
            
        except Exception as e:
            error_msg = f"Error saving template: {str(e)}"
            self.save_status.configure(text=f"✗ {error_msg}")
            messagebox.showerror("Error", error_msg)
    
    def add_category(self):
        """Add a category to the list with proper validation and error handling"""
        try:
            # Check if UI elements exist
            if not hasattr(self, 'manual_category_entry') or not hasattr(self, 'manual_category_combo'):
                messagebox.showerror("Error", "Category input fields not found. Please restart the application.")
                return
            
            # Try to get from text entry first, then from dropdown
            category = self.manual_category_entry.get().strip()
            
            if not category:
                # Try dropdown selection
                dropdown_value = self.manual_category_combo.get()
                if dropdown_value and dropdown_value not in ["Select...", "Select or type category..."]:
                    category = dropdown_value
            
            if not category:
                messagebox.showwarning("Validation Error", "Please select a category from dropdown or enter a custom one")
                self.manual_category_entry.focus()
                return
            
            # Check if already in list
            categories_list = []
            for i in range(self.categories_listbox.size()):
                categories_list.append(self.categories_listbox.get(i))
            
            if category not in categories_list:
                self.categories_listbox.insert(tk.END, category)
                self.manual_category_entry.delete(0, tk.END)
                self.manual_category_combo.set("Select...")
                self.update_status(f"Category '{category}' added successfully")
            else:
                messagebox.showwarning("Duplicate Category", f"Category '{category}' is already added")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add category: {str(e)}")
            print(f"Error in add_category: {str(e)}")
    
    def remove_category(self):
        """Remove selected category with proper validation"""
        try:
            selection = self.categories_listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a category to remove")
                return
            
            index = selection[0]
            category_text = self.categories_listbox.get(index)
            
            if messagebox.askyesno("Confirm Delete", f"Remove category '{category_text}'?"):
                self.categories_listbox.delete(index)
                self.update_status(f"Category '{category_text}' removed")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove category: {str(e)}")
            print(f"Error in remove_category: {str(e)}")
    
    def add_env_var(self):
        """Add an environment variable with proper validation and error handling"""
        try:
            # Check if UI elements exist
            if not hasattr(self, 'manual_env_name') or not hasattr(self, 'manual_env_value'):
                messagebox.showerror("Error", "Environment variable input fields not found. Please restart the application.")
                return
            
            name = self.manual_env_name.get().strip()
            value = self.manual_env_value.get().strip()
            
            # Validation
            if not name:
                messagebox.showwarning("Validation Error", "Environment variable name is required")
                self.manual_env_name.focus()
                return
            
            # Check for duplicates
            for i in range(self.env_listbox.size()):
                existing = self.env_listbox.get(i)
                existing_name = existing.split('=')[0] if '=' in existing else existing
                if existing_name == name:
                    messagebox.showwarning("Duplicate Variable", f"Environment variable '{name}' already exists")
                    return
            
            # Add the environment variable
            display_text = f"{name}={value}" if value else name
            self.env_listbox.insert(tk.END, display_text)
            self.manual_env_name.delete(0, tk.END)
            self.manual_env_value.delete(0, tk.END)
            
            self.update_status(f"Environment variable '{display_text}' added successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add environment variable: {str(e)}")
            print(f"Error in add_env_var: {str(e)}")
    
    def remove_env_var(self):
        """Remove selected environment variable with proper validation"""
        try:
            selection = self.env_listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select an environment variable to remove")
                return
            
            index = selection[0]
            env_text = self.env_listbox.get(index)
            
            if messagebox.askyesno("Confirm Delete", f"Remove environment variable '{env_text}'?"):
                self.env_listbox.delete(index)
                self.update_status(f"Environment variable '{env_text}' removed")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove environment variable: {str(e)}")
            print(f"Error in remove_env_var: {str(e)}")
    
    def add_port(self):
        """Add a port mapping with proper validation and error handling"""
        try:
            # Check if UI elements exist
            if not hasattr(self, 'manual_port_label') or not hasattr(self, 'manual_port_number'):
                messagebox.showerror("Error", "Port input fields not found. Please restart the application.")
                return
            
            label = self.manual_port_label.get().strip()
            port = self.manual_port_number.get().strip()
            
            # Validation
            if not label:
                messagebox.showwarning("Validation Error", "Port label is required")
                self.manual_port_label.focus()
                return
            
            if not port:
                messagebox.showwarning("Validation Error", "Port number is required")
                self.manual_port_number.focus()
                return
            
            # Check for duplicates
            for i in range(self.ports_listbox.size()):
                existing = self.ports_listbox.get(i)
                if existing.startswith(f"{label}: "):
                    messagebox.showwarning("Duplicate Port", f"Port label '{label}' already exists")
                    return
            
            # Add the port
            display_text = f"{label}: {port}"
            self.ports_listbox.insert(tk.END, display_text)
            self.manual_port_label.delete(0, tk.END)
            self.manual_port_number.delete(0, tk.END)
            
            self.update_status(f"Port '{label}: {port}' added successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add port: {str(e)}")
            print(f"Error in add_port: {str(e)}")
    
    def remove_port(self):
        """Remove selected port with proper validation"""
        try:
            selection = self.ports_listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a port to remove")
                return
            
            index = selection[0]
            port_text = self.ports_listbox.get(index)
            
            if messagebox.askyesno("Confirm Delete", f"Remove port '{port_text}'?"):
                self.ports_listbox.delete(index)
                self.update_status(f"Port '{port_text}' removed")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove port: {str(e)}")
            print(f"Error in remove_port: {str(e)}")
    
    def add_volume(self):
        """Add a volume mapping with proper validation and error handling"""
        try:
            # Check if UI elements exist
            if not hasattr(self, 'manual_volume_container') or not hasattr(self, 'manual_volume_bind'):
                messagebox.showerror("Error", "Volume input fields not found. Please restart the application.")
                return
            
            container_path = self.manual_volume_container.get().strip()
            bind_path = self.manual_volume_bind.get().strip()
            
            # Validation
            if not container_path:
                messagebox.showwarning("Validation Error", "Container path is required")
                self.manual_volume_container.focus()
                return
            
            if not bind_path:
                messagebox.showwarning("Validation Error", "Bind path is required")
                self.manual_volume_bind.focus()
                return
            
            # Check for duplicates
            for i in range(self.volumes_listbox.size()):
                existing = self.volumes_listbox.get(i)
                if existing.startswith(f"{container_path} -> "):
                    messagebox.showwarning("Duplicate Volume", f"Container path '{container_path}' already exists")
                    return
            
            # Add the volume
            display_text = f"{container_path} -> {bind_path}"
            self.volumes_listbox.insert(tk.END, display_text)
            self.manual_volume_container.delete(0, tk.END)
            self.manual_volume_bind.delete(0, tk.END)
            
            self.update_status(f"Volume '{container_path} -> {bind_path}' added successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add volume: {str(e)}")
            print(f"Error in add_volume: {str(e)}")
    
    def remove_volume(self):
        """Remove selected volume with proper validation"""
        try:
            selection = self.volumes_listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a volume to remove")
                return
            
            index = selection[0]
            volume_text = self.volumes_listbox.get(index)
            
            if messagebox.askyesno("Confirm Delete", f"Remove volume '{volume_text}'?"):
                self.volumes_listbox.delete(index)
                self.update_status(f"Volume '{volume_text}' removed")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove volume: {str(e)}")
            print(f"Error in remove_volume: {str(e)}")
    
    def clear_manual_form(self):
        """Clear all manual form fields"""
        # Clear basic fields
        self.manual_title.delete(0, tk.END)
        self.manual_description.delete(0, tk.END)
        self.manual_image.delete(0, tk.END)
        self.manual_logo.delete(0, tk.END)
        
        # Clear multiline note field and restore placeholder
        self.manual_note.delete("1.0", tk.END)
        self.manual_note.insert("1.0", self.manual_note_placeholder)
        self.manual_note.configure(text_color="gray")
        
        # Reset dropdowns
        self.manual_platform.set("linux")
        self.manual_restart.set("unless-stopped")
        
        # Clear checkbox
        self.manual_admin_only.deselect()
        
        # Clear entry fields
        self.manual_category_entry.delete(0, tk.END)
        self.manual_env_name.delete(0, tk.END)
        self.manual_env_value.delete(0, tk.END)
        self.manual_port_label.delete(0, tk.END)
        self.manual_port_number.delete(0, tk.END)
        self.manual_volume_container.delete(0, tk.END)
        self.manual_volume_bind.delete(0, tk.END)
        
        # Clear listboxes
        self.categories_listbox.delete(0, tk.END)
        self.env_listbox.delete(0, tk.END)
        self.ports_listbox.delete(0, tk.END)
        self.volumes_listbox.delete(0, tk.END)
        
        # Reset editing context
        self.reset_editing_context()
    
    def reset_editing_context(self):
        """Reset the editing context and button state"""
        self.current_editing_context = None
        self.add_template_btn.configure(text="Add Template", 
                                       command=self.add_manual_template)
        self.clear_form_btn.configure(text="Clear Form",
                                     command=self.clear_manual_form)
    
    def cancel_edit(self):
        """Cancel editing and restore the template if it was a manual template"""
        if self.current_editing_context and self.current_editing_context.get('is_manual_template', False):
            # Restore the manual template that was being edited
            original_template = self.current_editing_context['original_template']
            self.manual_templates.append(original_template)
            self.manual_templates_listbox.insert(tk.END, f"{original_template['title']} - {original_template['image']}")
        
        # Clear form and reset context
        self.clear_manual_form()
        
        messagebox.showinfo("Edit Cancelled", "Template editing has been cancelled.")
    
    def save_edited_template(self):
        """Handle saving edited template with options"""
        if not self.current_editing_context:
            # Fallback to regular add if no editing context
            self.add_manual_template()
            return
        
        if not self.validate_manual_template():
            return
        
        # Build the edited template with comprehensive debugging
        print("DEBUG: (save_edited_template) About to build template from form...")
        print(f"DEBUG: (save_edited_template) Environment variables listbox has {self.env_listbox.size()} items")
        for i in range(self.env_listbox.size()):
            print(f"DEBUG: (save_edited_template) Env var {i}: '{self.env_listbox.get(i)}'")
        
        edited_template = self.build_template_from_form()
        
        if edited_template:
            print(f"DEBUG: (save_edited_template) Built template successfully")
            print(f"DEBUG: (save_edited_template) Template keys: {list(edited_template.keys())}")
            if 'env' in edited_template:
                print(f"DEBUG: (save_edited_template) Template has {len(edited_template['env'])} env vars: {edited_template['env']}")
            else:
                print("DEBUG: (save_edited_template) Template has NO env vars!")
        else:
            print("ERROR: (save_edited_template) Failed to build template from form!")
            return
        
        original_template = self.current_editing_context['original_template']
        template_info = self.current_editing_context['template_info']
        
        # Handle manual template editing differently
        if self.current_editing_context.get('is_manual_template', False):
            self.save_manual_template_changes(edited_template)
            return
        
        # Create save options dialog
        save_dialog = ctk.CTkToplevel(self.root)
        save_dialog.title("Save Template Changes")
        save_dialog.geometry("500x300")
        save_dialog.resizable(False, False)
        
        # Center the dialog
        save_dialog.transient(self.root)
        save_dialog.grab_set()
        
        # Header
        header_frame = ctk.CTkFrame(save_dialog)
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(header_frame, text="Choose How to Save Your Changes", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        ctk.CTkLabel(header_frame, 
                    text=f"Editing: {template_info['title']}\nSource: {self.get_source_display_name(template_info['source'])}", 
                    font=ctk.CTkFont(size=12)).pack(pady=(0, 10))
        
        # Options frame
        options_frame = ctk.CTkFrame(save_dialog)
        options_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Option 1: Save as new template
        option1_frame = ctk.CTkFrame(options_frame)
        option1_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(option1_frame, text="Option 1: Save as New Template", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(option1_frame, 
                    text="• Creates a new template in your manual templates list\n• Original template remains unchanged\n• Safe option - no risk of losing original", 
                    font=ctk.CTkFont(size=11)).pack(anchor="w", padx=20, pady=(0, 10))
        
        def save_as_new():
            save_dialog.destroy()
            self.save_as_new_template(edited_template)
        
        ctk.CTkButton(option1_frame, text="Save as New Template", 
                     command=save_as_new, width=200, height=35).pack(pady=(0, 10))
        
        # Option 2: Update source (if possible)
        option2_frame = ctk.CTkFrame(options_frame)
        option2_frame.pack(fill="x", padx=10, pady=10)
        
        source_path = template_info['source']
        can_update_source = self.can_update_source(source_path)
        
        ctk.CTkLabel(option2_frame, text="Option 2: Update Original Source", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        if can_update_source:
            ctk.CTkLabel(option2_frame, 
                        text="• Modifies the original template in the source file\n• Updates the template for future use\n• Requires write access to source file", 
                        font=ctk.CTkFont(size=11)).pack(anchor="w", padx=20, pady=(0, 10))
            
            def update_source():
                save_dialog.destroy()
                self.update_source_template(edited_template, template_info)
            
            ctk.CTkButton(option2_frame, text="Update Original Source", 
                         command=update_source, width=200, height=35).pack(pady=(0, 10))
        else:
            ctk.CTkLabel(option2_frame, 
                        text="• Cannot update this source (URL or read-only file)\n• Only 'Save as New Template' is available", 
                        font=ctk.CTkFont(size=11)).pack(anchor="w", padx=20, pady=(0, 10))
            
            ctk.CTkButton(option2_frame, text="Cannot Update Source", 
                         state="disabled", width=200, height=35).pack(pady=(0, 10))
        
        # Cancel button
        cancel_frame = ctk.CTkFrame(save_dialog)
        cancel_frame.pack(pady=10)
        
        ctk.CTkButton(cancel_frame, text="Cancel", command=save_dialog.destroy, 
                     width=100, height=35).pack()
    
    def can_update_source(self, source_path):
        """Check if we can update the source file"""
        # Can't update URLs or base templates
        if source_path.startswith("http") or source_path.startswith("BASE_TEMPLATE:"):
            return False
        
        # Check if file exists and is writable
        if os.path.exists(source_path):
            try:
                return os.access(source_path, os.W_OK)
            except:
                return False
        
        return False
    
    def build_template_from_form(self):
        """Build template object from current form data with debugging"""
        try:
            # Build template object (same logic as add_manual_template)
            template = {
                "title": self.manual_title.get().strip(),
                "description": self.manual_description.get().strip(),
                "image": self.manual_image.get().strip(),
                "platform": self.manual_platform.get(),
                "restart_policy": self.manual_restart.get()
            }
            
            # Add optional fields
            logo = self.manual_logo.get().strip()
            if logo:
                template["logo"] = logo
            
            # Get note text and clean it (multiline textbox)
            note_text = self.manual_note.get("1.0", "end-1c").strip()
            if note_text and note_text != self.manual_note_placeholder:
                template["note"] = note_text
            
            if self.manual_admin_only.get():
                template["administrator_only"] = True
            
            # Add categories with debugging
            categories = []
            try:
                for i in range(self.categories_listbox.size()):
                    category = self.categories_listbox.get(i)
                    if category and category.strip():
                        categories.append(category.strip())
                if categories:
                    template["categories"] = categories
                    print(f"DEBUG: Added {len(categories)} categories: {categories}")
                else:
                    print("DEBUG: No categories found in listbox")
            except Exception as e:
                print(f"DEBUG: Error extracting categories: {str(e)}")
            
            # Add environment variables with debugging
            env_vars = []
            try:
                for i in range(self.env_listbox.size()):
                    env_text = self.env_listbox.get(i)
                    if env_text and env_text.strip():
                        if '=' in env_text:
                            name, value = env_text.split('=', 1)
                            env_vars.append({"name": name.strip(), "default": value.strip()})
                        else:
                            env_vars.append({"name": env_text.strip()})
                if env_vars:
                    template["env"] = env_vars
                    print(f"DEBUG: Added {len(env_vars)} environment variables: {[e.get('name') for e in env_vars]}")
                else:
                    print("DEBUG: No environment variables found in listbox")
            except Exception as e:
                print(f"DEBUG: Error extracting environment variables: {str(e)}")
            
            # Add ports with debugging
            ports = []
            try:
                for i in range(self.ports_listbox.size()):
                    port_text = self.ports_listbox.get(i)
                    if port_text and port_text.strip() and ': ' in port_text:
                        label, port_num = port_text.split(': ', 1)
                        ports.append({label.strip(): port_num.strip()})
                if ports:
                    template["ports"] = ports
                    print(f"DEBUG: Added {len(ports)} ports: {ports}")
                else:
                    print("DEBUG: No ports found in listbox")
            except Exception as e:
                print(f"DEBUG: Error extracting ports: {str(e)}")
            
            # Add volumes with debugging
            volumes = []
            try:
                for i in range(self.volumes_listbox.size()):
                    volume_text = self.volumes_listbox.get(i)
                    if volume_text and volume_text.strip() and ' -> ' in volume_text:
                        container_path, bind_path = volume_text.split(' -> ', 1)
                        volumes.append({"container": container_path.strip(), "bind": bind_path.strip()})
                if volumes:
                    template["volumes"] = volumes
                    print(f"DEBUG: Added {len(volumes)} volumes: {volumes}")
                else:
                    print("DEBUG: No volumes found in listbox")
            except Exception as e:
                print(f"DEBUG: Error extracting volumes: {str(e)}")
            
            print(f"DEBUG: Final template structure: {list(template.keys())}")
            return template
            
        except Exception as e:
            print(f"ERROR in build_template_from_form: {str(e)}")
            messagebox.showerror("Error", f"Failed to build template from form: {str(e)}")
            return None
    
    def save_as_new_template(self, template):
        """Save edited template as a new manual template"""
        # Add to manual templates list
        self.manual_templates.append(template)
        
        # Update listbox
        self.manual_templates_listbox.insert(tk.END, f"{template['title']} - {template['image']}")
        
        # Clear form and reset context
        self.clear_manual_form()
        
        messagebox.showinfo("Success", f"Template '{template['title']}' saved as new template!")
        self.update_status(f"Template '{template['title']}' saved as new manual template")
    
    def save_manual_template_changes(self, template):
        """Save changes to a manual template being edited"""
        # Add the updated template back to manual templates
        self.manual_templates.append(template)
        
        # Update listbox
        self.manual_templates_listbox.insert(tk.END, f"{template['title']} - {template['image']}")
        
        # Clear form and reset context
        self.clear_manual_form()
        
        messagebox.showinfo("Success", f"Manual template '{template['title']}' updated successfully!")
        self.update_status(f"Manual template '{template['title']}' updated")
    
    def update_source_template(self, template, template_info):
        """Update the template in its original source file"""
        source_path = template_info['source']
        
        try:
            # Load the current source file
            if source_path.endswith(('.yml', '.yaml')):
                import yaml
                with open(source_path, 'r', encoding='utf-8') as f:
                    source_data = yaml.safe_load(f)
            else:
                with open(source_path, 'r', encoding='utf-8') as f:
                    source_data = json.load(f)
            
            # Find and replace the template
            original_template = template_info['template']
            
            # Extract templates from source
            from utils import JSONValidator
            templates = JSONValidator.extract_templates(source_data)
            
            # Find the template to replace (match by title and image)
            template_found = False
            for i, tmpl in enumerate(templates):
                if (tmpl.get('title') == original_template.get('title') and 
                    tmpl.get('image') == original_template.get('image')):
                    # Replace the template
                    templates[i] = template
                    template_found = True
                    break
            
            if not template_found:
                raise ValueError("Could not find original template in source file")
            
            # Update the source data structure
            if isinstance(source_data, dict) and 'templates' in source_data:
                source_data['templates'] = templates
            elif isinstance(source_data, list):
                source_data = templates
            else:
                raise ValueError("Unknown source file format")
            
            # Save back to file
            if source_path.endswith(('.yml', '.yaml')):
                with open(source_path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(source_data, f, default_flow_style=False, sort_keys=False)
            else:
                with open(source_path, 'w', encoding='utf-8') as f:
                    json.dump(source_data, f, indent=2, ensure_ascii=False)
            
            # Update loaded templates in memory
            self.loaded_templates[source_path] = source_data
            
            # Refresh the templates list
            self.refresh_edit_templates_list()
            
            # Clear form and reset context  
            self.clear_manual_form()
            
            messagebox.showinfo("Success", 
                               f"Template '{template['title']}' updated in source file!\n\n"
                               f"File: {os.path.basename(source_path)}")
            
            self.update_status(f"Template '{template['title']}' updated in {os.path.basename(source_path)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update source file:\n{str(e)}")
            self.update_status(f"Error updating source: {str(e)}")
    
    
    def validate_manual_template(self):
        """Validate manual template input"""
        title = self.manual_title.get().strip()
        image = self.manual_image.get().strip()
        
        if not title:
            messagebox.showerror("Validation Error", "Title is required")
            return False
        
        if not image:
            messagebox.showerror("Validation Error", "Image is required")
            return False
        
        return True
    
    def add_manual_template(self):
        """Add manually created template to the collection"""
        if not self.validate_manual_template():
            return
        
        # Build template object
        template = {
            "title": self.manual_title.get().strip(),
            "description": self.manual_description.get().strip(),
            "image": self.manual_image.get().strip(),
            "platform": self.manual_platform.get(),
            "restart_policy": self.manual_restart.get()
        }
        
        # Add optional fields
        logo = self.manual_logo.get().strip()
        if logo:
            template["logo"] = logo
        
        # Get note text and clean it (multiline textbox)
        note_text = self.manual_note.get("1.0", "end-1c").strip()
        if note_text and note_text != self.manual_note_placeholder:
            template["note"] = note_text
        
        if self.manual_admin_only.get():
            template["administrator_only"] = True
        
        # Add categories
        categories = []
        for i in range(self.categories_listbox.size()):
            categories.append(self.categories_listbox.get(i))
        if categories:
            template["categories"] = categories
        
        # Add environment variables with debugging
        env_vars = []
        try:
            print(f"DEBUG: Extracting environment variables from listbox with {self.env_listbox.size()} items")
            for i in range(self.env_listbox.size()):
                env_text = self.env_listbox.get(i)
                print(f"DEBUG: Processing env var {i}: '{env_text}'")
                if env_text and env_text.strip():
                    if '=' in env_text:
                        name, value = env_text.split('=', 1)
                        env_vars.append({"name": name.strip(), "default": value.strip()})
                        print(f"DEBUG: Added env var with value: {name.strip()}={value.strip()}")
                    else:
                        env_vars.append({"name": env_text.strip()})
                        print(f"DEBUG: Added env var without value: {env_text.strip()}")
            if env_vars:
                template["env"] = env_vars
                print(f"DEBUG: Final env_vars added to template: {env_vars}")
            else:
                print("DEBUG: No environment variables found or all were empty")
        except Exception as e:
            print(f"ERROR: Failed to extract environment variables: {str(e)}")
            messagebox.showerror("Error", f"Failed to extract environment variables: {str(e)}")
        
        # Add ports
        ports = []
        for i in range(self.ports_listbox.size()):
            port_text = self.ports_listbox.get(i)
            if ': ' in port_text:
                label, port_num = port_text.split(': ', 1)
                ports.append({label: port_num})
        if ports:
            template["ports"] = ports
        
        # Add volumes
        volumes = []
        for i in range(self.volumes_listbox.size()):
            volume_text = self.volumes_listbox.get(i)
            if ' -> ' in volume_text:
                container_path, bind_path = volume_text.split(' -> ', 1)
                volumes.append({"container": container_path, "bind": bind_path})
        if volumes:
            template["volumes"] = volumes
        
        # Add to manual templates list
        self.manual_templates.append(template)
        
        # Update listbox
        self.manual_templates_listbox.insert(tk.END, f"{template['title']} - {template['image']}")
        
        # Clear form
        self.clear_manual_form()
        
        messagebox.showinfo("Success", f"Template '{template['title']}' added successfully!")
        
        self.update_status(f"Manual template '{template['title']}' added")
    
    def edit_manual_template(self):
        """Edit selected manual template using the standardized populate function"""
        try:
            selection = self.manual_templates_listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a template to edit")
                return
            
            index = selection[0]
            template = self.manual_templates[index]
            
            print(f"DEBUG: Editing manual template: {template.get('title', 'Untitled')}")
            
            # Use the standardized populate function
            self.populate_manual_form_with_template(template)
            
            # Set up editing context for manual template
            template_info = {
                'title': template.get('title', 'Manual Template'),
                'source': 'manual_template',
                'template': template,
                'manual_index': index
            }
            
            self.current_editing_context = {
                'template_info': template_info,
                'original_template': template.copy(),
                'is_editing_existing': True,
                'is_manual_template': True
            }
            
            # Update button text
            self.add_template_btn.configure(text="Save Changes", 
                                           command=self.save_edited_template)
            self.clear_form_btn.configure(text="Cancel Edit",
                                         command=self.cancel_edit)
            
            # Remove from list (will be re-added when user saves)
            self.manual_templates.pop(index)
            self.manual_templates_listbox.delete(index)
            
            messagebox.showinfo("Manual Template Loaded", f"Template '{template['title']}' loaded for editing.\n\nMake your changes and click 'Save Changes' to apply them.")
            
        except Exception as e:
            print(f"ERROR in edit_manual_template: {str(e)}")
            messagebox.showerror("Error", f"Failed to edit template: {str(e)}")
    
    def delete_manual_template(self):
        """Delete selected manual template"""
        selection = self.manual_templates_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a template to delete")
            return
        
        index = selection[0]
        template = self.manual_templates[index]
        
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete template '{template['title']}'?"):
            self.manual_templates.pop(index)
            self.manual_templates_listbox.delete(index)
            self.update_status(f"Manual template '{template['title']}' deleted")
    
    # Base Template Configuration Methods
    def toggle_base_template(self):
        """Toggle base template loading"""
        self.base_template_enabled = self.base_template_enabled_var.get()
        self.config.set('base_template.enabled', self.base_template_enabled)
        self.config.save_config()
        
        if self.base_template_enabled:
            self.update_status("Base template enabled")
        else:
            self.update_status("Base template disabled")
    
    def update_base_template_url(self):
        """Update base template URL"""
        new_url = self.base_template_entry.get().strip()
        if not new_url:
            messagebox.showwarning("Warning", "Please enter a valid URL")
            return
        
        self.base_template_url = new_url
        self.config.set('base_template.url', new_url)
        self.config.save_config()
        
        messagebox.showinfo("Success", "Base template URL updated successfully!")
        self.update_status(f"Base template URL updated: {new_url}")
    
    def clear_base_template(self):
        """Clear/remove the currently loaded base template"""
        # Find and remove base template from loaded templates
        base_template_key = None
        for key in self.loaded_templates.keys():
            if key.startswith("BASE_TEMPLATE:"):
                base_template_key = key
                break
        
        if base_template_key:
            del self.loaded_templates[base_template_key]
            messagebox.showinfo("Success", "Base template cleared successfully!")
            self.update_status("Base template removed from loaded templates")
            
            # Refresh displays
            self.refresh_categories()
            self.refresh_edit_templates_list()
        else:
            messagebox.showinfo("Info", "No base template is currently loaded")
    
    # Category Management Methods
    def edit_category(self, event=None):
        """Edit selected category"""
        selection = self.categories_listbox.curselection()
        if not selection:
            if event is None:  # Called from button, not double-click
                messagebox.showwarning("Warning", "Please select a category to edit")
            return
        
        index = selection[0]
        current_value = self.categories_listbox.get(index)
        
        # Create edit dialog
        dialog = ctk.CTkInputDialog(text=f"Edit category:", title="Edit Category")
        dialog._entry.insert(0, current_value)
        dialog._entry.select_range(0, tk.END)
        
        new_value = dialog.get_input()
        if new_value and new_value.strip():
            # Check for duplicates
            categories_list = []
            for i in range(self.categories_listbox.size()):
                if i != index:  # Skip the current item
                    categories_list.append(self.categories_listbox.get(i))
            
            if new_value.strip() not in categories_list:
                self.categories_listbox.delete(index)
                self.categories_listbox.insert(index, new_value.strip())
                self.categories_listbox.selection_set(index)
            else:
                messagebox.showinfo("Info", f"Category '{new_value.strip()}' already exists")
    
    def edit_env_var(self, event=None):
        """Edit selected environment variable"""
        selection = self.env_listbox.curselection()
        if not selection:
            if event is None:
                messagebox.showwarning("Warning", "Please select an environment variable to edit")
            return
        
        index = selection[0]
        current_value = self.env_listbox.get(index)
        
        # Parse current value
        if '=' in current_value:
            name, value = current_value.split('=', 1)
        else:
            name = current_value
            value = ""
        
        # Create edit dialog
        edit_window = ctk.CTkToplevel(self.root)
        edit_window.title("Edit Environment Variable")
        edit_window.geometry("400x150")
        edit_window.resizable(False, False)
        
        # Center the window
        edit_window.transient(self.root)
        edit_window.grab_set()
        
        # Name field
        name_frame = ctk.CTkFrame(edit_window)
        name_frame.pack(fill="x", padx=20, pady=(20, 5))
        
        ctk.CTkLabel(name_frame, text="Name:", width=60).pack(side="left")
        name_entry = ctk.CTkEntry(name_frame, placeholder_text="VAR_NAME")
        name_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
        name_entry.insert(0, name)
        
        # Value field
        value_frame = ctk.CTkFrame(edit_window)
        value_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(value_frame, text="Value:", width=60).pack(side="left")
        value_entry = ctk.CTkEntry(value_frame, placeholder_text="default_value")
        value_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
        value_entry.insert(0, value)
        
        # Buttons
        button_frame = ctk.CTkFrame(edit_window)
        button_frame.pack(pady=20)
        
        def save_changes():
            new_name = name_entry.get().strip()
            new_value = value_entry.get().strip()
            
            if new_name:
                display_text = f"{new_name}={new_value}" if new_value else new_name
                self.env_listbox.delete(index)
                self.env_listbox.insert(index, display_text)
                self.env_listbox.selection_set(index)
                edit_window.destroy()
            else:
                messagebox.showwarning("Warning", "Name is required")
        
        ctk.CTkButton(button_frame, text="Save", command=save_changes, width=80).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Cancel", command=edit_window.destroy, width=80).pack(side="left", padx=5)
        
        name_entry.focus()
    
    def edit_port(self, event=None):
        """Edit selected port with enhanced error handling and validation"""
        try:
            selection = self.ports_listbox.curselection()
            if not selection:
                if event is None:  # Called from button, not double-click
                    messagebox.showwarning("Warning", "Please select a port to edit")
                return
            
            index = selection[0]
            current_value = self.ports_listbox.get(index)
            
            # Parse current value
            if ': ' in current_value:
                label, port = current_value.split(': ', 1)
            else:
                label = ""
                port = current_value
            
            # Create edit dialog
            edit_window = ctk.CTkToplevel(self.root)
            edit_window.title("Edit Port")
            edit_window.geometry("400x180")
            edit_window.resizable(False, False)
            
            edit_window.transient(self.root)
            edit_window.grab_set()
            
            # Header
            header_frame = ctk.CTkFrame(edit_window)
            header_frame.pack(fill="x", padx=20, pady=(20, 10))
            ctk.CTkLabel(header_frame, text=f"Editing Port: {current_value}", 
                        font=ctk.CTkFont(size=14, weight="bold")).pack()
            
            # Label field
            label_frame = ctk.CTkFrame(edit_window)
            label_frame.pack(fill="x", padx=20, pady=5)
            
            ctk.CTkLabel(label_frame, text="Label:", width=60).pack(side="left")
            label_entry = ctk.CTkEntry(label_frame, placeholder_text="WebUI")
            label_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
            label_entry.insert(0, label)
            
            # Port field
            port_frame = ctk.CTkFrame(edit_window)
            port_frame.pack(fill="x", padx=20, pady=5)
            
            ctk.CTkLabel(port_frame, text="Port:", width=60).pack(side="left")
            port_entry = ctk.CTkEntry(port_frame, placeholder_text="80/tcp")
            port_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
            port_entry.insert(0, port)
            
            # Buttons
            button_frame = ctk.CTkFrame(edit_window)
            button_frame.pack(pady=20)
            
            def save_changes():
                try:
                    new_label = label_entry.get().strip()
                    new_port = port_entry.get().strip()
                    
                    # Validation
                    if not new_label:
                        messagebox.showwarning("Validation Error", "Port label is required")
                        label_entry.focus()
                        return
                    
                    if not new_port:
                        messagebox.showwarning("Validation Error", "Port number is required")
                        port_entry.focus()
                        return
                    
                    # Check for duplicates (excluding current item)
                    for i in range(self.ports_listbox.size()):
                        if i != index:  # Skip current item
                            existing = self.ports_listbox.get(i)
                            if existing.startswith(f"{new_label}: "):
                                messagebox.showwarning("Duplicate Port", f"Port label '{new_label}' already exists")
                                return
                    
                    # Update the port
                    display_text = f"{new_label}: {new_port}"
                    self.ports_listbox.delete(index)
                    self.ports_listbox.insert(index, display_text)
                    self.ports_listbox.selection_set(index)
                    
                    self.update_status(f"Port updated: {current_value} → {display_text}")
                    edit_window.destroy()
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save port changes: {str(e)}")
                    print(f"Error in save_changes (edit_port): {str(e)}")
            
            ctk.CTkButton(button_frame, text="Save Changes", command=save_changes, width=100).pack(side="left", padx=5)
            ctk.CTkButton(button_frame, text="Cancel", command=edit_window.destroy, width=80).pack(side="left", padx=5)
            
            label_entry.focus()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to edit port: {str(e)}")
            print(f"Error in edit_port: {str(e)}")
    
    def edit_volume(self, event=None):
        """Edit selected volume with enhanced error handling and validation"""
        try:
            selection = self.volumes_listbox.curselection()
            if not selection:
                if event is None:  # Called from button, not double-click
                    messagebox.showwarning("Warning", "Please select a volume to edit")
                return
            
            index = selection[0]
            current_value = self.volumes_listbox.get(index)
            
            # Parse current value
            if ' -> ' in current_value:
                container_path, bind_path = current_value.split(' -> ', 1)
            else:
                container_path = current_value
                bind_path = ""
            
            # Create edit dialog
            edit_window = ctk.CTkToplevel(self.root)
            edit_window.title("Edit Volume")
            edit_window.geometry("500x180")
            edit_window.resizable(False, False)
            
            edit_window.transient(self.root)
            edit_window.grab_set()
            
            # Header
            header_frame = ctk.CTkFrame(edit_window)
            header_frame.pack(fill="x", padx=20, pady=(20, 10))
            ctk.CTkLabel(header_frame, text=f"Editing Volume: {current_value}", 
                        font=ctk.CTkFont(size=14, weight="bold")).pack()
            
            # Container path field
            container_frame = ctk.CTkFrame(edit_window)
            container_frame.pack(fill="x", padx=20, pady=5)
            
            ctk.CTkLabel(container_frame, text="Container:", width=80).pack(side="left")
            container_entry = ctk.CTkEntry(container_frame, placeholder_text="/app/data")
            container_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
            container_entry.insert(0, container_path)
            
            # Bind path field
            bind_frame = ctk.CTkFrame(edit_window)
            bind_frame.pack(fill="x", padx=20, pady=5)
            
            ctk.CTkLabel(bind_frame, text="Bind:", width=80).pack(side="left")
            bind_entry = ctk.CTkEntry(bind_frame, placeholder_text="!data/app")
            bind_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
            bind_entry.insert(0, bind_path)
            
            # Buttons
            button_frame = ctk.CTkFrame(edit_window)
            button_frame.pack(pady=20)
            
            def save_changes():
                try:
                    new_container = container_entry.get().strip()
                    new_bind = bind_entry.get().strip()
                    
                    # Validation
                    if not new_container:
                        messagebox.showwarning("Validation Error", "Container path is required")
                        container_entry.focus()
                        return
                    
                    if not new_bind:
                        messagebox.showwarning("Validation Error", "Bind path is required")
                        bind_entry.focus()
                        return
                    
                    # Check for duplicates (excluding current item)
                    for i in range(self.volumes_listbox.size()):
                        if i != index:  # Skip current item
                            existing = self.volumes_listbox.get(i)
                            if existing.startswith(f"{new_container} -> "):
                                messagebox.showwarning("Duplicate Volume", f"Container path '{new_container}' already exists")
                                return
                    
                    # Update the volume
                    display_text = f"{new_container} -> {new_bind}"
                    self.volumes_listbox.delete(index)
                    self.volumes_listbox.insert(index, display_text)
                    self.volumes_listbox.selection_set(index)
                    
                    self.update_status(f"Volume updated: {current_value} → {display_text}")
                    edit_window.destroy()
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save volume changes: {str(e)}")
                    print(f"Error in save_changes (edit_volume): {str(e)}")
            
            ctk.CTkButton(button_frame, text="Save Changes", command=save_changes, width=100).pack(side="left", padx=5)
            ctk.CTkButton(button_frame, text="Cancel", command=edit_window.destroy, width=80).pack(side="left", padx=5)
            
            container_entry.focus()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to edit volume: {str(e)}")
            print(f"Error in edit_volume: {str(e)}")
    
    def on_category_selected(self, choice):
        """Handle category selection from dropdown"""
        if choice != "Select...":
            self.manual_category_entry.delete(0, tk.END)
            self.manual_category_entry.insert(0, choice)
    
    def extract_categories_from_templates(self):
        """Extract all unique categories from loaded templates"""
        categories = set()
        
        # Extract from loaded templates
        for source, data in self.loaded_templates.items():
            from utils import JSONValidator
            try:
                templates = JSONValidator.extract_templates(data)
                for template in templates:
                    if 'categories' in template and isinstance(template['categories'], list):
                        for cat in template['categories']:
                            if isinstance(cat, str) and cat.strip():
                                categories.add(cat.strip().lower())
            except:
                continue
        
        # Extract from manual templates
        for template in self.manual_templates:
            if 'categories' in template and isinstance(template['categories'], list):
                for cat in template['categories']:
                    if isinstance(cat, str) and cat.strip():
                        categories.add(cat.strip().lower())
        
        self.all_categories = categories
        return sorted(list(categories))
    
    def refresh_categories(self):
        """Refresh category dropdown with categories from loaded sources"""
        categories = self.extract_categories_from_templates()
        
        # Add common categories if not present
        common_categories = ["webserver", "database", "media", "networking", "tools", "monitoring", 
                           "storage", "development", "security", "backup", "communication"]
        for cat in common_categories:
            if cat not in categories:
                categories.append(cat)
        
        # Update dropdown
        self.manual_category_combo.configure(values=sorted(categories))
        self.update_status(f"Categories refreshed: {len(categories)} available")
    
    # Template Editing Methods
    def refresh_edit_templates_list(self):
        """Refresh the list of templates available for editing"""
        self.all_templates_for_editing = []
        
        # Collect all templates from all sources
        for source, data in self.loaded_templates.items():
            from utils import JSONValidator
            try:
                templates = JSONValidator.extract_templates(data)
                for template in templates:
                    template_info = {
                        'template': template,
                        'source': source,
                        'title': template.get('title', 'Untitled'),
                        'image': template.get('image', 'No image'),
                        'description': template.get('description', '')
                    }
                    self.all_templates_for_editing.append(template_info)
            except:
                continue
        
        # Update source filter dropdown
        sources = ["All Sources"] + list(self.loaded_templates.keys())
        source_names = []
        for source in sources:
            if source == "All Sources":
                source_names.append(source)
            else:
                # Shorten source names for display
                if os.path.exists(source):
                    source_names.append(f"File: {os.path.basename(source)}")
                else:
                    # Shorten URL
                    if len(source) > 50:
                        source_names.append(f"URL: ...{source[-40:]}")
                    else:
                        source_names.append(f"URL: {source}")
        
        self.source_filter_combo.configure(values=source_names)
        
        # Refresh the display
        self.filter_edit_templates()
        
        self.edit_status_label.configure(text=f"Found {len(self.all_templates_for_editing)} templates from {len(self.loaded_templates)} sources")
    
    def filter_edit_templates(self, event=None):
        """Filter templates in edit list based on search criteria"""
        filter_text = self.edit_filter_entry.get().lower()
        source_filter = self.source_filter_combo.get()
        
        # Clear current list
        self.edit_templates_listbox.delete(0, tk.END)
        
        # Filter templates
        for i, template_info in enumerate(self.all_templates_for_editing):
            # Source filter
            if source_filter != "All Sources":
                source_display = self.get_source_display_name(template_info['source'])
                if source_filter != source_display:
                    continue
            
            # Text filter
            if filter_text:
                title_match = filter_text in (template_info['title'] or '').lower()
                image_match = filter_text in (template_info['image'] or '').lower()
                desc_match = filter_text in (template_info['description'] or '').lower()
                
                if not (title_match or image_match or desc_match):
                    continue
            
            # Add to list
            display_text = f"{template_info['title']} | {template_info['image']} | {self.get_source_display_name(template_info['source'])}"
            self.edit_templates_listbox.insert(tk.END, display_text)
            # Store the index in the original list
            self.edit_templates_listbox.insert(tk.END, "")
            self.edit_templates_listbox.delete(tk.END)
    
    def get_source_display_name(self, source):
        """Get a short display name for a source"""
        if os.path.exists(source):
            return f"File: {os.path.basename(source)}"
        else:
            if len(source) > 50:
                return f"URL: ...{source[-40:]}"
            else:
                return f"URL: {source}"
    
    def filter_by_source(self, choice):
        """Filter templates by selected source"""
        self.filter_edit_templates()
    
    def edit_selected_template(self, event=None):
        """Edit the selected template"""
        selection = self.edit_templates_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a template to edit")
            return
        
        # Find the actual template
        selected_index = selection[0]
        visible_templates = []
        
        filter_text = self.edit_filter_entry.get().lower()
        source_filter = self.source_filter_combo.get()
        
        for template_info in self.all_templates_for_editing:
            # Apply same filtering logic
            if source_filter != "All Sources":
                source_display = self.get_source_display_name(template_info['source'])
                if source_filter != source_display:
                    continue
            
            if filter_text:
                title_match = filter_text in (template_info['title'] or '').lower()
                image_match = filter_text in (template_info['image'] or '').lower()
                desc_match = filter_text in (template_info['description'] or '').lower()
                
                if not (title_match or image_match or desc_match):
                    continue
            
            visible_templates.append(template_info)
        
        if selected_index >= len(visible_templates):
            messagebox.showerror("Error", "Invalid selection")
            return
        
        template_info = visible_templates[selected_index]
        template = template_info['template'].copy()
        
        # Remove internal fields
        if '_source' in template:
            del template['_source']
        
        # Store editing context for save operations
        self.current_editing_context = {
            'template_info': template_info,
            'original_template': template.copy(),
            'is_editing_existing': True
        }
        
        # Open dedicated edit window instead of reusing Manual Entry tab
        self.open_template_edit_window(template, template_info)
        
        messagebox.showinfo("Template Loaded for Editing", 
                           f"Template '{template_info['title']}' loaded for editing.\n\n"
                           f"Source: {self.get_source_display_name(template_info['source'])}\n\n"
                           f"Make your changes and click 'Save Changes' to choose save options.")
    
    def clone_selected_template(self):
        """Clone the selected template (same as edit but explicitly for cloning)"""
        self.edit_selected_template()
    
    def view_template_json(self):
        """View the JSON of the selected template"""
        selection = self.edit_templates_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a template to view")
            return
        
        # Find the actual template (same logic as edit)
        selected_index = selection[0]
        visible_templates = []
        
        filter_text = self.edit_filter_entry.get().lower()
        source_filter = self.source_filter_combo.get()
        
        for template_info in self.all_templates_for_editing:
            if source_filter != "All Sources":
                source_display = self.get_source_display_name(template_info['source'])
                if source_filter != source_display:
                    continue
            
            if filter_text:
                title_match = filter_text in (template_info['title'] or '').lower()
                image_match = filter_text in (template_info['image'] or '').lower() 
                desc_match = filter_text in (template_info['description'] or '').lower()
                
                if not (title_match or image_match or desc_match):
                    continue
            
            visible_templates.append(template_info)
        
        if selected_index >= len(visible_templates):
            messagebox.showerror("Error", "Invalid selection")
            return
        
        template_info = visible_templates[selected_index]
        template = template_info['template'].copy()
        
        # Remove internal fields
        if '_source' in template:
            del template['_source']
        
        # Create a popup window to show JSON
        json_window = ctk.CTkToplevel(self.root)
        json_window.title(f"Template JSON: {template_info['title']}")
        json_window.geometry("800x600")
        
        # JSON text display
        json_text = ctk.CTkTextbox(json_window)
        json_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Format and insert JSON
        formatted_json = json.dumps(template, indent=2, ensure_ascii=False)
        json_text.insert("1.0", formatted_json)
        
        # Close button
        close_btn = ctk.CTkButton(json_window, text="Close", command=json_window.destroy)
        close_btn.pack(pady=10)
    
    def open_template_edit_window(self, template, template_info):
        """Open a dedicated template editing window"""
        edit_window = ctk.CTkToplevel(self.root)
        edit_window.title(f"Edit Template: {template_info['title']}")
        edit_window.geometry("900x1000")  # INCREASED HEIGHT to show all sections
        edit_window.resizable(True, True)
        
        # Make it modal
        edit_window.transient(self.root)
        edit_window.grab_set()
        
        # Header
        header_frame = ctk.CTkFrame(edit_window)
        header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(header_frame, text=f"Editing Template: {template_info['title']}", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)
        ctk.CTkLabel(header_frame, text=f"Source: {self.get_source_display_name(template_info['source'])}", 
                    font=ctk.CTkFont(size=12)).pack()
        
        # Scrollable content - ADDED SCROLLABLE FRAME
        content_frame = ctk.CTkScrollableFrame(edit_window)
        content_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create editing form (similar to manual entry but separate)
        self.create_edit_form(content_frame, template, edit_window, template_info)
    
    def create_edit_form(self, parent, template, edit_window, template_info):
        """Create the editing form in the dedicated window"""
        print("DEBUG: Creating edit form for popup window")
        
        # Basic Information
        basic_frame = ctk.CTkFrame(parent)
        basic_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(basic_frame, text="Basic Information", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        
        # Grid for form fields
        form_grid = ctk.CTkFrame(basic_frame)
        form_grid.pack(fill="x", padx=10, pady=(0, 10))
        form_grid.grid_columnconfigure(1, weight=1)
        
        # Title
        ctk.CTkLabel(form_grid, text="Title*:", width=80, anchor="w").grid(row=0, column=0, sticky="w", padx=(5, 8), pady=3)
        edit_title = ctk.CTkEntry(form_grid, height=32)
        edit_title.grid(row=0, column=1, sticky="ew", padx=(0, 5), pady=3)
        edit_title.insert(0, template.get('title', ''))
        
        # Image
        ctk.CTkLabel(form_grid, text="Image*:", width=80, anchor="w").grid(row=1, column=0, sticky="w", padx=(5, 8), pady=3)
        edit_image = ctk.CTkEntry(form_grid, height=32)
        edit_image.grid(row=1, column=1, sticky="ew", padx=(0, 5), pady=3)
        edit_image.insert(0, template.get('image', ''))
        
        # Description
        ctk.CTkLabel(form_grid, text="Description:", width=80, anchor="w").grid(row=2, column=0, sticky="w", padx=(5, 8), pady=3)
        edit_description = ctk.CTkEntry(form_grid, height=32)
        edit_description.grid(row=2, column=1, sticky="ew", padx=(0, 5), pady=3)
        edit_description.insert(0, template.get('description', ''))
        
        # Logo URL
        ctk.CTkLabel(form_grid, text="Logo URL:", width=80, anchor="w").grid(row=3, column=0, sticky="w", padx=(5, 8), pady=3)
        edit_logo = ctk.CTkEntry(form_grid, height=32)
        edit_logo.grid(row=3, column=1, sticky="ew", padx=(0, 5), pady=3)
        edit_logo.insert(0, template.get('logo', ''))
        
        # Platform and Restart
        config_frame = ctk.CTkFrame(form_grid)
        config_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=5, pady=3)
        config_frame.grid_columnconfigure(1, weight=1)
        config_frame.grid_columnconfigure(3, weight=1)
        
        ctk.CTkLabel(config_frame, text="Platform:", width=70, anchor="w").grid(row=0, column=0, sticky="w", padx=(5, 5))
        edit_platform = ctk.CTkComboBox(config_frame, values=["linux", "windows"], width=100, height=32)
        edit_platform.grid(row=0, column=1, sticky="w", padx=(0, 15))
        edit_platform.set(template.get('platform', 'linux'))
        
        ctk.CTkLabel(config_frame, text="Restart:", width=70, anchor="w").grid(row=0, column=2, sticky="w", padx=(5, 5))
        edit_restart = ctk.CTkComboBox(config_frame, values=["unless-stopped", "always", "no", "on-failure"], width=130, height=32)
        edit_restart.grid(row=0, column=3, sticky="w", padx=(0, 5))
        edit_restart.set(template.get('restart_policy', 'unless-stopped'))
        
        # Note field
        ctk.CTkLabel(form_grid, text="Note:", width=80, anchor="nw").grid(row=5, column=0, sticky="nw", padx=(5, 8), pady=(8, 3))
        edit_note = ctk.CTkTextbox(form_grid, height=150, wrap="word", font=ctk.CTkFont(size=11))
        edit_note.grid(row=5, column=1, sticky="ew", padx=(0, 5), pady=3)
        if template.get('note'):
            edit_note.insert("1.0", template['note'])
        
        # Administrator Only
        admin_frame = ctk.CTkFrame(form_grid)
        admin_frame.grid(row=6, column=0, columnspan=2, sticky="w", padx=5, pady=(3, 8))
        edit_admin_only = ctk.CTkCheckBox(admin_frame, text="Administrator Only")
        edit_admin_only.pack(side="left", padx=5)
        if template.get('administrator_only'):
            edit_admin_only.select()
        
        # Categories Section with Add/Edit/Remove functionality
        categories_frame = ctk.CTkFrame(parent)
        categories_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(categories_frame, text="Categories", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        
        # Category input
        cat_input_frame = ctk.CTkFrame(categories_frame)
        cat_input_frame.pack(fill="x", padx=10, pady=5)
        cat_input_frame.grid_columnconfigure(1, weight=1)
        
        edit_category_combo = ctk.CTkComboBox(cat_input_frame, values=["webserver", "database", "media", "networking", "tools"], 
                                             width=120, height=28)
        edit_category_combo.grid(row=0, column=0, sticky="w", padx=(5, 5))
        edit_category_combo.set("Select...")
        
        edit_category_entry = ctk.CTkEntry(cat_input_frame, placeholder_text="or type custom", height=28)
        edit_category_entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        
        def add_edit_category():
            category = edit_category_entry.get().strip()
            if not category:
                category = edit_category_combo.get()
                if category == "Select...":
                    return
            if category:
                # Check for duplicates
                existing_cats = [edit_categories_listbox.get(i) for i in range(edit_categories_listbox.size())]
                if category not in existing_cats:
                    edit_categories_listbox.insert(tk.END, category)
                    edit_category_entry.delete(0, tk.END)
                    edit_category_combo.set("Select...")
        
        def remove_edit_category():
            selection = edit_categories_listbox.curselection()
            if selection:
                edit_categories_listbox.delete(selection[0])
        
        def edit_edit_category():
            selection = edit_categories_listbox.curselection()
            if not selection:
                return
            index = selection[0]
            current_value = edit_categories_listbox.get(index)
            
            # Create custom dialog instead of using CTkInputDialog._entry
            cat_edit_window = ctk.CTkToplevel(edit_window)
            cat_edit_window.title("Edit Category")
            cat_edit_window.geometry("350x120")
            cat_edit_window.resizable(False, False)
            cat_edit_window.transient(edit_window)
            cat_edit_window.grab_set()
            
            # Entry field
            entry_frame = ctk.CTkFrame(cat_edit_window)
            entry_frame.pack(fill="x", padx=20, pady=(20, 10))
            
            ctk.CTkLabel(entry_frame, text="Category:").pack(anchor="w")
            category_entry = ctk.CTkEntry(entry_frame, width=300)
            category_entry.pack(fill="x", pady=(5, 0))
            category_entry.insert(0, current_value)
            category_entry.select_range(0, tk.END)
            
            # Buttons
            button_frame = ctk.CTkFrame(cat_edit_window)
            button_frame.pack(pady=15)
            
            def save_category():
                new_value = category_entry.get().strip()
                if new_value:
                    edit_categories_listbox.delete(index)
                    edit_categories_listbox.insert(index, new_value)
                    edit_categories_listbox.selection_set(index)
                    cat_edit_window.destroy()
            
            ctk.CTkButton(button_frame, text="Save", command=save_category, width=80).pack(side="left", padx=5)
            ctk.CTkButton(button_frame, text="Cancel", command=cat_edit_window.destroy, width=80).pack(side="left", padx=5)
            
            category_entry.focus()
        
        ctk.CTkButton(cat_input_frame, text="Add", command=add_edit_category, width=50, height=28).grid(row=0, column=2, padx=(0, 5))
        
        edit_categories_listbox = tk.Listbox(categories_frame, height=3, font=("Segoe UI", 9))
        edit_categories_listbox.pack(fill="x", padx=10, pady=5)
        edit_categories_listbox.bind("<Double-Button-1>", lambda e: edit_edit_category())
        
        # Load existing categories
        for category in template.get('categories', []):
            edit_categories_listbox.insert(tk.END, category)
        
        # Category buttons
        cat_buttons = ctk.CTkFrame(categories_frame)
        cat_buttons.pack(pady=5)
        ctk.CTkButton(cat_buttons, text="Edit", command=edit_edit_category, width=60, height=25).pack(side="left", padx=2)
        ctk.CTkButton(cat_buttons, text="Remove", command=remove_edit_category, width=60, height=25).pack(side="left", padx=2)
        
        
        # Environment Variables Section with Add/Edit/Remove functionality
        env_frame = ctk.CTkFrame(parent)
        env_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(env_frame, text="Environment Variables", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        
        # Environment input
        env_input_frame = ctk.CTkFrame(env_frame)
        env_input_frame.pack(fill="x", padx=10, pady=5)
        env_input_frame.grid_columnconfigure(1, weight=1)
        env_input_frame.grid_columnconfigure(3, weight=1)
        
        ctk.CTkLabel(env_input_frame, text="Name:", width=50, anchor="w").grid(row=0, column=0, sticky="w", padx=(5, 2))
        edit_env_name = ctk.CTkEntry(env_input_frame, placeholder_text="VAR_NAME", width=100, height=28)
        edit_env_name.grid(row=0, column=1, sticky="w", padx=2)
        
        ctk.CTkLabel(env_input_frame, text="Value:", width=50, anchor="w").grid(row=0, column=2, sticky="w", padx=(8, 2))
        edit_env_value = ctk.CTkEntry(env_input_frame, placeholder_text="default_value", height=28)
        edit_env_value.grid(row=0, column=3, sticky="ew", padx=2)
        
        def add_edit_env_var():
            name = edit_env_name.get().strip()
            value = edit_env_value.get().strip()
            if name:
                display_text = f"{name}={value}" if value else name
                edit_env_listbox.insert(tk.END, display_text)
                edit_env_name.delete(0, tk.END)
                edit_env_value.delete(0, tk.END)
        
        def remove_edit_env_var():
            selection = edit_env_listbox.curselection()
            if selection:
                edit_env_listbox.delete(selection[0])
        
        def edit_edit_env_var():
            selection = edit_env_listbox.curselection()
            if not selection:
                return
            index = selection[0]
            current_value = edit_env_listbox.get(index)
            
            # Parse current value
            if '=' in current_value:
                name, value = current_value.split('=', 1)
            else:
                name = current_value
                value = ""
            
            # Create edit dialog - FIX: Use edit_window parameter as parent
            env_edit_window = ctk.CTkToplevel(edit_window)
            env_edit_window.title("Edit Environment Variable")
            env_edit_window.geometry("400x150")
            env_edit_window.resizable(False, False)
            env_edit_window.transient(edit_window)
            env_edit_window.grab_set()
            
            # Name field
            name_frame = ctk.CTkFrame(env_edit_window)
            name_frame.pack(fill="x", padx=20, pady=(20, 5))
            ctk.CTkLabel(name_frame, text="Name:", width=60).pack(side="left")
            name_entry = ctk.CTkEntry(name_frame, placeholder_text="VAR_NAME")
            name_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
            name_entry.insert(0, name)
            
            # Value field
            value_frame = ctk.CTkFrame(env_edit_window)
            value_frame.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(value_frame, text="Value:", width=60).pack(side="left")
            value_entry = ctk.CTkEntry(value_frame, placeholder_text="default_value")
            value_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
            value_entry.insert(0, value)
            
            # Buttons
            button_frame = ctk.CTkFrame(env_edit_window)
            button_frame.pack(pady=20)
            
            def save_env_changes():
                new_name = name_entry.get().strip()
                new_value = value_entry.get().strip()
                if new_name:
                    display_text = f"{new_name}={new_value}" if new_value else new_name
                    edit_env_listbox.delete(index)
                    edit_env_listbox.insert(index, display_text)
                    edit_env_listbox.selection_set(index)
                    env_edit_window.destroy()
            
            ctk.CTkButton(button_frame, text="Save", command=save_env_changes, width=80).pack(side="left", padx=5)
            ctk.CTkButton(button_frame, text="Cancel", command=env_edit_window.destroy, width=80).pack(side="left", padx=5)
            
            name_entry.focus()
        
        ctk.CTkButton(env_input_frame, text="Add", command=add_edit_env_var, width=50, height=28).grid(row=0, column=4, padx=(5, 5))
        
        edit_env_listbox = tk.Listbox(env_frame, height=4, font=("Segoe UI", 9))
        edit_env_listbox.pack(fill="x", padx=10, pady=5)
        edit_env_listbox.bind("<Double-Button-1>", lambda e: edit_edit_env_var())
        
        # Load existing environment variables
        for env_var in template.get('env', []):
            if isinstance(env_var, dict):
                name = env_var.get('name', '')
                default_val = env_var.get('default', env_var.get('value', ''))
                if default_val:
                    display_text = f"{name}={default_val}"
                else:
                    display_text = name
                edit_env_listbox.insert(tk.END, display_text)
        
        # Environment buttons
        env_buttons = ctk.CTkFrame(env_frame)
        env_buttons.pack(pady=5)
        ctk.CTkButton(env_buttons, text="Edit", command=edit_edit_env_var, width=60, height=25).pack(side="left", padx=2)
        ctk.CTkButton(env_buttons, text="Remove", command=remove_edit_env_var, width=60, height=25).pack(side="left", padx=2)
        
        # Ports Section
        ports_frame = ctk.CTkFrame(parent)
        ports_frame.pack(fill="x", padx=5, pady=5)
        
        print("DEBUG: Creating Ports section in POPUP WINDOW")
        
        ctk.CTkLabel(ports_frame, text="Ports", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        
        # Port input
        port_input_frame = ctk.CTkFrame(ports_frame)
        port_input_frame.pack(fill="x", padx=10, pady=5)
        port_input_frame.grid_columnconfigure(1, weight=1)
        port_input_frame.grid_columnconfigure(3, weight=1)
        
        ctk.CTkLabel(port_input_frame, text="Label:", width=50, anchor="w").grid(row=0, column=0, sticky="w", padx=(5, 2))
        edit_port_label = ctk.CTkEntry(port_input_frame, placeholder_text="WebUI", width=100, height=28)
        edit_port_label.grid(row=0, column=1, sticky="w", padx=2)
        
        ctk.CTkLabel(port_input_frame, text="Port:", width=50, anchor="w").grid(row=0, column=2, sticky="w", padx=(8, 2))
        edit_port_number = ctk.CTkEntry(port_input_frame, placeholder_text="80/tcp", height=28)
        edit_port_number.grid(row=0, column=3, sticky="ew", padx=2)
        
        def add_edit_port():
            label = edit_port_label.get().strip()
            port = edit_port_number.get().strip()
            if label and port:
                display_text = f"{label}: {port}"
                edit_ports_listbox.insert(tk.END, display_text)
                edit_port_label.delete(0, tk.END)
                edit_port_number.delete(0, tk.END)
        
        def remove_edit_port():
            selection = edit_ports_listbox.curselection()
            if selection:
                edit_ports_listbox.delete(selection[0])
        
        def edit_edit_port():
            selection = edit_ports_listbox.curselection()
            if not selection:
                return
            index = selection[0]
            current_value = edit_ports_listbox.get(index)
            
            # Parse current value
            if ': ' in current_value:
                label, port = current_value.split(': ', 1)
            else:
                label = ""
                port = current_value
            
            # Create edit dialog
            port_edit_window = ctk.CTkToplevel(edit_window)
            port_edit_window.title("Edit Port")
            port_edit_window.geometry("400x150")
            port_edit_window.resizable(False, False)
            port_edit_window.transient(edit_window)
            port_edit_window.grab_set()
            
            # Label field
            label_frame = ctk.CTkFrame(port_edit_window)
            label_frame.pack(fill="x", padx=20, pady=(20, 5))
            ctk.CTkLabel(label_frame, text="Label:", width=60).pack(side="left")
            label_entry = ctk.CTkEntry(label_frame, placeholder_text="WebUI")
            label_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
            label_entry.insert(0, label)
            
            # Port field
            port_frame = ctk.CTkFrame(port_edit_window)
            port_frame.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(port_frame, text="Port:", width=60).pack(side="left")
            port_entry = ctk.CTkEntry(port_frame, placeholder_text="80/tcp")
            port_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
            port_entry.insert(0, port)
            
            # Buttons
            button_frame = ctk.CTkFrame(port_edit_window)
            button_frame.pack(pady=20)
            
            def save_port_changes():
                new_label = label_entry.get().strip()
                new_port = port_entry.get().strip()
                if new_label and new_port:
                    display_text = f"{new_label}: {new_port}"
                    edit_ports_listbox.delete(index)
                    edit_ports_listbox.insert(index, display_text)
                    edit_ports_listbox.selection_set(index)
                    port_edit_window.destroy()
            
            ctk.CTkButton(button_frame, text="Save", command=save_port_changes, width=80).pack(side="left", padx=5)
            ctk.CTkButton(button_frame, text="Cancel", command=port_edit_window.destroy, width=80).pack(side="left", padx=5)
            
            label_entry.focus()
        
        ctk.CTkButton(port_input_frame, text="Add", command=add_edit_port, width=50, height=28).grid(row=0, column=4, padx=(5, 5))
        print("DEBUG: Port Add button created in POPUP WINDOW")
        
        edit_ports_listbox = tk.Listbox(ports_frame, height=3, font=("Segoe UI", 9))
        edit_ports_listbox.pack(fill="x", padx=10, pady=5)
        edit_ports_listbox.bind("<Double-Button-1>", lambda e: edit_edit_port())
        
        # Load existing ports
        for port_obj in template.get('ports', []):
            if isinstance(port_obj, dict):
                for label, port_num in port_obj.items():
                    edit_ports_listbox.insert(tk.END, f"{label}: {port_num}")
        
        # Port buttons
        port_buttons = ctk.CTkFrame(ports_frame)
        port_buttons.pack(pady=5)
        ctk.CTkButton(port_buttons, text="Edit", command=edit_edit_port, width=60, height=25).pack(side="left", padx=2)
        ctk.CTkButton(port_buttons, text="Remove", command=remove_edit_port, width=60, height=25).pack(side="left", padx=2)
        print("DEBUG: Port Edit/Remove buttons created in POPUP WINDOW")
        
        # Volumes Section
        volumes_frame = ctk.CTkFrame(parent)
        volumes_frame.pack(fill="x", padx=5, pady=5)
        
        print("DEBUG: Creating Volumes section in POPUP WINDOW")
        
        ctk.CTkLabel(volumes_frame, text="Volumes", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        
        # Volume input
        volume_input_frame = ctk.CTkFrame(volumes_frame)
        volume_input_frame.pack(fill="x", padx=10, pady=5)
        volume_input_frame.grid_columnconfigure(1, weight=1)
        volume_input_frame.grid_columnconfigure(3, weight=1)
        
        ctk.CTkLabel(volume_input_frame, text="Container:", width=70, anchor="w").grid(row=0, column=0, sticky="w", padx=(5, 2))
        edit_volume_container = ctk.CTkEntry(volume_input_frame, placeholder_text="/app/data", width=120, height=28)
        edit_volume_container.grid(row=0, column=1, sticky="w", padx=2)
        
        ctk.CTkLabel(volume_input_frame, text="Bind:", width=50, anchor="w").grid(row=0, column=2, sticky="w", padx=(8, 2))
        edit_volume_bind = ctk.CTkEntry(volume_input_frame, placeholder_text="!data/app", height=28)
        edit_volume_bind.grid(row=0, column=3, sticky="ew", padx=2)
        
        def add_edit_volume():
            container_path = edit_volume_container.get().strip()
            bind_path = edit_volume_bind.get().strip()
            if container_path and bind_path:
                display_text = f"{container_path} -> {bind_path}"
                edit_volumes_listbox.insert(tk.END, display_text)
                edit_volume_container.delete(0, tk.END)
                edit_volume_bind.delete(0, tk.END)
        
        def remove_edit_volume():
            selection = edit_volumes_listbox.curselection()
            if selection:
                edit_volumes_listbox.delete(selection[0])
        
        def edit_edit_volume():
            selection = edit_volumes_listbox.curselection()
            if not selection:
                return
            index = selection[0]
            current_value = edit_volumes_listbox.get(index)
            
            # Parse current value
            if ' -> ' in current_value:
                container_path, bind_path = current_value.split(' -> ', 1)
            else:
                container_path = current_value
                bind_path = ""
            
            # Create edit dialog
            volume_edit_window = ctk.CTkToplevel(edit_window)
            volume_edit_window.title("Edit Volume")
            volume_edit_window.geometry("450x150")
            volume_edit_window.resizable(False, False)
            volume_edit_window.transient(edit_window)
            volume_edit_window.grab_set()
            
            # Container path field
            container_frame = ctk.CTkFrame(volume_edit_window)
            container_frame.pack(fill="x", padx=20, pady=(20, 5))
            ctk.CTkLabel(container_frame, text="Container:", width=80).pack(side="left")
            container_entry = ctk.CTkEntry(container_frame, placeholder_text="/app/data")
            container_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
            container_entry.insert(0, container_path)
            
            # Bind path field
            bind_frame = ctk.CTkFrame(volume_edit_window)
            bind_frame.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(bind_frame, text="Bind:", width=80).pack(side="left")
            bind_entry = ctk.CTkEntry(bind_frame, placeholder_text="!data/app")
            bind_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
            bind_entry.insert(0, bind_path)
            
            # Buttons
            button_frame = ctk.CTkFrame(volume_edit_window)
            button_frame.pack(pady=20)
            
            def save_volume_changes():
                new_container = container_entry.get().strip()
                new_bind = bind_entry.get().strip()
                if new_container and new_bind:
                    display_text = f"{new_container} -> {new_bind}"
                    edit_volumes_listbox.delete(index)
                    edit_volumes_listbox.insert(index, display_text)
                    edit_volumes_listbox.selection_set(index)
                    volume_edit_window.destroy()
            
            ctk.CTkButton(button_frame, text="Save", command=save_volume_changes, width=80).pack(side="left", padx=5)
            ctk.CTkButton(button_frame, text="Cancel", command=volume_edit_window.destroy, width=80).pack(side="left", padx=5)
            
            container_entry.focus()
        
        ctk.CTkButton(volume_input_frame, text="Add", command=add_edit_volume, width=50, height=28).grid(row=0, column=4, padx=(5, 5))
        print("DEBUG: Volume Add button created in POPUP WINDOW")
        
        edit_volumes_listbox = tk.Listbox(volumes_frame, height=3, font=("Segoe UI", 9))
        edit_volumes_listbox.pack(fill="x", padx=10, pady=5)
        edit_volumes_listbox.bind("<Double-Button-1>", lambda e: edit_edit_volume())
        
        # Load existing volumes
        for volume in template.get('volumes', []):
            if isinstance(volume, dict):
                container_path = volume.get('container', '')
                bind_path = volume.get('bind', '')
                if container_path and bind_path:
                    edit_volumes_listbox.insert(tk.END, f"{container_path} -> {bind_path}")
        
        # Volume buttons
        volume_buttons = ctk.CTkFrame(volumes_frame)
        volume_buttons.pack(pady=5)
        ctk.CTkButton(volume_buttons, text="Edit", command=edit_edit_volume, width=60, height=25).pack(side="left", padx=2)
        ctk.CTkButton(volume_buttons, text="Remove", command=remove_edit_volume, width=60, height=25).pack(side="left", padx=2)
        print("DEBUG: Volume Edit/Remove buttons created in POPUP WINDOW")
        
        # Save Buttons - This is what you actually asked for!
        buttons_frame = ctk.CTkFrame(parent)
        buttons_frame.pack(fill="x", padx=5, pady=20)
        
        def save_template_choice():
            """Show the exact choice dialog you requested"""
            # Build the edited template
            edited_template = {
                "title": edit_title.get().strip(),
                "description": edit_description.get().strip(),
                "image": edit_image.get().strip(),
                "platform": edit_platform.get(),
                "restart_policy": edit_restart.get()
            }
            
            # Add optional fields
            if edit_logo.get().strip():
                edited_template["logo"] = edit_logo.get().strip()
            
            note_text = edit_note.get("1.0", "end-1c").strip()
            if note_text:
                edited_template["note"] = note_text
            
            if edit_admin_only.get():
                edited_template["administrator_only"] = True
            
            # Extract data from popup form listboxes with debugging
            print("DEBUG: (POPUP) Extracting template data from popup form")
            
            # Add categories from popup listbox
            categories = []
            try:
                for i in range(edit_categories_listbox.size()):
                    category = edit_categories_listbox.get(i)
                    if category and category.strip():
                        categories.append(category.strip())
                if categories:
                    edited_template["categories"] = categories
                    print(f"DEBUG: (POPUP) Extracted {len(categories)} categories: {categories}")
                else:
                    print("DEBUG: (POPUP) No categories found in popup listbox")
            except Exception as e:
                print(f"ERROR: (POPUP) Failed to extract categories: {str(e)}")
            
            # Add environment variables from popup listbox
            env_vars = []
            try:
                for i in range(edit_env_listbox.size()):
                    env_text = edit_env_listbox.get(i)
                    if env_text and env_text.strip():
                        if '=' in env_text:
                            name, value = env_text.split('=', 1)
                            env_vars.append({"name": name.strip(), "default": value.strip()})
                        else:
                            env_vars.append({"name": env_text.strip()})
                if env_vars:
                    edited_template["env"] = env_vars
                    print(f"DEBUG: (POPUP) Extracted {len(env_vars)} environment variables: {[e.get('name') for e in env_vars]}")
                else:
                    print("DEBUG: (POPUP) No environment variables found in popup listbox")
            except Exception as e:
                print(f"ERROR: (POPUP) Failed to extract environment variables: {str(e)}")
            
            # Add ports from popup listbox
            ports = []
            try:
                for i in range(edit_ports_listbox.size()):
                    port_text = edit_ports_listbox.get(i)
                    if port_text and port_text.strip() and ': ' in port_text:
                        label, port_num = port_text.split(': ', 1)
                        ports.append({label.strip(): port_num.strip()})
                if ports:
                    edited_template["ports"] = ports
                    print(f"DEBUG: (POPUP) Extracted {len(ports)} ports: {ports}")
                else:
                    print("DEBUG: (POPUP) No ports found in popup listbox")
            except Exception as e:
                print(f"ERROR: (POPUP) Failed to extract ports: {str(e)}")
            
            # Add volumes from popup listbox
            volumes = []
            try:
                for i in range(edit_volumes_listbox.size()):
                    volume_text = edit_volumes_listbox.get(i)
                    if volume_text and volume_text.strip() and ' -> ' in volume_text:
                        container_path, bind_path = volume_text.split(' -> ', 1)
                        volumes.append({"container": container_path.strip(), "bind": bind_path.strip()})
                if volumes:
                    edited_template["volumes"] = volumes
                    print(f"DEBUG: (POPUP) Extracted {len(volumes)} volumes: {volumes}")
                else:
                    print("DEBUG: (POPUP) No volumes found in popup listbox")
            except Exception as e:
                print(f"ERROR: (POPUP) Failed to extract volumes: {str(e)}")
            
            print(f"DEBUG: (POPUP) Final edited template keys: {list(edited_template.keys())}")
            
            # Show the correct choice based on source type
            choice_dialog = ctk.CTkToplevel(edit_window)
            choice_dialog.title("Save Template Changes")
            choice_dialog.geometry("500x300")
            choice_dialog.resizable(False, False)
            choice_dialog.transient(edit_window)
            choice_dialog.grab_set()
            
            ctk.CTkLabel(choice_dialog, text="How do you want to save your changes?", 
                        font=ctk.CTkFont(size=16, weight="bold")).pack(pady=20)
            
            # Check if source is URL or local file
            source_path = template_info['source']
            is_url_source = source_path.startswith('http') or source_path.startswith('BASE_TEMPLATE:')
            is_local_file = os.path.exists(source_path) and not is_url_source
            
            def save_as_separate():
                """Save as a separate template"""
                choice_dialog.destroy()
                edit_window.destroy()
                
                # Add to manual templates
                self.manual_templates.append(edited_template)
                self.manual_templates_listbox.insert(tk.END, f"{edited_template['title']} - {edited_template['image']}")
                
                messagebox.showinfo("Success", f"Template '{edited_template['title']}' saved as a separate template!")
            
            def save_to_local_file():
                """Save the entire template collection to a local file"""
                choice_dialog.destroy()
                
                try:
                    # Get the original template collection 
                    original_source_data = self.loaded_templates.get(source_path, {})
                    
                    # Extract all templates from the source
                    from utils import JSONValidator
                    all_templates = JSONValidator.extract_templates(original_source_data)
                    
                    # Find and replace the edited template
                    template_updated = False
                    for i, tmpl in enumerate(all_templates):
                        if (tmpl.get('title') == template_info['template'].get('title') and 
                            tmpl.get('image') == template_info['template'].get('image')):
                            all_templates[i] = edited_template
                            template_updated = True
                            break
                    
                    if not template_updated:
                        # If not found, add as new template
                        all_templates.append(edited_template)
                    
                    # Create the complete template file structure
                    complete_template_file = {
                        "version": "2",
                        "templates": all_templates
                    }
                    
                    # Show file save dialog
                    from tkinter import filedialog
                    save_path = filedialog.asksaveasfilename(
                        title="Save Template Collection",
                        defaultextension=".json",
                        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                        initialfile="templates.json"
                    )
                    
                    if save_path:
                        with open(save_path, 'w', encoding='utf-8') as f:
                            json.dump(complete_template_file, f, indent=2, ensure_ascii=False)
                        
                        edit_window.destroy()
                        messagebox.showinfo("Success", 
                                           f"Template collection saved to:\n{save_path}\n\n"
                                           f"Template '{edited_template['title']}' has been updated in the file.")
                    else:
                        # User cancelled save dialog, keep edit window open
                        pass
                        
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save template collection:\n{str(e)}")
            
            def update_local_file():
                """Update the original local source file"""
                choice_dialog.destroy()
                edit_window.destroy()
                
                try:
                    # Update the source file with the modified template
                    self.update_source_template(edited_template, template_info)
                    messagebox.showinfo("Success", f"Original template updated and source file saved!")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to update source file:\n{str(e)}")
            
            # Always show "Save as Separate Template" option
            ctk.CTkButton(choice_dialog, text="Save as Separate Template", 
                         command=save_as_separate, width=200, height=40,
                         font=ctk.CTkFont(size=12, weight="bold")).pack(pady=10)
            
            # Show different second option based on source type
            if is_local_file:
                # For local files, allow updating the original file
                ctk.CTkButton(choice_dialog, text="Update Original Source File", 
                             command=update_local_file, width=200, height=40,
                             font=ctk.CTkFont(size=12, weight="bold")).pack(pady=10)
            else:
                # For URLs/remote sources, offer to save to local file
                ctk.CTkButton(choice_dialog, text="Save Collection to Local File", 
                             command=save_to_local_file, width=200, height=40,
                             font=ctk.CTkFont(size=12, weight="bold")).pack(pady=10)
            
            ctk.CTkButton(choice_dialog, text="Cancel", 
                         command=choice_dialog.destroy, width=100, height=30).pack(pady=10)
        
        ctk.CTkButton(buttons_frame, text="Save Changes", 
                     command=save_template_choice, width=150, height=40,
                     font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=10)
        
        ctk.CTkButton(buttons_frame, text="Cancel", 
                     command=edit_window.destroy, width=100, height=40).pack(side="left", padx=10)

    def populate_manual_form_with_template(self, template):
        """Populate the manual entry form with template data with debugging"""
        try:
            print(f"DEBUG: Loading template into form: {template.get('title', 'Untitled')}")
            print(f"DEBUG: Template has these keys: {list(template.keys())}")
            
            # Clear form first
            self.clear_manual_form()
            
            # Populate basic fields
            if 'title' in template:
                self.manual_title.insert(0, template['title'])
                print(f"DEBUG: Loaded title: {template['title']}")
            if 'description' in template:
                self.manual_description.insert(0, template['description'])
            if 'image' in template:
                self.manual_image.insert(0, template['image'])
                print(f"DEBUG: Loaded image: {template['image']}")
            if 'logo' in template:
                self.manual_logo.insert(0, template['logo'])
            if 'note' in template:
                # Clear placeholder and insert actual note content
                self.manual_note.delete("1.0", tk.END)
                self.manual_note.insert("1.0", template['note'])
                self.manual_note.configure(text_color=("gray10", "gray90"))
            
            # Set dropdowns
            if 'platform' in template:
                self.manual_platform.set(template['platform'])
            if 'restart_policy' in template:
                self.manual_restart.set(template['restart_policy'])
            
            # Set administrator only
            if template.get('administrator_only'):
                self.manual_admin_only.select()
            
            # Load categories with debugging
            if 'categories' in template and isinstance(template['categories'], list):
                print(f"DEBUG: Loading {len(template['categories'])} categories: {template['categories']}")
                for category in template['categories']:
                    self.categories_listbox.insert(tk.END, category)
                print(f"DEBUG: Categories listbox now has {self.categories_listbox.size()} items")
            else:
                print("DEBUG: No categories found in template")
            
            # Load environment variables with debugging
            if 'env' in template and isinstance(template['env'], list):
                print(f"DEBUG: Loading {len(template['env'])} environment variables")
                for env_var in template['env']:
                    if isinstance(env_var, dict):
                        name = env_var.get('name', '')
                        default_val = env_var.get('default', env_var.get('value', ''))
                        if default_val:
                            display_text = f"{name}={default_val}"
                        else:
                            display_text = name
                        self.env_listbox.insert(tk.END, display_text)
                        print(f"DEBUG: Added env var: {display_text}")
                print(f"DEBUG: Environment variables listbox now has {self.env_listbox.size()} items")
            else:
                print("DEBUG: No environment variables found in template")
            
            # Load ports with debugging
            if 'ports' in template and isinstance(template['ports'], list):
                print(f"DEBUG: Loading {len(template['ports'])} ports")
                for port_obj in template['ports']:
                    if isinstance(port_obj, dict):
                        for label, port_num in port_obj.items():
                            display_text = f"{label}: {port_num}"
                            self.ports_listbox.insert(tk.END, display_text)
                            print(f"DEBUG: Added port: {display_text}")
                print(f"DEBUG: Ports listbox now has {self.ports_listbox.size()} items")
            else:
                print("DEBUG: No ports found in template")
            
            # Load volumes with debugging
            if 'volumes' in template and isinstance(template['volumes'], list):
                print(f"DEBUG: Loading {len(template['volumes'])} volumes")
                for volume in template['volumes']:
                    if isinstance(volume, dict):
                        container_path = volume.get('container', '')
                        bind_path = volume.get('bind', '')
                        if container_path and bind_path:
                            display_text = f"{container_path} -> {bind_path}"
                            self.volumes_listbox.insert(tk.END, display_text)
                            print(f"DEBUG: Added volume: {display_text}")
                print(f"DEBUG: Volumes listbox now has {self.volumes_listbox.size()} items")
            else:
                print("DEBUG: No volumes found in template")
                
            print("DEBUG: Template loading completed")
            
        except Exception as e:
            print(f"ERROR in populate_manual_form_with_template: {str(e)}")
            messagebox.showerror("Error", f"Failed to load template into form: {str(e)}")
    
    def update_status(self, message: str):
        """Update status label with debugging output"""
        def update():
            self.status_label.configure(text=message)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] STATUS: {message}")
        
        self.root.after(0, update)
    
    def debug_ui_elements(self):
        """Debug function to check if UI elements exist"""
        try:
            print("\n=== UI ELEMENTS DEBUG ===")
            
            # Check manual entry form elements
            elements_to_check = [
                ('manual_title', 'Title entry'),
                ('manual_description', 'Description entry'),
                ('manual_image', 'Image entry'),
                ('manual_logo', 'Logo entry'),
                ('manual_note', 'Note textbox'),
                ('manual_platform', 'Platform combo'),
                ('manual_restart', 'Restart combo'),
                ('manual_admin_only', 'Admin checkbox'),
                ('categories_listbox', 'Categories listbox'),
                ('manual_category_entry', 'Category entry'),
                ('manual_category_combo', 'Category combo'),
                ('env_listbox', 'Environment variables listbox'),
                ('manual_env_name', 'Env name entry'),
                ('manual_env_value', 'Env value entry'),
                ('ports_listbox', 'Ports listbox'),
                ('manual_port_label', 'Port label entry'),
                ('manual_port_number', 'Port number entry'),
                ('volumes_listbox', 'Volumes listbox'),
                ('manual_volume_container', 'Volume container entry'),
                ('manual_volume_bind', 'Volume bind entry'),
                ('manual_templates_listbox', 'Manual templates listbox'),
                ('add_template_btn', 'Add template button'),
                ('clear_form_btn', 'Clear form button')
            ]
            
            for attr_name, description in elements_to_check:
                if hasattr(self, attr_name):
                    element = getattr(self, attr_name)
                    print(f"  ✓ {description} ({attr_name}): {type(element).__name__}")
                else:
                    print(f"  ✗ {description} ({attr_name}): MISSING!")
            
            # Check listbox contents
            print("\n=== LISTBOX CONTENTS ===")
            if hasattr(self, 'categories_listbox'):
                print(f"  Categories: {self.categories_listbox.size()} items")
                for i in range(min(5, self.categories_listbox.size())):
                    print(f"    {i}: {self.categories_listbox.get(i)}")
            
            if hasattr(self, 'env_listbox'):
                print(f"  Environment Variables: {self.env_listbox.size()} items")
                for i in range(min(5, self.env_listbox.size())):
                    print(f"    {i}: {self.env_listbox.get(i)}")
            
            if hasattr(self, 'ports_listbox'):
                print(f"  Ports: {self.ports_listbox.size()} items")
                for i in range(min(5, self.ports_listbox.size())):
                    print(f"    {i}: {self.ports_listbox.get(i)}")
            
            if hasattr(self, 'volumes_listbox'):
                print(f"  Volumes: {self.volumes_listbox.size()} items")
                for i in range(min(5, self.volumes_listbox.size())):
                    print(f"    {i}: {self.volumes_listbox.get(i)}")
            
            print("=== END DEBUG ===\n")
            
        except Exception as e:
            print(f"ERROR in debug_ui_elements: {str(e)}")
    
    def run(self):
        """Run the application with debugging"""
        print("Starting JSON Template Combiner with enhanced debugging...")
        self.debug_ui_elements()
        self.root.mainloop()


def main():
    """Main entry point"""
    app = JSONTemplateApp()
    app.run()


if __name__ == "__main__":
    main()
