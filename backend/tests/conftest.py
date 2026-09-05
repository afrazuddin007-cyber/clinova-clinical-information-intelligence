import os
import sys
import shutil
import tempfile
from pathlib import Path

# Add backend directory to sys.path for test discovery
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Configure isolated test database and test uploads folder
test_dir = tempfile.mkdtemp(prefix="clinova_pytest_")
test_db = Path(test_dir) / "test_clinova.db"
test_uploads = Path(test_dir) / "uploads"
test_uploads.mkdir(parents=True, exist_ok=True)

os.environ["DATABASE_URL"] = f"sqlite:///{test_db}"
os.environ["UPLOAD_DIR"] = str(test_uploads)

import pytest

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_env():
    yield
    try:
        shutil.rmtree(test_dir, ignore_errors=True)
    except Exception:
        pass
