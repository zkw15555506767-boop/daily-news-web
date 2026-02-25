#!/usr/bin/env python3
"""
Daily News Website Builder
将 Markdown 日报转换为终端风格的 HTML 网页
支持获取 Product Hunt Top 30 和 GitHub Trending
"""

import os
import re
import json
import shutil
import requests
from pathlib import Path
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# 禁用 SSL 警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_producthunt_top30():
    """获取 Product Hunt Top 30 - 优先从缓存读取"""
    try:
        cache_file = Path(__file__).parent / 'producthunt_cache.json'
        if cache_file.exists():
            import json
            with open(cache_file, 'r', encoding='utf-8') as f:
                products = json.load(f)
            print(f"Product Hunt: 从缓存获取到 {len(products)} 个产品")
            return products
        else:
            return get_producthunt_fallback()
    except Exception as e:
        print(f"Product Hunt 获取失败: {e}")
        return []


def get_producthunt_fallback():
    """Product Hunt 备用数据源 - 使用 Product Hunt RSS 桥接服务"""
    try:
        # 使用 RSShub 桥接 Product Hunt RSS
        url = "https://api.rss2json.com/v1/api.json?rss_url=https://www.producthunt.com/feed"
        response = requests.get(url, timeout=15, verify=False)

        if response.status_code == 200:
            data = response.json()
            products = []
            for item in data.get('items', [])[:30]:
                # 提取产品名称（从标题中提取）
                title = item.get('title', '')
                # Product Hunt 标题格式通常是 "产品名 - 描述"
                parts = title.split(' - ')
                name = parts[0] if parts else title
                desc = parts[1] if len(parts) > 1 else item.get('description', '')

                products.append({
                    'name': name.strip(),
                    'url': item.get('link', ''),
                    'description': desc.strip()[:200]
                })
            print(f"Product Hunt (RSS): 获取到 {len(products)} 个产品")
            return products
        else:
            print(f"Product Hunt RSS 返回: {response.status_code}")
            return get_producthunt_mock()
    except Exception as e:
        print(f"Product Hunt RSS 失败: {e}")
        return get_producthunt_mock()


def get_producthunt_mock():
    """Product Hunt 模拟数据 - 当所有 API 都失败时使用"""
    return []  # 返回空列表而不是模拟数据

def get_github_trending(lang='', period='daily'):
    """获取 GitHub Trending - 使用 GitHub API"""
    try:
        # GitHub API: 搜索最流行的仓库
        # period: daily=1天内, weekly=7天内, monthly=30天内
        date_map = {'daily': '1', 'weekly': '7', 'monthly': '30'}
        days = date_map.get(period, '1')

        # 计算日期范围
        from datetime import datetime, timedelta
        date = (datetime.now() - timedelta(days=int(days))).strftime('%Y-%m-%d')

        query = f"created:>{date}"
        if lang:
            query += f" language:{lang}"

        url = "https://api.github.com/search/repositories"
        params = {
            'q': query,
            'sort': 'stars',
            'order': 'desc',
            'per_page': '30'
        }
        headers = {
            'User-Agent': 'DailyNews/1.0',
            'Accept': 'application/vnd.github.v3+json',
        }

        response = requests.get(url, params=params, headers=headers, timeout=15, verify=False)

        if response.status_code == 200:
            data = response.json()
            repos = []
            for item in data.get('items', [])[:30]:
                repos.append({
                    'name': item.get('full_name', ''),
                    'url': item.get('html_url', ''),
                    'description': item.get('description', '')[:200] if item.get('description') else '',
                    'language': item.get('language', ''),
                    'stars': str(item.get('stargazers_count', 0))
                })
            print(f"GitHub Trending: 获取到 {len(repos)} 个项目")
            return repos
        else:
            print(f"GitHub API 返回错误: {response.status_code}")
            return []

    except Exception as e:
        print(f"GitHub Trending 获取失败: {e}")
        return []

def parse_markdown(md_content):
    """解析 Markdown 内容"""
    sections = {
        'title': '',
        'summary': [],
        'five_star': [],
        'four_star': [],
        'worth_viewing': []
    }

    lines = md_content.split('\n')
    current_section = None
    current_item = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 提取日期
        if line.startswith('# Daily News'):
            match = re.search(r'(\d{4}-\d{2}-\d{2})', line)
            if match:
                sections['date'] = match.group(1)
            continue

        # 导读
        if line == '## 导读':
            current_section = 'summary'
            continue

        # 五星推荐
        if line == '## 五星推荐':
            current_section = 'five_star'
            if current_item:
                sections[current_section].append(current_item)
            current_item = None
            continue

        # 四星推荐
        if line == '## 四星推荐':
            current_section = 'four_star'
            if current_item and current_section != 'summary':
                sections[current_section].append(current_item)
            current_item = None
            continue

        # 值得一看
        if line == '## 值得一看':
            current_section = 'worth_viewing'
            if current_item and current_section != 'summary':
                sections[current_section].append(current_item)
            current_item = None
            continue

        # 解析内容
        if current_section == 'summary' and line.startswith('- **'):
            # 导读条目
            match = re.match(r'- \*\*(.+?)\*\*：(.+)', line)
            if match:
                sections['summary'].append({
                    'topic': match.group(1),
                    'content': match.group(2)
                })

        elif current_section in ['five_star', 'four_star', 'worth_viewing']:
            # 文章条目
            if line.startswith('**['):
                # 新条目开始
                if current_item:
                    sections[current_section].append(current_item)
                current_item = {'title': '', 'url': '', 'summary': '', 'meta': ''}

                # 提取标题和URL
                match = re.match(r'\*\*\[(.+?)\]\((.+?)\)\*\*', line)
                if match:
                    current_item['title'] = match.group(1)
                    current_item['url'] = match.group(2)

            elif line.startswith('`') and '·' in line:
                # 元数据行
                current_item['meta'] = line.strip('`')

            elif line and not line.startswith('---') and not line.startswith('*Generated'):
                # 摘要内容
                if current_item['summary']:
                    current_item['summary'] += ' ' + line
                else:
                    current_item['summary'] = line

    # 添加最后一个条目
    if current_item and current_section in ['five_star', 'four_star', 'worth_viewing']:
        sections[current_section].append(current_item)

    return sections

def generate_html(data, all_dates, producthunt=None, github_trending=None):
    """生成 HTML 页面"""

    if producthunt is None:
        producthunt = []
    if github_trending is None:
        github_trending = []

    # 星级图标
    star_icons = {
        5: '★★★★★',
        4: '★★★★☆',
        3: '★★★☆☆'
    }

    # 生成 Product Hunt 列表
    def generate_product_list(products):
        html = ''
        for i, product in enumerate(products, 1):
            html += f'''
            <article class="news-item">
                <div class="news-header">
                    <span class="rank-num">#{i}</span>
                    <a href="{product.get('url', '#')}" class="news-title" target="_blank" rel="noopener">{product.get('name', 'Untitled')}</a>
                </div>
                <p class="news-summary">{product.get('description', '')}</p>
            </article>
            '''
        return html

    # 生成 GitHub Trending 列表
    def generate_github_list(repos):
        html = ''
        for repo in repos:
            lang_color = {
                'Python': '#3572A5',
                'JavaScript': '#f1e05a',
                'TypeScript': '#2b7489',
                'Go': '#00ADD8',
                'Rust': '#dea584',
                'Java': '#b07219',
                'C++': '#f34b7d',
                'C': '#555555',
            }.get(repo.get('language', ''), '#666666')

            html += f'''
            <article class="news-item">
                <div class="news-header">
                    <a href="{repo.get('url', '#')}" class="news-title" target="_blank" rel="noopener">{repo.get('name', 'Untitled')}</a>
                    <span class="news-meta">
                        <span class="lang-dot" style="background: {lang_color}"></span>
                        {repo.get('language', '')} · ⭐ {repo.get('stars', '0')}
                    </span>
                </div>
                <p class="news-summary">{repo.get('description', '')}</p>
            </article>
            '''
        return html

    producthunt_html = generate_product_list(producthunt)
    github_trending_html = generate_github_list(github_trending)

    # 生成日期导航
    date_nav = ''
    for d in sorted(all_dates, reverse=True):
        active = 'active' if d == data.get('date') else ''
        date_nav += f'<a href="{d}.html" class="date-link {active}">{d}</a>'

    # 生成导读
    summary_html = ''
    for item in data.get('summary', []):
        summary_html += f'''
        <div class="summary-item">
            <span class="summary-topic">{item['topic']}</span>
            <span class="summary-content">{item['content']}</span>
        </div>
        '''

    # 生成文章列表
    def generate_articles(articles, stars):
        html = ''
        for article in articles:
            if not article.get('title'):
                continue
            html += f'''
            <article class="news-item">
                <div class="news-header">
                    <a href="{article.get('url', '#')}" class="news-title" target="_blank" rel="noopener">{article.get('title', 'Untitled')}</a>
                    <span class="news-meta">{article.get('meta', '')}</span>
                </div>
                <p class="news-summary">{article.get('summary', '')}</p>
            </article>
            '''
        return html

    five_star_html = generate_articles(data.get('five_star', []), 5)
    four_star_html = generate_articles(data.get('four_star', []), 4)
    worth_html = generate_articles(data.get('worth_viewing', []), 3)

    # Pre-build sections for Python 3.9 compatibility
    five_star_section = ''
    if five_star_html:
        five_star_section = f'''
        <section class="news-section">
            <div class="section-header">
                <span class="section-name">五星推荐</span>
                <span class="star-rating">{star_icons[5]}</span>
            </div>
            {five_star_html}
        </section>
        '''

    four_star_section = ''
    if four_star_html:
        four_star_section = f'''
        <section class="news-section">
            <div class="section-header">
                <span class="section-name">四星推荐</span>
                <span class="star-rating">{star_icons[4]}</span>
            </div>
            {four_star_html}
        </section>
        '''

    worth_section = ''
    if worth_html:
        worth_section = f'''
        <section class="news-section">
            <div class="section-header">
                <span class="section-name">值得一看</span>
                <span class="star-rating">{star_icons[3]}</span>
            </div>
            {worth_html}
        </section>
        '''

    # Product Hunt Section
    producthunt_section = ''
    if producthunt_html:
        producthunt_section = f'''
        <section class="news-section trending-section">
            <div class="trending-header">
                <span class="trending-name">Product Hunt Top 30</span>
                <span class="trending-badge ph">Product Hunt</span>
            </div>
            {producthunt_html}
        </section>
        '''

    # GitHub Trending Section
    github_section = ''
    if github_trending_html:
        github_section = f'''
        <section class="news-section trending-section">
            <div class="trending-header">
                <span class="trending-name">GitHub Trending</span>
                <span class="trending-badge gh">GitHub</span>
            </div>
            {github_trending_html}
        </section>
        '''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily News - {data.get('date', '')}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #fafafa;
            --bg-secondary: #f5f5f5;
            --bg-terminal: #1a1a1a;
            --text-primary: #1a1a1a;
            --text-secondary: #666666;
            --text-muted: #999999;
            --accent: #2563eb;
            --accent-light: #3b82f6;
            --border: #e5e5e5;
            --border-light: #f0f0f0;
            --star: #f59e0b;
            --code-bg: #f4f4f4;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
        }}

        /* Terminal Header */
        .terminal-header {{
            background: var(--bg-terminal);
            color: #fff;
            padding: 1rem 2rem;
            font-family: 'JetBrains Mono', monospace;
        }}

        .terminal-line {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.25rem;
        }}

        .terminal-prompt {{
            color: #10b981;
        }}

        .terminal-cursor {{
            display: inline-block;
            width: 8px;
            height: 1.2em;
            background: #10b981;
            animation: blink 1s infinite;
            vertical-align: text-bottom;
        }}

        @keyframes blink {{
            0%, 50% {{ opacity: 1; }}
            51%, 100% {{ opacity: 0; }}
        }}

        /* Navigation */
        .nav-container {{
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
            padding: 1rem 2rem;
            overflow-x: auto;
        }}

        .date-nav {{
            display: flex;
            gap: 0.5rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.875rem;
        }}

        .date-link {{
            padding: 0.5rem 1rem;
            color: var(--text-secondary);
            text-decoration: none;
            border-radius: 4px;
            transition: all 0.2s;
            white-space: nowrap;
        }}

        .date-link:hover {{
            background: var(--bg-primary);
            color: var(--accent);
        }}

        .date-link.active {{
            background: var(--accent);
            color: white;
        }}

        /* Main Content */
        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 3rem 2rem;
        }}

        .page-title {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            font-family: 'JetBrains Mono', monospace;
        }}

        .page-subtitle {{
            color: var(--text-muted);
            font-family: 'JetBrains Mono', monospace;
            margin-bottom: 3rem;
        }}

        /* Summary Section */
        .summary-section {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 3rem;
        }}

        .section-title {{
            font-size: 0.875rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 1rem;
            font-family: 'JetBrains Mono', monospace;
        }}

        .summary-item {{
            padding: 0.75rem 0;
            border-bottom: 1px solid var(--border);
        }}

        .summary-item:last-child {{
            border-bottom: none;
        }}

        .summary-topic {{
            font-weight: 600;
            color: var(--accent);
            margin-right: 0.5rem;
        }}

        .summary-content {{
            color: var(--text-secondary);
        }}

        /* News Sections */
        .news-section {{
            margin-bottom: 3rem;
        }}

        .section-header {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1.5rem;
            padding-bottom: 0.75rem;
            border-bottom: 2px solid var(--border);
        }}

        .section-name {{
            font-size: 1.25rem;
            font-weight: 600;
        }}

        .star-rating {{
            color: var(--star);
            font-size: 0.875rem;
        }}

        .news-item {{
            padding: 1.5rem;
            margin-bottom: 1rem;
            background: white;
            border: 1px solid var(--border-light);
            border-radius: 8px;
            transition: all 0.2s;
        }}

        .news-item:hover {{
            border-color: var(--accent);
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.08);
        }}

        .news-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 1rem;
            margin-bottom: 0.75rem;
        }}

        .news-title {{
            font-size: 1.125rem;
            font-weight: 600;
            color: var(--text-primary);
            text-decoration: none;
            line-height: 1.4;
        }}

        .news-title:hover {{
            color: var(--accent);
        }}

        .news-meta {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: var(--text-muted);
            background: var(--code-bg);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            white-space: nowrap;
        }}

        .news-summary {{
            color: var(--text-secondary);
            line-height: 1.7;
        }}

        /* Product Hunt & GitHub Trending Sections */
        .trending-section {{
            margin-top: 3rem;
        }}

        .trending-header {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1.5rem;
            padding-bottom: 0.75rem;
            border-bottom: 2px solid var(--border);
        }}

        .trending-name {{
            font-size: 1.25rem;
            font-weight: 600;
        }}

        .trending-badge {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            background: var(--code-bg);
            color: var(--text-muted);
        }}

        .trending-badge.ph {{
            background: #DA552F;
            color: white;
        }}

        .trending-badge.gh {{
            background: #24292e;
            color: white;
        }}

        .rank-num {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.875rem;
            color: var(--text-muted);
            margin-right: 0.5rem;
            min-width: 2rem;
            display: inline-block;
        }}

        .lang-dot {{
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 0.25rem;
            vertical-align: middle;
        }}

        /* Footer */
        .footer {{
            margin-top: 4rem;
            padding-top: 2rem;
            border-top: 1px solid var(--border);
            text-align: center;
            color: var(--text-muted);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.875rem;
        }}

        /* Responsive */
        @media (max-width: 768px) {{
            .container {{
                padding: 1.5rem;
            }}

            .page-title {{
                font-size: 1.75rem;
            }}

            .news-header {{
                flex-direction: column;
                gap: 0.5rem;
            }}

            .nav-container {{
                padding: 0.75rem 1rem;
            }}
        }}
    </style>
</head>
<body>
    <header class="terminal-header">
        <div class="terminal-line">
            <span class="terminal-prompt">$</span>
            <span>daily-news --date {data.get('date', '')}</span>
            <span class="terminal-cursor"></span>
        </div>
        <div class="terminal-line">
            <span class="terminal-prompt">&gt;</span>
            <span>Generating report... Done.</span>
        </div>
    </header>

    <nav class="nav-container">
        <div class="date-nav">
            {date_nav}
        </div>
    </nav>

    <main class="container">
        <h1 class="page-title">Daily News</h1>
        <p class="page-subtitle">// {data.get('date', '')}</p>

        <section class="summary-section">
            <div class="section-title">$ cat summary.md</div>
            {summary_html if summary_html else '<p class="text-muted">暂无导读</p>'}
        </section>

        {five_star_section}
        {four_star_section}
        {worth_section}

        {producthunt_section}
        {github_section}

        <footer class="footer">
            <p>Generated by Daily News Skill | Cloudflare Pages</p>
        </footer>
    </main>
</body>
</html>'''

    return html

def build():
    """构建网站"""
    workspace = Path.home() / 'daily-news'
    output_dir = workspace / 'output'
    dist_dir = workspace / 'website/dist'

    # 清理并重建 dist
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True)

    # 获取所有日期
    all_dates = []
    for md_file in sorted(output_dir.glob('*.md')):
        date = md_file.stem
        all_dates.append(date)

    print(f"找到 {len(all_dates)} 个日报文件")

    # 获取Trending数据
    print("正在获取 Product Hunt Top 30...")
    producthunt = get_producthunt_top30()
    print(f"获取到 {len(producthunt)} 个 Product Hunt 产品")

    print("正在获取 GitHub Trending...")
    github_trending = get_github_trending()
    print(f"获取到 {len(github_trending)} 个 GitHub Trending 项目")

    # 生成每个页面的 HTML
    for md_file in output_dir.glob('*.md'):
        date = md_file.stem
        md_content = md_file.read_text(encoding='utf-8')
        data = parse_markdown(md_content)
        data['date'] = date

        html = generate_html(data, all_dates, producthunt, github_trending)

        output_file = dist_dir / f'{date}.html'
        output_file.write_text(html, encoding='utf-8')
        print(f"生成: {output_file.name}")

    # 复制最新的作为 index.html
    if all_dates:
        latest = max(all_dates)
        shutil.copy(dist_dir / f'{latest}.html', dist_dir / 'index.html')
        print(f"首页: {latest}.html -> index.html")

    print(f"\n构建完成！输出目录: {dist_dir}")

if __name__ == '__main__':
    build()
