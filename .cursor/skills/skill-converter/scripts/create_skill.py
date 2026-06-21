#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill 文件创建辅助脚本
配合 Agent 使用，负责文件系统操作

功能：
- 创建 .cursor/skills/[skill-name]/ 目录
- 写入 SKILL.md 文件
- 验证格式和命名规范
- 返回 JSON 格式结果

用法：
    # 方式 1：命令行参数
    python create_skill.py --name my-skill --content "---\nname: my-skill\n..."
    
    # 方式 2：JSON 输入
    python create_skill.py --json '{"name": "my-skill", "content": "..."}'
    
    # 方式 3：从文件读取
    python create_skill.py --name my-skill --file template.md

作者：Cursor Agent
版本：1.0
创建日期：2026-01-18
"""

import os
import sys
import json
import argparse
import re
from pathlib import Path
from typing import Dict, Tuple


class SkillCreator:
    """Skill 文件创建器"""
    
    def __init__(self, base_dir: str = None):
        """
        初始化
        
        Args:
            base_dir: 基础目录（默认为 .cursor/skills）
        """
        if base_dir is None:
            # 自动查找工作区根目录的 .cursor/skills
            self.base_dir = self._find_base_dir()
        else:
            self.base_dir = Path(base_dir)
    
    def _find_base_dir(self) -> Path:
        """
        查找 .cursor/skills 目录
        
        从当前目录向上查找，直到找到 .cursor/skills 目录
        """
        current = Path.cwd()
        
        # 最多向上查找 5 层
        for _ in range(5):
            cursor_skills = current / ".cursor" / "skills"
            if cursor_skills.exists():
                return cursor_skills
            
            # 向上一层
            parent = current.parent
            if parent == current:  # 已到根目录
                break
            current = parent
        
        # 未找到，使用当前目录下的 .cursor/skills
        return Path.cwd() / ".cursor" / "skills"
    
    def validate_skill_name(self, skill_name: str) -> Tuple[bool, str]:
        """
        验证 skill 名称格式
        
        Args:
            skill_name: skill 名称
            
        Returns:
            (is_valid, error_message)
        """
        # 1. 不能为空
        if not skill_name or not skill_name.strip():
            return False, "Skill 名称不能为空"
        
        skill_name = skill_name.strip()
        
        # 2. 必须全小写
        if skill_name != skill_name.lower():
            return False, f"Skill 名称必须全小写: {skill_name} -> {skill_name.lower()}"
        
        # 3. 只能包含小写字母、数字、连字符
        if not re.match(r'^[a-z0-9-]+$', skill_name):
            return False, "Skill 名称只能包含小写字母、数字、连字符"
        
        # 4. 不能以连字符开头或结尾
        if skill_name.startswith('-') or skill_name.endswith('-'):
            return False, "Skill 名称不能以连字符开头或结尾"
        
        # 5. 不能包含连续的连字符
        if '--' in skill_name:
            return False, "Skill 名称不能包含连续的连字符"
        
        # 6. 长度限制（3-50字符）
        if len(skill_name) < 3:
            return False, "Skill 名称至少需要 3 个字符"
        if len(skill_name) > 50:
            return False, "Skill 名称不能超过 50 个字符"
        
        return True, ""
    
    def validate_content(self, content: str) -> Tuple[bool, str]:
        """
        验证 SKILL.md 内容格式
        
        Args:
            content: SKILL.md 内容
            
        Returns:
            (is_valid, error_message)
        """
        # 1. 不能为空
        if not content or not content.strip():
            return False, "内容不能为空"
        
        # 2. 必须包含 YAML Front Matter
        if not content.strip().startswith('---'):
            return False, "内容必须以 YAML Front Matter 开头（--- 开头）"
        
        # 3. 检查 YAML Front Matter 是否完整
        lines = content.strip().split('\n')
        yaml_end_count = 0
        yaml_end_line = -1
        
        for i, line in enumerate(lines):
            if line.strip() == '---':
                yaml_end_count += 1
                if yaml_end_count == 2:
                    yaml_end_line = i
                    break
        
        if yaml_end_count < 2:
            return False, "YAML Front Matter 不完整（需要两个 --- 包裹）"
        
        # 4. 提取 YAML 内容
        yaml_content = '\n'.join(lines[1:yaml_end_line])
        
        # 5. 检查必需字段
        if 'name:' not in yaml_content:
            return False, "YAML Front Matter 缺少 'name' 字段"
        
        if 'description:' not in yaml_content:
            return False, "YAML Front Matter 缺少 'description' 字段"
        
        # 6. 检查 description 长度（简单估算）
        desc_match = re.search(r'description:\s*(.+?)(?=\n[a-z_]+:|$)', 
                               yaml_content, re.DOTALL)
        if desc_match:
            desc_text = desc_match.group(1).strip()
            # 移除引号
            desc_text = desc_text.strip('"\'')
            
            # 中文字符数（粗略估算）
            chinese_chars = len([c for c in desc_text if '\u4e00' <= c <= '\u9fff'])
            total_chars = len(desc_text)
            
            # 如果主要是中文，检查字数
            if chinese_chars > total_chars * 0.3:
                if total_chars < 50:
                    return False, f"description 太短（当前 {total_chars} 字，建议 50-200 字）"
                if total_chars > 250:
                    return False, f"description 太长（当前 {total_chars} 字，建议 50-200 字）"
        
        return True, ""
    
    def create_skill(self, skill_name: str, content: str, 
                     force: bool = False, create_dirs: list = None) -> Dict:
        """
        创建 skill 目录和文件
        
        Args:
            skill_name: skill 名称（小写-连字符格式）
            content: SKILL.md 的完整内容
            force: 是否强制覆盖已存在的文件
            create_dirs: 要创建的可选目录列表 ['scripts', 'references', 'templates', 'assets']
            
        Returns:
            {
                "success": bool,
                "path": str,
                "message": str,
                "skill_name": str,
                "created_dirs": list
            }
        """
        try:
            # 1. 验证名称
            valid, error = self.validate_skill_name(skill_name)
            if not valid:
                return {
                    "success": False,
                    "path": "",
                    "message": f"名称验证失败: {error}",
                    "skill_name": skill_name,
                    "created_dirs": []
                }
            
            # 2. 验证内容
            valid, error = self.validate_content(content)
            if not valid:
                return {
                    "success": False,
                    "path": "",
                    "message": f"内容验证失败: {error}",
                    "skill_name": skill_name,
                    "created_dirs": []
                }
            
            # 3. 创建主目录
            skill_dir = self.base_dir / skill_name
            skill_file = skill_dir / "SKILL.md"
            
            # 检查是否已存在
            if skill_dir.exists() and not force:
                if skill_file.exists():
                    return {
                        "success": False,
                        "path": str(skill_file),
                        "message": f"Skill 已存在: {skill_file}\n使用 --force 强制覆盖",
                        "skill_name": skill_name,
                        "created_dirs": []
                    }
            
            # 创建主目录
            skill_dir.mkdir(parents=True, exist_ok=True)
            
            # 4. 创建可选目录
            created_dirs = []
            if create_dirs:
                valid_dirs = ['scripts', 'references', 'templates', 'assets']
                for dir_name in create_dirs:
                    if dir_name in valid_dirs:
                        dir_path = skill_dir / dir_name
                        dir_path.mkdir(exist_ok=True)
                        created_dirs.append(dir_name)
            
            # 5. 写入 SKILL.md 文件
            with open(skill_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 6. 验证文件已创建
            if not skill_file.exists():
                return {
                    "success": False,
                    "path": str(skill_file),
                    "message": "文件写入失败（文件不存在）",
                    "skill_name": skill_name,
                    "created_dirs": created_dirs
                }
            
            # 7. 返回成功结果
            dirs_info = f" (创建目录: {', '.join(created_dirs)})" if created_dirs else ""
            return {
                "success": True,
                "path": str(skill_file),
                "message": f"✅ Skill 创建成功: {skill_file}{dirs_info}",
                "skill_name": skill_name,
                "created_dirs": created_dirs
            }
        
        except PermissionError as e:
            return {
                "success": False,
                "path": "",
                "message": f"权限错误: {str(e)}",
                "skill_name": skill_name,
                "created_dirs": []
            }
        
        except Exception as e:
            return {
                "success": False,
                "path": "",
                "message": f"创建失败: {str(e)}",
                "skill_name": skill_name,
                "created_dirs": []
            }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='创建 Cursor Agent Skill 文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 方式 1：命令行参数
  python create_skill.py --name my-skill --content "---\\nname: my-skill\\n..."
  
  # 方式 2：JSON 输入
  python create_skill.py --json '{"name": "my-skill", "content": "..."}'
  
  # 方式 3：从文件读取
  python create_skill.py --name my-skill --file template.md
  
  # 强制覆盖已存在的文件
  python create_skill.py --name my-skill --content "..." --force
        """
    )
    
    # 参数组 1：普通参数
    parser.add_argument('--name', type=str, help='Skill 名称（小写-连字符格式）')
    parser.add_argument('--content', type=str, help='SKILL.md 内容')
    parser.add_argument('--file', type=str, help='从文件读取内容')
    
    # 参数组 2：JSON 输入
    parser.add_argument('--json', type=str, help='JSON 格式输入 {"name": "...", "content": "..."}')
    
    # 其他选项
    parser.add_argument('--base-dir', type=str, help='基础目录（默认为 .cursor/skills）')
    parser.add_argument('--force', action='store_true', help='强制覆盖已存在的文件')
    parser.add_argument('--dirs', type=str, help='创建可选目录（逗号分隔）：scripts,references,templates,assets')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细信息')
    
    args = parser.parse_args()
    
    # 解析输入
    skill_name = None
    content = None
    create_dirs = None
    
    if args.json:
        # 从 JSON 解析
        try:
            data = json.loads(args.json)
            skill_name = data.get('name')
            content = data.get('content')
            # 支持从 JSON 指定目录
            if 'dirs' in data:
                create_dirs = data['dirs'] if isinstance(data['dirs'], list) else data['dirs'].split(',')
        except json.JSONDecodeError as e:
            print(json.dumps({
                "success": False,
                "path": "",
                "message": f"JSON 解析失败: {str(e)}"
            }))
            sys.exit(1)
    else:
        # 从参数解析
        skill_name = args.name
        
        # 解析目录参数
        if args.dirs:
            create_dirs = [d.strip() for d in args.dirs.split(',')]
        
        if args.file:
            # 从文件读取
            try:
                with open(args.file, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                print(json.dumps({
                    "success": False,
                    "path": "",
                    "message": f"读取文件失败: {str(e)}"
                }))
                sys.exit(1)
        else:
            content = args.content
    
    # 验证必需参数
    if not skill_name:
        print(json.dumps({
            "success": False,
            "path": "",
            "message": "缺少 skill 名称（使用 --name 或 --json）"
        }))
        sys.exit(1)
    
    if not content:
        print(json.dumps({
            "success": False,
            "path": "",
            "message": "缺少内容（使用 --content、--file 或 --json）"
        }))
        sys.exit(1)
    
    # 创建 Skill
    creator = SkillCreator(base_dir=args.base_dir)
    
    if args.verbose:
        print(f"基础目录: {creator.base_dir}", file=sys.stderr)
        print(f"Skill 名称: {skill_name}", file=sys.stderr)
        print(f"内容长度: {len(content)} 字符", file=sys.stderr)
        if create_dirs:
            print(f"创建目录: {', '.join(create_dirs)}", file=sys.stderr)
    
    result = creator.create_skill(skill_name, content, force=args.force, create_dirs=create_dirs)
    
    # 输出 JSON 结果（处理 Windows 控制台编码问题）
    try:
        # 尝试使用 UTF-8 编码
        output = json.dumps(result, ensure_ascii=False, indent=2)
        print(output)
    except UnicodeEncodeError:
        # 如果失败，使用 ASCII 编码（转义中文）
        output = json.dumps(result, ensure_ascii=True, indent=2)
        print(output)
    
    # 设置退出码
    sys.exit(0 if result["success"] else 1)


if __name__ == '__main__':
    main()
