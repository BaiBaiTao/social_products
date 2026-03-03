"""
publish.py - 自动更新 index.html 并推送到 GitHub Pages
用法:
    python publish.py
    python publish.py -m "add beauty report 0303"
"""

import os
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

# --- 分类配置：文件夹名 => (显示名, 图标) ---
CATEGORIES = OrderedDict([
    ("all",              ("All (综合报告)",                  "📋")),
    ("beauty",           ("Beauty (美妆)",                   "💄")),
    ("cc_hashtag_trends",("CC Hashtag Trends (话题标签趋势)", "🏷️")),
    ("ce_od",            ("CE & Outdoors (消费电子/户外)",    "🏕️")),
    ("top_influencers",  ("Top Influencers (头部达人)",       "🌟")),
])

# --- 生成单个分类的 HTML ---
def build_category_block(folder: str, display_name: str, icon: str, files: list[Path]) -> str:
    cat_id = f"cat-{''.join(c for c in folder if c.isalnum())}"
    file_links = "\n".join(
        f'                <li><a href="{folder}/{f.name}">{f.stem}</a></li>'
        for f in sorted(files, key=lambda x: x.name)
    )
    return f'''        <div class="category collapsed" id="{cat_id}">
            <div class="category-header" onclick="toggle('{cat_id}')">
                <span class="icon">{icon}</span> {display_name}
                <span class="count">{len(files)}</span>
                <span class="arrow">▼</span>
            </div>
            <ul class="file-list">
{file_links}
            </ul>
        </div>'''

# --- 扫描目录 ---
def scan_reports() -> list[str]:
    blocks = []

    # 已配置的分类
    for folder, (display_name, icon) in CATEGORIES.items():
        folder_path = ROOT / folder
        if not folder_path.is_dir():
            continue
        files = list(folder_path.glob("*.html"))
        if not files:
            continue
        blocks.append(build_category_block(folder, display_name, icon, files))

    # 自动检测新文件夹
    for d in sorted(ROOT.iterdir()):
        if not d.is_dir() or d.name.startswith(".") or d.name in CATEGORIES:
            continue
        files = list(d.glob("*.html"))
        if not files:
            continue
        print(f"[INFO] 发现新文件夹 '{d.name}'，已自动加入索引 (可在脚本 CATEGORIES 中配置显示名和图标)")
        blocks.append(build_category_block(d.name, d.name, "📁", files))

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

    if not args.no_push:
        git_push(args.message)
        print("[OK] 已推送到 GitHub，页面稍后即可访问")
    else:
        print("[INFO] 已跳过 git 推送 (--no-push)")

if __name__ == "__main__":
    main()
