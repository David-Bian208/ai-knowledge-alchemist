"""
AI-Pulse 精选时间线前端 - 完全对齐AIHOT风格
左右布局 + 深色/浅色切换 + 时间轴样式
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import gradio as gr
import json
from datetime import datetime
from typing import Dict
from src.source_manager import SourceManager
from src.processor import HotPipeline
from src.storage import HotStorage

source_manager = SourceManager()
pipeline = HotPipeline()
storage = HotStorage()

CATEGORY_MAP = {"all": "全部", "ai-models": "模型", "ai-products": "产品", "industry": "行业", "paper": "论文", "tip": "技巧"}
TIER_MAP = {"T1": "T1 核心", "T1.5": "T1.5 优质", "T2": "T2 一般"}

def get_score_color(score):
    if score >= 150: return "#EF4444"
    if score >= 130: return "#F59E0B"
    if score >= 100: return "#3B82F6"
    if score >= 70: return "#10B981"
    return "#9CA3AF"

def get_tier_color(tier):
    return {"T1": "#EF4444", "T1.5": "#F59E0B", "T2": "#6B7280"}.get(tier, "#9CA3AF")

def format_aihot_time(date_str):
    try:
        return datetime.fromisoformat(date_str[:19]).strftime("%H:%M")
    except:
        return date_str.split(" ")[-1][:5] if " " in date_str else date_str[:5]

def format_ingest_time(date_str):
    try:
        return datetime.fromisoformat(date_str[:19]).strftime("%m月%d日 %H:%M")
    except:
        return date_str[:16] if date_str else ""

def render_card(item):
    score = item.get("final_score", 0)
    score_color = get_score_color(score)
    tier = item.get("source_tier", "T2")
    tier_color = get_tier_color(tier)
    tier_label = TIER_MAP.get(tier, tier)
    publish_date = item.get("publish_date", "")
    publish_time_str = format_aihot_time(publish_date)
    ingested_at = item.get("ingested_at", "")
    ingest_time_str = format_ingest_time(ingested_at)
    
    tags_raw = item.get("tags", "[]")
    try:
        tags = json.loads(tags_raw) if isinstance(tags_raw, str) else (tags_raw or [])
    except:
        tags = []
    tags_html = ""
    if tags:
        for tag in tags[:4]:
            tags_html += f'<span style="background:rgba(255,255,255,0.1);color:rgba(255,255,255,0.7);padding:2px 12px;border-radius:12px;font-size:12px;margin-right:8px;margin-top:8px;display:inline-block;">{tag}</span>'
    
    recommendation = item.get("recommendation_reason", "")
    rec_html = ""
    if recommendation:
        rec_html = f'<div style="background:rgba(16,185,129,0.1);border-radius:8px;padding:8px 12px;margin-top:12px;"><span style="color:#6EE7B7;font-size:13px;line-height:1.6;"><strong style="color:#6EE7B7;">推荐理由：</strong>{recommendation}</span></div>'
    
    content_type = item.get("content_type", "")
    content_type_html = f'<span style="background:rgba(99,102,241,0.2);color:#818CF8;padding:2px 8px;border-radius:10px;font-size:11px;margin-right:8px;">{content_type}</span>' if content_type else ""
    
    category = item.get("category", "")
    category_label = CATEGORY_MAP.get(category, category) if category else ""
    category_html = f'<span style="background:rgba(255,255,255,0.08);color:rgba(255,255,255,0.5);padding:2px 8px;border-radius:10px;font-size:11px;margin-right:8px;">{category_label}</span>' if category_label else ""
    
    summary = item.get("summary", "暂无摘要")
    if len(summary) > 250: summary = summary[:250] + "..."
    
    source = item.get("source", "")
    source_html = f'<span style="color:rgba(255,255,255,0.4);font-size:12px;margin-right:8px;">{source}</span>' if source else ""
    
    url = item.get("url", "#")
    
    return f'''<div style="display:flex;gap:16px;margin-bottom:16px;">
    <div style="min-width:70px;text-align:right;padding-top:8px;">
        <div style="font-size:24px;font-weight:700;color:rgba(255,255,255,0.9);line-height:1;margin-bottom:4px;">{publish_time_str}</div>
        <div style="display:flex;align-items:center;justify-content:flex-end;gap:6px;">
            <div style="width:8px;height:8px;background:#10B981;border-radius:50%;"></div>
            <div style="font-size:12px;color:rgba(255,255,255,0.4);">{ingest_time_str}</div>
        </div>
    </div>
    <div style="flex:1;background:rgba(30,41,59,0.6);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:20px 24px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
            <div style="display:flex;align-items:center;gap:8px;">{source_html}{content_type_html}{category_html}</div>
            <div style="text-align:right;"><div style="font-size:20px;font-weight:700;color:{score_color};">{score:.0f}</div><div style="font-size:11px;color:rgba(255,255,255,0.4);">综合评分</div></div>
        </div>
        <h3 style="margin:0 0 12px 0;font-size:18px;font-weight:600;color:rgba(255,255,255,0.95);line-height:1.5;">
            <a href="{url}" target="_blank" style="color:rgba(255,255,255,0.95);text-decoration:none;">{item.get('title', '无标题')}</a>
        </h3>
        <p style="color:rgba(255,255,255,0.6);font-size:14px;margin:0 0 12px 0;line-height:1.8;">{summary}</p>
        {tags_html}{rec_html}
    </div>
</div>'''

def load_selected_items(time_filter="today", tier_filter="all", category_filter="all", search_query=""):
    cat = None if category_filter == "all" else category_filter
    items = storage.query_selected(time_filter=time_filter, category=cat)
    if tier_filter != "all":
        items = [i for i in items if i.get("source_tier") == tier_filter]
    if search_query:
        q_lower = search_query.lower()
        items = [i for i in items if q_lower in str(i.get("title","")).lower() or q_lower in str(i.get("summary","")).lower() or q_lower in str(i.get("source","")).lower()]
    if not items:
        return '<div style="text-align:center;padding:80px;color:rgba(255,255,255,0.3);"><p style="font-size:18px;color:rgba(255,255,255,0.5);">暂无精选内容</p></div>'
    date_groups = {}
    for item in items:
        pub_date = item.get("publish_date", "")
        date_key = "今天"
        if pub_date:
            try:
                dt = datetime.fromisoformat(pub_date[:19])
                delta = (datetime.now() - dt).days
                if delta == 0: date_key = "今天"
                elif delta == 1: date_key = "昨天"
                else: date_key = dt.strftime("%Y年%m月%d日")
            except: date_key = "其他"
        date_groups.setdefault(date_key, []).append(item)
    html = ""
    for date_key, day_items in date_groups.items():
        html += f'<div style="margin-bottom:20px;padding:12px 0 0 86px;"><div style="font-size:16px;font-weight:600;color:rgba(255,255,255,0.6);margin-bottom:16px;">{date_key}</div></div>'
        for item in day_items:
            html += render_card(item)
    return html

CSS = """
body { background:linear-gradient(135deg,#0a0f1e 0%,#0f172a 50%,#0a0f1e 100%) !important; color:rgba(255,255,255,0.9) !important; font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif !important; margin:0 !important; padding:0 !important; }
.light-theme body { background:linear-gradient(135deg,#f8fafc 0%,#e2e8f0 50%,#f8fafc 100%) !important; color:#1e293b !important; }
.gradio-container { max-width:none !important; margin:0 !important; padding:0 !important; }

/* Hide Gradio's default tab bar completely */
.tab-nav { display:none !important; }
.tabitem { background:none !important; border:none !important; padding:0 !important; margin:0 !important; }

/* Wrap Gradio content in the right-content area */
main > div > div:first-child { display:flex !important; min-height:100vh !important; }
main > div > div:first-child > div:first-child { position:fixed !important; left:0 !important; top:0 !important; bottom:0 !important; width:240px !important; z-index:100 !important; }
main > div > div:first-child > div:last-child { margin-left:240px !important; padding:32px 40px !important; min-height:100vh !important; width:calc(100vw - 240px) !important; }

/* Left navigation */
.left-nav { position:fixed !important; left:0 !important; top:0 !important; bottom:0 !important; width:240px !important; background:rgba(15,23,42,0.95) !important; border-right:1px solid rgba(255,255,255,0.08) !important; padding:24px 0 !important; z-index:100 !important; overflow-y:auto !important; }
.light-theme .left-nav { background:rgba(248,250,252,0.95) !important; border-right:1px solid rgba(0,0,0,0.08) !important; }
.logo-box { padding:0 20px 32px !important; text-align:center !important; }
.logo-text { font-size:28px !important; font-weight:700 !important; background:linear-gradient(135deg,#60a5fa,#8b5cf6) !important; -webkit-background-clip:text !important; -webkit-text-fill-color:transparent !important; background-clip:text !important; margin-bottom:4px !important; }
.logo-subtitle { font-size:11px !important; color:rgba(255,255,255,0.5) !important; }
.light-theme .logo-subtitle { color:rgba(0,0,0,0.5) !important; }
.nav-item { padding:12px 24px !important; margin:4px 12px !important; border-radius:12px !important; cursor:pointer !important; transition:all 0.2s !important; display:flex !important; align-items:center !important; gap:12px !important; font-size:14px !important; font-weight:500 !important; color:rgba(255,255,255,0.7) !important; }
.light-theme .nav-item { color:rgba(0,0,0,0.7) !important; }
.nav-item:hover { background:rgba(99,102,241,0.1) !important; color:#60a5fa !important; }
.nav-item.active { background:rgba(99,102,241,0.15) !important; color:#60a5fa !important; border-left:3px solid #60a5fa !important; }

/* Right content area for Gradio components */
.right-content { margin-left:240px !important; padding:32px 40px !important; min-height:100vh !important; }
.page-title { font-size:32px !important; font-weight:700 !important; margin:0 0 8px 0 !important; }
.page-subtitle { font-size:14px !important; color:rgba(255,255,255,0.5) !important; margin:0 0 24px 0 !important; }
.light-theme .page-subtitle { color:rgba(0,0,0,0.5) !important; }
.filter-section { background:rgba(30,41,59,0.6) !important; border:1px solid rgba(255,255,255,0.08) !important; border-radius:16px !important; padding:24px !important; margin-bottom:24px !important; }
.light-theme .filter-section { background:rgba(248,250,252,0.6) !important; border:1px solid rgba(0,0,0,0.08) !important; }
.refresh-btn { background:linear-gradient(135deg,#6366F1,#8B5CF6) !important; color:white !important; border:none !important; border-radius:12px !important; padding:10px 32px !important; font-size:14px !important; font-weight:600 !important; cursor:pointer !important; margin-top:16px !important; }
.theme-toggle { position:fixed !important; bottom:24px !important; right:24px !important; background:linear-gradient(135deg,#6366F1,#8B5CF6) !important; color:white !important; border:none !important; border-radius:50% !important; width:56px !important; height:56px !important; font-size:24px !important; cursor:pointer !important; box-shadow:0 4px 12px rgba(0,0,0,0.2) !important; z-index:1000 !important; transition:all 0.3s !important; }
.theme-toggle:hover { transform:scale(1.1) !important; }
footer { display:none !important; }
input, textarea, select { background:rgba(15,23,42,0.6) !important; border:1px solid rgba(255,255,255,0.1) !important; border-radius:12px !important; color:rgba(255,255,255,0.9) !important; }
.light-theme input, .light-theme textarea, .light-theme select { background:rgba(248,250,252,0.6) !important; border:1px solid rgba(0,0,0,0.1) !important; color:#1e293b !important; }
"""

# Custom navigation HTML - placed before the Tabs
LEFT_NAV_HTML = """
<div class="left-nav">
    <div class="logo-box"><div class="logo-text">AI-Pulse</div><div class="logo-subtitle">精选AI动态</div></div>
    <div class="nav-item active" data-tab="0" onclick="switchTab(0)">📰 精选时间线</div>
    <div class="nav-item" data-tab="1" onclick="switchTab(1)">🔗 URL处理</div>
    <div class="nav-item" data-tab="2" onclick="switchTab(2)">📡 信源管理</div>
    <div class="nav-item" data-tab="3" onclick="switchTab(3)">🔌 Agent接入</div>
</div>
<script>
function switchTab(index) {
    var tabButtons = document.querySelectorAll('.tab-nav button');
    if (tabButtons[index]) {
        tabButtons[index].click();
    }
    document.querySelectorAll('.nav-item').forEach(function(n){n.classList.remove('active')});
    document.querySelector('.nav-item[data-tab="'+index+'"]').classList.add('active');
}
function toggleTheme(){document.body.classList.toggle('light-theme');localStorage.setItem('ai-pulse-theme',document.body.classList.contains('light-theme')?'light':'dark')}
document.addEventListener('DOMContentLoaded',function(){if(localStorage.getItem('ai-pulse-theme')==='light'){document.body.classList.add('light-theme')}});
</script>
<button class="theme-toggle" onclick="toggleTheme()">🌓</button>
"""

def build_page_header(title, subtitle):
    return f'<h1 class="page-title">{title}</h1><p class="page-subtitle">{subtitle}</p>'

with gr.Blocks(title="AI-Pulse 精选时间线", css=CSS) as app:
    # Custom left navigation
    gr.HTML(LEFT_NAV_HTML)
    
    # Wrap all tabs content in right-content container
    with gr.Column(elem_classes="right-content"):
        with gr.Tabs():
            # ===== Tab 0: Timeline =====
            with gr.Tab("精选时间线"):
                timeline_header = gr.HTML(build_page_header("精选", "AI自动挑选的高价值内容"))
                
                with gr.Column(elem_classes="filter-section"):
                    search_input = gr.Textbox(placeholder="搜索标题、摘要、信源...", label="🔍 搜索")
                    with gr.Row():
                        category_filter = gr.Radio(choices=[("全部","all"),("模型","ai-models"),("产品","ai-products"),("行业","industry"),("论文","paper"),("技巧","tip")], value="all", label="分类")
                        time_filter = gr.Radio(choices=[("今天","today"),("昨天","yesterday"),("近一周","week"),("全部","all")], value="today", label="时间范围")
                        tier_filter = gr.Radio(choices=[("全部","all"),("T1核心","T1"),("T1.5优质","T1.5"),("T2一般","T2")], value="all", label="信源等级")
                    refresh_btn = gr.Button("🔄 刷新列表", elem_classes="refresh-btn")
                items_html = gr.HTML(value=load_selected_items("today"))
                
                def update_list(tf, tdf, cf, sq):
                    return load_selected_items(tf, tdf, cf, sq)
                
                category_filter.change(update_list, inputs=[time_filter, tier_filter, category_filter, search_input], outputs=[items_html])
                time_filter.change(update_list, inputs=[time_filter, tier_filter, category_filter, search_input], outputs=[items_html])
                tier_filter.change(update_list, inputs=[time_filter, tier_filter, category_filter, search_input], outputs=[items_html])
                search_input.change(update_list, inputs=[time_filter, tier_filter, category_filter, search_input], outputs=[items_html])
                refresh_btn.click(update_list, inputs=[time_filter, tier_filter, category_filter, search_input], outputs=[items_html])
            
            # ===== Tab 1: URL Processing =====
            with gr.Tab("URL处理"):
                url_header = gr.HTML(build_page_header("URL处理", "输入网页URL自动分析评分入库"))
                
                with gr.Column(elem_classes="filter-section"):
                    with gr.Row():
                        url_input = gr.Textbox(label="URL", placeholder="https://example.com/article", lines=2, scale=3)
                        source_tier = gr.Radio(choices=["T1","T1.5","T2"], value="T2", label="信源等级", scale=1)
                    process_btn = gr.Button("🚀 处理并入库", variant="primary", size="lg")
                process_output = gr.HTML()
                
                def process_url_fn(url, st):
                    if not url or not url.startswith("http"): return "❌ 请输入有效的URL"
                    try:
                        selected, result = pipeline.process_url(url, st)
                        score = result.get("final_score", 0)
                        if selected:
                            return f'<div style="padding:20px;border-radius:16px;background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);"><h3 style="color:#6EE7B7;">✅ 已入选精选！</h3><p><strong>标题：</strong>{result.get("title","")}</p><p><strong>得分：</strong><span style="font-size:24px;font-weight:700;color:#6EE7B7;">{score:.0f}</span></p></div>'
                        else:
                            return f'<div style="padding:20px;border-radius:16px;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);"><h3 style="color:#F87171;">未入选精选</h3><p><strong>得分：</strong>{score:.0f}</p></div>'
                    except Exception as e:
                        return f'<div style="padding:20px;border-radius:16px;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);">❌ 处理失败: {str(e)}</div>'
                
                process_btn.click(fn=process_url_fn, inputs=[url_input, source_tier], outputs=[process_output])
            
            # ===== Tab 2: Source Management =====
            with gr.Tab("信源管理"):
                sources_header = gr.HTML(build_page_header("信源管理", "管理白名单信源分级"))
                
                with gr.Accordion("➕ 添加新信源", open=True):
                    with gr.Column(elem_classes="filter-section"):
                        with gr.Row():
                            add_name = gr.Textbox(label="信源名称", placeholder="如：OpenAI官方博客", scale=2)
                            add_url = gr.Textbox(label="URL", placeholder="https://openai.com/blog", scale=3)
                        with gr.Row():
                            add_tier = gr.Dropdown(choices=["T1","T1.5","T2"], value="T2", label="信源等级")
                            add_type = gr.Dropdown(choices=["web","rss","api","wechat","x"], value="web", label="类型")
                            add_interval = gr.Number(label="抓取间隔(分钟)", value=60, minimum=1, maximum=1440)
                        with gr.Row():
                            add_description = gr.Textbox(label="信源描述", lines=2, scale=2)
                            add_tags = gr.Textbox(label="标签（逗号分隔）", scale=1)
                        add_btn = gr.Button("添加信源", variant="primary")
                add_result = gr.Textbox(label="添加结果", interactive=False)
                
                with gr.Column(elem_classes="filter-section"):
                    tier_filter_sources = gr.Radio(choices=["all","T1","T1.5","T2"], value="all", label="按等级筛选")
                    with gr.Row():
                        refresh_sources_btn = gr.Button("🔄 刷新信源列表")
                        delete_unhealthy_btn = gr.Button("🗑️ 一键删除所有失效信源", variant="stop")
                sources_cards = gr.HTML(value="")
                delete_result = gr.Textbox(label="删除结果", interactive=False)
                
                def add_source_fn(name, url, tier, stype, interval, desc="", tags=""):
                    try:
                        if not name or not url: return "❌ 请填写完整的名称和URL"
                        tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
                        source_manager.add_source(name, url, tier, stype, True, interval, desc, tags_list)
                        return f"✅ 添加成功：{name}"
                    except Exception as e:
                        return f"❌ 添加失败：{str(e)}"
                
                def delete_source_fn(source_id):
                    """删除单个信源"""
                    try:
                        success = source_manager.delete_source(source_id)
                        if success:
                            return f"✅ 已删除信源 {source_id}", True
                        else:
                            return f"❌ 信源 {source_id} 不存在", False
                    except Exception as e:
                        return f"❌ 删除失败：{str(e)}", False
                
                def delete_unhealthy_fn():
                    """批量删除失效信源"""
                    try:
                        from src.source_health import SourceHealthChecker
                        checker = SourceHealthChecker()
                        unhealthy = checker.get_unhealthy_sources()
                        unhealthy_ids = [s["source_id"] for s in unhealthy]
                        if not unhealthy_ids:
                            return "✅ 没有失效信源需要删除"
                        deleted = source_manager.delete_unhealthy_sources(unhealthy_ids)
                        return f"✅ 已删除 {deleted} 个失效信源"
                    except Exception as e:
                        return f"❌ 删除失败：{str(e)}"
                
                def load_sources_cards_fn(tf="all"):
                    sources = source_manager.get_all_enabled_sources()
                    if tf != "all": sources = [s for s in sources if s.tier == tf]
                    tier_order = {"T1":0,"T1.5":1,"T2":2}
                    sources.sort(key=lambda s: tier_order.get(s.tier, 3))
                    
                    # 获取健康状态
                    from src.source_health import SourceHealthChecker
                    health_checker = SourceHealthChecker()
                    health_map = {}
                    for s in sources:
                        health = health_checker.get_source_health(s.id)
                        if health:
                            health_map[s.id] = health
                    
                    html = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(350px,1fr));gap:16px;margin-top:16px;">'
                    for idx, s in enumerate(sources, 1):
                        tc = get_tier_color(s.tier)
                        th = ""
                        if s.tags:
                            for tag in s.tags[:3]:
                                th += f'<span style="background:rgba(255,255,255,0.1);color:rgba(255,255,255,0.7);padding:2px 10px;border-radius:10px;font-size:12px;margin-right:6px;">{tag}</span>'
                        
                        # 健康状态标记
                        health = health_map.get(s.id)
                        health_badge = ""
                        card_style = ""
                        delete_btn_html = ""
                        
                        if health and not health.get('is_healthy', True):
                            # 失效信源
                            consecutive = health.get('consecutive_failures', 0)
                            last_error = health.get('last_error', '')[:50]
                            health_badge = f'''<span style="background:#EF4444;color:white;padding:2px 8px;border-radius:10px;font-size:11px;margin-left:8px;">已失效</span>
                                               <span style="color:rgba(255,255,255,0.4);font-size:11px;" title="{last_error}">连续失败{consecutive}次</span>'''
                            card_style = "opacity:0.6; border:1px solid rgba(239,68,68,0.3);"
                            delete_btn_html = f'<button onclick="deleteSource(\'{s.id}\')" style="background:#EF4444;color:white;border:none;border-radius:8px;padding:4px 12px;cursor:pointer;font-size:12px;">🗑️ 删除</button>'
                        
                        html += f'''<div style="background:rgba(30,41,59,0.6);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:20px;{card_style}">
                            <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
                                <div style="display:flex;align-items:center;gap:8px;">
                                    <span style="background:rgba(255,255,255,0.08);color:rgba(255,255,255,0.5);padding:2px 10px;border-radius:10px;font-size:12px;">N°{idx:03d}</span>
                                    <span style="background:{tc};color:white;padding:2px 8px;border-radius:10px;font-size:11px;">{s.tier}</span>
                                    {health_badge}
                                </div>
                                <div>{delete_btn_html}</div>
                            </div>
                            <h4 style="margin:0 0 4px 0;font-size:15px;font-weight:600;">{s.name}</h4>
                            <a href="{s.url}" target="_blank" style="color:#818CF8;font-size:12px;">{s.url[:50]}...</a>
                            <p style="color:rgba(255,255,255,0.5);font-size:13px;margin:8px 0 0;line-height:1.5;">{s.description or ''}</p>
                            <div style="margin-top:10px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;"><div>{th}</div><span style="color:rgba(255,255,255,0.3);font-size:11px;">{s.type}</span></div>
                        </div>'''
                    html += '</div>'
                    
                    # 添加删除脚本
                    html += '''
                    <script>
                    function deleteSource(sourceId) {
                        if (confirm('确定要删除这个信源吗？')) {
                            fetch('/api/v1/sources/' + sourceId, {method: 'DELETE'})
                                .then(r => r.json())
                                .then(data => {
                                    if (data.code === 0) {
                                        alert('已删除');
                                        location.reload();
                                    } else {
                                        alert('删除失败: ' + data.msg);
                                    }
                                })
                                .catch(e => alert('删除失败: ' + e));
                        }
                    }
                    </script>
                    '''
                    return html
                
                add_btn.click(fn=add_source_fn, inputs=[add_name, add_url, add_tier, add_type, add_interval, add_description, add_tags], outputs=[add_result])
                tier_filter_sources.change(load_sources_cards_fn, inputs=[tier_filter_sources], outputs=[sources_cards])
                refresh_sources_btn.click(load_sources_cards_fn, inputs=[tier_filter_sources], outputs=[sources_cards])
                delete_unhealthy_btn.click(fn=delete_unhealthy_fn, outputs=[delete_result])
                delete_unhealthy_btn.click(fn=load_sources_cards_fn, inputs=[tier_filter_sources], outputs=[sources_cards])
                app.load(fn=load_sources_cards_fn, inputs=[tier_filter_sources], outputs=[sources_cards])
            
            # ===== Tab 3: Agent Integration =====
            with gr.Tab("Agent接入"):
                agent_header = gr.HTML(build_page_header("Agent接入", "把AI-Pulse接进你的工作流"))
                
                with gr.Column(elem_classes="filter-section"):
                    gr.Markdown("### 📡 REST API")
                    gr.Markdown('```http\nGET /api/v1/items?mode=selected&limit=50\n```')
                    test_mode = gr.Radio(choices=["selected","all"], value="selected", label="模式")
                    test_limit = gr.Number(value=5, label="返回数量", minimum=1, maximum=100)
                    test_q = gr.Textbox(label="关键词搜索（可选）", placeholder="如：OpenAI")
                    test_api_btn = gr.Button("🚀 测试API")
                test_api_result = gr.Textbox(label="API响应", interactive=False, lines=10)
                
                def test_api_fn(mode, limit, q):
                    from api import get_items
                    result = get_items(mode=mode, limit=limit, q=q if q else None)
                    return json.dumps(result, ensure_ascii=False, indent=2)
                
                test_api_btn.click(fn=test_api_fn, inputs=[test_mode, test_limit, test_q], outputs=[test_api_result])

def init_scheduler():
    try:
        from src.scheduler import start_scheduler
        start_scheduler(storage=storage)
        print("✅ 日报定时任务已启动")
    except Exception as e:
        print(f"⚠️ 定时任务启动失败: {e}")

if __name__ == "__main__":
    init_scheduler()
    app.launch(server_name="0.0.0.0", server_port=8889, share=False)
