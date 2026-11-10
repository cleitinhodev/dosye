"""PyInstaller entry script (keeps `dosye` importable as a package inside the bundle)."""
import sys

from dosye.app import main

if __name__ == "__main__":
    sys.exit(main())
