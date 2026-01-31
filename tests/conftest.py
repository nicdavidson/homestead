import sys
import pytest
import tempfile
from pathlib import Path

# Add common to path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "common"))

@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a temporary directory for test databases."""
    return tmp_path

@pytest.fixture
def db_path(tmp_dir):
    return str(tmp_dir / "test.db")

@pytest.fixture
def skills_dir(tmp_dir):
    d = tmp_dir / "skills"
    d.mkdir()
    return d
