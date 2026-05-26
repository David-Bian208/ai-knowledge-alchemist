"""
日报生成模块
每天从精选内容中挑Top15高质量内容，生成结构化日报
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

def generate_daily_report(date_str: str, storage, force: bool = False) -> Dict[str, Any]:
    """
    生成指定日期的日报
    Args:
        date_str: 日期 YYYY-MM-DD
        storage: HotStorage实例
        force: 是否强制重新生成（覆盖已有日报）
    Returns:
        日报数据或错误信息
    """
    if not date_str:
        # 默认生成昨天的日报
        date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 检查是否已存在日报
    if not force:
        existing = storage.query_daily_report(date_str)
        if existing:
            return {
                "code": -1,
                "message": f"{date_str} 的日报已存在",
                "exists": True,
                "data": existing
            }
    
    # 获取当天精选内容（selected=1）
    items = storage.query_selected(
        time_filter="custom",
        custom_start=date_str,
        custom_end=date_str,
        include_unselected=False,
        limit=500
    )
    
    # 只取 selected=1 的内容
    selected_items = [i for i in items if i.get("selected", 0) == 1]
    
    if len(selected_items) < 5:
        return {
            "code": -1,
            "message": f"精选内容不足（{len(selected_items)}条），需要至少5条才能生成日报",
            "count": len(selected_items)
        }
    
    # 按评分排序，取Top15
    selected_items.sort(key=lambda x: x.get("final_score", 0), reverse=True)
    top_items = selected_items[:15]
    
    # 按分类分组
    section_map = {
        "ai-models": {"label": "大模型", "key": "ai-models", "items": []},
        "ai-products": {"label": "应用发布", "key": "ai-products", "items": []},
        "industry": {"label": "行业动态", "key": "industry", "items": []},
        "paper": {"label": "论文研究", "key": "paper", "items": []},
        "tip": {"label": "技巧观点", "key": "tip", "items": []}
    }
    
    for item in top_items:
        cat = item.get("category", "")
        if cat in section_map:
            section_map[cat]["items"].append(item)
        else:
            # 默认归入行业动态
            section_map["industry"]["items"].append(item)
    
    # 过滤掉空分类
    sections = [v for v in section_map.values() if v["items"]]
    
    # 生成AI主编导语
    lead_paragraph = generate_lead_paragraph(top_items)
    
    # 组装日报数据
    report_data = {
        "date": date_str,
        "lead": {
            "leadParagraph": lead_paragraph
        },
        "sections": sections,
        "total": len(top_items)
    }
    
    # 保存到数据库
    storage.save_daily_report(report_data)
    
    return {
        "code": 0,
        "message": "日报生成成功",
        "data": report_data
    }


def generate_lead_paragraph(items: List[Dict[str, Any]]) -> str:
    """
    生成AI主编导语（80-150字）
    概括当天精选内容的核心趋势
    """
    # 先尝试用AI生成
    try:
        from src.llm_client import LLMClient
        from src.config import config
        import os
        
        llm = LLMClient(
            api_key=config.get("llm.api_key") or os.getenv("DEEPSEEK_API_KEY", ""),
            base_url=config.get("llm.base_url", "https://api.deepseek.com"),
            model_map={"cheap": config.get("llm.cheap_model", "deepseek-chat"), "pro": config.get("llm.pro_model", "deepseek-pro")}
        )
        
        # 提取内容信息
        content_info = []
        for item in items[:10]:  # 取前10条给AI
            content_info.append({
                "title": item.get("title", "")[:40],
                "category": item.get("category", ""),
                "score": item.get("final_score", 0),
                "summary": item.get("summary", "")[:80]
            })
        
        # 统计分类
        cat_count = {}
        for item in items:
            cat = item.get("category", "其他")
            cat_count[cat] = cat_count.get(cat, 0) + 1
        
        cat_labels = {
            "ai-models": "大模型",
            "ai-products": "AI应用",
            "industry": "行业动态",
            "paper": "论文研究",
            "tip": "技巧观点"
        }
        top_cat = max(cat_count, key=cat_count.get) if cat_count else "AI"
        top_cat_label = cat_labels.get(top_cat, "AI")
        
        prompt = f"""你是AI行业日报主编，有10年经验，擅长从碎片信息中提炼趋势洞察。

## 今日精选内容（共{len(items)}条）

### 分类分布
{chr(10).join([f"- {cat_labels.get(c, c)}: {n}条" for c, n in sorted(cat_count.items(), key=lambda x: -x[1])])}

### Top内容（按评分排序）
{chr(10).join([f"{i+1}. [{cat_labels.get(c.get('category',''),'')}] {c['title']}" + (f"——{c['summary']}" if c['summary'] else '') for i, c in enumerate(content_info[:8])])}

## 你的任务
写一段主编导语，放在日报最开头，帮读者快速把握今天AI圈发生了什么。

## 写作风格
- 像36氪/晚点LatePost的资深编辑，有洞察力但不装
- 抓住1-2个核心趋势，不要面面俱到
- 可以用"一边...一边..."的对比结构，或者"关键词+解读"的句式
- 口语化但不随便，专业但不学术
- 不要套话开头（"今日AI领域"、"今天AI圈"都不要）
- 不要"值得关注"、"持续升温"这种空话
- 不要列举数据（"X条内容"、"X分"不要出现在导语里）

## 长度
80-120字，一句话或两句话

## 好例子
- 华为突破存储堆叠极限的同时，硅谷投资人预警推理算力即将反超训练——硬件创新和算力结构正在双向改写AI基础设施格局。
- 大厂在核心业务上谨慎改版，创业公司在细分场景疯狂试水——AI落地进入深水区，速度比方向更重要。

直接输出导语，不要标题，不要解释：
"""
        
        result = llm.chat(
            "只输出导语内容，不要任何其他解释，80-120字。",
            prompt,
            model="pro"
        ).strip()
        
        # 确保字数合理
        if 50 <= len(result) <= 150:
            return result
        
        # 如果AI生成不符合要求，用模板
    except Exception as e:
        print(f"[日报导语] AI生成失败，使用模板: {e}")
    
    # 模板生成（fallback）
    cat_count = {}
    for item in items:
        cat = item.get("category", "其他")
        cat_count[cat] = cat_count.get(cat, 0) + 1
    
    top_cat = max(cat_count, key=cat_count.get) if cat_count else "AI"
    cat_labels = {
        "ai-models": "大模型",
        "ai-products": "AI应用",
        "industry": "行业动态",
        "paper": "论文研究",
        "tip": "技巧观点"
    }
    top_cat_label = cat_labels.get(top_cat, "AI")
    
    items_sorted = sorted(items, key=lambda x: x.get("final_score", 0), reverse=True)
    top_title = items_sorted[0].get("title", "")[:30] if items_sorted else ""
    avg_score = sum(i.get("final_score", 0) for i in items) / len(items) if items else 0
    
    lead = f"今日AI领域共收录{len(items)}条精选内容，{top_cat_label}方向最为活跃。"
    if top_title:
        lead += f"《{top_title}》获最高评分（{int(items_sorted[0].get('final_score', 0))}分）。"
    lead += f"整体内容质量评分均值{int(avg_score)}分，行业持续保持高热度。"
    
    if len(lead) > 100:
        lead = lead[:99] + "。"
    
    return lead


def check_daily_report_ready(date_str: str, storage) -> Dict[str, Any]:
    """
    检查指定日期是否可以生成日报
    Returns:
        {"ready": bool, "count": int, "message": str}
    """
    if not date_str:
        date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    items = storage.query_selected(
        time_filter="custom",
        custom_start=date_str,
        custom_end=date_str,
        include_unselected=False,
        limit=500
    )
    
    selected_items = [i for i in items if i.get("selected", 0) == 1]
    count = len(selected_items)
    
    return {
        "ready": count >= 10,
        "count": count,
        "message": f"精选内容{count}条" + ("，可以生成日报" if count >= 10 else "，不足10条无法生成")
    }
