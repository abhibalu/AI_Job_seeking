
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from lakehouse.app_sync import sync_gold_to_app

if __name__ == "__main__":
    sync_gold_to_app()
