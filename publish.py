"""
publish.py - 自动更新 index.html 并推送到 GitHub Pages
用法:
    python publish.py
    python publish.py -m "add beauty report 0303"
"""

import os
import re
import sys
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from collections import OrderedDict

ROOT = Path(__file__).parent
HOME_URL = "https://baibaitao.github.io/social_products/"

# 注入到每个报告 HTML 中的返回主页按钮（用标记注释防止重复注入）
INJECT_MARKER = "<!-- SOCIAL_PRODUCTS_NAV -->"
INJECT_SNIPPET = f'''{INJECT_MARKER}
<div id="sp-home-btn" style="
    position:fixed; top:16px; right:20px; z-index:9999;
">
    <a href="{HOME_URL}" style="
        display:inline-flex; align-items:center; gap:6px;
        padding:8px 16px; background:rgba(37,99,235,0.92); color:#fff;
        border-radius:8px; text-decoration:none; font-size:14px;
        font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
        box-shadow:0 2px 10px rgba(0,0,0,0.25);
        transition:background 0.2s, transform 0.2s;
    " onmouseover="this.style.background='rgba(30,64,175,0.95)';this.style.transform='scale(1.05)'"
       onmouseout="this.style.background='rgba(37,99,235,0.92)';this.style.transform='scale(1)'">
        🏠 返回主页
    </a>
</div>
'''

# --- 不在 index 中展示的文件夹 ---
EXCLUDE_FOLDERS = {"beauty", "ce_od", "design"}

# --- 分类配置：顶级文件夹名 => (显示名, 图标) ---
CATEGORIES = OrderedDict([
    ("HashTags",        ("HashTags",           "🏷️")),
    ("InfluencersReports", ("Influencers Reports", "📈")),
    ("TopInfluencers",  ("Top Influencers",    "🌟")),
    ("design",          ("Design",             "📐")),
])

# --- 从文件名中提取日期后缀用于排序（如 _0302 => "0302"）---
def _extract_date(path: Path) -> str:
    m = re.search(r'_(\d{4})(?:\D|$)', path.stem)
    return m.group(1) if m else '0000'

# --- 生成单个分类的 HTML（自动检测子目录层级）---
def build_category_block(folder: str, display_name: str, icon: str) -> str | None:
    folder_path = ROOT / folder
    cat_id = f"cat-{''.join(c for c in folder if c.isalnum())}"

    # 收集直属 HTML 文件
    direct_files = sorted(folder_path.glob("*.html"), key=_extract_date, reverse=True)

    # 收集子目录及其 HTML 文件
    subdirs = []
    for d in sorted(folder_path.iterdir()):
        if d.is_dir() and not d.name.startswith("."):
            sub_files = sorted(d.rglob("*.html"), key=_extract_date, reverse=True)
            if sub_files:
                subdirs.append((d.name, sub_files))

    total = len(direct_files) + sum(len(sf) for _, sf in subdirs)
    if total == 0:
        return None

    parts = []

    # 直属文件
    if direct_files:
        links = "\n".join(
            f'                <li><a href="{f.relative_to(ROOT).as_posix()}">{f.stem}</a></li>'
            for f in direct_files
        )
        parts.append(f'''            <ul class="file-list">
{links}
            </ul>''')

    # 子目录
    for sub_name, sub_files in subdirs:
        sub_id = f"{cat_id}-{''.join(c for c in sub_name if c.isalnum())}"
        sub_links = "\n".join(
            f'                    <li><a href="{f.relative_to(ROOT).as_posix()}">{f.stem}</a></li>'
            for f in sub_files
        )
        parts.append(f'''            <div class="subcategory collapsed" id="{sub_id}">
                <div class="subcategory-header" onclick="toggle('{sub_id}')">
                    <span class="icon">📁</span> {sub_name}
                    <span class="count">{len(sub_files)}</span>
                    <span class="arrow">▼</span>
                </div>
                <ul class="file-list">
{sub_links}
                </ul>
            </div>''')

    inner = "\n".join(parts)
    return f'''        <div class="category collapsed" id="{cat_id}">
            <div class="category-header" onclick="toggle('{cat_id}')">
                <span class="icon">{icon}</span> {display_name}
                <span class="count">{total}</span>
                <span class="arrow">▼</span>
            </div>
{inner}
        </div>'''

# --- 扫描目录 ---
def scan_reports() -> list[str]:
    blocks = []

    # 已配置的分类
    for folder, (display_name, icon) in CATEGORIES.items():
        folder_path = ROOT / folder
        if not folder_path.is_dir():
            continue
        block = build_category_block(folder, display_name, icon)
        if block:
            blocks.append(block)

    # 自动检测新文件夹
    for d in sorted(ROOT.iterdir()):
        if not d.is_dir() or d.name.startswith(".") or d.name in CATEGORIES or d.name in EXCLUDE_FOLDERS:
            continue
        block = build_category_block(d.name, d.name, "📁")
        if block:
            print(f"[INFO] 发现新文件夹 '{d.name}'，已自动加入索引 (可在脚本 CATEGORIES 中配置显示名和图标)")
            blocks.append(block)

    return blocks

# --- 统计总文件数 ---
def count_total() -> int:
    return sum(
        1 for f in ROOT.rglob("*.html")
        if f.name != "index.html" and ".git" not in f.parts
    )

# --- 生成完整 HTML ---
def generate_html(blocks: list[str]) -> str:
    total = count_total()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    categories_html = "\n\n".join(blocks)

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Social Products Reports</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f7fa;
            color: #333;
            padding: 2rem;
        }}
        h1 {{
            text-align: center;
            margin-bottom: 0.5rem;
            font-size: 1.8rem;
            color: #1a1a2e;
        }}
        .subtitle {{
            text-align: center;
            color: #888;
            margin-bottom: 2rem;
            font-size: 0.9rem;
        }}
        .container {{
            max-width: 960px;
            margin: 0 auto;
        }}
        .category {{
            background: #fff;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 1.5rem;
            overflow: hidden;
        }}
        .category-header {{
            padding: 1rem 1.5rem;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.6rem;
            user-select: none;
            transition: background 0.2s;
        }}
        .category-header:hover {{ background: #f0f4ff; }}
        .category-header .icon {{ font-size: 1.3rem; }}
        .category-header .count {{
            margin-left: auto;
            background: #e8ecf1;
            color: #555;
            font-size: 0.8rem;
            padding: 2px 10px;
            border-radius: 12px;
        }}
        .category-header .arrow {{
            transition: transform 0.3s;
            font-size: 0.7rem;
            color: #aaa;
        }}
        .category.collapsed .arrow {{ transform: rotate(-90deg); }}
        .category.collapsed .file-list {{ display: none; }}
        .category.collapsed .subcategory {{ display: none; }}
        .file-list {{
            list-style: none;
            border-top: 1px solid #f0f0f0;
        }}
        .file-list li {{
            border-bottom: 1px solid #f7f7f7;
        }}
        .file-list li:last-child {{ border-bottom: none; }}
        .file-list a {{
            display: block;
            padding: 0.75rem 1.5rem 0.75rem 3rem;
            text-decoration: none;
            color: #2563eb;
            transition: background 0.15s;
            font-size: 0.95rem;
        }}
        .file-list a:hover {{
            background: #f0f4ff;
            color: #1d4ed8;
        }}
        .file-list a::before {{
            content: "📄 ";
            font-size: 0.85rem;
        }}
        .subcategory {{
            border-top: 1px solid #f0f0f0;
        }}
        .subcategory-header {{
            padding: 0.7rem 1.5rem 0.7rem 2.5rem;
            font-size: 0.95rem;
            font-weight: 500;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            user-select: none;
            transition: background 0.2s;
            color: #555;
        }}
        .subcategory-header:hover {{ background: #f5f8ff; }}
        .subcategory-header .icon {{ font-size: 1.1rem; }}
        .subcategory-header .count {{
            margin-left: auto;
            background: #e8ecf1;
            color: #555;
            font-size: 0.75rem;
            padding: 2px 8px;
            border-radius: 12px;
        }}
        .subcategory-header .arrow {{
            transition: transform 0.3s;
            font-size: 0.7rem;
            color: #aaa;
        }}
        .subcategory.collapsed .arrow {{ transform: rotate(-90deg); }}
        .subcategory.collapsed .file-list {{ display: none; }}
        .subcategory .file-list a {{
            padding-left: 4.5rem;
        }}
        footer {{
            text-align: center;
            color: #aaa;
            font-size: 0.8rem;
            margin-top: 2rem;
        }}
        @media (max-width: 600px) {{
            body {{ padding: 1rem; }}
            .file-list a {{ padding-left: 2rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Social Products Reports</h1>
        <p class="subtitle">共 {total} 份报告 · 更新于 {timestamp} · 点击分类展开/收起</p>

{categories_html}

        <footer>Auto-generated by publish.py · Social Products Reports</footer>
    </div>

    <script>
        function toggle(id) {{
            document.getElementById(id).classList.toggle('collapsed');
        }}
    </script>
</body>
</html>'''

# --- 为所有报告 HTML 注入返回主页按钮 ---
def inject_home_button():
    count = 0
    for html_file in ROOT.rglob("*.html"):
        if html_file.name == "index.html" or ".git" in html_file.parts:
            continue
        content = html_file.read_text(encoding="utf-8", errors="ignore")
        if INJECT_MARKER in content:
            continue  # 已注入，跳过

        # 在 <body> 标签后注入（兼容 <body ...> 带属性的情况）
        new_content = re.sub(
            r"(<body[^>]*>)",
            r"\1\n" + INJECT_SNIPPET,
            content,
            count=1,
            flags=re.IGNORECASE,
        )
        if new_content != content:
            html_file.write_text(new_content, encoding="utf-8")
            count += 1

    print(f"[OK] 已为 {count} 个报告注入返回主页按钮" if count else "[OK] 所有报告已有返回按钮，无需更新")

# --- Git 推送 ---
def git_push(message: str):
    os.chdir(ROOT)
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", "commit", "-m", message], check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True)

# --- 主流程 ---
def main():
    parser = argparse.ArgumentParser(description="更新 index.html 并推送到 GitHub Pages")
    parser.add_argument("-m", "--message", default="add new report", help="Git commit message")
    parser.add_argument("--no-push", action="store_true", help="只更新 index.html，不推送")
    args = parser.parse_args()

    blocks = scan_reports()
    html = generate_html(blocks)

    index_path = ROOT / "index.html"
    index_path.write_text(html, encoding="utf-8")
    total = count_total()
    print(f"[OK] index.html 已更新 (共 {total} 份报告)")

    # 注入返回主页按钮
    inject_home_button()

    if not args.no_push:
        git_push(args.message)
        print("[OK] 已推送到 GitHub，页面稍后即可访问")
    else:
        print("[INFO] 已跳过 git 推送 (--no-push)")

if __name__ == "__main__":
    main()
