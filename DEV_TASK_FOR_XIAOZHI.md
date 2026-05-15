# 给小治的知识炼金术Agent V1.0开发指令
## 👋 任务说明
你负责知识炼金术Agent V1.0逻辑验证版的开发，严格按照《ITER_V1.0_DEVELOPMENT_GUIDE.md》开发手册执行，所有要求必须100%遵守。
---
## 🎯 你的执行步骤（1天完成）
### 🔹 第一步：环境准备 & 基础结构搭建（0.5天）
1. 克隆仓库：`git clone git@github.com:David-Bian208/ai-knowledge-alchemist.git`
2. 初始化项目结构：
   ```
   ai-knowledge-alchemist/
   ├── prompts/           # 存放所有LLM提示词
   │   ├── classification.md
   │   ├── rating.md
   │   ├── extraction.md
   │   └── relation.md
   ├── agents/            # 核心处理逻辑
   │   └── knowledge_processor.py
   ├── utils/             # 工具类
   │   └── llm_client.py  # 复用视频项目的LLM调用工具，直接复制过来即可
   ├── test.py            # 测试脚本
   ├── requirements.txt   # 依赖清单
   └── README.md          # 项目说明
   ```
3. 编写requirements.txt，只需要必要依赖：`openai`/`python-dotenv`/`json5`（用来解析LLM返回的JSON，避免格式错误）
4. 提交commit：`[init] 项目基础结构搭建完成`
### 🔹 第二步：核心逻辑开发（0.5天）
1. **编写提示词**：
   - 按照开发手册的要求，分别编写4步的提示词，每个步骤的要求、可选值、输出格式必须写死在提示词中，要求LLM只输出标准JSON，不输出任何其他内容
   - 提示词最后必须加："输出必须是纯JSON格式，不要包含任何markdown格式、解释性文字、代码块标记"
2. **开发知识处理核心逻辑**：
   - 在`knowledge_processor.py`中实现4步处理函数：`classify()`/`rate()`/`extract()`/`relate()`
   - 实现错误重试逻辑：每一步调用LLM如果返回JSON格式错误，自动重试最多3次，重试失败抛出异常
   - 实现主函数：接收输入的markdown文本和3个笔记标题，按顺序执行4步，最后合并输出完整的JSON结果
3. **开发测试脚本**：
   - 编写`test.py`，内置测试用的Markdown文本和3个笔记标题，运行后打印每一步的处理结果和最终的完整JSON
   - 要求测试脚本可以一键运行：`python test.py`
4. 提交commit：`[core] 核心逻辑开发完成，全流程可跑通`
### 🔹 第三步：测试 & 验证（当天完成）
1. 运行测试脚本至少5次，验证同一输入的输出结果一致，无随机差异
2. 验证输出格式100%符合要求，无JSON解析错误
3. 检查分类、评级、梳理结果是否符合预期，准确率达到验收标准
4. 编写README.md，说明项目使用方法，如何配置API Key，如何运行测试
5. 提交最终commit：`[test] 全流程测试通过，V1.0版本就绪`
---
## ✅ 交付要求
1. 所有代码提交到`master`分支，推送到远程仓库
2. 提交测试报告，包含至少3次运行的输出结果截图
3. 确认所有依赖都写入requirements.txt，在新环境可以一键安装运行
---
## ❓ 问题反馈
如果遇到阻塞问题，第一时间反馈，不要修改核心流程和输出规范。
