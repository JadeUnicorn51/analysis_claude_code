#!/usr/bin/env python3
"""
批量修复导入路径问题
"""

import os
import re
from pathlib import Path

def fix_imports_in_file(file_path: Path):
    """修复单个文件的导入路径"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 修复模式1: from utf. -> from universal_tool_framework.utf.
        content = re.sub(
            r'from utf\.',
            'from universal_tool_framework.utf.',
            content
        )
        
        # 修复模式2: import utf -> import universal_tool_framework.utf
        content = re.sub(
            r'^import utf$',
            'import universal_tool_framework.utf as utf',
            content,
            flags=re.MULTILINE
        )
        
        # 修复模式3: from utf import -> from universal_tool_framework.utf import
        content = re.sub(
            r'from utf import',
            'from universal_tool_framework.utf import',
            content
        )
        
        # 如果内容有变化，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复: {file_path}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ 修复失败 {file_path}: {e}")
        return False

def main():
    """主函数"""
    print("🔧 批量修复导入路径问题")
    print("=" * 50)
    
    # 获取项目根目录
    root_dir = Path(__file__).parent
    
    # 需要修复的文件模式
    patterns_to_fix = [
        "**/*.py",
    ]
    
    # 排除不需要修复的文件
    exclude_patterns = [
        "__pycache__",
        ".git",
        "venv",
        "env",
        "fix_imports.py"  # 排除自己
    ]
    
    files_to_fix = []
    
    # 收集需要修复的文件
    for pattern in patterns_to_fix:
        for file_path in root_dir.glob(pattern):
            if file_path.is_file():
                # 检查是否在排除列表中
                should_exclude = False
                for exclude in exclude_patterns:
                    if exclude in str(file_path):
                        should_exclude = True
                        break
                
                if not should_exclude:
                    files_to_fix.append(file_path)
    
    print(f"📋 找到 {len(files_to_fix)} 个Python文件")
    
    # 修复文件
    fixed_count = 0
    
    for file_path in files_to_fix:
        if fix_imports_in_file(file_path):
            fixed_count += 1
    
    print("=" * 50)
    print(f"🎯 修复完成: {fixed_count}/{len(files_to_fix)} 个文件")
    
    if fixed_count > 0:
        print("✅ 导入路径修复成功!")
        print("\n💡 现在可以重新运行测试:")
        print("   python test_basic.py")
        print("   python test_deep_capabilities.py")
    else:
        print("ℹ️  没有文件需要修复")

if __name__ == "__main__":
    main()
