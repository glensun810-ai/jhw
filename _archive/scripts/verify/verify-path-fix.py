#!/usr/bin/env python3
"""
Path Reference Fix Verification Script
"""
import json
import os

print("=" * 70)
print("PATH REFERENCE FIX VERIFICATION")
print("=" * 70)
print()

# 1. Check if logger.js and storage.js exist in utils/
print("1. Checking utils/ directory:")
utils_files = {
    'utils/logger.js': False,
    'utils/storage.js': False,
    'utils/local-storage.js': False
}

for file_path in utils_files.keys():
    if os.path.exists(file_path):
        utils_files[file_path] = True
        print(f"   ✅ {file_path}")
    else:
        print(f"   ❌ {file_path} MISSING")

print()

# 2. Check pages that use these utilities
print("2. Checking page references:")

pages_to_check = [
    ('pages/report/dashboard/index.js', ['../../utils/logger', '../../utils/storage']),
    ('pages/data-manager/data-manager.js', ['../../utils/local-storage.js']),
    ('pages/public-history/public-history.js', ['../../utils/local-storage.js'])
]

all_ok = True
for page_file, required_imports in pages_to_check:
    if os.path.exists(page_file):
        with open(page_file, 'r') as f:
            content = f.read()
        
        print(f"   📄 {page_file}:")
        for import_path in required_imports:
            if import_path in content:
                print(f"      ✅ Uses {import_path}")
            else:
                print(f"      ⚠️  Missing {import_path}")
                all_ok = False
    else:
        print(f"   ❌ {page_file} NOT FOUND")
        all_ok = False

print()

# 3. Check app.json registration
print("3. Checking page registration in app.json:")
with open('app.json', 'r') as f:
    app_config = json.load(f)

problem_pages = [
    'pages/config-manager/config-manager',
    'pages/permission-manager/permission-manager',
    'pages/data-manager/data-manager',
    'pages/user-guide/user-guide',
    'pages/personal-history/personal-history',
    'pages/report/dashboard/index'
]

for page in problem_pages:
    if page in app_config['pages']:
        print(f"   ✅ {page}")
    else:
        print(f"   ❌ {page} NOT REGISTERED")
        all_ok = False

print()

# 4. Check page JSON configs
print("4. Checking page JSON configurations:")
for page in problem_pages[:-1]:  # Exclude dashboard
    json_file = f'{page}.json'
    if os.path.exists(json_file):
        with open(json_file, 'r') as f:
            try:
                config = json.load(f)
                title = config.get('navigationBarTitleText', 'MISSING')
                print(f"   ✅ {page} (Title: {title})")
            except:
                print(f"   ❌ {page} JSON parse error")
                all_ok = False
    else:
        print(f"   ❌ {page}.json NOT FOUND")
        all_ok = False

print()
print("=" * 70)
if all_ok and all(utils_files.values()):
    print("✅ ALL CHECKS PASSED - Fix complete!")
    print()
    print("Next steps:")
    print("1. Close WeChat Developer Tools completely")
    print("2. Re-import the project (File → Import Project)")
    print("3. Clear all cache (Tools → Clear Cache → Clear All)")
    print("4. Recompile (Ctrl/Cmd + B)")
    print("5. Test all navigation buttons")
else:
    print("❌ SOME CHECKS FAILED - Review needed")
print("=" * 70)
