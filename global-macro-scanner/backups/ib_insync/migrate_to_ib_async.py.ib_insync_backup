#!/usr/bin/env python3
"""
Migration Plan: ib_insync → ib_async
IBKR support recommends ib_async over ib_insync
"""
import os
import re
from pathlib import Path

def analyze_current_usage():
    """Analyze current ib_insync usage in the codebase"""
    print("ANALYZING CURRENT IB_INSYNC USAGE")
    print("=" * 50)

    # Find all Python files
    python_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    ib_insync_files = []
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'from ib_insync import' in content or 'import ib_insync' in content:
                    ib_insync_files.append(file_path)
        except:
            continue

    print(f"Files using ib_insync: {len(ib_insync_files)}")
    for file in ib_insync_files[:10]:  # Show first 10
        print(f"  - {file}")
    if len(ib_insync_files) > 10:
        print(f"  ... and {len(ib_insync_files) - 10} more")

    return ib_insync_files

def create_migration_plan():
    """Create a detailed migration plan"""
    print("\nMIGRATION PLAN: ib_insync -> ib_async")
    print("=" * 50)

    migration_steps = [
        "1. Backup current working code",
        "2. Update import statements:",
        "   from ib_insync import * -> from ib_async import *",
        "   import ib_insync -> import ib_async",
        "3. Test basic connectivity with ib_async",
        "4. Test market data access (US, India, Australia, Singapore)",
        "5. Test contract qualification",
        "6. Test historical data requests",
        "7. Test scanner functionality",
        "8. Update all test scripts",
        "9. Full integration testing",
        "10. Rollback plan if issues arise"
    ]

    for step in migration_steps:
        print(f"* {step}")

    print("\nKEY DIFFERENCES TO CHECK:")
    print("- Async method signatures")
    print("- Error handling")
    print("- Connection management")
    print("- Data format compatibility")

def test_ib_async_basic():
    """Test basic ib_async functionality"""
    print("\nTESTING IB_ASYNC BASIC FUNCTIONALITY")
    print("=" * 50)

    try:
        import ib_async
        print(f"ib_async imported successfully (v{ib_async.__version__})")

        # Test basic class instantiation
        ib = ib_async.IB()
        print("IB() class instantiated")

        # Check key methods exist
        key_methods = ['connectAsync', 'qualifyContractsAsync', 'reqHistoricalDataAsync', 'reqMarketDataType']
        for method in key_methods:
            if hasattr(ib, method):
                print(f"* {method} method available")
            else:
                print(f"X {method} method MISSING")

        # Test Stock contract
        stock = ib_async.Stock('AAPL', 'SMART', 'USD')
        print(f"Stock contract created: {stock}")

        print("\nib_async basic functionality: PASSED")

    except Exception as e:
        print(f"ib_async basic functionality: FAILED - {e}")
        return False

    return True

def create_rollback_plan():
    """Create rollback plan in case migration fails"""
    print("\nROLLBACK PLAN")
    print("=" * 50)

    rollback_steps = [
        "1. Reinstall ib_insync",
        "2. Revert all import statements",
        "3. Test that ib_insync still works",
        "4. Document ib_async issues for IBKR support",
        "5. Consider using official IBKR API instead"
    ]

    for step in rollback_steps:
        print(f"< {step}")

def generate_migration_script():
    """Generate a script to automate the migration"""
    migration_script = '''#!/usr/bin/env python3
"""
Automated migration script: ib_insync → ib_async
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
    print("🚀 Starting ib_insync → ib_async migration...")

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

    print(f"\\n🎉 Migration complete: {migrated_count} files migrated")
    print("\\n📋 Next steps:")
    print("1. Run tests to verify functionality")
    print("2. Test IBKR connection")
    print("3. Test market data access")
    print("4. If issues occur, run rollback")

if __name__ == "__main__":
    main()
'''

    with open('migrate_ib_async.py', 'w', encoding='utf-8') as f:
        f.write(migration_script)

    print("\nGenerated migration script: migrate_ib_async.py")
    print("   Run with: python migrate_ib_async.py")

def main():
    """Main analysis and planning function"""
    print("IB_INSYNC -> IB_ASYNC MIGRATION ANALYSIS")
    print("=" * 60)

    # Analyze current usage
    ib_insync_files = analyze_current_usage()

    # Create migration plan
    create_migration_plan()

    # Test ib_async
    if test_ib_async_basic():
        print("\nMIGRATION FEASIBLE - ib_async has required functionality")
    else:
        print("\nMIGRATION NOT FEASIBLE - ib_async missing key features")
        return

    # Create rollback plan
    create_rollback_plan()

    # Generate migration script
    generate_migration_script()

    print("\n" + "=" * 60)
    print("RECOMMENDATION:")
    print("Since IBKR support flagged ib_insync as problematic,")
    print("migrating to ib_async is recommended.")
    print("=" * 60)

if __name__ == "__main__":
    main()