import os
import sys
from pathlib import Path

import PySide6
from PySide6.QtWidgets import QApplication


CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
for path in (str(CURRENT_DIR), str(PROJECT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

pyside_dir = Path(PySide6.__file__).parent
plugin_dir = pyside_dir / "plugins"
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(plugin_dir)

from login_window import LoginWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Football Motion Analysis System")
    app.setOrganizationName("FootballSystem")

    window = LoginWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
