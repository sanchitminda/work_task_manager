# Workday Widget-Friendly Desktop Task Manager

A lightweight, **always-on-top** Windows desktop widget designed to help manage split-shift workdays (4 hours Team A, 4 hours Team B, plus personal projects). Built with PyQt6 and optimized for friendly UX patterns.

## Features

### 🎯 Core Functionality
- **Three-Tab System**: Separate workspaces for Team A, Team B, and SAP Project
- **Task Management**: Add, complete, and delete tasks from each context
- **Active Work Log**: Quick note-taking for current tasks
- **Session Timer**: Visual time tracking with HH:MM:SS format
- **Auto-Save**: Persistent storage of all tasks and notes in JSON format

### 🎨 Optimized UI
- **Dark Theme (Catppuccin)**: High-contrast, low-distraction color palette
- **Always-On-Top**: Widget stays visible above other windows
- **Frameless Design**: Minimal visual noise, modern appearance
- **Draggable Window**: Click and drag anywhere to reposition
- **Visual Context Switching**: Active tab highlighted with accent colors
- **Clear Actions**: Distinct buttons for common operations (✓ Complete, ✕ Delete, 💾 Save)

### 💾 Data Persistence
- Tasks automatically saved to `~/.workday_widget/tasks.json`
- Session notes backed up on export
- Full data restored on application startup

### ⏱️ Time Management
- Built-in session timer for tracking work blocks
- Reset timer button for new task cycles
- Visual feedback on elapsed time

## Installation

### Windows
```bash
# Clone/download the repository
cd mytool

# Run setup script
setup.bat

# Or manually install
pip install -r requirements.txt
```

### macOS/Linux
```bash
cd mytool
chmod +x setup.sh
./setup.sh
# Or manually: pip install -r requirements.txt
```

## Usage

### Launch the Widget
```bash
python workday_widget.py
```

### Basic Workflow

1. **Select a Tab**: Click "Team A", "Team B", or "SAP Project"
2. **Add a Task**: Type in the input field and press Enter or click "+"
3. **Select a Task**: Click any task to view/edit its notes
4. **Take Notes**: Use the "Active Work Log" text area for rapid note-taking
5. **Mark Complete**: Click "✓ Complete" when done
6. **Delete Task**: Click "✕ Delete" to remove a task
7. **Save**: Click "💾 Save All" or let it auto-save on close

### Advanced Features

- **Export Log**: Click "📝 Export Log" to save current tab's notes to a timestamped file
- **Reset Timer**: Click "🔄 Reset Timer" when starting a new work block
- **Drag Widget**: Click and drag the title bar to reposition

## File Structure

```
mytool/
├── workday_widget.py      # Main application (single-file implementation)
├── requirements.txt       # Python dependencies
├── setup.bat             # Windows setup script
├── setup.sh              # Unix setup script
└── README.md             # This file
```

## Data Storage

- **Location**: `~/.workday_widget/` (hidden folder in your home directory)
- **Tasks**: `tasks.json` - Contains all tasks and session notes
- **Session Logs**: `<team>_<timestamp>.txt` - Exported work logs

## Code Structure

The application is organized into logical sections:

- **Configuration**: Colors (Catppuccin palette), file paths, constants
- **Data Models**: `Task` and `WorkLog` dataclasses for type safety
- **Data Persistence**: `DataManager` class for JSON serialization
- **UI Components**: `WorkLogTab` for reusable tab widget, `WorkdayWidget` main window
- **Application**: `main()` entry point and QApplication setup

## Keyboard Shortcuts

- **Enter** in task field: Add new task
- **Click task**: Select and load its notes
- **Q/Alt+F4**: Close application (auto-saves)

## Customization

### Change Colors
Edit `CATPPUCCIN_COLORS` dictionary in `workday_widget.py` to use your preferred palette.

### Adjust Window Size
Modify `WINDOW_WIDTH` and `WINDOW_HEIGHT` constants.

### Change Data Location
Edit `APP_DATA_DIR` to store data elsewhere.

### Timer Interval
Adjust `TIMER_INTERVAL` constant (in milliseconds).

## Requirements

- Python 3.10+
- PyQt6 6.7.1+
- Windows 10/11 (or cross-platform with minor adjustments)

## Troubleshooting

### Widget appears behind other windows
- The "Always On Top" flag is enabled; if another "always-on-top" window is active, use Alt+Tab

### Data not saving
- Check `~/.workday_widget/` folder exists and is writable
- Ensure app closes properly (click window close button)

### Qt platform plugin not found
```bash
pip install --upgrade PyQt6
```

## Future Enhancement Ideas

- 🔔 Notifications for task deadlines
- 📊 Session analytics and productivity charts
- 🔗 Integration with calendar or task management APIs
- 🎵 Focus music/ambient sound controls
- 📱 Mobile companion app for task sync
- 🌙 Additional theme options (light mode, custom colors)

## License

Free to use and modify for personal or professional use.

## Support

For issues or questions, review the troubleshooting section or check the application console output for error messages.

---

Built with ❤️ for friendly productivity

