"""Entry point for Sheriff of Nottingham."""
import sys
import os

# Ensure project root is on the Python path regardless of CWD
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.app import App


def main():
    app = App()
    app.run()


if __name__ == "__main__":
    main()
