# 知识炼金术 Agent V1.0

将杂乱的网页信息自动转化为高价值的结构化素材。

## 功能特性
- 自动抓取网页正文，去除广告/导航等噪音
- 三维分类（时间/内容/场景）
- 三维评分（重要性/稀缺性/实用性）
- 自动计算最终分并映射星级
- 核心观点提炼+视频适用场景建议
- 自动归档到本地目录+SQLite数据库

## 安装

```bash
# 安装依赖
pip install -r requirements.txt

# 设置API Key（必需）
export DEEPSEEK_API_KEY="your_api_key_here"
```

## 使用方法

```bash
# 处理单个URL
python main.py process --url https://example.com/article

# 以JSON格式输出
python main.py process --url https://example.com/article --format json
```

## 输出结构

处理完成后，素材会自动归档到：
- 本地目录：`data/output/内容维度/时间维度/标题.md`
- 数据库：`data/materials.db`

每个归档文件包含FrontMatter元数据（分类/评分/核心观点等）和干净的正文内容。

## 评分公式

```
最终分 = (重要性×0.4 + 稀缺性×0.3 + 实用性×0.3) × 10 × 时效性权重
```

时效性权重：7天内×1.5 / 1个月内×1.2 / 3个月内×1.0 / 1年内×0.9 / 超过1年×0.8

星级映射：≥90分→5星 / ≥80分→4星 / ≥70分→3星 / ≥60分→2星 / <60分→1星
