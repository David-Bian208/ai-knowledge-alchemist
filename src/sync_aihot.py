#!/usr/bin/env python3
"""
同步AI HOT公开API内容到本地数据库
策略：
1. 原始URL可访问 → 直接抓取全文
2. 原始URL无法访问 → 用标题在国内媒体源（IT之家/量子位等）搜索匹配文章
3. 国内源也找不到 → 用AI HOT摘要作为后备内容
"""
import os
import json
import time
import requests
from datetime import datetime, timezone
from src.storage import HotStorage
from src.llm_client import LLMClient
from src.config import config
from src.crawler import WebCrawler
from src.domestic_fetcher import fetch_domestic_content
from src.dedup import DeduplicationService

# AI HOT API配置
BASE_URL = "https://aihot.virxact.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 aihot-skill/0.2.0"
}
LIMIT = 50  # 每次拉50条（100条API常返回403）

# 必须跳过的域名（反爬严重或无法抓取正文）
SKIP_DOMAINS = ["x.com", "twitter.com", "weibo.com", "bsky.app", "threads.net"]

# 国内可访问域名（优先抓取，成功率更高）
DOMESTIC_DOMAINS = ["36kr.com", "ithome.com", "qbitai.com", "tmtpost.com", "geekpark.net",
                    "sohu.com", "163.com", "baijiahao.baidu.com", "mp.weixin.qq.com",
                    "zhihu.com", "jianshu.com", "csdn.net", "oschina.net", "segmentfault.com",
                    "infoq.cn", "jqr.com", "aiqiyi.com"]

# 高成功率域名（优先抓取）
HIGH_SUCCESS_DOMAINS = ["huggingface.co", "github.com", "openai.com", "blog.google",
                        "anthropic.com", "medium.com", "arxiv.org"]

def _is_domestic(url):
    """判断是否为国内可访问域名"""
    return any(d in url.lower() for d in DOMESTIC_DOMAINS)

def _is_high_success(url):
    """判断是否为高成功率域名"""
    return any(d in url.lower() for d in HIGH_SUCCESS_DOMAINS)

def sync_items(mode="selected", category=None, max_retries=3):
    """同步AI HOT条目到本地数据库"""
    storage = HotStorage()
    params = {"mode": mode, "take": LIMIT}
    if category:
        params["category"] = category
    
    print(f"同步AI HOT {mode} 条目，分类: {category or '全部'}")
    crawler = WebCrawler(use_gallery_dl=True, use_media_crawler=True)
    
    # 初始化去重服务
    dedup_service = DeduplicationService()
    url_count = dedup_service.load_existing_urls(storage)
    vec_count = dedup_service.load_existing_vectors(storage)
    print(f"去重服务初始化完成: 已加载{url_count}条URL，{vec_count}条内容向量")
    
    # API重试机制（应对403限流）
    data = None
    for attempt in range(max_retries):
        try:
            resp = requests.get(f"{BASE_URL}/api/public/items", params=params, headers=HEADERS, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                break
            elif resp.status_code == 403:
                wait = (attempt + 1) * 5
                print(f"  API返回403，等待{wait}秒后重试 ({attempt+1}/{max_retries})")
                time.sleep(wait)
            else:
                resp.raise_for_status()
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  API请求失败: {e}，重试 ({attempt+1}/{max_retries})")
                time.sleep(3)
    
    if not data:
        print(f"同步失败: API请求{max_retries}次后仍未成功")
        return 0
    
    items = data.get("items", [])
    print(f"拉取到 {len(items)} 条内容")
    
    # 按优先级排序：国内 > 高成功率 > 其他 > 跳过域名
    def priority_key(item):
        url = item.get("url", "").lower()
        if any(d in url for d in SKIP_DOMAINS):
            return 3
        if _is_domestic(url):
            return 0
        if _is_high_success(url):
            return 1
        return 2
    
    items.sort(key=priority_key)
    
    saved = 0
    skipped = 0
    skipped_domain = 0
    crawl_success = 0
    crawl_failed = 0
    domestic_success = 0
    
    for item in items:
        url = item.get("url", "")
        
        # 跳过反爬严重的域名
        if any(d in url.lower() for d in SKIP_DOMAINS):
            skipped_domain += 1
            # 检查是否已存在，不存在也要记录（用AI HOT摘要作为内容）
            conn = storage._get_conn()
            c = conn.cursor()
            c.execute("SELECT id FROM selected_items WHERE url = ?", (url,))
            if not c.fetchone():
                # 转换时间
                published_at = item.get("publishedAt", "")
                if published_at:
                    try:
                        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                        publish_date = dt.strftime("%Y-%m-%dT%H:%M:%S.%f")
                    except:
                        publish_date = published_at
                else:
                    publish_date = datetime.now().isoformat()
                
                base_score = item.get("final_score") or item.get("score", 85)
                final_score = min(base_score, 100)
                
                tier_map = {"T1": "T1", "T1.5": "T2", "T2": "T3"}
                our_tier = tier_map.get(item.get("source_tier") or item.get("tier", "T1.5"), "T2")
                
                # 用AI HOT摘要作为内容
                summary_content = f"# {item['title']}\n\n> {item.get('summary', '')}\n\n来源: {item.get('source', '')}"
                
                try:
                    c.execute("""
                    INSERT INTO selected_items (
                        url, title, source, source_tier, category, publish_date,
                        summary, final_score, selected, created_at, source_from,
                        content, full_content
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        url, item["title"], item["source"], our_tier,
                        item.get("category", "industry"), publish_date,
                        item.get("summary", ""), final_score,
                        1 if mode == "selected" else 0,
                        datetime.now().isoformat(), "aihot",
                        summary_content, summary_content
                    ))
                    conn.commit()
                    saved += 1
                    print(f"  跳过域名(摘要入库): {item['title'][:30]}...")
                except Exception as e:
                    pass
            conn.close()
            continue
        
        # 正常URL：检查是否已存在
        conn = storage._get_conn()
        c = conn.cursor()
        c.execute("SELECT id FROM selected_items WHERE url = ?", (url,))
        exists = c.fetchone()
        
        if exists:
            skipped += 1
            conn.close()
            continue
        
        # 语义去重检查
        title = item.get("title", "")
        summary = item.get("summary", "")
        duplicate_check = dedup_service.check_semantic_duplicate(
            title=title,
            content=summary,
            score=final_score
        )
        
        if duplicate_check["is_duplicate"]:
            dup_info = duplicate_check["duplicate_info"]
            # 重复内容处理：保留最高分版本
            if final_score > dup_info["score"]:
                # 当前内容分数更高，更新已有内容
                print(f"  语义重复(当前分更高，更新): 当前分{final_score}，已有分{dup_info['score']}，相似度{dup_info['similarity']:.2f}")
                # 先完成抓取，再更新已有内容
                update_mode = True
                existing_id = dup_info["id"]
            else:
                # 已有内容分数更高，跳过当前内容
                skipped += 1
                print(f"  语义重复(已有分更高，跳过): 当前分{final_score}，已有分{dup_info['score']}，相似度{dup_info['similarity']:.2f}")
                conn.close()
                continue
        else:
            update_mode = False
            existing_id = None
        
        # 转换时间格式
        published_at = item.get("publishedAt")
        if published_at:
            try:
                dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                publish_date = dt.strftime("%Y-%m-%dT%H:%M:%S.%f")
            except:
                publish_date = published_at
        else:
            publish_date = datetime.now().isoformat()
        
        # 差异化评分
        base_score = item.get("final_score") or item.get("score", 0)
        if base_score > 0:
            final_score = min(base_score, 100)
        else:
            try:
                dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                dt_naive = dt.astimezone(timezone.utc).replace(tzinfo=None)
                now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
                days_ago = (now_naive - dt_naive).days
                hours_ago = (now_naive - dt_naive).seconds // 3600
                if days_ago < 0:
                    time_score = 100
                elif days_ago == 0:
                    time_score = 100 - hours_ago * 0.4
                elif days_ago < 7:
                    time_score = 90 - (days_ago - 1) * 3
                else:
                    time_score = 70 + min(10, 10 - days_ago//7)
                source_bonus = 5
                final_score = max(65, min(100, int(time_score + source_bonus)))
            except Exception as e:
                final_score = 85
        
        tier_map = {"T1": "T1", "T1.5": "T2", "T2": "T3"}
        aihot_tier = item.get("source_tier") or item.get("tier", "T1.5")
        our_tier = tier_map.get(aihot_tier, "T2")
        
        # 抓取正文（三级策略）
        content = ""
        crawl_ok = False
        content_source = ""
        
        # 策略1：直接抓取原始URL
        if not _is_domestic(url) and not _is_high_success(url):
            # 国外非高成功率站点，跳过直接抓取，优先尝试国内源
            print(f"  跳过原始URL，尝试国内源搜索: {url[:50]}...")
        else:
            try:
                crawl_result = crawler.fetch(url)
                if crawl_result.get("success"):
                    content = crawl_result.get("markdown", "")
                    if len(content) > 50000:
                        content = content[:50000] + "\n\n[内容过长已截断]"
                    if len(content) > 100:
                        crawl_ok = True
                        content_source = "原始URL"
            except Exception as e:
                print(f"  原始URL抓取失败: {e}")
        
        # 策略2：国内源搜索（仅当原始URL抓取失败时）
        if not crawl_ok and not any(d in url.lower() for d in SKIP_DOMAINS):
            try:
                print(f"  尝试国内源搜索: {item['title'][:30]}...")
                domestic_result = fetch_domestic_content(item['title'], url)
                if domestic_result and domestic_result.get("content"):
                    content = domestic_result["content"]
                    if len(content) > 50000:
                        content = content[:50000] + "\n\n[内容过长已截断]"
                    if len(content) > 100:
                        crawl_ok = True
                        content_source = f"国内源({domestic_result['source']})"
                        domestic_success += 1
                        print(f"  国内源匹配成功: {domestic_result['source']}, {len(content)}字符")
            except Exception as e:
                print(f"  国内源搜索失败: {e}")
        
        # 策略3：AI HOT摘要作为后备
        if not crawl_ok:
            crawl_failed += 1
            content = f"# {item['title']}\n\n> {item.get('summary', '')}\n\n来源: {item.get('source', '')}"
            content_source = "摘要后备"
        else:
            crawl_success += 1
        
        # 插入或更新数据库
        try:
            if update_mode and existing_id:
                # 更新已有内容
                c.execute("""
                UPDATE selected_items SET
                    url = ?, title = ?, source = ?, source_tier = ?, category = ?, 
                    publish_date = ?, summary = ?, final_score = ?, 
                    full_content = ?, content = ?, updated_at = ?
                WHERE id = ?
                """, (
                    url, item["title"], item["source"], our_tier,
                    item.get("category", "industry"), publish_date,
                    item.get("summary", ""), final_score,
                    content if content else None,
                    content if content else None,
                    datetime.now().isoformat(),
                    existing_id
                ))
                saved += 1
                print(f"  更新完成: {item['title'][:30]}... (分数{final_score} > {dup_info['score']})")
            else:
                # 插入新内容
                c.execute("""
                INSERT INTO selected_items (
                    url, title, source, source_tier, category, publish_date,
                    summary, final_score, selected, created_at, source_from, full_content, content
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    url, item["title"], item["source"], our_tier,
                    item.get("category", "industry"), publish_date,
                    item.get("summary", ""), final_score,
                    1 if mode == "selected" else 0,
                    datetime.now().isoformat(), "aihot",
                    content if content else None,
                    content if content else None
                ))
                saved += 1
                if crawl_ok:
                    print(f"  入库(有正文): {item['title'][:30]}... ({len(content)}字符)")
                else:
                    print(f"  入库(摘要后备): {item['title'][:30]}...")
            conn.commit()
        except Exception as e:
            print(f"  操作失败: {e}")
        finally:
            conn.close()
    
    # 生成推荐理由和标签
    if saved > 0:
        print(f'开始为新增的{saved}条内容生成推荐理由和标签...')
        generate_recommendation_and_tags()
    
    print(f"同步完成: 新增 {saved} 条，跳过已存在 {skipped} 条，跳过域名 {skipped_domain} 条")
    print(f"爬虫结果: 成功 {crawl_success} 条，失败(摘要后备) {crawl_failed} 条")
    return saved


def generate_recommendation_and_tags():
    """为没有推荐理由的内容生成推荐理由和标签"""
    llm = LLMClient(
        api_key=config.get("llm.api_key") or os.getenv("DEEPSEEK_API_KEY", ""),
        base_url=config.get("llm.base_url", "https://api.deepseek.com"),
        model_map={
            "cheap": config.get("llm.cheap_model", "deepseek-chat"),
            "pro": config.get("llm.pro_model", "deepseek-pro")
        }
    )
    
    category_desc = {
        'ai-models': '模型发布/更新',
        'ai-products': '产品发布/更新',
        'industry': '行业动态',
        'paper': '论文研究',
        'tip': '技巧与观点'
    }
    
    storage = HotStorage()
    conn = storage._get_conn()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, title, summary, category, content FROM selected_items WHERE recommendation_reason IS NULL OR recommendation_reason == "" LIMIT 20')
    items = cursor.fetchall()
    
    for item in items:
        try:
            item_id = item['id']
            title = item['title']
            summary = item['summary']
            category = item['category']
            content = item['content'] or summary or title
            
            cat_name = category_desc.get(category, 'AI资讯')
            
            # 生成推荐理由
            prompt = f"""你是AI行业资深编辑，请为以下内容生成一段推荐理由。

【内容信息】
标题: {title}
分类: {cat_name} ({category})
摘要: {summary}
全文: {content[:3000]}

【生成公式】
核心价值/独家信息 + 针对什么人群/解决什么痛点 + 推荐价值/行动建议

【质量要求】
1. 必须指出内容里最有价值的具体信息点，不说空话
2. 明确告诉目标读者谁该看、解决什么痛点
3. 隐含给出读了之后的收益
4. 口语化表达，像行业朋友推荐，不要用\"本文阐述了\"\"本文介绍了\"这类书面语
5. 字数40-120字
6. 禁止使用\"极高质量\"\"优质内容\"\"值得一看\"等无信息量的表述
7. 每个理由必须明确对应一类目标用户

直接输出推荐理由，不要其他内容：
"""
            reason_resp = llm.chat(
                "只输出推荐理由，不要其他内容，40-120字。",
                prompt,
                model="cheap"
            )
            reason = reason_resp.strip() if reason_resp else "重要AI行业动态，建议相关从业者关注。"
            
            if len(reason) > 120:
                reason = reason[:118] + "。"
                
            # 生成标签
            tag_prompt = f"""请为以下AI内容生成3-5个标签，用JSON数组返回，标签要准确、简短，符合行业通用分类：
标题: {title}
分类: {cat_name}
摘要: {summary[:1000]}
输出示例：[\"OpenAI\", \"GPT-4o\", \"多模态\"]
直接输出JSON，不要其他内容：
"""
            tags_resp = llm.chat(
                "只输出JSON数组，不要其他内容，不要解释。",
                tag_prompt,
                model="cheap"
            )
            tags_str = tags_resp.strip() if tags_resp else '["行业动态"]'
            
            try:
                tags = json.loads(tags_str)
                tags_str = json.dumps(tags, ensure_ascii=False)
            except:
                tags_str = json.dumps([category], ensure_ascii=False)
                
            # 保存
            cursor.execute('UPDATE selected_items SET recommendation_reason = ?, tags = ? WHERE id = ?', (reason, tags_str, item_id))
            conn.commit()
            print(f'生成成功：{title[:20]}...')
            
        except Exception as e:
            print(f'生成失败 id={item_id}: {e}')
            continue
    
    conn.close()

if __name__ == "__main__":
    # 同步精选内容
    sync_items("selected")
    # 同步全部内容
    sync_items("all")
    print("AI HOT数据同步完成！")
