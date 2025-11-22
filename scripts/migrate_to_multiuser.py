#!/usr/bin/env python3
"""Migrate single-user ProcOrg data to multi-user structure.

This script migrates from:
    data/processes.json
    data/logs/
To:
    data/users/<uid>/processes.json
    data/users/<uid>/logs/
"""

import json
import os
import shutil
import sys
from pathlib import Path


def main():
    """Run the migration."""
    print("=" * 60)
    print("ProcOrg Multi-User Migration Script")
    print("=" * 60)
    print()

    # Get current working directory
    base_dir = Path.cwd()
    old_processes_file = base_dir / "data" / "processes.json"
    old_logs_dir = base_dir / "data" / "logs"
    new_users_dir = base_dir / "data" / "users"

    # Check if already migrated
    if new_users_dir.exists() and not old_processes_file.exists():
        print("✓ Already migrated to multi-user structure")
        return 0

    # Check if old structure exists
    if not old_processes_file.exists():
        print("! No old data structure found")
        print("  This appears to be a fresh installation")
        return 0

    # Get current user UID
    current_uid = os.getuid()

    print(f"Current UID: {current_uid}")
    print(f"Old processes file: {old_processes_file}")
    print(f"Old logs directory: {old_logs_dir}")
    print()

    # Create backup
    backup_dir = base_dir / "data_backup_single_user"
    if backup_dir.exists():
        print(f"! Backup directory already exists: {backup_dir}")
        response = input("  Overwrite backup? [y/N]: ")
        if response.lower() != 'y':
            print("  Aborting migration")
            return 1
        shutil.rmtree(backup_dir)

    print(f"Creating backup: {backup_dir}")
    shutil.copytree(base_dir / "data", backup_dir)
    print("✓ Backup created")
    print()

    # Create new structure
    new_user_dir = new_users_dir / str(current_uid)
    new_user_logs_dir = new_user_dir / "logs"

    print(f"Creating new directory structure:")
    print(f"  {new_user_dir}")
    new_user_dir.mkdir(parents=True, exist_ok=True)
    print(f"  {new_user_logs_dir}")
    new_user_logs_dir.mkdir(parents=True, exist_ok=True)
    print("✓ Directories created")
    print()

    # Migrate processes.json
    print("Migrating processes.json...")
    new_processes_file = new_user_dir / "processes.json"

    with open(old_processes_file, 'r') as f:
        processes = json.load(f)

    # Add owner_uid to each process
    for proc_name, proc_data in processes.items():
        if 'owner_uid' not in proc_data:
            proc_data['owner_uid'] = current_uid

    with open(new_processes_file, 'w') as f:
        json.dump(processes, f, indent=2)

    print(f"✓ Migrated {len(processes)} processes")
    print()

    # Migrate logs
    if old_logs_dir.exists():
        print("Migrating logs...")
        log_count = 0

        for process_dir in old_logs_dir.iterdir():
            if process_dir.is_dir():
                dest_dir = new_user_logs_dir / process_dir.name
                shutil.copytree(process_dir, dest_dir)
                log_count += sum(1 for _ in dest_dir.glob("*.log"))

        print(f"✓ Migrated {log_count} log files")
        print()

    # Remove old structure
    print("Removing old structure...")
    response = input("  Proceed with removing old data? [y/N]: ")
    if response.lower() == 'y':
        old_processes_file.unlink()
        if old_logs_dir.exists():
            shutil.rmtree(old_logs_dir)
        print("✓ Old structure removed")
    else:
        print("  Keeping old structure (you can remove it manually later)")

    print()
    print("=" * 60)
    print("Migration completed successfully!")
    print("=" * 60)
    print()
    print(f"Your data is now in: {new_user_dir}")
    print(f"Backup is available in: {backup_dir}")
    print()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n! Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n! Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
