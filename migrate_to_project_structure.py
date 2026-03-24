#!/usr/bin/env python3
"""
Migration script to convert old archive_results structure to project-based structure.

Old structure:
  archive_results/
  └── {runtime}--{instance_type}--{model_name}/
      └── test_*.json

New structure:
  archive_results/
  ├── default/
  │   └── {runtime}--{instance_type}--{model_name}/
  │       └── test_*.json
  └── [other_projects]/
      └── ...
"""

import os
import shutil
from pathlib import Path
from typing import List, Tuple


def detect_old_structure(results_dir: Path) -> List[Path]:
    """
    Detect old-style test result directories at the root level.
    Old structure has test_*.json files directly in subdirectories.
    """
    old_dirs = []

    if not results_dir.exists():
        return old_dirs

    for item in results_dir.iterdir():
        if not item.is_dir() or item.name.startswith('.'):
            continue

        # Check if this directory contains test_*.json files (old structure)
        test_files = list(item.glob("test_*.json"))
        if test_files:
            old_dirs.append(item)

    return old_dirs


def migrate_to_default_project(results_dir: Path, backup: bool = True) -> Tuple[bool, str]:
    """
    Migrate old structure to new project-based structure.

    Returns:
        Tuple of (success: bool, message: str)
    """
    old_dirs = detect_old_structure(results_dir)

    if not old_dirs:
        return True, "No old structure detected. Already using project-based structure."

    # Create backup if requested
    if backup:
        backup_path = results_dir.parent / f"archive_results_backup_{os.environ.get('USER', 'unknown')}"
        if results_dir.exists():
            print(f"Creating backup at {backup_path}...")
            if backup_path.exists():
                shutil.rmtree(backup_path)
            shutil.copytree(results_dir, backup_path)
            print(f"Backup created successfully.")

    # Create default project directory
    default_project_dir = results_dir / "default"
    default_project_dir.mkdir(parents=True, exist_ok=True)

    # Move old directories to default project
    for old_dir in old_dirs:
        target_path = default_project_dir / old_dir.name
        if target_path.exists():
            print(f"Warning: {target_path} already exists. Removing it...")
            shutil.rmtree(target_path)

        print(f"Moving {old_dir.name} to default project...")
        shutil.move(str(old_dir), str(target_path))

    print(f"\nMigration completed successfully!")
    print(f"  - Moved {len(old_dirs)} directories to default project")
    print(f"  - New structure: {results_dir}/default/")

    return True, f"Successfully migrated {len(old_dirs)} directories to default project"


def show_structure(results_dir: Path, level: int = 0) -> None:
    """Pretty print the directory structure."""
    if not results_dir.exists():
        print(f"  Directory does not exist: {results_dir}")
        return

    indent = "  " * level
    print(f"{indent}{results_dir.name}/")

    try:
        items = sorted(results_dir.iterdir())
        dirs = [item for item in items if item.is_dir() and not item.name.startswith('.')]

        for i, item in enumerate(dirs[:5]):  # Show first 5 items
            is_last = i == len(dirs) - 1
            if level < 2:  # Only show 2 levels deep
                show_structure(item, level + 1)
            else:
                print(f"  {'  ' * (level + 1)}{item.name}/")

        if len(dirs) > 5:
            print(f"  {'  ' * (level + 1)}... and {len(dirs) - 5} more items")
    except PermissionError:
        print(f"{indent}  (Permission denied)")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate archive_results from old structure to project-based structure",
        epilog="""
Examples:
  %(prog)s                              # Migrate with backup
  %(prog)s --no-backup                  # Migrate without backup
  %(prog)s --show-structure             # Show current structure
  %(prog)s -d /custom/path              # Migrate custom directory
        """
    )
    parser.add_argument(
        "-d", "--directory",
        type=str,
        default="archive_results",
        help="Results directory to migrate (default: archive_results)"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip backup creation"
    )
    parser.add_argument(
        "--show-structure",
        action="store_true",
        help="Show current directory structure and exit"
    )

    args = parser.parse_args()
    results_dir = Path(args.directory).resolve()

    print("=" * 60)
    print("Archive Results Migration Tool")
    print("=" * 60)

    if args.show_structure:
        print("\nCurrent directory structure:")
        show_structure(results_dir)
        return

    # Check if directory exists
    if not results_dir.exists():
        print(f"Directory does not exist: {results_dir}")
        print("Creating directory...")
        results_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nResults directory: {results_dir}")

    # Check old structure
    old_dirs = detect_old_structure(results_dir)
    if not old_dirs:
        print("\n✓ Already using project-based structure (no migration needed)")
        print("\nCurrent structure:")
        show_structure(results_dir)
        return

    print(f"\n⚠ Found {len(old_dirs)} old-style directories:")
    for old_dir in old_dirs:
        print(f"  - {old_dir.name}")

    # Confirm migration
    print("\n" + "=" * 60)
    print("Migration Plan:")
    print("  - Move all old directories to: archive_results/default/")
    print("  - Create backup: Yes" if not args.no_backup else "  - Create backup: No")
    print("=" * 60)

    response = input("\nProceed with migration? (y/n): ").strip().lower()
    if response != 'y':
        print("Migration cancelled.")
        return

    # Perform migration
    success, message = migrate_to_default_project(
        results_dir,
        backup=not args.no_backup
    )

    if success:
        print(f"\n✓ {message}")
        print("\nNew structure:")
        show_structure(results_dir)
    else:
        print(f"\n✗ Migration failed: {message}")
        return 1

    print("\n" + "=" * 60)
    print("Migration completed successfully!")
    print("You can now use the web UI with multiple projects.")
    print("=" * 60)


if __name__ == "__main__":
    main()
