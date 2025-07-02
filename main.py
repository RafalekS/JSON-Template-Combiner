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
        self.root.geometry("900x700")
        
        # Data storage
        self.url_sources = []
        self.file_sources = []
        self.loaded_templates = {}
        self.final_template = {"version": "2", "templates": []}
        
        # Initialize base template from the ibaraki source
        self.base_template_url = "https://templates-portainer.ibaraki.app"
        
        self.setup_ui()
        self.load_base_template()
        
    def setup_ui(self):
        """Set up the user interface"""
        # Create notebook for tabs
        self.notebook = ctk.CTkTabview(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create tabs
        self.setup_sources_tab()
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
        
        self.add_file_btn = ctk.CTkButton(file_frame, text="Add Local JSON File", 
                                         command=self.add_file_source)
        self.add_file_btn.pack(pady=5)
        
        # File list
        self.file_listbox = tk.Listbox(file_frame, height=6)
        self.file_listbox.pack(fill="x", padx=10, pady=5)
        
        self.remove_file_btn = ctk.CTkButton(file_frame, text="Remove Selected File", 
                                            command=self.remove_file_source)
        self.remove_file_btn.pack(pady=5)
        
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
    
    def load_base_template(self):
        """Load the base template from ibaraki"""
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
                    self.loaded_templates[self.base_template_url] = converted_data
                except ValueError as e:
                    self.update_status(f"Base template format conversion error: {str(e)}")
                    # Store as-is if conversion fails
                    self.loaded_templates[self.base_template_url] = base_data
                
                # Add to URL sources
                self.url_sources.append(self.base_template_url)
                self.url_listbox.insert(tk.END, self.base_template_url)
                
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
        
        # Don't allow removing the base template
        if url == self.base_template_url:
            messagebox.showwarning("Warning", "Cannot remove the base template source")
            return
        
        del self.url_sources[index]
        self.url_listbox.delete(index)
        
        # Remove from loaded templates if exists
        if url in self.loaded_templates:
            del self.loaded_templates[url]
    
    def add_file_source(self):
        """Add a local file source"""
        file_path = filedialog.askopenfilename(
            title="Select JSON File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
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
                            with open(file_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            
                            # Convert to Portainer format if needed
                            from utils import TemplateConverter
                            try:
                                converted_data = TemplateConverter.convert_to_portainer(data)
                                self.loaded_templates[file_path] = converted_data
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
                
            except Exception as e:
                self.update_status(f"Error processing sources: {str(e)}")
        
        threading.Thread(target=process_thread, daemon=True).start()
    
    def generate_summary(self):
        """Generate processing summary"""
        summary = []
        total_templates = 0
        
        for source, data in self.loaded_templates.items():
            source_name = os.path.basename(source) if os.path.exists(source) else source
            
            if isinstance(data, dict):
                if 'templates' in data and isinstance(data['templates'], list):
                    template_count = len(data['templates'])
                    total_templates += template_count
                    summary.append(f"✓ {source_name}: {template_count} templates")
                elif isinstance(data, list):
                    template_count = len(data)
                    total_templates += template_count
                    summary.append(f"✓ {source_name}: {template_count} templates")
                else:
                    # Try to extract using the new converter
                    try:
                        from utils import JSONValidator
                        extracted = JSONValidator.extract_templates(data)
                        template_count = len(extracted)
                        total_templates += template_count
                        summary.append(f"✓ {source_name}: {template_count} templates (converted)")
                    except:
                        summary.append(f"? {source_name}: Unknown format")
            else:
                summary.append(f"✗ {source_name}: Invalid JSON format")
        
        summary.insert(0, f"Total sources processed: {len(self.loaded_templates)}")
        summary.insert(1, f"Total templates found: {total_templates}")
        summary.append("")
        summary.append("Click 'Generate Final Template' to combine and deduplicate templates.")
        
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
