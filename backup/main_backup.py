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
        self.root.geometry("1200x800")
        
        # Data storage
        self.url_sources = []
        self.file_sources = []
        self.loaded_templates = {}
        self.manual_templates = []  # Store manually created templates
        self.all_categories = set()  # Store all unique categories from sources
        self.all_templates_for_editing = []  # Store all templates for editing tab
        self.final_template = {"version": "2", "templates": []}
        
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
        
        # Create scrollable frame
        self.manual_scroll = ctk.CTkScrollableFrame(tab_manual)
        self.manual_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_label = ctk.CTkLabel(self.manual_scroll, text="Create Template Manually", 
                                  font=ctk.CTkFont(size=18, weight="bold"))
        title_label.pack(pady=(0, 20))
        
        # Basic Information Section
        basic_frame = ctk.CTkFrame(self.manual_scroll)
        basic_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(basic_frame, text="Basic Information", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        # Title (required)
        title_row = ctk.CTkFrame(basic_frame)
        title_row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(title_row, text="Title*:", width=100).pack(side="left", padx=(0, 10))
        self.manual_title = ctk.CTkEntry(title_row, placeholder_text="e.g., Nginx Web Server")
        self.manual_title.pack(side="left", fill="x", expand=True)
        
        # Description
        desc_row = ctk.CTkFrame(basic_frame)
        desc_row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(desc_row, text="Description:", width=100).pack(side="left", padx=(0, 10))
        self.manual_description = ctk.CTkEntry(desc_row, placeholder_text="Brief description of the application")
        self.manual_description.pack(side="left", fill="x", expand=True)
        
        # Image (required)
        image_row = ctk.CTkFrame(basic_frame)
        image_row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(image_row, text="Image*:", width=100).pack(side="left", padx=(0, 10))
        self.manual_image = ctk.CTkEntry(image_row, placeholder_text="e.g., nginx:latest")
        self.manual_image.pack(side="left", fill="x", expand=True)
        
        # Logo
        logo_row = ctk.CTkFrame(basic_frame)
        logo_row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(logo_row, text="Logo URL:", width=100).pack(side="left", padx=(0, 10))
        self.manual_logo = ctk.CTkEntry(logo_row, placeholder_text="https://example.com/logo.png")
        self.manual_logo.pack(side="left", fill="x", expand=True)
        
        # Platform
        platform_row = ctk.CTkFrame(basic_frame)
        platform_row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(platform_row, text="Platform:", width=100).pack(side="left", padx=(0, 10))
        self.manual_platform = ctk.CTkComboBox(platform_row, values=["linux", "windows"])
        self.manual_platform.pack(side="left", padx=(0, 10))
        self.manual_platform.set("linux")
        
        # Restart Policy
        restart_row = ctk.CTkFrame(basic_frame)
        restart_row.pack(fill="x", padx=10, pady=(2, 10))
        ctk.CTkLabel(restart_row, text="Restart Policy:", width=100).pack(side="left", padx=(0, 10))
        self.manual_restart = ctk.CTkComboBox(restart_row, values=["unless-stopped", "always", "no", "on-failure"])
        self.manual_restart.pack(side="left", padx=(0, 10))
        self.manual_restart.set("unless-stopped")
        
        # Categories Section
        categories_frame = ctk.CTkFrame(self.manual_scroll)
        categories_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(categories_frame, text="Categories", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        cat_input_frame = ctk.CTkFrame(categories_frame)
        cat_input_frame.pack(fill="x", padx=10, pady=5)
        
        # Category dropdown with option to add custom
        self.manual_category_combo = ctk.CTkComboBox(cat_input_frame, values=["webserver", "database", "media", "networking", "tools"], 
                                                    width=200, command=self.on_category_selected)
        self.manual_category_combo.pack(side="left", padx=(0, 5))
        self.manual_category_combo.set("Select or type category...")
        
        # Allow custom entry
        self.manual_category_entry = ctk.CTkEntry(cat_input_frame, placeholder_text="or type custom category", width=150)
        self.manual_category_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        ctk.CTkButton(cat_input_frame, text="Add", command=self.add_category, width=60).pack(side="right")
        
        # Refresh categories button
        refresh_cat_frame = ctk.CTkFrame(categories_frame)
        refresh_cat_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkButton(refresh_cat_frame, text="🔄 Refresh Categories from Sources", 
                     command=self.refresh_categories, width=200).pack(side="left", padx=10)
        
        self.categories_listbox = tk.Listbox(categories_frame, height=3)
        self.categories_listbox.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(categories_frame, text="Remove Selected", 
                     command=self.remove_category).pack(pady=5)
        
        # Environment Variables Section
        env_frame = ctk.CTkFrame(self.manual_scroll)
        env_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(env_frame, text="Environment Variables", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        env_input_frame = ctk.CTkFrame(env_frame)
        env_input_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(env_input_frame, text="Name:", width=60).pack(side="left")
        self.manual_env_name = ctk.CTkEntry(env_input_frame, placeholder_text="VAR_NAME", width=120)
        self.manual_env_name.pack(side="left", padx=5)
        
        ctk.CTkLabel(env_input_frame, text="Value:", width=60).pack(side="left")
        self.manual_env_value = ctk.CTkEntry(env_input_frame, placeholder_text="default_value")
        self.manual_env_value.pack(side="left", fill="x", expand=True, padx=5)
        
        ctk.CTkButton(env_input_frame, text="Add", command=self.add_env_var, width=60).pack(side="right")
        
        self.env_listbox = tk.Listbox(env_frame, height=4)
        self.env_listbox.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(env_frame, text="Remove Selected", 
                     command=self.remove_env_var).pack(pady=5)
        
        # Ports Section
        ports_frame = ctk.CTkFrame(self.manual_scroll)
        ports_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(ports_frame, text="Ports", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        port_input_frame = ctk.CTkFrame(ports_frame)
        port_input_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(port_input_frame, text="Label:", width=60).pack(side="left")
        self.manual_port_label = ctk.CTkEntry(port_input_frame, placeholder_text="WebUI", width=100)
        self.manual_port_label.pack(side="left", padx=5)
        
        ctk.CTkLabel(port_input_frame, text="Port:", width=60).pack(side="left")
        self.manual_port_number = ctk.CTkEntry(port_input_frame, placeholder_text="80/tcp", width=100)
        self.manual_port_number.pack(side="left", padx=5)
        
        ctk.CTkButton(port_input_frame, text="Add", command=self.add_port, width=60).pack(side="right")
        
        self.ports_listbox = tk.Listbox(ports_frame, height=3)
        self.ports_listbox.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(ports_frame, text="Remove Selected", 
                     command=self.remove_port).pack(pady=5)
        
        # Volumes Section
        volumes_frame = ctk.CTkFrame(self.manual_scroll)
        volumes_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(volumes_frame, text="Volumes", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        volume_input_frame = ctk.CTkFrame(volumes_frame)
        volume_input_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(volume_input_frame, text="Container:", width=80).pack(side="left")
        self.manual_volume_container = ctk.CTkEntry(volume_input_frame, placeholder_text="/app/data", width=150)
        self.manual_volume_container.pack(side="left", padx=5)
        
        ctk.CTkLabel(volume_input_frame, text="Bind:", width=60).pack(side="left")
        self.manual_volume_bind = ctk.CTkEntry(volume_input_frame, placeholder_text="!data/app")
        self.manual_volume_bind.pack(side="left", fill="x", expand=True, padx=5)
        
        ctk.CTkButton(volume_input_frame, text="Add", command=self.add_volume, width=60).pack(side="right")
        
        self.volumes_listbox = tk.Listbox(volumes_frame, height=3)
        self.volumes_listbox.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(volumes_frame, text="Remove Selected", 
                     command=self.remove_volume).pack(pady=5)
        
        # Additional Fields Section
        additional_frame = ctk.CTkFrame(self.manual_scroll)
        additional_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(additional_frame, text="Additional Options", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        # Note
        note_row = ctk.CTkFrame(additional_frame)
        note_row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(note_row, text="Note:", width=100).pack(side="left", padx=(0, 10))
        self.manual_note = ctk.CTkEntry(note_row, placeholder_text="Additional information or instructions")
        self.manual_note.pack(side="left", fill="x", expand=True)
        
        # Administrator Only
        admin_row = ctk.CTkFrame(additional_frame)
        admin_row.pack(fill="x", padx=10, pady=(2, 10))
        self.manual_admin_only = ctk.CTkCheckBox(admin_row, text="Administrator Only")
        self.manual_admin_only.pack(side="left", padx=10)
        
        # Action Buttons
        action_frame = ctk.CTkFrame(self.manual_scroll)
        action_frame.pack(fill="x", padx=5, pady=10)
        
        button_frame = ctk.CTkFrame(action_frame)
        button_frame.pack(pady=10)
        
        self.clear_form_btn = ctk.CTkButton(button_frame, text="Clear Form", 
                                           command=self.clear_manual_form, width=120)
        self.clear_form_btn.pack(side="left", padx=5)
        
        self.add_template_btn = ctk.CTkButton(button_frame, text="Add Template", 
                                             command=self.add_manual_template, width=120,
                                             font=ctk.CTkFont(weight="bold"))
        self.add_template_btn.pack(side="left", padx=5)
        
        # Manual Templates List
        list_frame = ctk.CTkFrame(self.manual_scroll)
        list_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(list_frame, text="Created Templates", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.manual_templates_listbox = tk.Listbox(list_frame, height=5)
        self.manual_templates_listbox.pack(fill="x", padx=10, pady=5)
        
        manual_buttons_frame = ctk.CTkFrame(list_frame)
        manual_buttons_frame.pack(pady=5)
        
        self.edit_manual_btn = ctk.CTkButton(manual_buttons_frame, text="Edit Selected", 
                                            command=self.edit_manual_template, width=120)
        self.edit_manual_btn.pack(side="left", padx=5)
        
        self.delete_manual_btn = ctk.CTkButton(manual_buttons_frame, text="Delete Selected", 
                                              command=self.delete_manual_template, width=120)
        self.delete_manual_btn.pack(side="left", padx=5)
    
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
        """Add a category to the list"""
        # Try to get from text entry first, then from dropdown
        category = self.manual_category_entry.get().strip()
        
        if not category:
            # Try dropdown selection
            dropdown_value = self.manual_category_combo.get()
            if dropdown_value and dropdown_value != "Select or type category...":
                category = dropdown_value
        
        if category:
            # Check if already in list
            categories_list = []
            for i in range(self.categories_listbox.size()):
                categories_list.append(self.categories_listbox.get(i))
            
            if category not in categories_list:
                self.categories_listbox.insert(tk.END, category)
                self.manual_category_entry.delete(0, tk.END)
                self.manual_category_combo.set("Select or type category...")
            else:
                messagebox.showinfo("Info", f"Category '{category}' is already added")
        else:
            messagebox.showwarning("Warning", "Please select a category from dropdown or enter a custom one")
    
    def remove_category(self):
        """Remove selected category"""
        selection = self.categories_listbox.curselection()
        if selection:
            self.categories_listbox.delete(selection[0])
    
    def add_env_var(self):
        """Add an environment variable"""
        name = self.manual_env_name.get().strip()
        value = self.manual_env_value.get().strip()
        if name:
            display_text = f"{name}={value}" if value else name
            self.env_listbox.insert(tk.END, display_text)
            self.manual_env_name.delete(0, tk.END)
            self.manual_env_value.delete(0, tk.END)
    
    def remove_env_var(self):
        """Remove selected environment variable"""
        selection = self.env_listbox.curselection()
        if selection:
            self.env_listbox.delete(selection[0])
    
    def add_port(self):
        """Add a port mapping"""
        label = self.manual_port_label.get().strip()
        port = self.manual_port_number.get().strip()
        if label and port:
            display_text = f"{label}: {port}"
            self.ports_listbox.insert(tk.END, display_text)
            self.manual_port_label.delete(0, tk.END)
            self.manual_port_number.delete(0, tk.END)
    
    def remove_port(self):
        """Remove selected port"""
        selection = self.ports_listbox.curselection()
        if selection:
            self.ports_listbox.delete(selection[0])
    
    def add_volume(self):
        """Add a volume mapping"""
        container_path = self.manual_volume_container.get().strip()
        bind_path = self.manual_volume_bind.get().strip()
        if container_path and bind_path:
            display_text = f"{container_path} -> {bind_path}"
            self.volumes_listbox.insert(tk.END, display_text)
            self.manual_volume_container.delete(0, tk.END)
            self.manual_volume_bind.delete(0, tk.END)
    
    def remove_volume(self):
        """Remove selected volume"""
        selection = self.volumes_listbox.curselection()
        if selection:
            self.volumes_listbox.delete(selection[0])
    
    def clear_manual_form(self):
        """Clear all manual form fields"""
        # Clear basic fields
        self.manual_title.delete(0, tk.END)
        self.manual_description.delete(0, tk.END)
        self.manual_image.delete(0, tk.END)
        self.manual_logo.delete(0, tk.END)
        self.manual_note.delete(0, tk.END)
        
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
        
        note = self.manual_note.get().strip()
        if note:
            template["note"] = note
        
        if self.manual_admin_only.get():
            template["administrator_only"] = True
        
        # Add categories
        categories = []
        for i in range(self.categories_listbox.size()):
            categories.append(self.categories_listbox.get(i))
        if categories:
            template["categories"] = categories
        
        # Add environment variables
        env_vars = []
        for i in range(self.env_listbox.size()):
            env_text = self.env_listbox.get(i)
            if '=' in env_text:
                name, value = env_text.split('=', 1)
                env_vars.append({"name": name, "default": value})
            else:
                env_vars.append({"name": env_text})
        if env_vars:
            template["env"] = env_vars
        
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
        """Edit selected manual template"""
        selection = self.manual_templates_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a template to edit")
            return
        
        index = selection[0]
        template = self.manual_templates[index]
        
        # Populate form with template data
        self.clear_manual_form()
        
        self.manual_title.insert(0, template.get('title', ''))
        self.manual_description.insert(0, template.get('description', ''))
        self.manual_image.insert(0, template.get('image', ''))
        self.manual_logo.insert(0, template.get('logo', ''))
        self.manual_note.insert(0, template.get('note', ''))
        
        self.manual_platform.set(template.get('platform', 'linux'))
        self.manual_restart.set(template.get('restart_policy', 'unless-stopped'))
        
        if template.get('administrator_only'):
            self.manual_admin_only.select()
        
        # Load categories
        for category in template.get('categories', []):
            self.categories_listbox.insert(tk.END, category)
        
        # Load environment variables
        for env_var in template.get('env', []):
            if 'default' in env_var:
                display_text = f"{env_var['name']}={env_var['default']}"
            else:
                display_text = env_var['name']
            self.env_listbox.insert(tk.END, display_text)
        
        # Load ports
        for port_obj in template.get('ports', []):
            for label, port_num in port_obj.items():
                self.ports_listbox.insert(tk.END, f"{label}: {port_num}")
        
        # Load volumes
        for volume in template.get('volumes', []):
            container_path = volume.get('container', '')
            bind_path = volume.get('bind', '')
            self.volumes_listbox.insert(tk.END, f"{container_path} -> {bind_path}")
        
        # Remove from list (will be re-added when user clicks Add Template)
        self.manual_templates.pop(index)
        self.manual_templates_listbox.delete(index)
        
        messagebox.showinfo("Edit Mode", f"Template '{template['title']}' loaded for editing. Make your changes and click 'Add Template' to save.")
    
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
    def on_category_selected(self, choice):
        """Handle category selection from dropdown"""
        if choice != "Select or type category...":
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
                title_match = filter_text in template_info['title'].lower()
                image_match = filter_text in template_info['image'].lower()
                desc_match = filter_text in template_info['description'].lower()
                
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
                title_match = filter_text in template_info['title'].lower()
                image_match = filter_text in template_info['image'].lower()
                desc_match = filter_text in template_info['description'].lower()
                
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
        
        # Switch to manual entry tab and populate form
        self.notebook.set("Manual Entry")
        self.populate_manual_form_with_template(template)
        
        messagebox.showinfo("Template Loaded", 
                           f"Template '{template_info['title']}' loaded into manual entry form.\n\n"
                           f"Source: {self.get_source_display_name(template_info['source'])}\n\n"
                           f"Make your changes and click 'Add Template' to save as a new template.")
    
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
                title_match = filter_text in template_info['title'].lower()
                image_match = filter_text in template_info['image'].lower() 
                desc_match = filter_text in template_info['description'].lower()
                
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
    
    def populate_manual_form_with_template(self, template):
        """Populate the manual entry form with template data"""
        # Clear form first
        self.clear_manual_form()
        
        # Populate basic fields
        if 'title' in template:
            self.manual_title.insert(0, template['title'])
        if 'description' in template:
            self.manual_description.insert(0, template['description'])
        if 'image' in template:
            self.manual_image.insert(0, template['image'])
        if 'logo' in template:
            self.manual_logo.insert(0, template['logo'])
        if 'note' in template:
            self.manual_note.insert(0, template['note'])
        
        # Set dropdowns
        if 'platform' in template:
            self.manual_platform.set(template['platform'])
        if 'restart_policy' in template:
            self.manual_restart.set(template['restart_policy'])
        
        # Set administrator only
        if template.get('administrator_only'):
            self.manual_admin_only.select()
        
        # Load categories
        if 'categories' in template and isinstance(template['categories'], list):
            for category in template['categories']:
                self.categories_listbox.insert(tk.END, category)
        
        # Load environment variables
        if 'env' in template and isinstance(template['env'], list):
            for env_var in template['env']:
                if isinstance(env_var, dict):
                    name = env_var.get('name', '')
                    default_val = env_var.get('default', env_var.get('value', ''))
                    if default_val:
                        display_text = f"{name}={default_val}"
                    else:
                        display_text = name
                    self.env_listbox.insert(tk.END, display_text)
        
        # Load ports
        if 'ports' in template and isinstance(template['ports'], list):
            for port_obj in template['ports']:
                if isinstance(port_obj, dict):
                    for label, port_num in port_obj.items():
                        self.ports_listbox.insert(tk.END, f"{label}: {port_num}")
        
        # Load volumes
        if 'volumes' in template and isinstance(template['volumes'], list):
            for volume in template['volumes']:
                if isinstance(volume, dict):
                    container_path = volume.get('container', '')
                    bind_path = volume.get('bind', '')
                    if container_path and bind_path:
                        self.volumes_listbox.insert(tk.END, f"{container_path} -> {bind_path}")
    
    def update_status(self, message: str):
        """Update status label"""
        def update():
            self.status_label.configure(text=message)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        
        self.root.after(0, update)
    
    def run(self):
        """Run the application"""
        self.root.mainloop()


def main():
    """Main entry point"""
    app = JSONTemplateApp()
    app.run()


if __name__ == "__main__":
    main()
