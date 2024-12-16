import sys
from pathlib import Path

# Add app root to path
app_root = Path(__file__).parent.parent
sys.path.append(str(app_root))

# Add src directory if it exists
src_path = app_root / "src"
if src_path.exists():
    sys.path.append(str(src_path))
