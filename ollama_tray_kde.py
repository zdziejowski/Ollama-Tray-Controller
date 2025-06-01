#!/usr/bin/env python3

"""
Ollama Tray Controller

A lightweight system tray application for KDE Plasma to manage the Ollama service.
Provides a convenient way to monitor status, start and stop the Ollama service
directly from the system tray with sudo authentication.

Author: Wojciech Zdziejowski
License: MIT
Version: 1.0.2
Date: 2025-06-01

Copyright (c) 2023 Wojciech Zdziejowski

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import sys
import subprocess
import os
import signal
from PyQt5.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QAction,
                           QDialog, QVBoxLayout, QLabel, QHBoxLayout,
                           QPushButton, QMessageBox, QWidget, QFrame, QToolButton,
                           QListWidget, QListWidgetItem, QScrollArea, QSizePolicy)
from PyQt5.QtGui import QIcon, QPainter, QColor, QPen, QBrush, QPainterPath, QPixmap, QCursor, QFontMetrics
from PyQt5.QtCore import QTimer, Qt, QSize, QRectF, pyqtSignal, QPoint, QEvent, QMimeData

# Suppress Wayland warnings
os.environ['QT_LOGGING_RULES'] = 'qt.qpa.wayland=false'

class ModelItem(QWidget):
    """
    Custom widget for displaying a model in the list.
    """
    def __init__(self, name, size, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)

        name_label = QLabel(name)
        name_label.setStyleSheet("font-weight: bold; background: transparent;")

        # Truncate long names if necessary
        metrics = QFontMetrics(name_label.font())
        if metrics.width(name) > 200:
            name_label.setToolTip(name)
            name_label.setText(metrics.elidedText(name, Qt.ElideMiddle, 200))

        size_label = QLabel(size)
        size_label.setStyleSheet("background: transparent;")
        size_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout.addWidget(name_label, 3)
        layout.addWidget(size_label, 1)

        # Store full name for copying
        self.model_name = name

        # Make background transparent
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

class CustomTooltip(QWidget):
    """
    Custom tooltip-like widget that appears when clicking on the tray icon.
    Provides status information and control buttons.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        # Use a dialog with system decorations but still look nice
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Ollama Tray")

        # Make the widget semi-transparent with a nice background
        self.setStyleSheet("""
            QWidget {
                background-color: palette(window);
            }
            QPushButton {
                padding: 6px 12px;
                background-color: palette(button);
                border: 1px solid palette(dark);
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: palette(light);
            }
            QLabel {
                color: palette(text);
                padding: 2px;
                border: none;
            }
            QToolButton {
                border: none;
                padding: 2px;
            }
            QToolButton:hover {
                background-color: rgba(255, 0, 0, 80);
                border-radius: 2px;
            }
            QListWidget {
                border: 1px solid palette(mid);
                border-radius: 3px;
                background-color: transparent;
            }
            QListWidget::item {
                padding: 2px;
                background-color: transparent;
            }
            QListWidget::item:selected {
                background-color: palette(highlight);
                color: palette(highlighted-text);
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: palette(mid);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            #statusLabel, #iconLabel, #titleLabel, #modelsLabel {
                border: none;
                background: transparent;
            }
        """)

        # Main layout with increased padding
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Top bar with title
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)

        # Icon on the left
        self.icon_label = QLabel()
        self.icon_label.setObjectName("iconLabel")
        self.icon_label.setFixedSize(32, 32)
        top_layout.addWidget(self.icon_label)

        # Title
        title_label = QLabel("Ollama Tray Controller")
        title_label.setObjectName("titleLabel")
        font = title_label.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 1)
        title_label.setFont(font)
        top_layout.addWidget(title_label)

        top_layout.addStretch(1)

        layout.addLayout(top_layout)

        # Separator line
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.HLine)
        separator1.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator1)

        # Status with indicator
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(10)

        # Status indicator (colored circle)
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(20, 20)
        status_layout.addWidget(self.status_indicator)

        # Status text
        self.status_label = QLabel("Status: Checking...")
        self.status_label.setObjectName("statusLabel")
        font = self.status_label.font()
        font.setPointSize(font.pointSize() + 1)
        self.status_label.setFont(font)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch(1)

        layout.addLayout(status_layout)

        # Control buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(5, 5, 5, 5)

        self.toggle_button = QPushButton("Toggle Ollama")
        self.toggle_button.setFixedWidth(150)
        button_layout.addWidget(self.toggle_button, 1, Qt.AlignCenter)

        # Add buton to exit app
        self.exit_button = QPushButton("Close App")
        self.exit_button.setFixedWidth(150)
        self.exit_button.clicked.connect(QApplication.quit)
        button_layout.addWidget(self.exit_button, 0, Qt.AlignRight)

        layout.addLayout(button_layout)

        # Separator line
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator2)

        # Models section
        models_header = QLabel("Available Models (double-click to copy):")
        models_header.setObjectName("modelsLabel")
        font = models_header.font()
        font.setBold(True)
        models_header.setFont(font)
        layout.addWidget(models_header)

        # Models list (with adaptive height)
        self.models_list = QListWidget()
        self.models_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.models_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.models_list.setSizeAdjustPolicy(QListWidget.AdjustToContents)
        self.models_list.setResizeMode(QListWidget.Adjust)
        self.models_list.setSelectionMode(QListWidget.NoSelection)
        self.models_list.setFrameStyle(QFrame.NoFrame)
        self.models_list.setAutoFillBackground(False)
        self.models_list.setAttribute(Qt.WA_TranslucentBackground, True)

        # Override max height policy
        self.models_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.models_list.itemDoubleClicked.connect(self.copy_model_name)
        layout.addWidget(self.models_list)

        # Set size
        self.setMinimumWidth(400)

        # Flag to track if we need to resize
        self.need_resize = False

    def update_status(self, status, is_running):
        """Update the status display and buttons"""
        self.status_label.setText(f"Status: {status}")

        # Update toggle button text based on status
        if is_running:
            self.toggle_button.setText("Stop Ollama")
        else:
            self.toggle_button.setText("Start Ollama")

        # Update icon (without status indicator - it's shown separately)
        pixmap = QPixmap("src/ollama.svg").scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.icon_label.setPixmap(pixmap)

        # Update status indicator (colored circle)
        indicator_pixmap = QPixmap(20, 20)
        indicator_pixmap.fill(Qt.transparent)
        painter = QPainter(indicator_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor(0, 180, 0) if is_running else QColor(160, 160, 160)
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(Qt.black, 1))
        painter.drawEllipse(4, 4, 12, 12)  # center
        painter.end()

        self.status_indicator.setPixmap(indicator_pixmap)

        # Update models list if Ollama is running
        if is_running:
            self.refresh_models()

    def refresh_models(self):
        """Get available Ollama models and display them"""
        self.models_list.clear()

        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                # Parse the output
                lines = result.stdout.strip().split("\n")
                if len(lines) <= 1:  # No models or just header
                    self.models_list.addItem("No models found")
                    return

                # Skip the header line and sort models alphabetically
                models = []
                for line in lines[1:]:
                    parts = line.split()
                    if len(parts) >= 3:
                        name = parts[0]
                        size = parts[2] + " " + parts[3]  # Size column
                        models.append((name, size))

                # Sort alphabetically
                models.sort(key=lambda x: x[0].lower())

                # Add to list
                for name, size in models:
                    item = QListWidgetItem()
                    item.setSizeHint(QSize(0, 30))

                    model_widget = ModelItem(name, size)

                    self.models_list.addItem(item)
                    self.models_list.setItemWidget(item, model_widget)

                # Adjust the height of the list widget to fit content
                total_items = self.models_list.count()
                item_height = 30  # Assuming each item is 30 pixels high

                # Calculate the new height, but limit to maximum 7 items
                max_visible_items = min(total_items, 7)
                new_height = max_visible_items * item_height + 5  # 5px for padding

                self.models_list.setFixedHeight(new_height)

                # Mark for resizing the entire window
                self.need_resize = True
                QTimer.singleShot(50, self.adjust_window_size)

            else:
                self.models_list.addItem("Error getting models: " + result.stderr)

        except Exception as e:
            self.models_list.addItem(f"Error: {str(e)}")

    def adjust_window_size(self):
        """Adjust window size to fit content after models are loaded"""
        if self.need_resize:
            self.adjustSize()
            self.need_resize = False

    def copy_model_name(self, item):
        """Copy model name to clipboard on double-click"""
        model_widget = self.models_list.itemWidget(item)
        if hasattr(model_widget, 'model_name'):
            clipboard = QApplication.clipboard()
            clipboard.setText(model_widget.model_name)

            # Flash the item to indicate it was copied
            original_bg = item.background()
            item.setBackground(QBrush(QColor(100, 200, 100)))
            QTimer.singleShot(300, lambda: item.setBackground(original_bg))

    def showEvent(self, event):
        """When window is shown"""
        super().showEvent(event)
        # Adjust size on show
        QTimer.singleShot(100, self.adjust_window_size)

class OllamaTray(QSystemTrayIcon):
    """
    Main class for the Ollama system tray application.
    Inherits from QSystemTrayIcon to create an icon in the system tray.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = False  # Stores the current state of the Ollama service
        self.app_name = "Ollama Tray Controller"

        # Create the custom tooltip widget
        self.tooltip_widget = CustomTooltip()
        self.tooltip_widget.toggle_button.clicked.connect(self.toggle_ollama)

        # Create context menu (for right click)
        self.menu = QMenu()
        self.menu.setStyleSheet("QMenu { padding: 5px; }")

        # Add app name at the top of the menu
        app_name_action = QAction(self.app_name)
        font = app_name_action.font()
        font.setBold(True)
        app_name_action.setFont(font)
        app_name_action.setEnabled(False)  # Make it non-clickable
        self.menu.addAction(app_name_action)

        self.menu.addSeparator()

        # Status item
        self.status_action = QAction("Status: Checking...")
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)

        # Toggle action
        self.toggle_action = QAction("Toggle Ollama")
        self.toggle_action.triggered.connect(self.toggle_ollama)
        self.menu.addAction(self.toggle_action)

        self.menu.addSeparator()

        # Turn off Ollama service action
        turn_off_ollama_action = QAction("Turn off Ollama service")
        turn_off_ollama_action.triggered.connect(lambda: self.stop_ollama_service())
        self.menu.addAction(turn_off_ollama_action)

        self.menu.addSeparator()

        # Exit application action
        exit_action = QAction("Exit Ollama Tray Controller")
        exit_action.triggered.connect(QApplication.quit)
        self.menu.addAction(exit_action)

        self.setContextMenu(self.menu)

        # Set icon from SVG file
        self.update_icon()

        # Set the tooltip text with status circle
        self.update_tooltip()

        # Connect the activated signal to handle clicks
        self.activated.connect(self.on_activated)

        # Make the icon visible
        self.setVisible(True)

        # Check initial status and set timer for regular updates
        self.check_status()  # First status check
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_status)
        self.timer.start(600000)  # Refresh every 10 minutes (600000ms)

    def stop_ollama_service(self):
        """Stop Ollama service directly from the menu"""
        if self.is_running:
            self.toggle_ollama(force_stop=True)

    def update_tooltip(self):
        """Update the tooltip with status indicator"""
        # Simple text tooltip (rich tooltips aren't well supported in system tray)
        self.setToolTip(f"{self.app_name}\nStatus: {'Running' if self.is_running else 'Stopped'}")

    def update_icon(self):
        """Update the tray icon with status indicator"""
        if os.path.exists("src/ollama.svg"):
            # Create icon with status indicator
            pixmap = QPixmap("src/ollama.svg").scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            # Add status indicator - LARGER SIZE
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            color = QColor(0, 180, 0) if self.is_running else QColor(160, 160, 160)
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(Qt.black, 1))

            # Draw larger circle in bottom-right corner
            indicator_size = 60
            painter.drawEllipse(
                int(pixmap.width() - indicator_size - 5),
                int(pixmap.height() - indicator_size - 5),
                indicator_size,
                indicator_size
            )
            painter.end()

            self.setIcon(QIcon(pixmap))
        else:
            # Fallback to system icon if SVG not found
            self.setIcon(QIcon.fromTheme("computer"))
            print(f"Warning: SVG icon not found at src/ollama.svg")

    def on_activated(self, reason):
        """
        Handle tray icon activation (clicks)
        """
        if reason == QSystemTrayIcon.Trigger:  # Left click
            # Position the window in a more suitable location
            cursor_pos = QCursor.pos()
            # Center the window near the cursor
            self.tooltip_widget.move(cursor_pos.x() - self.tooltip_widget.width() // 2,
                                    cursor_pos.y() - 20)
            self.tooltip_widget.show()
        # Right-click will show the context menu automatically

    def check_status(self):
        """
        Checks the current status of the Ollama service via systemctl.
        Updates the icon and status information.
        """
        try:
            # Run systemctl command to check status
            result = subprocess.run(
                ["systemctl", "is-active", "ollama"],
                capture_output=True,
                text=True
            )

            # Analyze the result and update the interface
            if result.stdout.strip() == "active":
                # Ollama is running
                status_text = "Running"
                self.is_running = True
            else:
                # Ollama is stopped
                status_text = "Stopped"
                self.is_running = False

            # Update icon and tooltip widget
            self.update_icon()
            self.update_tooltip()
            self.tooltip_widget.update_status(status_text, self.is_running)

            # Update menu
            self.status_action.setText(f"Status: {status_text}")
            self.toggle_action.setText("Stop Ollama" if self.is_running else "Start Ollama")

        except Exception as e:
            # Handle errors during status check
            error_text = f"Error - {str(e)}"
            self.tooltip_widget.update_status(error_text, False)
            self.status_action.setText(f"Status: {error_text}")

    def toggle_ollama(self, force_stop=False):
        """
        Toggles the Ollama service state (start/stop).
        Uses pkexec for system authentication dialog.
        """
        # Determine action based on current state
        action = "stop" if self.is_running else "start"

        # If force_stop is True, always stop regardless of current state
        if force_stop:
            action = "stop"

        # Hide the tooltip widget
        self.tooltip_widget.hide()

        # Skip confirmation for force_stop
        if not force_stop:
            # Confirmation dialog before performing the action
            reply = QMessageBox.question(
                None,
                "Confirmation",
                f"Do you want to {action} Ollama? This requires sudo privileges.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No  # Default is "No" for safety
            )

            if reply != QMessageBox.Yes:
                return

        try:
            # Use pkexec for system authentication - this will trigger KDE's polkit auth dialog
            process = subprocess.Popen(
                ["pkexec", "systemctl", action, "ollama"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()

            # Check if the command succeeded
            if process.returncode != 0:
                # Display error message
                QMessageBox.critical(
                    None,
                    "Error",
                    f"Error executing command: {stderr.decode()}"
                )
            else:
                # Command executed successfully, check status after a short delay
                QTimer.singleShot(1000, self.check_status)
        except Exception as e:
            # Handle other exceptions
            QMessageBox.critical(
                None,
                "Error",
                f"Exception: {str(e)}"
            )

# Handle CTRL+C in terminal
def signal_handler(sig, frame):
    QApplication.quit()

if __name__ == "__main__":
    # Register signal handler for clean exit with CTRL+C
    signal.signal(signal.SIGINT, signal_handler)

    # Application entry point
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Prevents application from closing when windows are closed

    # Create and run the main application object
    tray = OllamaTray()

    # Allow handling CTRL+C from terminal
    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)  # Let the interpreter run each 500 ms

    sys.exit(app.exec_())  # Start the main application loop
