#!/usr/bin/env python3
"""
Script to migrate all commands to use ctx.obj.formatter instead of creating
UniversalOutputFormatter instances.
"""

import re
from pathlib import Path

# Files to migrate
FILES_TO_MIGRATE = [
    # Cluster commands
    "vantage_cli/commands/cluster/list.py",
    "vantage_cli/commands/cluster/get.py",
    "vantage_cli/commands/cluster/delete.py",
    "vantage_cli/commands/cluster/create.py",
    # Job commands
    "vantage_cli/commands/job/script/list.py",
    "vantage_cli/commands/job/script/get.py",
    "vantage_cli/commands/job/script/create.py",
    "vantage_cli/commands/job/script/update.py",
    "vantage_cli/commands/job/script/delete.py",
    "vantage_cli/commands/job/template/list.py",
    "vantage_cli/commands/job/template/get.py",
    "vantage_cli/commands/job/template/create.py",
    "vantage_cli/commands/job/template/update.py",
    "vantage_cli/commands/job/template/delete.py",
    "vantage_cli/commands/job/submission/list.py",
    "vantage_cli/commands/job/submission/get.py",
    "vantage_cli/commands/job/submission/create.py",
    "vantage_cli/commands/job/submission/update.py",
    "vantage_cli/commands/job/submission/delete.py",
    # License server commands
    "vantage_cli/commands/license/server/list.py",
    "vantage_cli/commands/license/server/get.py",
    "vantage_cli/commands/license/server/create.py",
    "vantage_cli/commands/license/server/update.py",
    "vantage_cli/commands/license/server/delete.py",
    # License feature commands
    "vantage_cli/commands/license/feature/list.py",
    "vantage_cli/commands/license/feature/get.py",
    "vantage_cli/commands/license/feature/create.py",
    "vantage_cli/commands/license/feature/update.py",
    "vantage_cli/commands/license/feature/delete.py",
    # License product commands
    "vantage_cli/commands/license/product/list.py",
    "vantage_cli/commands/license/product/get.py",
    "vantage_cli/commands/license/product/create.py",
    "vantage_cli/commands/license/product/update.py",
    "vantage_cli/commands/license/product/delete.py",
    # License configuration commands
    "vantage_cli/commands/license/configuration/list.py",
    "vantage_cli/commands/license/configuration/get.py",
    "vantage_cli/commands/license/configuration/create.py",
    "vantage_cli/commands/license/configuration/update.py",
    "vantage_cli/commands/license/configuration/delete.py",
    # License deployment commands
    "vantage_cli/commands/license/deployment/list.py",
    "vantage_cli/commands/license/deployment/get.py",
    "vantage_cli/commands/license/deployment/create.py",
    "vantage_cli/commands/license/deployment/update.py",
    "vantage_cli/commands/license/deployment/delete.py",
    # Profile commands
    "vantage_cli/commands/profile/crud.py",
    # Support ticket commands
    "vantage_cli/commands/support_ticket/list.py",
    "vantage_cli/commands/support_ticket/get.py",
    "vantage_cli/commands/support_ticket/create.py",
    "vantage_cli/commands/support_ticket/update.py",
    "vantage_cli/commands/support_ticket/delete.py",
    # Notebook commands
    "vantage_cli/commands/notebook/list.py",
    "vantage_cli/commands/notebook/get.py",
    "vantage_cli/commands/notebook/create.py",
    # Network commands
    "vantage_cli/commands/network/list.py",
    "vantage_cli/commands/network/delete.py",
    "vantage_cli/commands/network/update.py",
    # Team commands
    "vantage_cli/commands/team/list.py",
    "vantage_cli/commands/team/get.py",
    "vantage_cli/commands/team/create.py",
    "vantage_cli/commands/team/update.py",
    "vantage_cli/commands/team/delete.py",
    # App commands
    "vantage_cli/commands/app/list.py",
]


def migrate_file(file_path: Path) -> tuple[bool, str]:
    """Migrate a single file to use ctx.obj.formatter."""
    if not file_path.exists():
        return False, f"File not found: {file_path}"
    
    content = file_path.read_text()
    original_content = content
    
    # Pattern 1: formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)
    pattern1 = r'\s*formatter = UniversalOutputFormatter\(console=ctx\.obj\.console, json_output=ctx\.obj\.json_output\)'
    content = re.sub(pattern1, '', content)
    
    # Pattern 2: formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=json_output)
    pattern2 = r'\s*formatter = UniversalOutputFormatter\(console=ctx\.obj\.console, json_output=json_output\)'
    content = re.sub(pattern2, '', content)
    
    # Replace formatter. with ctx.obj.formatter.
    content = re.sub(r'\bformatter\.', 'ctx.obj.formatter.', content)
    
    # Remove UniversalOutputFormatter import if it's no longer needed
    # Check if UniversalOutputFormatter is still referenced
    if 'UniversalOutputFormatter' not in content or content.count('UniversalOutputFormatter') == content.count('from vantage_cli.render import UniversalOutputFormatter'):
        content = re.sub(
            r'from vantage_cli\.render import UniversalOutputFormatter\n',
            '',
            content
        )
    
    if content != original_content:
        file_path.write_text(content)
        return True, f"✅ Migrated: {file_path}"
    else:
        return False, f"⏭️  No changes needed: {file_path}"


def main():
    """Main migration function."""
    print("=" * 80)
    print("Migrating commands to use ctx.obj.formatter")
    print("=" * 80)
    
    repo_root = Path(__file__).parent.parent
    migrated = []
    skipped = []
    errors = []
    
    for file_rel_path in FILES_TO_MIGRATE:
        file_path = repo_root / file_rel_path
        success, message = migrate_file(file_path)
        print(message)
        
        if "Migrated" in message:
            migrated.append(file_rel_path)
        elif "No changes" in message:
            skipped.append(file_rel_path)
        else:
            errors.append(message)
    
    print("\n" + "=" * 80)
    print(f"✅ Migrated: {len(migrated)} files")
    print(f"⏭️  Skipped: {len(skipped)} files")
    print(f"❌ Errors: {len(errors)} files")
    print("=" * 80)
    
    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"  {error}")


if __name__ == "__main__":
    main()
