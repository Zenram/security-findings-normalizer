"""Make the repo root importable so `import src...` and `import schema...` work
under pytest regardless of the invocation directory."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
