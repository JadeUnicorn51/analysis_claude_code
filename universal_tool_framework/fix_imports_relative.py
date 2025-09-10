#!/usr/bin/env python3
"""
将导入修复为相对导入 - 更适合包结构
"""

import os
import re
from pathlib import Path

def fix_imports_to_relative(file_path: Path, project_root: Path):
    """将导入修复为相对导入"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 计算当前文件相对于utf包的位置
        relative_path = file_path.relative_to(project_root)
        
        # 确定文件在包结构中的深度
        parts = relative_path.parts
        
        if 'utf' in parts:
            utf_index = parts.index('utf')
            depth_from_utf = len(parts) - utf_index - 2  # -2 for 'utf' and filename
            
            if depth_from_utf == 0:
                # 在utf根目录下的文件 (如 utf/__init__.py)
                prefix = "."
            elif depth_from_utf == 1:
                # 在utf子目录下的文件 (如 utf/core/engine.py)
                prefix = ".."
            elif depth_from_utf == 2:
                # 在utf子子目录下的文件 (如 utf/tools/file_tools/read_tool.py)
                prefix = "..."
            else:
                prefix = "." + "." * depth_from_utf
        else:
            # 文件在utf包外面，使用绝对导入utf
            content = re.sub(
                r'from universal_tool_framework\.utf\.',
                'from utf.',
                content
            )
            
            content = re.sub(
                r'from universal_tool_framework\.utf import',
                'from utf import',
                content
            )
            
            # 如果内容有变化，写回文件
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ 修复外部文件: {file_path}")
                return True
            return False
        
        # 修复utf包内部的导入为相对导入
        content = re.sub(
            r'from universal_tool_framework\.utf\.',
            f'from {prefix}',
            content
        )
        
        # 修复根级导入
        content = re.sub(
            r'from universal_tool_framework\.utf import',
            f'from {prefix} import',
            content
        )
        
        # 如果内容有变化，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复相对导入: {file_path}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ 修复失败 {file_path}: {e}")
        return False

def main():
    """主函数"""
    print("🔧 修复为相对导入和绝对导入")
    print("=" * 50)
    
    # 获取项目根目录
    root_dir = Path(__file__).parent
    
    # 收集所有Python文件
    all_py_files = list(root_dir.glob("**/*.py"))
    
    # 排除不需要修复的文件
    exclude_patterns = [
        "__pycache__",
        ".git",
        "fix_imports",
        "test_",
        "start_",
        "main.py",
        "run_example.py"
    ]
    
    files_to_fix = []
    for file_path in all_py_files:
        should_exclude = False
        for exclude in exclude_patterns:
            if exclude in str(file_path):
                should_exclude = True
                break
        
        if not should_exclude:
            files_to_fix.append(file_path)
    
    print(f"📋 找到 {len(files_to_fix)} 个Python文件需要检查")
    
    # 修复文件
    fixed_count = 0
    
    for file_path in files_to_fix:
        if fix_imports_to_relative(file_path, root_dir):
            fixed_count += 1
    
    print("=" * 50)
    print(f"🎯 修复完成: {fixed_count}/{len(files_to_fix)} 个文件")
    
    if fixed_count > 0:
        print("✅ 导入路径修复成功!")
        print("\n💡 包结构说明:")
        print("   - utf包内部使用相对导入")
        print("   - 外部文件使用绝对导入 'from utf import'")
    else:
        print("ℹ️  没有文件需要修复")

if __name__ == "__main__":
    main()
