"""
AIHOT核心处理流水线
双速模型架构：cheap模型预筛 → pro模型精评 → 代码计算最终分
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from src.llm_client import LLMClient
from src.config import config
from src.crawler import WebCrawler

logger = logging.getLogger(__name__)

# 信源等级权重配置（T1=原T1, T2=原T1.5, T3=原T2）
TIER_WEIGHT = {
    "T1": 1.3,  # 官方/权威来源权重最高
    "T2": 1.15, # 垂直领域头部媒体
    "T3": 1.0   # 普通媒体/自媒体
}

# 评分维度权重
SCORING_WEIGHTS = {
    "timeliness": 0.25, # 时效性
    "importance": 0.25, # 重要性
    "scarcity": 0.2, # 稀缺性
    "practicality": 0.15, # 实用性
    "relevance": 0.15 # 行业相关性
}

# 精选阈值，不同信源等级有不同的阈值（T1=原T1, T2=原T1.5, T3=原T2）
SELECTION_THRESHOLD = {
    "T1": 60,
    "T2": 65,
    "T3": 75
}

# 内容类型关键词（用于快速匹配/打标辅助）
CONTENT_TYPE_KEYWORDS = {
    "模型发布": ["发布", "上线"],
    "产品更新": ["更新", "升级", "公测"],
    "行业动态": ["市场", "投资", "融资", "趋势", "预测"],
    "论文研究": ["论文", "研究", "arxiv"],
    "教程/实践": ["教程", "指南", "实践", "最佳实践"],
    "开源生态": ["开源"],
    "评测": ["评测", "基准", "性能"],
}

# 内容来源类型关键词
SOURCE_TYPE_KEYWORDS = {
    "推文": ["X/Twitter", "Twitter", "推文", "tweet", "thread"],
    "博客": ["Blog", "博客", "engineering blog", "技术博客"],
    "新闻": ["News", "新闻", "报道", "media", "资讯"],
    "论文": ["论文", "paper", "arxiv", "research", "学术"],
    "文档": ["文档", "documentation", "docs", "手册"],
    "视频": ["视频", "video", "YouTube", "B站"],
}

class HotPipeline:
    """AI热点处理引擎"""
    
    # LLM结果缓存（内存级，进程内有效）
    _cache = {}

    def __init__(self):
        # LLM客户端
        model_map = {
            "cheap": config.get("llm.cheap_model", "deepseek-chat"),
            "pro": config.get("llm.pro_model", "deepseek-pro")
        }
        self.llm = LLMClient(
            api_key=config.get("llm.api_key") or os.getenv("DEEPSEEK_API_KEY", ""),
            base_url=config.get("llm.base_url", "https://api.deepseek.com"),
            model_map=model_map
        )
        
        # 爬虫
        self.crawler = WebCrawler()
        
        # 行业关键词，预筛用
        self.industry_keywords = config.get("industry.keywords", [
            "AI", "人工智能", "大模型", "AIGC", "大语言模型",
            "AGI", "生成式AI", "多模态", "Agent", "智能体",
            "ChatGPT", "GPT", "Claude", "文心一言", "通义千问"
        ])
        
        logger.info("AI热点处理引擎初始化完成")

    def process_url(self, url: str, source_tier: str = "T2") -> Tuple[bool, Dict[str, Any]]:
        """
        处理URL，跑完完整双速流程
        Args:
            url: 网页URL
            source_tier: 来源等级 T1/T1.5/T2
        Returns:
            (是否入选精选, 完整处理结果)
        """
        # 先抓取
        logger.info("步骤1：开始抓取网页...")
        crawl_result = self.crawler.fetch(url)
        if not crawl_result.get("success"):
            error_msg = f"抓取失败: {crawl_result.get('error')}"
            logger.error(error_msg)
            return False, {"error": error_msg}
        
        return self.process_crawl_result(url, crawl_result, source_tier)
    
    def process_rss_entry(self, entry: Dict[str, Any], source_tier: str = "T2", source_name: str = "", lightweight: bool = False) -> Tuple[bool, Dict[str, Any]]:
        """
        处理RSS条目，无需下载网页，直接使用RSS中的title和summary
        Args:
            entry: RSS条目，包含 title, link, summary, published, author 等字段
            source_tier: 来源等级
            source_name: 信源名称
            lightweight: 轻量模式，T1源跳过LLM直接入库（大幅提速）
        Returns:
            (是否入选精选, 完整处理结果)
        """
        url = entry.get('link', entry.get('url', ''))
        title = entry.get('title', '')
        summary = entry.get('summary', entry.get('description', ''))
        published = entry.get('published', entry.get('published_parsed', ''))
        author = entry.get('author', '')
        
        if not url or not title:
            return False, {"error": "RSS条目缺少URL或标题"}
        
        # 用 title + summary 作为内容
        content = f"标题: {title}\n摘要: {summary}"
        
        result = {
            "url": url,
            "source_tier": source_tier,
            "source": source_name,
            "title": title,
            "publish_date": published,
            "author": author,
            "pre_screen_result": {},
            "scoring": {},
            "final_score": 0,
            "selected": False,
            "crawl_time": datetime.now().isoformat(),
            "summary": summary[:300] if summary else ""
        }
        
        logger.info(f"RSS条目: {title[:50]}")
        
        # 轻量模式：T1源直接给高分入库，跳过LLM
        if lightweight and source_tier in ("T1",):
            result["final_score"] = 85
            result["selected"] = True
            result["category"] = "industry"
            result["tags"] = '["行业动态"]'
            result["summary"] = summary[:300] if summary else title
            result["recommendation_reason"] = f"来自{source_name}的AI相关资讯，值得关注。"
            result["full_content"] = content if len(content) < 50000 else content[:50000]
            
            # 轻量模式也需要翻译英文内容
            result = self._translate_if_english(result)
            
            return True, result
        
        # 步骤2：cheap模型预筛
        logger.info("步骤2：开始预筛...")
        is_relevant, pre_screen_result = self._do_pre_screen(content, title)
        result["pre_screen_result"] = pre_screen_result
        
        if not is_relevant:
            logger.info(f"预筛不通过: {pre_screen_result.get('reason', '不符合行业关键词')}")
            return False, result
        logger.info("预筛通过")
        
        # 步骤3：pro模型多维评分
        logger.info("步骤3：开始多维评分...")
        scoring_result = self._do_scoring(content, title)
        result["scoring"] = scoring_result
        logger.info(f"评分结果: {json.dumps(scoring_result, ensure_ascii=False)}")
        
        # 步骤4：代码计算最终分
        logger.info("步骤4：计算最终分...")
        final_score = self._calculate_final_score(
            scoring_result, 
            source_tier,
            publish_date=result["publish_date"]
        )
        result["final_score"] = final_score
        
        # 步骤5：判断是否入选精选
        threshold = SELECTION_THRESHOLD.get(source_tier, 75)
        result["selected"] = final_score >= threshold
        logger.info(f"最终分: {final_score}, 阈值: {threshold}, 是否入选: {result['selected']}")
        
        # 入选内容：一次性调用LLM获取分类+标签+摘要+推荐理由（4合1）
        if result["selected"]:
            logger.info("步骤6-9：批量生成分类/标签/摘要/推荐理由...")
            batch_result = self._do_batch_generation(content, title, source_name)
            result["category"] = batch_result.get("category", "industry")
            result["tags"] = batch_result.get("tags", '["行业动态"]')
            result["summary"] = batch_result.get("summary", summary[:300] if summary else "")
            result["recommendation_reason"] = batch_result.get("recommendation_reason", "")
            logger.info(f"分类: {result['category']}, 标签: {result['tags'][:30]}...")
        
        # 未入选内容：只生成分类和标签
        else:
            logger.info("步骤6-7：生成分类和标签...")
            basic_result = self._do_basic_generation(content, title, source_name)
            result["category"] = basic_result.get("category", "industry")
            result["tags"] = basic_result.get("tags", '["行业动态"]')
        
        # 保存完整正文
        result["full_content"] = content if len(content) < 50000 else content[:50000]
        
        # 英文内容自动翻译为中文
        result = self._translate_if_english(result)
        
        return result["selected"], result
    
    def process_crawl_result(self, url: str, crawl_result: Dict[str, Any], source_tier: str = "T2") -> Tuple[bool, Dict[str, Any]]:
        """
        处理已抓取的网页内容，跑完双速流程
        Args:
            url: 网页URL
            crawl_result: 爬虫返回的结果（包含metadata和markdown）
            source_tier: 来源等级 T1/T1.5/T2
        Returns:
            (是否入选精选, 完整处理结果)
        """
        # 兼容ArticleMetadata对象和dict两种格式
        metadata = crawl_result["metadata"]
        if hasattr(metadata, 'to_dict'):
            # ArticleMetadata对象
            meta_dict = metadata.to_dict()
        elif isinstance(metadata, dict):
            meta_dict = metadata
        else:
            meta_dict = {}
        
        result = {
            "url": url,
            "source_tier": source_tier,
            "source": meta_dict.get("source", ""),
            "title": meta_dict.get("title", ""),
            "publish_date": meta_dict.get("publish_date", ""),
            "author": meta_dict.get("author", ""),
            "pre_screen_result": {},
            "scoring": {},
            "final_score": 0,
            "selected": False,
            "crawl_time": datetime.now().isoformat(),
            "summary": ""
        }
        
        markdown_content = crawl_result["markdown"]
        logger.info(f"抓取成功: {result['title']}")
        
        # 步骤2：cheap模型预筛，判断是否符合行业热点
        logger.info("步骤2：开始预筛...")
        is_relevant, pre_screen_result = self._do_pre_screen(markdown_content, result['title'])
        result["pre_screen_result"] = pre_screen_result
        
        if not is_relevant:
            logger.info(f"预筛不通过: {pre_screen_result.get('reason', '不符合行业关键词')}")
            return False, result
        logger.info("预筛通过")
        
        # 步骤3：pro模型多维评分
        logger.info("步骤3：开始多维评分...")
        scoring_result = self._do_scoring(markdown_content, result['title'])
        result["scoring"] = scoring_result
        logger.info(f"评分结果: {json.dumps(scoring_result, ensure_ascii=False)}")
        
        # 步骤4：代码计算最终分
        logger.info("步骤4：计算最终分...")
        final_score = self._calculate_final_score(
            scoring_result, 
            source_tier,
            publish_date=result["publish_date"]
        )
        result["final_score"] = final_score
        
        # 步骤5：判断是否入选精选
        threshold = SELECTION_THRESHOLD.get(source_tier, 75)
        result["selected"] = final_score >= threshold
        logger.info(f"最终分: {final_score}, 阈值: {threshold}, 是否入选: {result['selected']}")
        
        # 步骤6：自动分类（对齐AIHOT的5个分类）
        logger.info("步骤6：自动分类...")
        result["category"] = self._classify_content(markdown_content, result['title'])
        logger.info(f"分类结果: {result['category']}")
        
        # 步骤7：生成标签
        logger.info("步骤7：生成标签...")
        result["tags"] = self._generate_tags(markdown_content, result['title'], result.get('source', ''))
        logger.info(f"标签: {result['tags']}")
        
        # 步骤8：生成摘要
        if result["selected"]:
            logger.info("步骤8：生成摘要...")
            result["summary"] = self._generate_summary(markdown_content, result['title'])
        
        # 步骤9：生成推荐理由（仅入选内容）
        if result["selected"]:
            logger.info("步骤9：生成推荐理由...")
            result["recommendation_reason"] = self._generate_recommendation(
                markdown_content, result['title'], result['tags'], result.get('summary', '')
            )
            logger.info(f"推荐理由: {result['recommendation_reason'][:50]}...")
        
        # 保存完整正文（清洗后的Markdown）
        result["full_content"] = markdown_content if len(markdown_content) < 50000 else markdown_content[:50000]
        
        return result["selected"], result

    def _do_pre_screen(self, content: str, title: str) -> Tuple[bool, Dict[str, Any]]:
        """用cheap模型执行预筛，判断是否符合行业相关"""
        # 先快速规则过滤，没有命中行业关键词直接返回不通过
        content_lower = content[:3000].lower()
        title_lower = title.lower()
        has_keyword = any(k.lower() in content_lower or k.lower() in title_lower for k in self.industry_keywords)
        if not has_keyword:
            return False, {"reason": "未命中行业关键词", "score": 0}
        
        # 规则过滤通过，调用LLM二次判断
        prompt = f"""
        请判断以下文章内容是否属于人工智能/大模型/AI相关的行业新闻/技术资讯/动态。
        标题: {title}
        内容摘要: {content[:3000]}
        
        只需要输出JSON格式的结果，不要其他解释：
        {{
            "is_relevant": true/false, // 是否相关
            "confidence": 0-100, // 置信度
            "reason": "判断依据"
        }}
        """
        
        try:
            result = self.llm.chat_json(
                "只输出JSON，不要任何额外解释。",
                prompt,
                model="cheap"
            )
            is_relevant = result.get("is_relevant", False) and result.get("confidence", 0) >= 60
            return is_relevant, result
        except Exception as e:
            logger.error(f"预筛调用LLM失败: {e}")
            return has_keyword, {"reason": "规则过滤通过，LLM调用失败默认通过", "score": 60}

    def _do_scoring(self, content: str, title: str) -> Dict[str, Any]:
        """用pro模型执行多维评分"""
        prompt = f"""
        请从以下5个维度给这篇AI行业相关的文章打分，每个维度0-10分，整数分：
        1. timeliness: 时效性，内容越新/最近发生的事分数越高
        2. importance: 重要性，事件影响范围越大/级别越高分数越高
        3. scarcity: 稀缺性，信息越独家/少见/不容易获取分数越高
        4. practicality: 实用性，对从业者的参考/借鉴/帮助价值越高分数越高
        5. relevance: 相关性，和AI行业/大模型/技术发展的关联度越高分数越高
        
        标题: {title}
        内容: {content[:5000]}
        
        只需要输出JSON格式的结果，不要其他解释，结构如下：
        {{
            "timeliness": 分数,
            "importance": 分数,
            "scarcity": 分数,
            "practicality": 分数,
            "relevance": 分数,
            "reason": "打分的简要依据"
        }}
        """
        
        try:
            return self.llm.chat_json(
                "只输出JSON，不要任何额外解释。",
                prompt,
                model="pro"
            )
        except Exception as e:
            logger.error(f"评分调用LLM失败: {e}")
            # 失败返回默认中等分数
            return {
                "timeliness": 6,
                "importance": 6,
                "scarcity": 6,
                "practicality": 6,
                "relevance": 6,
                "reason": "LLM调用失败，返回默认分数"
            }

    def _calculate_final_score(self, scoring: Dict[str, Any], source_tier: str, publish_date: Optional[str] = None) -> float:
        """
        计算最终分（100分制）
        公式：(各维度加权和 × 10) × 信源等级权重 × 时效性额外加权
        """
        # 计算各维度加权和（0-10分制）
        weighted_sum = 0
        for dim, weight in SCORING_WEIGHTS.items():
            score = scoring.get(dim, 5)
            weighted_sum += score * weight
        
        # 信源等级权重
        tier_weight = TIER_WEIGHT.get(source_tier, 1.0)
        
        # 时效性额外加权
        time_weight = self._get_time_weight(publish_date)
        
        # 最终分（0-100分制）
        final_score = weighted_sum * 10 * tier_weight * time_weight
        
        return round(final_score, 1)

    def _get_time_weight(self, publish_date: Optional[str]) -> float:
        """根据发布时间获取时效性权重"""
        if not publish_date:
            return 1.2  # 默认1个月内
        
        try:
            pub_date = datetime.fromisoformat(publish_date.replace("Z", "+00:00"))
            now = datetime.now(pub_date.tzinfo) if pub_date.tzinfo else datetime.now()
            delta = now - pub_date
            
            if delta.days <= 1:
                return 1.5  # 24小时内
            elif delta.days <= 3:
                return 1.4  # 3天内
            elif delta.days <= 7:
                return 1.3  # 7天内
            elif delta.days <= 30:
                return 1.2  # 1个月内
            elif delta.days <= 90:
                return 1.0  # 3个月内
            elif delta.days <= 365:
                return 0.9  # 1年内
            else:
                return 0.7  # 超过1年
        except Exception as e:
            logger.warning(f"解析发布时间失败: {e}")
            return 1.2

    def _generate_summary(self, content: str, title: str) -> str:
        """生成文章摘要，用于精选展示"""
        prompt = f"""
        请给以下AI行业文章生成一篇不超过300字的摘要，提炼核心要点，语言简洁：
        标题: {title}
        内容: {content[:3000]}
        """
        
        try:
            return self.llm.chat(
                "只输出摘要内容，不要任何其他解释。",
                prompt,
                model="pro"
            ).strip()
        except Exception as e:
            logger.error(f"生成摘要调用LLM失败: {e}")
            return ""

    def _classify_content(self, content: str, title: str) -> str:
        """
        自动分类内容（对齐AIHOT的5个固定分类）
        Returns:
            ai-models / ai-products / industry / paper / tip
        """
        prompt = f"""
        请将以下AI行业文章分类到以下5个类别之一（只输出类别名称，不要其他内容）：
        
        1. ai-models（模型发布/更新）- 大模型发布、更新、评测等
        2. ai-products（产品发布/更新）- AI产品/工具/平台发布或更新
        3. industry（行业动态）- 行业新闻、政策、融资、合作等
        4. paper（论文研究）- 学术论文、研究报告、技术突破等
        5. tip（技巧与观点）- 教程、技巧、观点、经验分析等
        
        标题: {title}
        内容摘要: {content[:2000]}
        
        只输出类别名称（ai-models/ai-products/industry/paper/tip），不要其他内容：
        """
        
        try:
            result = self.llm.chat(
                "只输出类别名称，不要任何其他解释。",
                prompt,
                model="cheap"  # 分类任务简单，用cheap模型即可
            ).strip().lower()
            
            # 验证返回的类别是否合法
            valid_categories = ["ai-models", "ai-products", "industry", "paper", "tip"]
            if result in valid_categories:
                return result
            else:
                # 如果返回不合法，尝试匹配
                if "model" in result:
                    return "ai-models"
                elif "product" in result:
                    return "ai-products"
                elif "industry" in result or "动态" in result:
                    return "industry"
                elif "paper" in result or "研究" in result:
                    return "paper"
                elif "tip" in result or "技巧" in result:
                    return "tip"
                else:
                    return "industry"  # 默认分类
        except Exception as e:
            logger.error(f"分类调用LLM失败: {e}")
            return "industry"  # 失败返回默认分类

    def _generate_tags(self, content: str, title: str, source: str) -> str:
        """
        自动生成标签（三层标签体系，对齐AIHOT规则）
        
        三层标签体系：
        1. 主体标签（1个）：厂商/机构/人物
        2. 技术/领域标签（2-3个）：Agent/MCP/MoE/RAG等
        3. 内容类型标签（1个）：模型发布/产品更新/行业动态等
        
        打标规则：
        - 每条内容必须有3-5个标签
        - 1个主体标签 + 2-3个技术标签 + 1个内容类型标签
        
        Returns:
            JSON字符串，如 '["Anthropic", "MCP/工具", "部署/工程", "产品更新"]'
        """
        import json
        import os
        
        # 预设标签词库（对齐AIHOT三层标签体系）
        TAG_DB = {
            "主体标签": {
                "国外厂商": ["OpenAI", "Anthropic", "Google", "NVIDIA", "xAI", "GitHub", "Hugging Face", "Cursor", "Cloudflare", "Meta", "Microsoft", "Twitter", "X"],
                "国内厂商": ["腾讯", "阿里", "百度", "字节", "小米", "地平线", "华为", "DeepSeek", "商汤", "智谱", "MiniMax", "月之暗面", "Kimi"],
                "机构/媒体": ["Hacker News", "IT之家", "36氪", "量子位", "机器之心", "arXiv", "CVPR", "NeurIPS", "ICML"],
                "人物": ["马斯克", "Sam Altman", "Yann LeCun", "李沐", "邱锡鹏", "Andrej Karpathy", "Ilya Sutskever", "Dario Amodei"]
            },
            "技术标签": {
                "智能体": ["Agent", "MCP/工具", "编码", "工作流", "Prompt工程", "可审计"],
                "具身智能": ["人形机器人", "VLA模型", "机器人控制", "端侧推理"],
                "多模态": ["OCR", "视频生成", "图像生成", "语音生成", "3D生成"],
                "模型技术": ["推理", "MoE", "自蒸馏", "LoRA", "DoRA", "微调", "大模型训练", "KV-cache", "稀疏激活", "量化", "混合精度"],
                "部署工程": ["云服务", "算力", "本地部署", "自托管", "边缘推理", "沙箱", "MCP隧道", "API"],
                "检索增强": ["RAG", "文档智能", "向量数据库", "语义搜索", "Embedding"],
                "安全合规": ["数据安全", "AI伦理", "数据主权", "合规", "隐私保护"]
            },
            "内容类型标签": ["模型发布", "产品更新", "行业动态", "论文研究", "教程/实践", "开源生态", "大佬观点", "评测/基准", "投资融资", "快讯"]
        }
        
        # 展平所有预设标签（用于匹配）
        all_known_tags = []
        for category, tags in TAG_DB.items():
            if isinstance(tags, dict):
                for sub_tags in tags.values():
                    all_known_tags.extend(sub_tags)
            else:
                all_known_tags.extend(tags)
        
        prompt = f"""
        请从以下AI行业文章中提取标签，必须按照三层标签体系：
        
        ## 第一层：主体标签（必须1个，优先从下方选择）
        国外厂商: {", ".join(TAG_DB["主体标签"]["国外厂商"][:12])}
        国内厂商: {", ".join(TAG_DB["主体标签"]["国内厂商"][:12])}
        机构/媒体: {", ".join(TAG_DB["主体标签"]["机构/媒体"][:9])}
        人物: {", ".join(TAG_DB["主体标签"]["人物"][:8])}
        
        ## 第二层：技术/领域标签（必须2-3个，优先从下方选择）
        智能体: {", ".join(TAG_DB["技术标签"]["智能体"])}
        具身智能: {", ".join(TAG_DB["技术标签"]["具身智能"])}
        多模态: {", ".join(TAG_DB["技术标签"]["多模态"])}
        模型技术: {", ".join(TAG_DB["技术标签"]["模型技术"][:8])}
        部署工程: {", ".join(TAG_DB["技术标签"]["部署工程"][:8])}
        检索增强: {", ".join(TAG_DB["技术标签"]["检索增强"])}
        安全合规: {", ".join(TAG_DB["技术标签"]["安全合规"])}
        
        ## 第三层：内容类型标签（必须1个，从下方选择）
        {", ".join(TAG_DB["内容类型标签"])}
        
        ## 规则
        - 必须有3-5个标签
        - 必须包含：1个主体标签 + 2-3个技术标签 + 1个内容类型标签
        - 标签简洁（2-10个字）
        - 不要重复含义相同的标签
        - 优先使用上方列出的标准标签
        - 如果文章中有新的概念，可以生成新标签（会在后台记录待审核）
        
        标题: {title}
        信源: {source}
        内容摘要: {content[:2000]}
        
        请以JSON数组格式返回，只输出JSON，不要其他内容：
        例如: ["Anthropic", "MCP/工具", "部署/工程", "产品更新"]
        """
        
        try:
            result = self.llm.chat(
                "只输出JSON数组，不要其他内容。",
                prompt,
                model="cheap"  # 标签生成简单，用cheap模型
            ).strip()
            
            # 验证返回的是合法JSON数组
            if result.startswith('[') and result.endswith(']'):
                tags = json.loads(result)
                if isinstance(tags, list) and len(tags) >= 3:
                    # 限制3-5个标签
                    tags = tags[:5]
                    
                    # 记录新标签（不在词库中的标签）
                    new_tags = [t for t in tags if t not in all_known_tags]
                    if new_tags:
                        self._log_new_tags(new_tags, title)
                    
                    return json.dumps(tags, ensure_ascii=False)
            
            # fallback
            return json.dumps(["行业动态"], ensure_ascii=False)
        except Exception as e:
            logger.error(f"标签生成调用LLM失败: {e}")
            return json.dumps(["行业动态"], ensure_ascii=False)

    def _log_new_tags(self, new_tags: list, title: str):
        """
        记录新标签到日志文件，供后续审核
        """
        try:
            log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, "new_tags_audit.log")
            
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] 新标签: {', '.join(new_tags)}\n")
                f.write(f"  来源文章: {title}\n")
                f.write(f"  建议操作: 审核后将新标签加入 TAG_DB\n\n")
            
            logger.info(f"记录新标签: {new_tags}")
        except Exception as e:
            logger.error(f"记录新标签失败: {e}")

    def _do_batch_generation(self, content: str, title: str, source: str) -> Dict[str, Any]:
        """
        一次性生成分类+标签+摘要+推荐理由（4合1，大幅减少LLM调用）
        Returns:
            {"category": str, "tags": str, "summary": str, "recommendation_reason": str}
        """
        # 缓存键（基于标题哈希）
        cache_key = f"batch:{hash(title)}"
        if cache_key in self._cache:
            logger.info(f"LLM缓存命中: {title[:40]}")
            return self._cache[cache_key]
        
        prompt = f"""你是AI行业资深编辑，请分析以下内容并生成结构化信息。

【内容信息】
标题: {title}
信源: {source}
摘要: {content[:3000]}

【任务1 - 分类】从以下5个类别选1个：
ai-models（模型发布/更新）/ ai-products（产品发布/更新）/ industry（行业动态）/ paper（论文研究）/ tip（技巧与观点）

【任务2 - 标签】生成3-5个标签，格式：1个主体标签 + 2-3个技术标签 + 1个内容类型标签
主体示例：OpenAI/Anthropic/Google/百度/阿里/DeepSeek/智谱/IT之家/36氪/量子位
技术示例：Agent/MCP/RAG/多模态/推理/微调/部署/向量数据库/AI伦理
类型示例：模型发布/产品更新/行业动态/论文研究/教程/开源/大佬观点/评测/投资融资

【任务3 - 摘要】生成不超过200字的简洁摘要，提炼核心要点

【任务4 - 推荐理由】按公式"核心价值 + 针对人群/解决痛点 + 推荐收益"生成40-100字推荐理由
要求：口语化、不说空话、指出具体价值点

请以JSON格式返回，结构如下（只输出JSON，不要其他内容）：
{{
    "category": "类别",
    "tags": ["标签1", "标签2", "标签3"],
    "summary": "摘要内容",
    "recommendation_reason": "推荐理由"
}}
"""
        
        try:
            raw = self.llm.chat_json(
                "只输出JSON，不要任何其他内容。",
                prompt,
                model="pro"
            )
            result = raw if isinstance(raw, dict) else json.loads(raw) if isinstance(raw, str) else {}
            
            # 提取并格式化
            output = {
                "category": result.get("category", "industry"),
                "tags": json.dumps(result.get("tags", ["行业动态"]), ensure_ascii=False),
                "summary": result.get("summary", "")[:300],
                "recommendation_reason": result.get("recommendation_reason", "")[:120]
            }
            
            # 存入缓存
            self._cache[cache_key] = output
            if len(self._cache) > 500:
                self._cache.clear()
            
            logger.info(f"批量生成完成: {title[:40]}, 分类={output['category']}")
            return output
            
        except Exception as e:
            logger.error(f"批量生成调用LLM失败: {e}")
            return {
                "category": "industry",
                "tags": '["行业动态"]',
                "summary": content[:300],
                "recommendation_reason": ""
            }
    
    def _do_basic_generation(self, content: str, title: str, source: str) -> Dict[str, Any]:
        """
        轻量模式：只生成分类和标签（2合1）
        Returns:
            {"category": str, "tags": str}
        """
        cache_key = f"basic:{hash(title)}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        prompt = f"""请将以下AI行业文章分类并生成标签。

【内容信息】
标题: {title}
信源: {source}
摘要: {content[:2000]}

【分类】选1个：ai-models/ai-products/industry/paper/tip
【标签】3-5个：1个主体 + 2-3个技术 + 1个类型

只输出JSON：
{{"category": "类别", "tags": ["标签1", "标签2", "标签3"]}}
"""
        
        try:
            raw = self.llm.chat_json_raw(
                "只输出JSON，不要任何其他内容。",
                prompt,
                model="cheap"
            )
            result = raw if isinstance(raw, dict) else json.loads(raw) if isinstance(raw, str) else {}
            
            output = {
                "category": result.get("category", "industry"),
                "tags": json.dumps(result.get("tags", ["行业动态"]), ensure_ascii=False)
            }
            
            self._cache[cache_key] = output
            return output
            
        except Exception as e:
            logger.error(f"轻量生成调用LLM失败: {e}")
            return {"category": "industry", "tags": '["行业动态"]'}

    def _generate_recommendation(self, content: str, title: str, tags: str, summary: str) -> str:
        """
        生成推荐理由（AI HOT风格：LLM驱动的模板+推理）
        参考临床推理引擎的LLM调用模式
        Returns:
            推荐理由文本
        """
        # 提取分类信息（用于构建提示）
        try:
            import json
            tag_list = json.loads(tags) if isinstance(tags, str) else tags
        except:
            tag_list = []
        
        prompt = f"""你是AI行业资深编辑，请为以下内容生成推荐理由。

【内容信息】
标题: {title}
标签: {tags}
摘要: {summary}
全文摘要: {content[:2000]}

【生成公式】
核心价值/独家信息 + 针对什么人群/解决什么痛点 + 推荐价值/行动建议

【质量要求】
1. 必须指出内容里最有价值的具体信息点，不说空话
2. 明确告诉目标读者谁该看、解决什么痛点
3. 隐含给出读了之后的收益
4. 口语化表达，像行业朋友推荐
5. 字数40-120字
6. 禁止使用"极高质量""优质内容""值得一看"等表述
7. 每个理由必须明确对应一类目标用户

直接输出推荐理由，不要其他内容：
"""
        
        try:
            result = self.llm.chat(
                "只输出推荐理由，不要其他内容，40-120字。",
                prompt,
                model="cheap"
            ).strip()
            
            # 确保不超过120字
            if len(result) > 120:
                result = result[:118] + "。"
            
            return result
        except Exception as e:
            logger.error(f"推荐理由生成调用LLM失败: {e}")
            return summary[:80] if summary else ""
    
    def _is_english_text(self, text: str) -> bool:
        """
        检测文本是否为英文
        判断标准：英文字符占比超过60%
        """
        if not text:
            return False
        
        # 只检测前2000字符
        sample = text[:2000]
        
        # 统计中文字符数量
        chinese_count = sum(1 for c in sample if '\u4e00' <= c <= '\u9fff')
        
        # 统计英文字母数量
        english_count = sum(1 for c in sample if c.isascii() and c.isalpha())
        
        # 如果英文字母占比超过中文字符，判定为英文
        return english_count > chinese_count
    
    def _translate_if_english(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        如果内容是英文，自动翻译为中文
        翻译：标题、摘要、全文
        """
        title = result.get("title", "")
        summary = result.get("summary", "")
        full_content = result.get("full_content", "")
        
        # 检测是否为英文内容
        content_to_check = f"{title}\n{summary}"
        if not self._is_english_text(content_to_check):
            return result
        
        logger.info(f"检测到英文内容，开始翻译: {title[:40]}...")
        
        try:
            # 翻译标题和摘要
            trans_prompt = f"""请将以下英文AI相关内容翻译为中文，保持专业术语准确：

标题: {title}
摘要: {summary[:500] if summary else '无'}

请以JSON格式返回翻译结果，结构如下：
{{
    "title_zh": "翻译后的标题",
    "summary_zh": "翻译后的摘要"
}}
"""
            
            trans_result = self.llm.chat_json(
                "只输出JSON，不要其他内容。",
                trans_prompt,
                model="cheap"
            )
            
            title_zh = trans_result.get("title_zh", title)
            summary_zh = trans_result.get("summary_zh", summary)
            
            # 只翻译标题和摘要，全文太长不翻译（节省token）
            result["title"] = title_zh
            result["summary"] = summary_zh
            result["translated_from_english"] = True
            
            logger.info(f"翻译完成: {title_zh[:40]}...")
            
        except Exception as e:
            logger.warning(f"翻译失败，保留原文: {e}")
            result["translated_from_english"] = False
        
        return result
