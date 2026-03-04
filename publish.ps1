# publish.ps1 - 自动更新 index.html 并推送到 GitHub Pages
# 用法: .\publish.ps1
#       .\publish.ps1 -CommitMessage "add beauty report 0303"

param(
    [string]$CommitMessage = "add new report"
)

$root = $PSScriptRoot
Set-Location $root

# --- 不在 index 中展示的文件夹 ---
$excludeFolders = @('beauty', 'ce_od', 'design')

# --- 分类配置：文件夹路径 => (显示名, 图标) ---
$categories = [ordered]@{
    "HashTags"                          = @("HashTags", "🏷️")
    "TopInfluencers/NoxTopInfluencers"  = @("Nox Top Influencers", "🌟")
    "TopInfluencers/JunyaoInfluencers" = @("Junyao Influencers", "👤")
    "design"                            = @("Design", "📐")
}

# --- 扫描目录，生成分类 HTML ---
$categoryBlocks = @()

foreach ($folder in $categories.Keys) {
    $folderPath = Join-Path $root $folder
    if (-not (Test-Path $folderPath)) { continue }

    $files = Get-ChildItem -Path $folderPath -Filter "*.html" | Sort-Object {
        if ($_.BaseName -match '_(\d{4})') { $matches[1] } else { '0000' }
    } -Descending
    if ($files.Count -eq 0) { continue }

    $displayName = $categories[$folder][0]
    $icon = $categories[$folder][1]
    $catId = "cat-$($folder -replace '[^a-zA-Z0-9]', '')"

    $fileLinks = ($files | ForEach-Object {
        $name = $_.BaseName
        "                <li><a href=`"$folder/$($_.Name)`">$name</a></li>"
    }) -join "`n"

    $categoryBlocks += @"
        <div class="category collapsed" id="$catId">
            <div class="category-header" onclick="toggle('$catId')">
                <span class="icon">$icon</span> $displayName
                <span class="count">$($files.Count)</span>
                <span class="arrow">▼</span>
            </div>
            <ul class="file-list">
$fileLinks
            </ul>
        </div>
"@
}

# --- 检测未配置的新文件夹 ---
$allFolders = Get-ChildItem -Path $root -Directory | Where-Object { -not $_.Name.StartsWith('.') }
$configuredRoots = $categories.Keys | ForEach-Object { ($_ -split '[/\\]')[0] } | Select-Object -Unique
foreach ($dir in $allFolders) {
    if ($dir.Name -notin $configuredRoots -and $dir.Name -notin $excludeFolders) {
        $files = Get-ChildItem -Path $dir.FullName -Filter "*.html" | Sort-Object {
            if ($_.BaseName -match '_(\d{4})') { $matches[1] } else { '0000' }
        } -Descending
        if ($files.Count -eq 0) { continue }

        $catId = "cat-$($dir.Name -replace '[^a-zA-Z0-9]', '')"
        $fileLinks = ($files | ForEach-Object {
            $name = $_.BaseName
            "                <li><a href=`"$($dir.Name)/$($_.Name)`">$name</a></li>"
        }) -join "`n"

        $categoryBlocks += @"
        <div class="category collapsed" id="$catId">
            <div class="category-header" onclick="toggle('$catId')">
                <span class="icon">📁</span> $($dir.Name)
                <span class="count">$($files.Count)</span>
                <span class="arrow">▼</span>
            </div>
            <ul class="file-list">
$fileLinks
            </ul>
        </div>
"@
        Write-Host "[INFO] 发现新文件夹 '$($dir.Name)'，已自动加入索引 (可在脚本中配置显示名和图标)" -ForegroundColor Yellow
    }
}

$totalFiles = (Get-ChildItem -Path $root -Recurse -Filter "*.html" | Where-Object { $_.Name -ne "index.html" }).Count
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"

# --- 组装完整 HTML ---
$html = @"
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Social Products Reports</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f7fa;
            color: #333;
            padding: 2rem;
        }
        h1 {
            text-align: center;
            margin-bottom: 0.5rem;
            font-size: 1.8rem;
            color: #1a1a2e;
        }
        .subtitle {
            text-align: center;
            color: #888;
            margin-bottom: 2rem;
            font-size: 0.9rem;
        }
        .container {
            max-width: 960px;
            margin: 0 auto;
        }
        .category {
            background: #fff;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 1.5rem;
            overflow: hidden;
        }
        .category-header {
            padding: 1rem 1.5rem;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.6rem;
            user-select: none;
            transition: background 0.2s;
        }
        .category-header:hover { background: #f0f4ff; }
        .category-header .icon { font-size: 1.3rem; }
        .category-header .count {
            margin-left: auto;
            background: #e8ecf1;
            color: #555;
            font-size: 0.8rem;
            padding: 2px 10px;
            border-radius: 12px;
        }
        .category-header .arrow {
            transition: transform 0.3s;
            font-size: 0.7rem;
            color: #aaa;
        }
        .category.collapsed .arrow { transform: rotate(-90deg); }
        .category.collapsed .file-list { display: none; }
        .file-list {
            list-style: none;
            border-top: 1px solid #f0f0f0;
        }
        .file-list li {
            border-bottom: 1px solid #f7f7f7;
        }
        .file-list li:last-child { border-bottom: none; }
        .file-list a {
            display: block;
            padding: 0.75rem 1.5rem 0.75rem 3rem;
            text-decoration: none;
            color: #2563eb;
            transition: background 0.15s;
            font-size: 0.95rem;
        }
        .file-list a:hover {
            background: #f0f4ff;
            color: #1d4ed8;
        }
        .file-list a::before {
            content: "📄 ";
            font-size: 0.85rem;
        }
        footer {
            text-align: center;
            color: #aaa;
            font-size: 0.8rem;
            margin-top: 2rem;
        }
        @media (max-width: 600px) {
            body { padding: 1rem; }
            .file-list a { padding-left: 2rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Social Products Reports</h1>
        <p class="subtitle">共 $totalFiles 份报告 · 更新于 $timestamp · 点击分类展开/收起</p>

$($categoryBlocks -join "`n`n")

        <footer>Auto-generated by publish.ps1 · Social Products Reports</footer>
    </div>

    <script>
        function toggle(id) {
            document.getElementById(id).classList.toggle('collapsed');
        }
    </script>
</body>
</html>
"@

# --- 写入 index.html ---
$indexPath = Join-Path $root "index.html"
$html | Out-File -FilePath $indexPath -Encoding utf8
Write-Host "[OK] index.html 已更新 (共 $totalFiles 份报告)" -ForegroundColor Green

# --- Git 推送 ---
git add -A
git commit -m $CommitMessage
git push origin main

Write-Host "[OK] 已推送到 GitHub，页面稍后即可访问" -ForegroundColor Green
