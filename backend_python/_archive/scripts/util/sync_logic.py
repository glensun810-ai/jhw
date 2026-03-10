import os
import ast
import json


def audit_and_map():
    print("🔍 正在扫描系统全目录逻辑模块...")
    inventory = []
    # 扫描根目录及所有子目录
    for root, dirs, files in os.walk("."):
        if 'venv' in root or '__pycache__' in root or '.git' in root:
            continue
        for file in files:
            if file.endswith(".py") and file != "sync_logic.py":
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                        tree = ast.parse(content)
                        # 提取函数名和类名
                        funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
                        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
                        if funcs or classes:
                            inventory.append({"file": path, "logic": funcs + classes})
                except Exception as e:
                    continue

    print(f"✅ 审计完成，共发现 {len(inventory)} 个潜在逻辑模块。")
    with open("internal_function_map.json", "w") as f:
        json.dump(inventory, f, indent=4)
    print("📁 功能地图已保存至 internal_function_map.json")


if __name__ == "__main__":
    audit_and_map()