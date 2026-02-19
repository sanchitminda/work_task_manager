import sys
import json
import os
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict, field

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QListWidget, QListWidgetItem, QPushButton, QLineEdit, QTextEdit,
    QLabel, QFrame, QScrollArea, QDialog, QSpinBox, QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt, QPoint, QTimer, QSize, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QColor, QIcon, QPixmap, QPainter, QBrush, QDesktopServices


# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

CATPPUCCIN_COLORS = {
    "rosewater": "#f5e0dc",
    "flamingo": "#f2cdcd",
    "pink": "#f5c2e7",
    "mauve": "#cba6f7",
    "red": "#f38ba8",
    "maroon": "#eba0ac",
    "peach": "#fab387",
    "yellow": "#f9e2af",
    "green": "#a6e3a1",
    "teal": "#94e2d5",
    "sky": "#89dceb",
    "sapphire": "#74c7ec",
    "blue": "#89b4fa",
    "lavender": "#b4befe",
    "text": "#cdd6f4",
    "subtext1": "#bac2de",
    "surface2": "#585b70",
    "surface1": "#45475a",
    "surface0": "#313244",
    "base": "#1e1e2e",
    "mantle": "#181825",
    "crust": "#11111b",
}

APP_DATA_DIR = Path.home() / ".workday_widget"
TASKS_FILE = APP_DATA_DIR / "tasks.json"
CONFIG_FILE = APP_DATA_DIR / "config.json"
LOGS_FILE = APP_DATA_DIR / "logs.json"

APP_DATA_DIR.mkdir(exist_ok=True)

WINDOW_WIDTH = 520
WINDOW_HEIGHT = 550
WINDOW_MIN_WIDTH = 200
WINDOW_MIN_HEIGHT = 500
TIMER_INTERVAL = 1000  # 1 second

# Presentation mode dimensions
PRESENTATION_MODE_WIDTH = 300
PRESENTATION_MODE_HEIGHT = 80


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Task:
    id: str
    title: str
    created_at: str
    completed: bool = False
    notes: str = ""

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> 'Task':
        return Task(**data)


@dataclass
class WorkLog:
    teams: Dict[str, List[Task]] = field(default_factory=dict)
    session_notes: Dict[str, str] = field(default_factory=dict)
    session_start: str = ""

    def to_dict(self):
        return {
            "teams": {name: [t.to_dict() for t in tasks] for name, tasks in self.teams.items()},
            "session_notes": self.session_notes,
            "session_start": self.session_start,
        }

    @staticmethod
    def from_dict(data: dict) -> 'WorkLog':
        teams = {}
        for name, task_list in data.get("teams", {}).items():
            teams[name] = [Task.from_dict(t) for t in task_list]
        
        # Migrate old format if needed
        if "team_a" in data:
            teams["Team A"] = [Task.from_dict(t) for t in data.get("team_a", [])]
        if "team_b" in data:
            teams["Team B"] = [Task.from_dict(t) for t in data.get("team_b", [])]
        if "sap_project" in data:
            teams["SAP Project"] = [Task.from_dict(t) for t in data.get("sap_project", [])]
        
        return WorkLog(
            teams=teams if teams else {"Team A": [], "Team B": [], "SAP Project": []},
            session_notes=data.get("session_notes", {}),
            session_start=data.get("session_start", ""),
        )


@dataclass
class AppConfig:
    teams: List[Dict[str, str]] = field(default_factory=list)  # [{"name": "Team A", "color": "#..."}]
    window_width: int = WINDOW_WIDTH
    window_height: int = WINDOW_HEIGHT
    window_x: int = 100
    window_y: int = 100
    notes_collapsed: bool = False
    presentation_mode: bool = False

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> 'AppConfig':
        return AppConfig(
            teams=data.get("teams", [{"name": "Team A", "color": CATPPUCCIN_COLORS["sapphire"]},
                                       {"name": "Team B", "color": CATPPUCCIN_COLORS["mauve"]},
                                       {"name": "SAP Project", "color": CATPPUCCIN_COLORS["peach"]}]),
            window_width=data.get("window_width", WINDOW_WIDTH),
            window_height=data.get("window_height", WINDOW_HEIGHT),
            window_x=data.get("window_x", 100),
            window_y=data.get("window_y", 100),
            notes_collapsed=data.get("notes_collapsed", False),
            presentation_mode=data.get("presentation_mode", False),
        )
# ============================================================================
# DATA PERSISTENCE
# ============================================================================

class DataManager:
    """Manages persistence of tasks and logs to JSON."""

    @staticmethod
    def load_worklog() -> WorkLog:
        """Load work log from disk or return empty one."""
        if TASKS_FILE.exists():
            try:
                with open(TASKS_FILE, "r") as f:
                    data = json.load(f)
                    return WorkLog.from_dict(data)
            except Exception as e:
                print(f"Error loading tasks: {e}")
        return WorkLog(session_start=datetime.now().isoformat())

    @staticmethod
    def save_worklog(worklog: WorkLog) -> None:
        """Save work log to disk."""
        try:
            with open(TASKS_FILE, "w") as f:
                json.dump(worklog.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Error saving tasks: {e}")

    @staticmethod
    def load_config() -> AppConfig:
        """Load app config from disk or return defaults."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    return AppConfig.from_dict(data)
            except Exception as e:
                print(f"Error loading config: {e}")
        return AppConfig(
            teams=[
                {"name": "Team A", "color": CATPPUCCIN_COLORS["sapphire"]},
                {"name": "Team B", "color": CATPPUCCIN_COLORS["mauve"]},
                {"name": "SAP Project", "color": CATPPUCCIN_COLORS["peach"]}
            ]
        )

    @staticmethod
    def save_config(config: AppConfig) -> None:
        """Save app config to disk."""
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    @staticmethod
    def save_session_log(filename: str, content: str) -> None:
        """Save session log with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = APP_DATA_DIR / f"{filename}_{timestamp}.txt"
        try:
            with open(log_path, "w") as f:
                f.write(content)
        except Exception as e:
            print(f"Error saving session log: {e}")


# ============================================================================
# UI COMPONENTS
# ============================================================================

class LinkAwareTextEdit(QTextEdit):
    """Custom QTextEdit that makes HTML links clickable."""
    
    def mousePressEvent(self, event):
        """Handle mouse clicks to detect and open links."""
        # Get the character at click position
        cursor = self.cursorForPosition(event.pos())
        char_format = cursor.charFormat()
        
        # Check if clicked on a link
        if char_format.isAnchor():
            link = char_format.anchorHref()
            if link:
                QDesktopServices.openUrl(QUrl(link))
                return
        
        # Otherwise, proceed with normal text editing
        super().mousePressEvent(event)


class WorkLogTab(QWidget):
    """A single tab for managing tasks and work log for a team/project."""

    notes_toggled = pyqtSignal(bool)  # Signal when notes are toggled (bool = is_visible)

    def __init__(self, tab_name: str, tab_id: str, color_hex: str, parent=None):
        super().__init__(parent)
        self.tab_name = tab_name
        self.tab_id = tab_id
        self.color_hex = color_hex
        self.tasks: List[Task] = []
        self.current_task: Optional[Task] = None
        self.notes_visible = True
        self.setup_ui()

    def setup_ui(self):
        """Initialize UI for this tab."""
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(10, 8, 10, 8)

        # Task input section
        input_layout = QHBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText(f"Add task...")
        self.task_input.setMinimumHeight(28)
        self.task_input.setStyleSheet(self._get_input_style())
        self.task_input.returnPressed.connect(self.add_task)

        add_btn = QPushButton("+")
        add_btn.setMaximumWidth(36)
        add_btn.setMinimumHeight(28)
        add_btn.setStyleSheet(self._get_button_style("add"))
        add_btn.clicked.connect(self.add_task)
        add_btn.setToolTip("Add new task (Enter)")

        input_layout.addWidget(self.task_input)
        input_layout.addWidget(add_btn)
        layout.addLayout(input_layout)

        # Task list
        list_label = QLabel("Tasks")
        list_label.setStyleSheet(f"color: {CATPPUCCIN_COLORS['lavender']}; font-weight: bold; font-size: 9pt;")
        layout.addWidget(list_label)

        self.task_list = QListWidget()
        self.task_list.setMinimumHeight(30)
        self.task_list.setStyleSheet(self._get_list_style())
        self.task_list.itemClicked.connect(self.on_task_selected)
        layout.addWidget(self.task_list, 1)  # Give it stretch factor

        # Action buttons for tasks
        task_btn_layout = QHBoxLayout()
        task_btn_layout.setSpacing(4)
        self.complete_btn = QPushButton("✓")
        self.complete_btn.setMaximumWidth(36)
        self.complete_btn.setMinimumHeight(24)
        self.complete_btn.setStyleSheet(self._get_button_style("complete"))
        self.complete_btn.clicked.connect(self.complete_task)
        self.complete_btn.setToolTip("Mark task as complete")

        self.delete_btn = QPushButton("✕")
        self.delete_btn.setMaximumWidth(36)
        self.delete_btn.setMinimumHeight(24)
        self.delete_btn.setStyleSheet(self._get_button_style("delete"))
        self.delete_btn.clicked.connect(self.delete_task)
        self.delete_btn.setToolTip("Delete task")

        self.toggle_notes_btn = QPushButton("▼")
        self.toggle_notes_btn.setMaximumWidth(36)
        self.toggle_notes_btn.setMinimumHeight(24)
        self.toggle_notes_btn.setStyleSheet(self._get_button_style("toggle"))
        self.toggle_notes_btn.clicked.connect(self.toggle_notes)
        self.toggle_notes_btn.setToolTip("Toggle notes panel")

        task_btn_layout.addWidget(self.complete_btn)
        task_btn_layout.addWidget(self.delete_btn)
        task_btn_layout.addStretch()
        task_btn_layout.addWidget(self.toggle_notes_btn)
        layout.addLayout(task_btn_layout)

        # Notes container - will be toggled on/off
        self.notes_container = QWidget()
        notes_layout = QVBoxLayout()
        notes_layout.setSpacing(8)
        notes_layout.setContentsMargins(0, 0, 0, 0)

        self.log_label = QLabel("Notes")
        self.log_label.setStyleSheet(f"color: {CATPPUCCIN_COLORS['lavender']}; font-weight: bold; font-size: 9pt;")
        notes_layout.addWidget(self.log_label)

        self.work_log = LinkAwareTextEdit()
        self.work_log.setPlaceholderText("Quick notes for current task...")
        self.work_log.setMinimumHeight(70)
        self.work_log.setMaximumHeight(110)
        self.work_log.setStyleSheet(self._get_text_edit_style())
        # Enable HTML and convert links when text changes
        self.work_log.setAcceptRichText(True)
        self.work_log.textChanged.connect(self._convert_urls_to_links)
        # Store reference for link clicking
        self.work_log.parent_tab = self
        notes_layout.addWidget(self.work_log)

        self.notes_container.setLayout(notes_layout)
        layout.addWidget(self.notes_container)

        self.setLayout(layout)

    def _on_link_clicked(self, url: QUrl):
        """Handle link clicks in notes."""
        QDesktopServices.openUrl(url)

    def _convert_urls_to_links(self):
        """Convert URLs in text to clickable HTML links."""
        text = self.work_log.toPlainText()
        # Check if text already has HTML tags (to avoid double-converting)
        if "<a href=" in self.work_log.toHtml():
            return
        
        # Regex to find URLs
        url_pattern = r'(https?://[^\s]+|ftp://[^\s]+)'
        # Replace URLs with HTML links
        html_text = re.sub(
            url_pattern,
            r'<a href="\1" style="color: #89dceb; text-decoration: underline;">\1</a>',
            text
        )
        
        # Only update if changes were made
        if html_text != text:
            # Store current cursor position
            cursor = self.work_log.textCursor()
            cursor_pos = cursor.position()
            
            # Temporarily disconnect to avoid recursive calls
            self.work_log.textChanged.disconnect(self._convert_urls_to_links)
            self.work_log.setHtml(html_text)
            
            # Restore cursor position
            cursor = self.work_log.textCursor()
            cursor.setPosition(min(cursor_pos, len(self.work_log.toPlainText())))
            self.work_log.setTextCursor(cursor)
            
            # Reconnect signal
            self.work_log.textChanged.connect(self._convert_urls_to_links)

    def _get_input_style(self) -> str:
        return f"""
            QLineEdit {{
                background-color: {CATPPUCCIN_COLORS['surface0']};
                color: {CATPPUCCIN_COLORS['text']};
                border: 2px solid {CATPPUCCIN_COLORS['surface1']};
                border-radius: 4px;
                padding: 6px;
                font-size: 10pt;
            }}
            QLineEdit:focus {{
                border: 2px solid {self.color_hex};
            }}
        """

    def _get_list_style(self) -> str:
        return f"""
            QListWidget {{
                background-color: {CATPPUCCIN_COLORS['surface0']};
                color: {CATPPUCCIN_COLORS['text']};
                border: 1px solid {CATPPUCCIN_COLORS['surface1']};
                border-radius: 3px;
            }}
            QListWidget::item {{
                padding: 2px;
                border-bottom: 1px solid {CATPPUCCIN_COLORS['surface1']};
            }}
            QListWidget::item:selected {{
                background-color: {self.color_hex}40;
                border-left: 3px solid {self.color_hex};
            }}
            QListWidget::item:hover {{
                background-color: {CATPPUCCIN_COLORS['surface1']};
            }}
        """

    def _get_text_edit_style(self) -> str:
        return f"""
            QTextEdit {{
                background-color: {CATPPUCCIN_COLORS['surface0']};
                color: {CATPPUCCIN_COLORS['text']};
                border: 1px solid {CATPPUCCIN_COLORS['surface1']};
                border-radius: 3px;
                padding: 6px;
                font-size: 9pt;
            }}
            QTextEdit:focus {{
                border: 2px solid {self.color_hex};
            }}
        """

    def _get_button_style(self, button_type: str) -> str:
        if button_type == "add":
            color = CATPPUCCIN_COLORS["green"]
            hover = CATPPUCCIN_COLORS["teal"]
        elif button_type == "complete":
            color = CATPPUCCIN_COLORS["green"]
            hover = CATPPUCCIN_COLORS["teal"]
        elif button_type == "delete":
            color = CATPPUCCIN_COLORS["red"]
            hover = CATPPUCCIN_COLORS["maroon"]
        elif button_type == "toggle":
            color = CATPPUCCIN_COLORS["sapphire"]
            hover = CATPPUCCIN_COLORS["blue"]
        else:
            color = self.color_hex
            hover = color

        return f"""
            QPushButton {{
                background-color: {color};
                color: {CATPPUCCIN_COLORS['base']};
                border: none;
                border-radius: 3px;
                padding: 4px;
                font-weight: bold;
                font-size: 9pt;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:pressed {{
                background-color: {CATPPUCCIN_COLORS['surface1']};
            }}
        """

    def add_task(self):
        """Add a new task from input field."""
        text = self.task_input.text().strip()
        if not text:
            return

        task = Task(
            id=f"{self.tab_id}_{datetime.now().timestamp()}",
            title=text,
            created_at=datetime.now().isoformat(),
        )
        self.tasks.append(task)
        self.refresh_list()
        self.task_input.clear()

    def refresh_list(self):
        """Refresh the task list widget."""
        self.task_list.clear()
        for task in self.tasks:
            strike = "~~" if task.completed else ""
            item_text = f"{strike}{task.title}{strike}"
            item = QListWidgetItem(item_text)
            if task.completed:
                item.setForeground(QColor(CATPPUCCIN_COLORS['subtext1']))
            self.task_list.addItem(item)

    def on_task_selected(self, item: QListWidgetItem):
        """Handle task selection."""
        idx = self.task_list.row(item)
        if 0 <= idx < len(self.tasks):
            self.current_task = self.tasks[idx]
            self.work_log.setText(self.current_task.notes)

    def complete_task(self):
        """Mark current task as complete."""
        if self.current_task:
            self.current_task.completed = True
            self.current_task.notes = self.work_log.toPlainText()
            self.refresh_list()

    def delete_task(self):
        """Delete current task."""
        if self.current_task and self.current_task in self.tasks:
            self.tasks.remove(self.current_task)
            self.current_task = None
            self.work_log.clear()
            self.refresh_list()

    def toggle_notes(self):
        """Toggle notes visibility."""
        self.notes_visible = not self.notes_visible
        self.notes_container.setVisible(self.notes_visible)
        self.toggle_notes_btn.setText("▼" if self.notes_visible else "▶")
        # Emit signal to parent widget to adjust window size
        self.notes_toggled.emit(self.notes_visible)

    def update_notes(self):
        """Update notes for current task."""
        if self.current_task:
            self.current_task.notes = self.work_log.toPlainText()

    def get_data(self) -> List[Task]:
        """Return current tasks."""
        self.update_notes()
        return self.tasks

    def set_data(self, tasks: List[Task]):
        """Load tasks into this tab."""
        self.tasks = tasks
        self.refresh_list()


class SettingsDialog(QDialog):
    """Dialog for managing teams and app settings."""

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.setup_ui()
        self.setWindowTitle("Settings")
        self.setGeometry(200, 200, 500, 400)

    def setup_ui(self):
        """Initialize settings UI."""
        layout = QVBoxLayout()

        # Team management
        teams_label = QLabel("Teams & Projects")
        teams_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(teams_label)

        self.teams_list = QListWidget()
        self.teams_list.setMinimumHeight(200)
        self.refresh_teams_list()
        layout.addWidget(self.teams_list)

        # Team buttons
        team_btn_layout = QHBoxLayout()
        add_team_btn = QPushButton("+ Add Team")
        add_team_btn.clicked.connect(self.add_team)
        add_team_btn.setToolTip("Add a new team or project")
        edit_team_btn = QPushButton("✎ Edit")
        edit_team_btn.clicked.connect(self.edit_team)
        edit_team_btn.setToolTip("Edit selected team name")
        remove_team_btn = QPushButton("✕ Remove")
        remove_team_btn.clicked.connect(self.remove_team)
        remove_team_btn.setToolTip("Remove selected team")
        
        team_btn_layout.addWidget(add_team_btn)
        team_btn_layout.addWidget(edit_team_btn)
        team_btn_layout.addWidget(remove_team_btn)
        layout.addLayout(team_btn_layout)

        # Separator
        separator = QFrame()
        separator.setStyleSheet(f"border: 1px solid {CATPPUCCIN_COLORS['surface1']};")
        separator.setFixedHeight(2)
        layout.addWidget(separator)

        # Options
        options_label = QLabel("Options")
        options_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(options_label)

        self.collapse_notes_check = QCheckBox("Collapse notes by default")
        self.collapse_notes_check.setChecked(self.config.notes_collapsed)
        layout.addWidget(self.collapse_notes_check)

        layout.addStretch()

        # OK button
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setToolTip("Save settings and close")
        layout.addWidget(ok_btn)

        self.setLayout(layout)

    def refresh_teams_list(self):
        """Refresh the teams list display."""
        self.teams_list.clear()
        for team in self.config.teams:
            item = QListWidgetItem(f"● {team['name']}")
            self.teams_list.addItem(item)

    def add_team(self):
        """Add a new team."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Team")
        layout = QVBoxLayout()

        name_label = QLabel("Team Name:")
        name_input = QLineEdit()
        layout.addWidget(name_label)
        layout.addWidget(name_input)

        ok_btn = QPushButton("Add")
        ok_btn.clicked.connect(dialog.accept)
        ok_btn.setToolTip("Create new team")
        layout.addWidget(ok_btn)

        dialog.setLayout(layout)
        if dialog.exec() and name_input.text().strip():
            self.config.teams.append({
                "name": name_input.text().strip(),
                "color": CATPPUCCIN_COLORS["blue"]
            })
            self.refresh_teams_list()

    def edit_team(self):
        """Edit selected team name."""
        current = self.teams_list.currentRow()
        if current < 0:
            QMessageBox.warning(self, "Warning", "Please select a team to edit.")
            return

        team = self.config.teams[current]
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Team")
        layout = QVBoxLayout()

        name_label = QLabel("Team Name:")
        name_input = QLineEdit()
        name_input.setText(team['name'])
        layout.addWidget(name_label)
        layout.addWidget(name_input)

        ok_btn = QPushButton("Update")
        ok_btn.clicked.connect(dialog.accept)
        ok_btn.setToolTip("Save team name changes")
        layout.addWidget(ok_btn)

        dialog.setLayout(layout)
        if dialog.exec() and name_input.text().strip():
            self.config.teams[current]['name'] = name_input.text().strip()
            self.refresh_teams_list()

    def remove_team(self):
        """Remove selected team."""
        current = self.teams_list.currentRow()
        if current < 0:
            QMessageBox.warning(self, "Warning", "Please select a team to remove.")
            return

        if len(self.config.teams) <= 1:
            QMessageBox.warning(self, "Warning", "You must have at least one team.")
            return

        reply = QMessageBox.question(self, "Confirm", 
                                      f"Remove '{self.config.teams[current]['name']}'?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.config.teams.pop(current)
            self.refresh_teams_list()

    def get_config(self) -> AppConfig:
        """Return updated config."""
        self.config.notes_collapsed = self.collapse_notes_check.isChecked()
        return self.config


class WorkdayWidget(QWidget):
    """Main always-on-top desktop widget for workday management."""

    def __init__(self):
        super().__init__()
        self.worklog = DataManager.load_worklog()
        self.config = DataManager.load_config()
        self.drag_position = QPoint()
        self.elapsed_seconds = 0
        self.tabs_dict: Dict[str, WorkLogTab] = {}
        self.presentation_mode = False
        self.baseline_height = WINDOW_HEIGHT  # Track full height with notes expanded
        self.setup_window()
        self.setup_ui()
        self.setup_timer()
        self.restore_data()

    def setup_window(self):
        """Configure window properties."""
        self.setWindowTitle("Workday Widget")
        
        # Always position at top-right corner on startup
        screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()
        x = screen_rect.right() - self.config.window_width - 10
        y = screen_rect.top() + 10
        
        # Use config's saved height as baseline (full height with notes expanded)
        self.baseline_height = self.config.window_height
        self.setGeometry(x, y, self.config.window_width, self.config.window_height)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        # Frameless and always on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        # Transparency
        self.setWindowOpacity(0.98)

        # Dark background
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {CATPPUCCIN_COLORS['base']};
                color: {CATPPUCCIN_COLORS['text']};
            }}
        """)

    def setup_ui(self):
        """Initialize UI."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header with title and controls
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {CATPPUCCIN_COLORS['surface0']};
                border-bottom: 2px solid {CATPPUCCIN_COLORS['surface1']};
            }}
        """)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(12, 8, 12, 8)
        header_layout.setSpacing(8)

        title = QLabel("⏱️")
        title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))

        self.timer_label = QLabel("00:00:00")
        self.timer_label.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        self.timer_label.setStyleSheet(f"color: {CATPPUCCIN_COLORS['green']};")

        header_layout.addWidget(title)
        header_layout.addWidget(self.timer_label)
        header_layout.addStretch()

        # Header buttons
        settings_btn = QPushButton("⚙")
        settings_btn.setMaximumWidth(32)
        settings_btn.setMinimumHeight(28)
        settings_btn.setStyleSheet(self._get_header_button_style())
        settings_btn.clicked.connect(self.open_settings)
        settings_btn.setToolTip("Settings")

        present_btn = QPushButton("👁")
        present_btn.setMaximumWidth(32)
        present_btn.setMinimumHeight(28)
        present_btn.setStyleSheet(self._get_header_button_style())
        present_btn.clicked.connect(self.toggle_presentation_mode)
        present_btn.setToolTip("Presentation mode (hide details)")

        exit_btn = QPushButton("✕")
        exit_btn.setMaximumWidth(32)
        exit_btn.setMinimumHeight(28)
        exit_btn.setStyleSheet(self._get_header_button_style(is_exit=True))
        exit_btn.clicked.connect(self.exit_app)
        exit_btn.setToolTip("Exit application")

        header_layout.addWidget(settings_btn)
        header_layout.addWidget(present_btn)
        header_layout.addWidget(exit_btn)
        header.setLayout(header_layout)
        main_layout.addWidget(header)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(self._get_tab_style())

        # Create tabs from config
        for team_config in self.config.teams:
            team_name = team_config['name']
            team_color = team_config['color']
            tab_id = team_name.lower().replace(" ", "_")
            
            tab = WorkLogTab(team_name, tab_id, team_color)
            # Connect notes toggle signal to window resize
            tab.notes_toggled.connect(self.on_notes_toggled)
            self.tabs_dict[team_name] = tab
            self.tabs.addTab(tab, team_name)

        main_layout.addWidget(self.tabs)

        # Footer with action buttons
        footer = QFrame()
        footer.setStyleSheet(f"""
            QFrame {{
                background-color: {CATPPUCCIN_COLORS['surface1']};
                border-top: 1px solid {CATPPUCCIN_COLORS['surface2']};
            }}
        """)
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(12, 8, 12, 8)
        footer_layout.setSpacing(6)

        save_btn = QPushButton("💾")
        save_btn.setMaximumWidth(40)
        save_btn.clicked.connect(self.save_all)
        save_btn.setStyleSheet(self._get_footer_button_style(CATPPUCCIN_COLORS["green"]))
        save_btn.setToolTip("Save all tasks")

        export_btn = QPushButton("📝")
        export_btn.setMaximumWidth(40)
        export_btn.clicked.connect(self.export_log)
        export_btn.setStyleSheet(self._get_footer_button_style(CATPPUCCIN_COLORS["blue"]))
        export_btn.setToolTip("Export current tab's log")

        reset_btn = QPushButton("🔄")
        reset_btn.setMaximumWidth(40)
        reset_btn.clicked.connect(self.reset_timer)
        reset_btn.setStyleSheet(self._get_footer_button_style(CATPPUCCIN_COLORS["yellow"]))
        reset_btn.setToolTip("Reset timer")

        footer_layout.addWidget(save_btn)
        footer_layout.addWidget(export_btn)
        footer_layout.addWidget(reset_btn)
        footer_layout.addStretch()
        footer.setLayout(footer_layout)
        main_layout.addWidget(footer)

        self.setLayout(main_layout)

    def _get_header_button_style(self, is_exit: bool = False) -> str:
        if is_exit:
            normal_color = CATPPUCCIN_COLORS['red']
            hover_color = CATPPUCCIN_COLORS['maroon']
        else:
            normal_color = CATPPUCCIN_COLORS['surface1']
            hover_color = CATPPUCCIN_COLORS['surface2']
        return f"""
            QPushButton {{
                background-color: {normal_color};
                color: {CATPPUCCIN_COLORS['text']};
                border: none;
                border-radius: 3px;
                padding: 4px;
                font-size: 10pt;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """

    def _get_tab_style(self) -> str:
        return f"""
            QTabWidget::pane {{
                border: none;
                background-color: {CATPPUCCIN_COLORS['base']};
            }}
            QTabBar::tab {{
                background-color: {CATPPUCCIN_COLORS['surface0']};
                color: {CATPPUCCIN_COLORS['subtext1']};
                padding: 6px 12px;
                border: none;
                font-size: 9pt;
            }}
            QTabBar::tab:selected {{
                background-color: {CATPPUCCIN_COLORS['sapphire']};
                color: {CATPPUCCIN_COLORS['base']};
                font-weight: bold;
            }}
        """

    def _get_footer_button_style(self, color: str) -> str:
        return f"""
            QPushButton {{
                background-color: {color};
                color: {CATPPUCCIN_COLORS['base']};
                border: none;
                border-radius: 3px;
                padding: 6px;
                font-weight: bold;
                font-size: 9pt;
            }}
            QPushButton:hover {{
                background-color: {color}E0;
            }}
        """

    def setup_timer(self):
        """Initialize session timer."""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(TIMER_INTERVAL)
        self.elapsed_seconds = 0

    def update_timer(self):
        """Update elapsed time display."""
        self.elapsed_seconds += 1
        hours = self.elapsed_seconds // 3600
        minutes = (self.elapsed_seconds % 3600) // 60
        seconds = self.elapsed_seconds % 60
        self.timer_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        # Also update presentation view if active
        self.update_presentation_view()

    def reset_timer(self):
        """Reset the session timer."""
        self.elapsed_seconds = 0
        self.timer_label.setText("00:00:00")

    def save_all(self):
        """Save all tasks and current work logs."""
        for team_name, tab in self.tabs_dict.items():
            self.worklog.teams[team_name] = tab.get_data()
        DataManager.save_worklog(self.worklog)
        print("✓ All data saved successfully")

    def export_log(self):
        """Export current session log to file."""
        current_tab = self.tabs.currentWidget()
        if isinstance(current_tab, WorkLogTab):
            content = current_tab.work_log.toPlainText()
            tab_name = current_tab.tab_name.replace(" ", "_")
            DataManager.save_session_log(tab_name, content)
            print(f"✓ Log exported for {current_tab.tab_name}")

    def restore_data(self):
        """Restore saved tasks on startup."""
        for team_name, tab in self.tabs_dict.items():
            tasks = self.worklog.teams.get(team_name, [])
            tab.set_data(tasks)
        # Apply initial notes collapse state if configured (without triggering resize)
        if self.config.notes_collapsed:
            for tab in self.tabs_dict.values():
                # Hide notes directly without emitting signal (avoid resize on startup)
                tab.notes_visible = False
                tab.notes_container.setVisible(False)
                tab.toggle_notes_btn.setText("▶")
                # Adjust window height immediately
                self.resize(self.width(), WINDOW_HEIGHT - 85)
    
    def on_notes_toggled(self, is_visible: bool):
        """Handle notes collapse/expand to resize window."""
        if self.presentation_mode:
            return  # Don't resize in presentation mode
        
        # Use baseline height as reference for all calculations
        if is_visible:
            # Expand - use full baseline height
            new_height = self.baseline_height
        else:
            # Collapse - subtract notes height from baseline
            new_height = self.baseline_height - 85
        
        # Resize window
        self.resize(self.width(), new_height)

    def open_settings(self):
        """Open settings dialog."""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config = dialog.get_config()
            DataManager.save_config(self.config)

    def exit_app(self):
        """Save data and close the application."""
        self.close()

    def toggle_presentation_mode(self):
        """Toggle presentation mode (hide details for screen sharing)."""
        self.presentation_mode = not self.presentation_mode
        
        if self.presentation_mode:
            # Save current size
            self.normal_geom = self.geometry()
            # Switch to presentation mode - show only timer and active task
            self.setGeometry(self.normal_geom.x(), self.normal_geom.y(),
                           PRESENTATION_MODE_WIDTH, PRESENTATION_MODE_HEIGHT)
            self.tabs.hide()
            # Create minimal presentation view
            if not hasattr(self, 'presentation_widget'):
                self.presentation_widget = self._create_presentation_view()
                self.layout().addWidget(self.presentation_widget)
            self.presentation_widget.show()
        else:
            # Back to normal mode
            if hasattr(self, 'presentation_widget'):
                self.presentation_widget.hide()
            self.tabs.show()
            self.setGeometry(self.normal_geom)

    def _create_presentation_view(self) -> QWidget:
        """Create minimal presentation view."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # Timer display
        self.presentation_timer_label = QLabel(self.timer_label.text())
        self.presentation_timer_label.setFont(QFont("Courier New", 28, QFont.Weight.Bold))
        self.presentation_timer_label.setStyleSheet(f"color: {CATPPUCCIN_COLORS['green']}; text-align: center;")
        layout.addWidget(self.presentation_timer_label)

        # Current task preview
        self.presentation_task_label = QLabel("Focus Mode")
        self.presentation_task_label.setFont(QFont("Segoe UI", 10))
        current_tab = self.tabs.currentWidget()
        if current_tab and isinstance(current_tab, WorkLogTab):
            if current_tab.current_task:
                self.presentation_task_label.setText(f"📌 {current_tab.current_task.title[:30]}")
        layout.addWidget(self.presentation_task_label)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def update_presentation_view(self):
        """Update presentation view with current timer and task."""
        if hasattr(self, 'presentation_timer_label'):
            self.presentation_timer_label.setText(self.timer_label.text())
        if hasattr(self, 'presentation_task_label'):
            current_tab = self.tabs.currentWidget()
            if current_tab and isinstance(current_tab, WorkLogTab):
                if current_tab.current_task:
                    self.presentation_task_label.setText(f"📌 {current_tab.current_task.title[:30]}")
                else:
                    self.presentation_task_label.setText("Focus Mode")

    def mousePressEvent(self, event):
        """Handle mouse press for dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging."""
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)

    def closeEvent(self, event):
        """Save data and window state before closing."""
        # Stop the timer first
        self.timer.stop()
        
        self.save_all()
        # Update baseline height if notes are currently expanded
        current_tab = self.tabs.currentWidget()
        if current_tab and isinstance(current_tab, WorkLogTab) and current_tab.notes_visible:
            self.baseline_height = self.height()
        # Save window state (height with notes expanded)
        self.config.window_width = self.width()
        self.config.window_height = self.baseline_height
        self.config.presentation_mode = self.presentation_mode
        DataManager.save_config(self.config)
        event.accept()


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Launch the application."""
    app = QApplication(sys.argv)

    widget = WorkdayWidget()
    widget.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
