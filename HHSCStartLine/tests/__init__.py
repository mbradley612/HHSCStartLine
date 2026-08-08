import os
import sys

# Make the application packages (model, controllers, screenui, ...) importable
# from the tests, regardless of the current working directory.
_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
