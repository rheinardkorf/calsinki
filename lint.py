#!/usr/bin/env python3
"""Run all linters for the Calsinki project."""

import subprocess
import sys
from pathlib import Path
import os

def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n🔍 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} passed")
            return True
        else:
            print(f"❌ {description} failed")
            if result.stdout:
                print("STDOUT:", result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            return False
    except Exception as e:
        print(f"❌ {description} error: {e}")
        return False

def main():
    """Run all linters."""
    print("🧹 Running Calsinki Linters")
    print("=" * 50)
    
    # Change to project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    results = []
    
    # Run ruff (fastest, catches most issues)
    results.append(run_command("uv run ruff check calsinki/", "Ruff (code quality)"))
    
    # Run black formatting check
    results.append(run_command("uv run black --check calsinki/", "Black (code formatting)"))
    
    # Run isort import sorting check
    results.append(run_command("uv run isort --check calsinki/", "isort (import sorting)"))
    
    # Run mypy type checking (slowest, most strict)
    results.append(run_command("uv run mypy calsinki/", "mypy (type checking)"))
    
    # Summary
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 All linters passed! ({passed}/{total})")
        return 0
    else:
        print(f"⚠️  Some linters failed ({passed}/{total})")
        return 1

if __name__ == "__main__":
    sys.exit(main())
