#!/usr/bin/env python3
"""
Hearth Installation Verification

Checks that everything is ready to run before starting the entity.
"""

import os
import sys
from pathlib import Path

# Add hearth to path
sys.path.insert(0, str(Path(__file__).parent))

def check(name, test_func):
    """Run a check and print result."""
    try:
        result = test_func()
        if result:
            print(f"✅ {name}")
            return True
        else:
            print(f"❌ {name}")
            return False
    except Exception as e:
        print(f"❌ {name}: {e}")
        return False


def main():
    print("=" * 70)
    print("🔥 Hearth Installation Verification")
    print("=" * 70)
    print()

    checks_passed = 0
    checks_total = 0

    # 1. Python version
    checks_total += 1
    if check("Python 3.10+", lambda: sys.version_info >= (3, 10)):
        checks_passed += 1
        print(f"   Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

    # 2. Virtual environment
    checks_total += 1
    if check("Virtual environment active", lambda: hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)):
        checks_passed += 1
        print(f"   {sys.prefix}")

    # 3. Required packages
    checks_total += 1
    def check_packages():
        required = ['fastapi', 'uvicorn', 'anthropic', 'openai', 'google.generativeai', 'click', 'rich']
        missing = []
        for pkg in required:
            try:
                __import__(pkg.replace('-', '_'))
            except ImportError:
                missing.append(pkg)
        if missing:
            print(f"   Missing: {', '.join(missing)}")
            return False
        return True

    if check("Required packages installed", check_packages):
        checks_passed += 1

    # 4. Entity home directory
    checks_total += 1
    entity_home = os.environ.get('ENTITY_HOME')
    if check("ENTITY_HOME set", lambda: entity_home is not None):
        checks_passed += 1
        print(f"   {entity_home}")

        # Check if directory exists
        checks_total += 1
        if check("Entity home exists", lambda: Path(entity_home).exists()):
            checks_passed += 1

            # Check required subdirectories
            checks_total += 1
            def check_dirs():
                required_dirs = ['data', 'reflections', 'skills', 'projects', 'pending']
                for d in required_dirs:
                    path = Path(entity_home) / d
                    if not path.exists():
                        print(f"   Missing directory: {d}")
                        path.mkdir(parents=True, exist_ok=True)
                        print(f"   Created: {d}")
                return True

            if check("Required directories", check_dirs):
                checks_passed += 1

    # 5. API Keys
    print()
    print("API Keys (Optional - at least one required):")

    api_keys_found = 0

    # XAI
    if os.environ.get('XAI_API_KEY'):
        print("  ✅ XAI_API_KEY set")
        api_keys_found += 1
    else:
        print("  ⚠️  XAI_API_KEY not set")

    # Anthropic
    if os.environ.get('ANTHROPIC_API_KEY'):
        print("  ✅ ANTHROPIC_API_KEY set")
        api_keys_found += 1
    else:
        print("  ⚠️  ANTHROPIC_API_KEY not set")

    # OpenAI
    if os.environ.get('OPENAI_API_KEY'):
        print("  ✅ OPENAI_API_KEY set")
        api_keys_found += 1
    else:
        print("  ⚠️  OPENAI_API_KEY not set")

    # Google
    if os.environ.get('GOOGLE_API_KEY'):
        print("  ✅ GOOGLE_API_KEY set")
        api_keys_found += 1
    else:
        print("  ⚠️  GOOGLE_API_KEY not set")

    checks_total += 1
    if api_keys_found > 0:
        print(f"  ✅ At least one API key configured ({api_keys_found} total)")
        checks_passed += 1
    else:
        print("  ❌ No API keys found - entity cannot function")

    # 6. Core imports
    checks_total += 1
    def check_core_imports():
        try:
            from core import get_config, get_state, get_task_manager
            from agents import Gateway
            from web.app import create_app
            return True
        except Exception as e:
            print(f"   Error: {e}")
            return False

    if check("Core modules import", check_core_imports):
        checks_passed += 1

    # 7. Database initialization
    checks_total += 1
    def check_database():
        try:
            from core import get_state
            state = get_state()
            # Try a simple operation
            stats = state.get_task_stats()
            return True
        except Exception as e:
            print(f"   Error: {e}")
            return False

    if check("Database initializes", check_database):
        checks_passed += 1

    # Summary
    print()
    print("=" * 70)
    print(f"Results: {checks_passed}/{checks_total} checks passed")
    print("=" * 70)
    print()

    if checks_passed == checks_total:
        print("✅ ALL CHECKS PASSED - Ready to start!")
        print()
        print("Start the entity:")
        print("  hearth serve")
        print()
        print("Or install as service:")
        print("  sudo /opt/hearth/install-service.sh")
        print("  sudo systemctl start hearth")
        print()
        return 0
    else:
        print("⚠️  SOME CHECKS FAILED")
        print()
        print("Common fixes:")
        print()
        print("1. Activate virtual environment:")
        print("   source /opt/hearth/venv/bin/activate")
        print()
        print("2. Install dependencies:")
        print("   pip install -r /opt/hearth/requirements.txt")
        print()
        print("3. Set environment variables:")
        print("   export ENTITY_HOME=/home/nic/.hearth")
        print("   export ENTITY_USER=nic")
        print("   export XAI_API_KEY=your_key_here")
        print()
        print("4. Create entity home:")
        print("   mkdir -p $ENTITY_HOME/{data,reflections,skills,projects,pending}")
        print()
        return 1


if __name__ == '__main__':
    sys.exit(main())
