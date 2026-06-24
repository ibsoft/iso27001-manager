import os
import sys


def is_bundled():
    return getattr(sys, "frozen", False)


def app_root():
    """Read-only application resources (templates, static, seed_data, translations).

    In development: project root directory.
    In bundled demo: PyInstaller temp extraction dir (sys._MEIPASS).
    """
    if is_bundled():
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_root():
    """Writable data directory (DB, logs, uploads, backups).

    In development: project root directory.
    In bundled demo: directory containing the .exe file.
    """
    if is_bundled():
        return os.path.dirname(sys.executable)
    return app_root()
