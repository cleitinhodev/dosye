"""Operating-system integration (Windows + Linux). Every OS-specific call is guarded here."""
import sys

IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux") or "bsd" in sys.platform
