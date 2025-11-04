#!/usr/bin/env python3
"""
JSON Template Combiner - PyQt6 Main Window
A comprehensive GUI application for combining multiple JSON template sources
"""

from PyQt6.QtWidgets import (
    QMainWindow, QFileDialog, QMessageBox, QListWidgetItem,
    QInputDialog, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QCheckBox, QComboBox,
    QGroupBox, QFormLayout, QScrollArea, QWidget
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6 import uic
import requests
import json
import os
import difflib
import threading
from typing import List, Dict, Any, Tuple
from datetime import datetime
from utils import TemplateConverter, JSONValidator, ConfigManager


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


class LoadTemplateWorker(QThread):
    """Worker thread for loading a template from URL"""
    finished = pyqtSignal(str, dict, str)  # url, data, error

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            response = requests.get(self.url, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Convert to Portainer format if needed
            try:
                converted_data = TemplateConverter.convert_to_portainer(data)
                self.finished.emit(self.url, converted_data, "")
            except ValueError as e:
                # Store as-is if conversion fails
                self.finished.emit(self.url, data, f"Format conversion warning: {str(e)}")
        except Exception as e:
            self.finished.emit(self.url, {}, str(e))


class ProcessSourcesWorker(QThread):
    """Worker thread for processing all sources"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(dict)  # loaded_templates

    def __init__(self, url_sources: List[str], file_sources: List[str], loaded_templates: Dict):
        super().__init__()
        self.url_sources = url_sources
        self.file_sources = file_sources
        self.loaded_templates = loaded_templates.copy()

    def run(self):
        try:
            total_sources = len(self.url_sources) + len(self.file_sources)
            current = 0

            # Process URL sources
            for url in self.url_sources:
                if url not in self.loaded_templates:
                    self.status.emit(f"Loading URL: {url}")
                    try:
                        response = requests.get(url, timeout=30)
                        response.raise_for_status()
                        data = response.json()

                        # Convert to Portainer format if needed
                        try:
                            converted_data = TemplateConverter.convert_to_portainer(data)
                            self.loaded_templates[url] = converted_data
                        except ValueError as e:
                            self.status.emit(f"Format conversion error for {url}: {str(e)}")
                            self.loaded_templates[url] = data
                    except Exception as e:
                        self.status.emit(f"Error loading {url}: {str(e)}")

                current += 1
                self.progress.emit(int((current / total_sources) * 100))

            # Process file sources
            for file_path in self.file_sources:
                if file_path not in self.loaded_templates:
                    self.status.emit(f"Loading file: {os.path.basename(file_path)}")
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        # Convert to Portainer format if needed
                        try:
                            converted_data = TemplateConverter.convert_to_portainer(data)
                            self.loaded_templates[file_path] = converted_data
                        except ValueError as e:
                            self.status.emit(f"Format conversion error for {file_path}: {str(e)}")
                            self.loaded_templates[file_path] = data
                    except Exception as e:
                        self.status.emit(f"Error loading {file_path}: {str(e)}")

                current += 1
                self.progress.emit(int((current / total_sources) * 100))

            self.status.emit("All sources processed successfully")
            self.finished.emit(self.loaded_templates)
        except Exception as e:
            self.status.emit(f"Error processing sources: {str(e)}")
            self.finished.emit({})


class GenerateTemplateWorker(QThread):
    """Worker thread for generating the final template"""
    status = pyqtSignal(str)
    finished = pyqtSignal(dict, int, int)  # final_template, original_count, final_count

    def __init__(self, loaded_templates: Dict, manual_templates: List, processor):
        super().__init__()
        self.loaded_templates = loaded_templates
        self.manual_templates = manual_templates
        self.processor = processor

    def run(self):
        try:
            self.status.emit("Generating final template...")

            all_templates = []

            # Collect all templates from all sources
            for source, data in self.loaded_templates.items():
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

            # Add manual templates
            for template in self.manual_templates:
                template['_source'] = 'manual'
                all_templates.append(template)

            # Process templates for duplicates and architecture
            processed_templates = self.processor.process_duplicate_templates(all_templates)

            # Create final template structure
            final_template = {
                "version": "2",
                "templates": processed_templates
            }

            self.status.emit(f"Final template generated with {len(processed_templates)} templates")
            self.finished.emit(final_template, len(all_templates), len(processed_templates))
        except Exception as e:
            self.status.emit(f"Error generating template: {str(e)}")
            self.finished.emit({}, 0, 0)


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()

        # Load UI from file
        ui_path = os.path.join(os.path.dirname(__file__), 'config', 'main_window_pyqt6.ui')
        uic.loadUi(ui_path, self)

        # Data storage
        self.url_sources = []
        self.file_sources = []
        self.loaded_templates = {}
        self.manual_templates = []  # Store manually created templates
        self.all_categories = set()  # Store all unique categories from sources
        self.all_templates_for_editing = []  # Store all templates for editing tab
        self.final_template = {"version": "2", "templates": []}
        self.current_editing_context = None  # For tracking template edits

        # Worker threads
        self.load_worker = None
        self.process_worker = None
        self.generate_worker = None

        # Configuration
        self.config = ConfigManager()

        # Initialize base template from configuration
        self.base_template_enabled = self.config.get('base_template.enabled', True)
        self.base_template_url = self.config.get('base_template.url', 'https://templates-portainer.ibaraki.app')
        self.base_template_auto_load = self.config.get('base_template.auto_load', True)

        # Set base template values in UI
        self.baseTemplateEnabledCheckBox.setChecked(self.base_template_enabled)
        self.baseTemplateUrlLineEdit.setText(self.base_template_url)

        # Connect signals
        self.setup_connections()

        # Load base template if enabled
        if self.base_template_enabled and self.base_template_auto_load:
            self.load_base_template()

    def setup_connections(self):
        """Set up signal/slot connections"""
        # Sources tab
        self.addUrlButton.clicked.connect(self.add_url_source)
        self.removeUrlButton.clicked.connect(self.remove_url_source)
        self.addFileButton.clicked.connect(self.add_file_source)
        self.removeFileButton.clicked.connect(self.remove_file_source)
        self.processButton.clicked.connect(self.process_sources)
        self.urlLineEdit.returnPressed.connect(self.add_url_source)

        # Base template connections
        self.baseTemplateEnabledCheckBox.toggled.connect(self.toggle_base_template)
        self.updateBaseTemplateButton.clicked.connect(self.update_base_template_url)
        self.clearBaseTemplateButton.clicked.connect(self.clear_base_template)

        # Manual Entry tab
        self.clearFormButton.clicked.connect(self.clear_manual_form)
        self.addManualTemplateButton.clicked.connect(self.add_manual_template)

        # Categories
        self.addCategoryButton.clicked.connect(self.add_category)
        self.removeCategoryButton.clicked.connect(self.remove_category)
        self.editCategoryButton.clicked.connect(self.edit_category)
        self.refreshCategoriesButton.clicked.connect(self.refresh_categories)
        self.categoriesListWidget.itemDoubleClicked.connect(self.edit_category)

        # Environment Variables
        self.addEnvButton.clicked.connect(self.add_env_var)
        self.removeEnvButton.clicked.connect(self.remove_env_var)
        self.editEnvButton.clicked.connect(self.edit_env_var)
        self.envListWidget.itemDoubleClicked.connect(self.edit_env_var)

        # Ports
        self.addPortButton.clicked.connect(self.add_port)
        self.removePortButton.clicked.connect(self.remove_port)
        self.editPortButton.clicked.connect(self.edit_port)
        self.portsListWidget.itemDoubleClicked.connect(self.edit_port)

        # Volumes
        self.addVolumeButton.clicked.connect(self.add_volume)
        self.removeVolumeButton.clicked.connect(self.remove_volume)
        self.editVolumeButton.clicked.connect(self.edit_volume)
        self.volumesListWidget.itemDoubleClicked.connect(self.edit_volume)

        # Edit Templates tab
        self.refreshEditListButton.clicked.connect(self.refresh_edit_templates_list)
        self.editFilterLineEdit.textChanged.connect(self.filter_edit_templates)
        self.sourceFilterComboBox.currentTextChanged.connect(self.filter_by_source)
        self.editSelectedTemplateButton.clicked.connect(self.edit_selected_template)
        self.cloneTemplateButton.clicked.connect(self.clone_selected_template)
        self.viewJsonButton.clicked.connect(self.view_template_json)
        self.editTemplatesListWidget.itemDoubleClicked.connect(self.edit_selected_template)

        # Preview tab
        self.generateButton.clicked.connect(self.generate_final_template)

        # Save tab
        self.browseButton.clicked.connect(self.browse_save_location)
        self.saveButton.clicked.connect(self.save_template)

    # ========== SOURCES TAB METHODS ==========

    def load_base_template(self):
        """Load the base template from configured URL"""
        if not self.base_template_enabled:
            self.update_status("Base template is disabled")
            return

        self.update_status("Loading base template...")
        self.load_worker = LoadTemplateWorker(self.base_template_url)
        self.load_worker.finished.connect(self.on_base_template_loaded)
        self.load_worker.start()

    def on_base_template_loaded(self, url: str, data: dict, error: str):
        """Handle base template loaded"""
        if error:
            self.update_status(f"Error loading base template: {error}")
        else:
            # Store with special key to distinguish from URL sources
            self.loaded_templates[f"BASE_TEMPLATE:{url}"] = data
            self.update_status("Base template loaded successfully")

    def add_url_source(self):
        """Add a URL source"""
        url = self.urlLineEdit.text().strip()
        if not url:
            QMessageBox.warning(self, "Warning", "Please enter a URL")
            return

        if url in self.url_sources:
            QMessageBox.warning(self, "Warning", "URL already added")
            return

        # Validate URL
        from urllib.parse import urlparse
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                raise ValueError("Invalid URL")
        except:
            QMessageBox.critical(self, "Error", "Invalid URL format")
            return

        self.url_sources.append(url)
        self.urlListWidget.addItem(url)
        self.urlLineEdit.clear()
        self.update_status(f"Added URL source: {url}")

    def remove_url_source(self):
        """Remove selected URL source"""
        current_item = self.urlListWidget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a URL to remove")
            return

        row = self.urlListWidget.row(current_item)
        url = self.url_sources[row]

        # Remove from sources and UI
        del self.url_sources[row]
        self.urlListWidget.takeItem(row)

        # Remove from loaded templates if exists
        if url in self.loaded_templates:
            del self.loaded_templates[url]

        self.update_status(f"Removed URL source: {url}")

    def add_file_source(self):
        """Add a local file source"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Template File",
            "",
            "Template files (*.json *.yml *.yaml);;JSON files (*.json);;YAML files (*.yml *.yaml);;Docker Compose (docker-compose*.yml docker-compose*.yaml);;All files (*.*)"
        )

        if not file_path:
            return

        if file_path in self.file_sources:
            QMessageBox.warning(self, "Warning", "File already added")
            return

        self.file_sources.append(file_path)
        self.fileListWidget.addItem(os.path.basename(file_path))
        self.update_status(f"Added file source: {os.path.basename(file_path)}")

    def remove_file_source(self):
        """Remove selected file source"""
        current_item = self.fileListWidget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a file to remove")
            return

        row = self.fileListWidget.row(current_item)
        file_path = self.file_sources[row]

        del self.file_sources[row]
        self.fileListWidget.takeItem(row)

        # Remove from loaded templates if exists
        if file_path in self.loaded_templates:
            del self.loaded_templates[file_path]

        self.update_status(f"Removed file source: {os.path.basename(file_path)}")

    def toggle_base_template(self, checked: bool):
        """Toggle base template enabled/disabled"""
        self.base_template_enabled = checked
        self.config.set('base_template.enabled', checked)
        self.config.save_config()
        self.update_status(f"Base template {'enabled' if checked else 'disabled'}")

    def update_base_template_url(self):
        """Update the base template URL"""
        new_url = self.baseTemplateUrlLineEdit.text().strip()
        if not new_url:
            QMessageBox.warning(self, "Warning", "Please enter a URL")
            return

        self.base_template_url = new_url
        self.config.set('base_template.url', new_url)
        self.config.save_config()

        # Reload if enabled
        if self.base_template_enabled:
            # Clear old base template
            keys_to_remove = [k for k in self.loaded_templates.keys() if k.startswith("BASE_TEMPLATE:")]
            for key in keys_to_remove:
                del self.loaded_templates[key]

            # Load new one
            self.load_base_template()

    def clear_base_template(self):
        """Clear the base template"""
        # Remove from loaded templates
        keys_to_remove = [k for k in self.loaded_templates.keys() if k.startswith("BASE_TEMPLATE:")]
        for key in keys_to_remove:
            del self.loaded_templates[key]

        self.update_status("Base template cleared")

    def process_sources(self):
        """Process all sources and load JSON data"""
        if not self.url_sources and not self.file_sources:
            QMessageBox.warning(self, "Warning", "Please add at least one source")
            return

        self.process_worker = ProcessSourcesWorker(
            self.url_sources, self.file_sources, self.loaded_templates
        )
        self.process_worker.progress.connect(self.progressBar.setValue)
        self.process_worker.status.connect(self.update_status)
        self.process_worker.finished.connect(self.on_sources_processed)
        self.process_worker.start()

    def on_sources_processed(self, loaded_templates: dict):
        """Handle sources processed"""
        self.loaded_templates = loaded_templates
        self.generate_summary()

        # Refresh categories and edit templates list
        self.extract_categories_from_templates()
        self.refresh_edit_templates_list()

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
                        extracted = JSONValidator.extract_templates(data)
                        template_count = len(extracted)
                        total_templates += template_count
                        summary.append(f"✓ {source_name}: {template_count} templates (converted)")
                    except:
                        summary.append(f"? {source_name}: Unknown format")
            else:
                summary.append(f"✗ {source_name}: Invalid JSON format")

        # Add manual templates count
        if self.manual_templates:
            summary.append(f"✓ Manual templates: {len(self.manual_templates)}")
            total_templates += len(self.manual_templates)

        summary.insert(0, f"Total sources processed: {len(self.loaded_templates)}")
        summary.insert(1, f"Total templates found: {total_templates}")
        summary.append("")
        summary.append("Click 'Generate Final Template' to combine and deduplicate templates.")

        self.summaryTextEdit.setPlainText("\n".join(summary))

        # Switch to preview tab
        self.tabWidget.setCurrentIndex(3)  # Preview tab index

    # ========== MANUAL ENTRY TAB METHODS ==========

    def add_category(self):
        """Add a category to the list"""
        # Try entry first, then combo
        category = self.manualCategoryComboBox.currentText().strip()

        if not category or category == "Select...":
            QMessageBox.warning(self, "Validation Error", "Please select or enter a category")
            return

        # Check if already in list
        for i in range(self.categoriesListWidget.count()):
            if self.categoriesListWidget.item(i).text() == category:
                QMessageBox.warning(self, "Duplicate Category", f"Category '{category}' is already added")
                return

        self.categoriesListWidget.addItem(category)
        self.manualCategoryComboBox.setCurrentIndex(0)  # Reset to "Select..."
        self.update_status(f"Category '{category}' added")

    def remove_category(self):
        """Remove selected category"""
        current_item = self.categoriesListWidget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a category to remove")
            return

        row = self.categoriesListWidget.row(current_item)
        category_text = current_item.text()

        reply = QMessageBox.question(self, "Confirm Delete", 
                                     f"Remove category '{category_text}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.categoriesListWidget.takeItem(row)
            self.update_status(f"Category '{category_text}' removed")

    def edit_category(self, item=None):
        """Edit a category"""
        if item is None:
            item = self.categoriesListWidget.currentItem()
        if not item:
            QMessageBox.warning(self, "Warning", "Please select a category to edit")
            return

        old_text = item.text()
        new_text, ok = QInputDialog.getText(self, "Edit Category", 
                                            "Category name:", 
                                            text=old_text)
        if ok and new_text.strip():
            item.setText(new_text.strip())
            self.update_status(f"Category updated: {old_text} -> {new_text}")

    def refresh_categories(self):
        """Refresh categories from loaded templates"""
        self.extract_categories_from_templates()
        # Update combo box
        categories_list = ["Select..."] + sorted(list(self.all_categories))
        self.manualCategoryComboBox.clear()
        self.manualCategoryComboBox.addItems(categories_list)
        self.update_status("Categories refreshed")

    def extract_categories_from_templates(self):
        """Extract all unique categories from loaded templates"""
        self.all_categories = set()
        
        for source, data in self.loaded_templates.items():
            try:
                templates = JSONValidator.extract_templates(data)
                for template in templates:
                    if 'categories' in template and isinstance(template['categories'], list):
                        self.all_categories.update(template['categories'])
            except:
                pass

    def on_category_selected(self, choice: str):
        """Handle category selection from combo box"""
        # Auto-select could be implemented here if needed
        pass

    def add_env_var(self):
        """Add an environment variable"""
        name = self.manualEnvNameLineEdit.text().strip()
        value = self.manualEnvValueLineEdit.text().strip()

        if not name:
            QMessageBox.warning(self, "Validation Error", "Environment variable name is required")
            return

        # Check for duplicates
        for i in range(self.envListWidget.count()):
            existing = self.envListWidget.item(i).text()
            existing_name = existing.split('=')[0] if '=' in existing else existing
            if existing_name == name:
                QMessageBox.warning(self, "Duplicate Variable", 
                                  f"Environment variable '{name}' already exists")
                return

        display_text = f"{name}={value}" if value else name
        self.envListWidget.addItem(display_text)
        self.manualEnvNameLineEdit.clear()
        self.manualEnvValueLineEdit.clear()
        self.update_status(f"Environment variable '{display_text}' added")

    def remove_env_var(self):
        """Remove selected environment variable"""
        current_item = self.envListWidget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select an environment variable to remove")
            return

        row = self.envListWidget.row(current_item)
        env_text = current_item.text()

        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Remove environment variable '{env_text}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.envListWidget.takeItem(row)
            self.update_status(f"Environment variable '{env_text}' removed")

    def edit_env_var(self, item=None):
        """Edit an environment variable"""
        if item is None:
            item = self.envListWidget.currentItem()
        if not item:
            QMessageBox.warning(self, "Warning", "Please select an environment variable to edit")
            return

        old_text = item.text()
        # Parse existing
        parts = old_text.split('=', 1)
        old_name = parts[0] if parts else ""
        old_value = parts[1] if len(parts) > 1 else ""

        # Simple dialog for editing
        new_name, ok = QInputDialog.getText(self, "Edit Environment Variable", 
                                           "Variable name:", text=old_name)
        if not ok or not new_name.strip():
            return

        new_value, ok = QInputDialog.getText(self, "Edit Environment Variable",
                                            "Variable value:", text=old_value)
        if ok:
            new_text = f"{new_name.strip()}={new_value.strip()}" if new_value.strip() else new_name.strip()
            item.setText(new_text)
            self.update_status(f"Environment variable updated")

    def add_port(self):
        """Add a port mapping"""
        label = self.manualPortLabelLineEdit.text().strip()
        port = self.manualPortNumberLineEdit.text().strip()

        if not label:
            QMessageBox.warning(self, "Validation Error", "Port label is required")
            return

        if not port:
            QMessageBox.warning(self, "Validation Error", "Port number is required")
            return

        # Check for duplicates
        for i in range(self.portsListWidget.count()):
            existing = self.portsListWidget.item(i).text()
            if existing.startswith(f"{label}: "):
                QMessageBox.warning(self, "Duplicate Port", f"Port label '{label}' already exists")
                return

        display_text = f"{label}: {port}"
        self.portsListWidget.addItem(display_text)
        self.manualPortLabelLineEdit.clear()
        self.manualPortNumberLineEdit.setText("80/tcp")
        self.update_status(f"Port '{label}: {port}' added")

    def remove_port(self):
        """Remove selected port"""
        current_item = self.portsListWidget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a port to remove")
            return

        row = self.portsListWidget.row(current_item)
        port_text = current_item.text()

        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Remove port '{port_text}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.portsListWidget.takeItem(row)
            self.update_status(f"Port '{port_text}' removed")

    def edit_port(self, item=None):
        """Edit a port"""
        if item is None:
            item = self.portsListWidget.currentItem()
        if not item:
            QMessageBox.warning(self, "Warning", "Please select a port to edit")
            return

        old_text = item.text()
        parts = old_text.split(': ', 1)
        old_label = parts[0] if parts else ""
        old_port = parts[1] if len(parts) > 1 else ""

        new_label, ok = QInputDialog.getText(self, "Edit Port", "Port label:", text=old_label)
        if not ok or not new_label.strip():
            return

        new_port, ok = QInputDialog.getText(self, "Edit Port", "Port number:", text=old_port)
        if ok and new_port.strip():
            new_text = f"{new_label.strip()}: {new_port.strip()}"
            item.setText(new_text)
            self.update_status(f"Port updated")

    def add_volume(self):
        """Add a volume mapping"""
        container_path = self.manualVolumeContainerLineEdit.text().strip()
        bind_path = self.manualVolumeBindLineEdit.text().strip()

        if not container_path:
            QMessageBox.warning(self, "Validation Error", "Container path is required")
            return

        if not bind_path:
            QMessageBox.warning(self, "Validation Error", "Bind path is required")
            return

        # Check for duplicates
        for i in range(self.volumesListWidget.count()):
            existing = self.volumesListWidget.item(i).text()
            if existing.startswith(f"{container_path} -> "):
                QMessageBox.warning(self, "Duplicate Volume", 
                                  f"Container path '{container_path}' already exists")
                return

        display_text = f"{container_path} -> {bind_path}"
        self.volumesListWidget.addItem(display_text)
        self.manualVolumeContainerLineEdit.clear()
        self.manualVolumeBindLineEdit.clear()
        self.update_status(f"Volume '{container_path} -> {bind_path}' added")

    def remove_volume(self):
        """Remove selected volume"""
        current_item = self.volumesListWidget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a volume to remove")
            return

        row = self.volumesListWidget.row(current_item)
        volume_text = current_item.text()

        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Remove volume '{volume_text}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.volumesListWidget.takeItem(row)
            self.update_status(f"Volume '{volume_text}' removed")

    def edit_volume(self, item=None):
        """Edit a volume"""
        if item is None:
            item = self.volumesListWidget.currentItem()
        if not item:
            QMessageBox.warning(self, "Warning", "Please select a volume to edit")
            return

        old_text = item.text()
        parts = old_text.split(' -> ', 1)
        old_container = parts[0] if parts else ""
        old_bind = parts[1] if len(parts) > 1 else ""

        new_container, ok = QInputDialog.getText(self, "Edit Volume", 
                                                "Container path:", text=old_container)
        if not ok or not new_container.strip():
            return

        new_bind, ok = QInputDialog.getText(self, "Edit Volume",
                                           "Bind path:", text=old_bind)
        if ok and new_bind.strip():
            new_text = f"{new_container.strip()} -> {new_bind.strip()}"
            item.setText(new_text)
            self.update_status(f"Volume updated")

    def clear_manual_form(self):
        """Clear all manual form fields"""
        # Clear basic fields
        self.manualTitleLineEdit.clear()
        self.manualDescriptionLineEdit.clear()
        self.manualImageLineEdit.clear()
        self.manualLogoLineEdit.clear()
        self.manualNoteTextEdit.clear()

        # Reset dropdowns
        self.manualPlatformComboBox.setCurrentIndex(0)  # linux
        self.manualRestartComboBox.setCurrentIndex(0)  # unless-stopped

        # Clear checkbox
        self.manualAdminOnlyCheckBox.setChecked(False)

        # Clear listboxes
        self.categoriesListWidget.clear()
        self.envListWidget.clear()
        self.portsListWidget.clear()
        self.volumesListWidget.clear()

        # Reset editing context
        self.reset_editing_context()

        self.update_status("Form cleared")

    def reset_editing_context(self):
        """Reset the editing context"""
        self.current_editing_context = None
        self.addManualTemplateButton.setText("Add Template")

    def validate_manual_template(self) -> bool:
        """Validate manual template form"""
        title = self.manualTitleLineEdit.text().strip()
        image = self.manualImageLineEdit.text().strip()

        if not title:
            QMessageBox.warning(self, "Validation Error", "Title is required")
            return False

        if not image:
            QMessageBox.warning(self, "Validation Error", "Image is required")
            return False

        return True

    def build_template_from_form(self) -> Dict:
        """Build template dictionary from form"""
        template = {}

        # Basic fields
        template['title'] = self.manualTitleLineEdit.text().strip()
        template['description'] = self.manualDescriptionLineEdit.text().strip()
        template['image'] = self.manualImageLineEdit.text().strip()

        if self.manualLogoLineEdit.text().strip():
            template['logo'] = self.manualLogoLineEdit.text().strip()

        template['platform'] = self.manualPlatformComboBox.currentText()
        template['restart_policy'] = self.manualRestartComboBox.currentText()

        # Note field
        note_text = self.manualNoteTextEdit.toPlainText().strip()
        if note_text:
            template['note'] = note_text

        # Administrator only
        if self.manualAdminOnlyCheckBox.isChecked():
            template['administrator_only'] = True

        # Categories
        categories = []
        for i in range(self.categoriesListWidget.count()):
            categories.append(self.categoriesListWidget.item(i).text())
        if categories:
            template['categories'] = categories

        # Environment variables
        env_vars = []
        for i in range(self.envListWidget.count()):
            env_text = self.envListWidget.item(i).text()
            if '=' in env_text:
                name, value = env_text.split('=', 1)
                env_vars.append({"name": name, "default": value})
            else:
                env_vars.append({"name": env_text})
        if env_vars:
            template['env'] = env_vars

        # Ports
        ports = []
        for i in range(self.portsListWidget.count()):
            port_text = self.portsListWidget.item(i).text()
            if ': ' in port_text:
                label, port = port_text.split(': ', 1)
                ports.append(f"{port}/{label}")
        if ports:
            template['ports'] = ports

        # Volumes
        volumes = []
        for i in range(self.volumesListWidget.count()):
            volume_text = self.volumesListWidget.item(i).text()
            if ' -> ' in volume_text:
                container, bind = volume_text.split(' -> ', 1)
                volumes.append({"container": container, "bind": bind})
        if volumes:
            template['volumes'] = volumes

        return template

    def add_manual_template(self):
        """Add a manual template"""
        if not self.validate_manual_template():
            return

        template = self.build_template_from_form()

        # Add to manual templates
        self.manual_templates.append(template)

        self.update_status(f"Manual template '{template['title']}' added successfully")

        # Clear form
        self.clear_manual_form()

        # Show confirmation
        QMessageBox.information(self, "Success", 
                               f"Template '{template['title']}' added successfully!\n\n"
                               f"You can now generate the final template in the Preview tab.")

    # ========== EDIT TEMPLATES TAB METHODS ==========

    def refresh_edit_templates_list(self):
        """Refresh the list of templates available for editing"""
        self.all_templates_for_editing = []
        self.editTemplatesListWidget.clear()

        # Collect all templates with their source
        for source, data in self.loaded_templates.items():
            try:
                templates = JSONValidator.extract_templates(data)
                for template in templates:
                    if isinstance(template, dict) and template.get('title'):
                        template_info = {
                            'template': template,
                            'source': source
                        }
                        self.all_templates_for_editing.append(template_info)

                        # Add to list widget
                        source_name = self.get_source_display_name(source)
                        display_text = f"{template['title']} - {template.get('image', 'N/A')} [{source_name}]"
                        self.editTemplatesListWidget.addItem(display_text)
            except:
                pass

        # Update source filter combo
        sources = ["All Sources"] + [self.get_source_display_name(s) for s in self.loaded_templates.keys()]
        self.sourceFilterComboBox.clear()
        self.sourceFilterComboBox.addItems(sources)

        self.update_status(f"Loaded {len(self.all_templates_for_editing)} templates for editing")

    def get_source_display_name(self, source: str) -> str:
        """Get a friendly display name for a source"""
        if source.startswith("BASE_TEMPLATE:"):
            return "Base Template"
        elif os.path.exists(source):
            return os.path.basename(source)
        else:
            # Shorten long URLs
            if len(source) > 50:
                return source[:47] + "..."
            return source

    def filter_edit_templates(self, text: str = ""):
        """Filter templates by search text"""
        search_text = self.editFilterLineEdit.text().lower()

        for i in range(self.editTemplatesListWidget.count()):
            item = self.editTemplatesListWidget.item(i)
            if search_text in item.text().lower():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def filter_by_source(self, source_name: str):
        """Filter templates by source"""
        if source_name == "All Sources":
            # Show all
            for i in range(self.editTemplatesListWidget.count()):
                self.editTemplatesListWidget.item(i).setHidden(False)
        else:
            # Filter by source
            for i in range(self.editTemplatesListWidget.count()):
                item = self.editTemplatesListWidget.item(i)
                if f"[{source_name}]" in item.text():
                    item.setHidden(False)
                else:
                    item.setHidden(True)

    def edit_selected_template(self, item=None):
        """Edit the selected template"""
        if item is None:
            current_item = self.editTemplatesListWidget.currentItem()
        else:
            current_item = item

        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a template to edit")
            return

        row = self.editTemplatesListWidget.row(current_item)
        if row < 0 or row >= len(self.all_templates_for_editing):
            return

        template_info = self.all_templates_for_editing[row]
        self.open_template_edit_window(template_info['template'], template_info)

    def clone_selected_template(self):
        """Clone the selected template"""
        current_item = self.editTemplatesListWidget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a template to clone")
            return

        row = self.editTemplatesListWidget.row(current_item)
        if row < 0 or row >= len(self.all_templates_for_editing):
            return

        template = self.all_templates_for_editing[row]['template'].copy()
        template['title'] = f"{template['title']} (Copy)"

        # Add to manual templates
        self.manual_templates.append(template)

        QMessageBox.information(self, "Success", 
                               f"Template '{template['title']}' cloned successfully!")

    def view_template_json(self):
        """View the JSON of the selected template"""
        current_item = self.editTemplatesListWidget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a template to view")
            return

        row = self.editTemplatesListWidget.row(current_item)
        if row < 0 or row >= len(self.all_templates_for_editing):
            return

        template = self.all_templates_for_editing[row]['template']

        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Template JSON")
        dialog.resize(600, 400)

        layout = QVBoxLayout(dialog)
        text_edit = QTextEdit(dialog)
        text_edit.setPlainText(json.dumps(template, indent=2))
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)

        close_btn = QPushButton("Close", dialog)
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.exec()

    def open_template_edit_window(self, template: Dict, template_info: Dict):
        """Open a window to edit the template"""
        # For simplicity, populate the manual entry form
        self.populate_manual_form_with_template(template)
        
        # Store editing context
        self.current_editing_context = template_info

        # Switch to manual entry tab
        self.tabWidget.setCurrentIndex(1)

        QMessageBox.information(self, "Edit Mode", 
                               "Template loaded into Manual Entry tab.\n\n"
                               "Make your changes and click 'Add Template' to save as a new template.")

    def populate_manual_form_with_template(self, template: Dict):
        """Populate the manual entry form with template data"""
        # Clear first
        self.clear_manual_form()

        # Basic fields
        if 'title' in template:
            self.manualTitleLineEdit.setText(template['title'])
        if 'description' in template:
            self.manualDescriptionLineEdit.setText(template['description'])
        if 'image' in template:
            self.manualImageLineEdit.setText(template['image'])
        if 'logo' in template:
            self.manualLogoLineEdit.setText(template['logo'])
        if 'note' in template:
            self.manualNoteTextEdit.setPlainText(template['note'])

        # Platform and restart
        if 'platform' in template:
            index = self.manualPlatformComboBox.findText(template['platform'])
            if index >= 0:
                self.manualPlatformComboBox.setCurrentIndex(index)

        if 'restart_policy' in template:
            index = self.manualRestartComboBox.findText(template['restart_policy'])
            if index >= 0:
                self.manualRestartComboBox.setCurrentIndex(index)

        # Admin only
        if template.get('administrator_only', False):
            self.manualAdminOnlyCheckBox.setChecked(True)

        # Categories
        if 'categories' in template and isinstance(template['categories'], list):
            for category in template['categories']:
                self.categoriesListWidget.addItem(category)

        # Environment variables
        if 'env' in template and isinstance(template['env'], list):
            for env_var in template['env']:
                if isinstance(env_var, dict):
                    name = env_var.get('name', '')
                    default = env_var.get('default', '')
                    display_text = f"{name}={default}" if default else name
                    self.envListWidget.addItem(display_text)

        # Ports
        if 'ports' in template and isinstance(template['ports'], list):
            for port in template['ports']:
                # Port format varies, handle both "80/tcp" and more complex formats
                self.portsListWidget.addItem(str(port))

        # Volumes
        if 'volumes' in template and isinstance(template['volumes'], list):
            for volume in template['volumes']:
                if isinstance(volume, dict):
                    container = volume.get('container', '')
                    bind = volume.get('bind', '')
                    if container and bind:
                        self.volumesListWidget.addItem(f"{container} -> {bind}")

    # ========== PREVIEW AND SAVE TAB METHODS ==========

    def generate_final_template(self):
        """Generate the final combined template"""
        self.generate_worker = GenerateTemplateWorker(
            self.loaded_templates, self.manual_templates, self
        )
        self.generate_worker.status.connect(self.update_status)
        self.generate_worker.finished.connect(self.on_template_generated)
        self.generate_worker.start()

    def on_template_generated(self, final_template: dict, original_count: int, final_count: int):
        """Handle template generated"""
        self.final_template = final_template

        # Update preview
        self.previewTextEdit.setPlainText(json.dumps(self.final_template, indent=2))

        # Update summary with deduplication info
        self.update_summary_with_dedup_info(original_count, final_count)

    def update_summary_with_dedup_info(self, original_count: int, final_count: int):
        """Update summary with deduplication information"""
        current_text = self.summaryTextEdit.toPlainText()

        dedup_info = f"\n--- Processing Complete ---\n"
        dedup_info += f"Original templates: {original_count}\n"
        dedup_info += f"Final templates: {final_count}\n"
        dedup_info += f"Duplicates removed: {original_count - final_count}\n"

        self.summaryTextEdit.setPlainText(current_text + dedup_info)

    def browse_save_location(self):
        """Browse for save location"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Template File",
            "templates.json",
            "JSON files (*.json);;All files (*.*)"
        )

        if file_path:
            self.savePathLineEdit.setText(file_path)

    def save_template(self):
        """Save the final template to file"""
        if not self.final_template.get('templates'):
            QMessageBox.warning(self, "Warning", 
                               "No template generated yet. Please generate a template first.")
            return

        save_path = self.savePathLineEdit.text().strip()
        if not save_path:
            QMessageBox.warning(self, "Warning", "Please specify a save location")
            return

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

            # Save the file
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(self.final_template, f, indent=2, ensure_ascii=False)

            self.saveStatusLabel.setText(f"✓ Template saved successfully to: {save_path}")
            QMessageBox.information(
                self,
                "Success",
                f"Template saved successfully!\n\n"
                f"Location: {save_path}\n"
                f"Templates: {len(self.final_template['templates'])}"
            )
        except Exception as e:
            error_msg = f"Error saving template: {str(e)}"
            self.saveStatusLabel.setText(f"✗ {error_msg}")
            QMessageBox.critical(self, "Error", error_msg)

    # ========== TEMPLATE PROCESSING METHODS ==========

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

    # ========== UTILITY METHODS ==========

    def update_status(self, message: str):
        """Update status label"""
        self.statusLabel.setText(message)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
