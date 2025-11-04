#!/usr/bin/env python3
"""
JSON Template Combiner - PyQt6 Version
Entry point for the PyQt6 application
"""

import sys
from PyQt6.QtWidgets import QApplication
from main_window_pyqt6 import MainWindow


def main():
    """Main entry point"""
    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName("JSON Template Combiner")
    app.setOrganizationName("JSON Template Combiner")
    app.setApplicationVersion("2.0 PyQt6")

    # Create and show main window
    window = MainWindow()
    window.show()

    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
