#!/usr/bin/env python3
"""
Quick installation check for Anemone.
Run with: python check_install.py
"""

import sys

def check_import(module_name, package=None):
    """Try to import a module and report success/failure."""
    try:
        if package:
            __import__(package)
            print(f"✓ {module_name} ({package})")
        else:
            __import__(module_name)
            print(f"✓ {module_name}")
        return True
    except ImportError as e:
        print(f"✗ {module_name}: {e}")
        return False

def main():
    print("🔍 Checking Anemone dependencies...\n")
    
    # Core dependencies
    deps = [
        ("flask", None),
        ("flask_socketio", None),
        ("chromadb", None),
        ("ollama", None),
        ("pocketflow", None),
        ("pydantic", None),
        ("numpy", None),
        ("eventlet", None),
    ]
    
    all_ok = True
    for mod, pkg in deps:
        if not check_import(mod, pkg):
            all_ok = False
    
    print("\n📦 Checking project modules...")
    # Project modules
    project_modules = [
        ("memory", None),
        ("nodes", None),
        ("orchestration", None),
        ("utils", None),
    ]
    
    for mod, pkg in project_modules:
        try:
            __import__(mod)
            print(f"✓ {mod}.py")
        except ImportError as e:
            print(f"✗ {mod}.py: {e}")
            all_ok = False
    
    # Check Python version
    print(f"\n🐍 Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    if sys.version_info >= (3, 13):
        print("✓ Python version ≥ 3.13")
    else:
        print("⚠ Python version < 3.13 (requires 3.13+)")
        all_ok = False
    
    if all_ok:
        print("\n✅ All checks passed! Anemone should be ready to run.")
        print("   Start the UI with: python app.py")
    else:
        print("\n❌ Some checks failed. Please install missing dependencies.")
        print("   Run: uv sync  # or pip install -e .")
        sys.exit(1)

if __name__ == "__main__":
    main()