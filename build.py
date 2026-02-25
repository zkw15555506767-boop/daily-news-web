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

def get_github_trending(lang='', period='weekly'):
    """获取 GitHub Trending - 从缓存读取"""
    try:
        # 优先从缓存读取
        cache_file = Path(__file__).parent / 'github_trending_cache.json'
        if cache_file.exists():
            import json
            with open(cache_file, 'r', encoding='utf-8') as f:
                repos = json.load(f)
            print(f"GitHub Trending: 从缓存获取到 {len(repos)} 个项目")
            return repos
        else:
            print("GitHub Trending: 缓存不存在，使用备用方案")
            return []
    except Exception as e:
        print(f"GitHub Trending 获取失败: {e}")
        return []


def generate_chinese_description(name, desc_en, language):
    """为 GitHub 项目生成中文描述"""
    if not desc_en:
        # 基于项目名生成描述
        name_part = name.split('/')[-1] if '/' in name else name
        return f"{name_part} - 一个{language}项目" if language else f"{name_part}项目"

    # 简短翻译/润色
    return desc_en[:150]


def get_ai_models():
    """获取 AI 模型排行榜信息 - 从 OpenRouter 缓存读取"""
    try:
        cache_file = Path(__file__).parent / 'openrouter_cache.json'
        if cache_file.exists():
            import json
            with open(cache_file, 'r', encoding='utf-8') as f:
                models = json.load(f)
            print(f"AI Models: 从缓存获取到 {len(models)} 个模型")
            return models
    except Exception as e:
        print(f"AI Models 获取失败: {e}")

    # 备用数据
    models = [
        {
            'name': 'MiniMax M2.5',
            'provider': 'MiniMax',
            'description': '本周使用量最高，达 2.09T tokens，增速 15%',
            'url': 'https://openrouter.ai/minimax/minimax-m2.5',
            'rank': 1
        },
        {
            'name': 'Claude 3.5 Sonnet',
            'provider': 'Anthropic',
            'description': 'Anthropic 出品的 Claude 系列最新模型，在代码生成和长文本理解方面表现优异',
            'url': 'https://www.anthropic.com',
            'rank': 2
        },
        {
            'name': 'Gemini 2.0 Pro',
            'provider': 'Google',
            'description': 'Google 最强的多模态模型，支持原生音频、视频理解，推理能力大幅提升',
            'url': 'https://gemini.google.com',
            'rank': 3
        },
        {
            'name': 'Llama 3.1 405B',
            'provider': 'Meta',
            'description': 'Meta 开源的超大参数模型，性能接近闭源模型，支持长上下文',
            'url': 'https://ai.meta.com/llama',
            'rank': 4
        },
        {
            'name': 'Mistral Large 2',
            'provider': 'Mistral AI',
            'description': '法国 AI 公司 Mistral 的旗舰模型，在数学和代码方面表现出色',
            'url': 'https://mistral.ai',
            'rank': 5
        },
        {
            'name': 'Qwen 2.5',
            'provider': '阿里云',
            'description': '阿里巴巴开源的千问大模型系列，中文能力突出，生态完善',
            'url': 'https://qwenlm.github.io',
            'rank': 6
        },
        {
            'name': 'DeepSeek V2.5',
            'provider': 'DeepSeek',
            'description': '中国 AI 公司 DeepSeek 出品，性价比极高，代码能力接近 GPT-4',
            'url': 'https://www.deepseek.com',
            'rank': 7
        },
        {
            'name': 'Grok-2',
            'provider': 'xAI',
            'description': '马斯克 xAI 出品的模型，擅长幽默和创意写作，与 X 平台深度集成',
            'url': 'https://x.ai',
            'rank': 8
        },
    ]
    print(f"AI Models: 获取到 {len(models)} 个模型")
    return models


def get_ai_tools():
    """获取热门 AI 工具推荐"""
    tools = [
        {
            'name': 'Cursor',
            'category': '代码编辑器',
            'description': 'AI 驱动的代码编辑器，基于 VS Code，集成 Claude 和 GPT-4，适合快速开发',
            'url': 'https://cursor.sh'
        },
        {
            'name': 'Windsurf',
            'category': '代码编辑器',
            'description': 'Codeium 出品的 AI IDE，Flow Agent 模式可自主完成复杂任务',
            'url': 'https://windsurf.ai'
        },
        {
            'name': 'v0',
            'category': 'UI 生成',
            'description': 'Vercel 出品的 AI UI 工具，通过自然语言生成 React 组件和页面',
            'url': 'https://v0.dev'
        },
        {
            'name': 'bolt.new',
            'category': '全栈开发',
            'description': 'AI 全栈开发平台，一句话生成完整应用，支持部署到 Netlify',
            'url': 'https://bolt.new'
        },
        {
            'name': 'Lovable',
            'category': '全栈开发',
            'description': 'AI 编程助手，特别擅长构建 Web 应用，集成 Supabase',
            'url': 'https://lovable.dev'
        },
        {
            'name': 'Replit Agent',
            'category': '全栈开发',
            'description': 'Replit 的 AI 代理功能，一句话开发完整应用',
            'url': 'https://replit.com'
        },
        {
            'name': 'Perplexity',
            'category': 'AI 搜索',
            'description': 'AI 驱动的搜索引擎，实时获取网上信息，带引用来源',
            'url': 'https://www.perplexity.ai'
        },
        {
            'name': 'Notion AI',
            'category': '笔记/办公',
            'description': 'Notion 集成的 AI 功能，帮你写作、总结、头脑风暴',
            'url': 'https://notion.so/product/ai'
        },
        {
            'name': 'Raycast AI',
            'category': '效率工具',
            'description': 'Mac 效率工具的 AI 扩展，支持 AI 搜索、命令执行',
            'url': 'https://raycast.com'
        },
        {
            'name': 'Gamma',
            'category': 'PPT/演示',
            'description': 'AI PPT 生成工具，一句话生成专业演示文稿',
            'url': 'https://gamma.app'
        },
        {
            'name': 'Runway',
            'category': '视频生成',
            'description': 'AI 视频生成和处理平台，Gen-3 Alpha 视频效果惊人',
            'url': 'https://runwayml.com'
        },
        {
            'name': 'Pika',
            'category': '视频生成',
            'description': 'AI 视频生成工具，支持文本转视频和图片转视频',
            'url': 'https://pika.art'
        },
        {
            'name': 'Midjourney',
            'category': '图像生成',
            'description': '最强 AI 图像生成工具，V6 版本支持文本理解和高清输出',
            'url': 'https://www.midjourney.com'
        },
        {
            'name': 'DALL-E 3',
            'category': '图像生成',
            'description': 'OpenAI 的图像生成模型，集成在 ChatGPT 中使用',
            'url': 'https://openai.com/dall-e-3'
        },
        {
            'name': 'ElevenLabs',
            'category': '语音合成',
            'description': 'AI 语音合成平台，生成的语音非常自然，支持多语言',
            'url': 'https://elevenlabs.io'
        },
        {
            'name': 'HeyGen',
            'category': '数字人',
            'description': 'AI 数字人视频生成，支持多语言配音和虚拟主播',
            'url': 'https://heygen.com'
        },
    ]
    print(f"AI Tools: 获取到 {len(tools)} 个工具")
    return tools


def get_ai_trends():
    """获取 AI 趋势和热点"""
    trends = [
        {
            'title': 'AI Agent 爆发',
            'description': '2025-2026 年是 AI Agent 元年，从 Claude Code 到 Cursor、Windsurf，AI 正在从聊天工具向自主执行任务的助手演进',
            'category': '技术趋势'
        },
        {
            'title': 'Vibe Coding 兴起',
            'description': '无需写代码，通过自然语言描述即可生成完整应用。v0、bolt.new、Lovable 等工具让人人都是开发者',
            'category': '开发范式'
        },
        {
            'title': '多模态成为标配',
            'description': 'GPT-4o、Gemini 2.0 等模型原生支持文本、图像、音频、视频，理解能力大幅提升',
            'category': '模型能力'
        },
        {
            'title': '开源模型崛起',
            'description': 'Llama 3.1、Qwen 2.5、DeepSeek 等开源模型性能逼近闭源，企业可以私有化部署',
            'category': '开源生态'
        },
        {
            'title': 'AI 硬件创新',
            'description': '除了 GPU，Apple Neural Engine、NPU 等专用 AI 芯片让端侧 AI 成为可能',
            'category': '硬件'
        },
        {
            'title': 'AI 搜索重构信息获取',
            'description': 'Perplexity、Arc Search 等 AI 搜索工具正在替代传统搜索引擎',
            'category': '产品形态'
        },
        {
            'title': 'AI 视频生成突破',
            'description': 'Sora、Pika、Runway 等工具让 AI 视频从概念进入实用阶段',
            'category': 'AIGC'
        },
        {
            'title': 'AI 编程助手普及',
            'description': 'GitHub Copilot、Cursor、Codeium 等工具让开发者效率提升 50% 以上',
            'category': '开发工具'
        },
    ]
    print(f"AI Trends: 获取到 {len(trends)} 个趋势")
    return trends


def get_ai_news():
    """获取最新 AI 资讯 - 从缓存读取"""
    try:
        cache_file = Path(__file__).parent / 'ai_news_cache.json'
        if cache_file.exists():
            import json
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            quantum = data.get('quantum', [])
            print(f"AI News: 从缓存获取到 {len(quantum)} 条最新资讯")
            return quantum
    except Exception as e:
        print(f"AI News 获取失败: {e}")
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

def generate_html(data, all_dates, producthunt=None, github_trending=None, ai_models=None, ai_tools=None, ai_trends=None, ai_news=None):
    """生成 HTML 页面"""

    if producthunt is None:
        producthunt = []
    if github_trending is None:
        github_trending = []
    if ai_models is None:
        ai_models = []
    if ai_tools is None:
        ai_tools = []
    if ai_trends is None:
        ai_trends = []
    if ai_news is None:
        ai_news = []

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

    # 生成 AI 模型列表
    def generate_ai_models_list(models):
        html = ''
        for model in models[:8]:
            html += f'''
            <article class="news-item">
                <div class="news-header">
                    <span class="rank-num">#{model.get('rank', '')}</span>
                    <a href="{model.get('url', '#')}" class="news-title" target="_blank" rel="noopener">{model.get('name', 'Unknown')}</a>
                    <span class="news-meta">{model.get('provider', '')}</span>
                </div>
                <p class="news-summary">{model.get('description', '')}</p>
            </article>
            '''
        return html

    # 生成 AI 工具列表
    def generate_ai_tools_list(tools):
        html = ''
        for tool in tools[:16]:
            html += f'''
            <article class="news-item">
                <div class="news-header">
                    <a href="{tool.get('url', '#')}" class="news-title" target="_blank" rel="noopener">{tool.get('name', 'Unknown')}</a>
                    <span class="news-meta tool-category">{tool.get('category', '')}</span>
                </div>
                <p class="news-summary">{tool.get('description', '')}</p>
            </article>
            '''
        return html

    # 生成 AI 趋势列表
    def generate_ai_trends_list(trends):
        html = ''
        for trend in trends:
            html += f'''
            <article class="news-item trend-item">
                <div class="trend-header">
                    <span class="trend-category">{trend.get('category', '')}</span>
                    <span class="trend-title">{trend.get('title', '')}</span>
                </div>
                <p class="news-summary">{trend.get('description', '')}</p>
            </article>
            '''
        return html

    producthunt_html = generate_product_list(producthunt)
    github_trending_html = generate_github_list(github_trending)
    ai_models_html = generate_ai_models_list(ai_models)
    ai_tools_html = generate_ai_tools_list(ai_tools)
    ai_trends_html = generate_ai_trends_list(ai_trends)

    # 生成 AI 新闻列表
    def generate_ai_news_list(news):
        html = ''
        for item in news[:15]:
            html += f'''
            <article class="news-item">
                <div class="news-header">
                    <a href="{item.get('url', '#')}" class="news-title" target="_blank" rel="noopener">{item.get('title', '')}</a>
                    <span class="news-meta">{item.get('source', '')}</span>
                </div>
            </article>
            '''
        return html

    ai_news_html = generate_ai_news_list(ai_news)

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
                <span class="trending-badge gh"><a href="https://github.com/trending" target="_blank" style="color:white;text-decoration:none;">GitHub</a></span>
            </div>
            {github_trending_html}
        </section>
        '''

    # AI Models Section
    ai_models_section = ''
    if ai_models_html:
        ai_models_section = f'''
        <section class="news-section trending-section ai-section">
            <div class="trending-header">
                <span class="trending-name">AI 模型排行</span>
                <span class="trending-badge ai">LLM</span>
            </div>
            {ai_models_html}
        </section>
        '''

    # AI Tools Section
    ai_tools_section = ''
    if ai_tools_html:
        ai_tools_section = f'''
        <section class="news-section trending-section ai-section">
            <div class="trending-header">
                <span class="trending-name">AI 工具推荐</span>
                <span class="trending-badge ai">Tools</span>
            </div>
            {ai_tools_html}
        </section>
        '''

    # AI Trends Section
    ai_trends_section = ''
    if ai_trends_html:
        ai_trends_section = f'''
        <section class="news-section trending-section trends-section">
            <div class="trending-header">
                <span class="trending-name">AI 趋势洞察</span>
                <span class="trending-badge trend">趋势</span>
            </div>
            {ai_trends_html}
        </section>
        '''

    # AI News Section
    ai_news_section = ''
    if ai_news_html:
        ai_news_section = f'''
        <section class="news-section trending-section news-section">
            <div class="trending-header">
                <span class="trending-name">最新 AI 资讯</span>
                <span class="trending-badge news">量子位</span>
            </div>
            {ai_news_html}
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
        {ai_models_section}
        {ai_tools_section}
        {ai_trends_section}
        {ai_news_section}

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

    # 获取 AI 数据
    print("正在获取 AI 模型信息...")
    ai_models = get_ai_models()

    print("正在获取 AI 工具推荐...")
    ai_tools = get_ai_tools()

    print("正在获取 AI 趋势分析...")
    ai_trends = get_ai_trends()

    print("正在获取最新 AI 资讯...")
    ai_news = get_ai_news()

    # 生成每个页面的 HTML
    for md_file in output_dir.glob('*.md'):
        date = md_file.stem
        md_content = md_file.read_text(encoding='utf-8')
        data = parse_markdown(md_content)
        data['date'] = date

        html = generate_html(data, all_dates, producthunt, github_trending, ai_models, ai_tools, ai_trends, ai_news)

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
