#!/usr/bin/env python3
"""
Automated migration script: ib_insync -> ib_async
"""

import os
import re
from pathlib import Path

def migrate_file(file_path):
    """Migrate a single file from ib_insync to ib_async"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Replace imports
    content = re.sub(r'from ib_insync import', 'from ib_async import', content)
    content = re.sub(r'import ib_insync', 'import ib_async', content)
    content = re.sub(r'ib_insync\.', 'ib_async.', content)

    if content != original_content:
        # Create backup
        backup_path = file_path + '.ib_insync_backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)

        # Write migrated content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ Migrated: {file_path}")
        print(f"📁 Backup: {backup_path}")
        return True

    return False

def main():
    """Main migration function"""
    print("Starting ib_insync -> ib_async migration...")

    # Find files to migrate
    files_to_migrate = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        if 'ib_insync' in f.read():
                            files_to_migrate.append(file_path)
                except:
                    continue

    print(f"📁 Found {len(files_to_migrate)} files to migrate")

    migrated_count = 0
    for file_path in files_to_migrate:
        if migrate_file(file_path):
            migrated_count += 1

    print(f"\n🎉 Migration complete: {migrated_count} files migrated")
    print("\n📋 Next steps:")
    print("1. Run tests to verify functionality")
    print("2. Test IBKR connection")
    print("3. Test market data access")
    print("4. If issues occur, run rollback")

if __name__ == "__main__":
    main()
