"""
测试第一优先级工具的实际抓取能力
"""
import subprocess
import os
import json
from pathlib import Path

TEST_DIR = Path("/home/admin/.openclaw/workspace/behavior_recorder_service/ai-knowledge-alchemist/test_output")
TEST_DIR.mkdir(exist_ok=True)

def test_ytdlp():
    """测试yt-dlp - 多平台媒体下载"""
    print("\n" + "="*80)
    print("🎯 测试 yt-dlp - 视频/音频/多平台下载")
    print("="*80)
    
    test_urls = [
        # B站视频（测试国内平台）
        ("https://www.bilibili.com/video/BV1GJ411x7h7", "B站视频"),
        # YouTube视频（测试国际平台）
        ("https://www.youtube.com/watch?v=jNQXAC9IVRw", "YouTube视频"),
    ]
    
    results = []
    
    for url, desc in test_urls:
        print(f"\n📺 测试: {desc}")
        print(f"URL: {url}")
        
        # 获取视频信息（不下载）
        cmd = [
            "yt-dlp",
            "--no-download",
            "--dump-json",
            "--socket-timeout", "10",
            url
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                print(f"✅ 成功")
                print(f"  标题: {info.get('title', 'N/A')}")
                print(f"  时长: {info.get('duration', 0)}秒")
                print(f"  分辨率: {info.get('resolution', 'N/A')}")
                print(f"  格式: {info.get('ext', 'N/A')}")
                results.append({"platform": desc, "success": True, "title": info.get('title')})
            else:
                error_msg = result.stderr[:200]
                print(f"❌ 失败: {error_msg}")
                results.append({"platform": desc, "success": False, "error": error_msg})
        except Exception as e:
            print(f"❌ 异常: {str(e)}")
            results.append({"platform": desc, "success": False, "error": str(e)})
    
    return results


def test_gallery_dl():
    """测试gallery-dl - 图片/社交媒体抓取"""
    print("\n" + "="*80)
    print("🎯 测试 gallery-dl - 图片/社交媒体抓取")
    print("="*80)
    
    # 测试支持的站点列表
    cmd = ["gallery-dl", "--list-modules"]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            modules = result.stdout.strip().split('\n')
            
            # 检查关键平台支持
            key_platforms = {
                '微博': 'weibo',
                'Instagram': 'instagram',
                'Twitter/X': 'twitter',
                'Pixiv': 'pixiv',
                'Flickr': 'flickr',
                'Tumblr': 'tumblr',
                'DeviantArt': 'deviantart',
                'ArtStation': 'artstation',
                'Pinterest': 'pinterest',
                '小红书': 'xiaohongshu',
            }
            
            print(f"\n📸 支持 {len(modules)} 个站点")
            print("\n关键平台支持情况:")
            
            support_results = []
            
            for platform_name, module_name in key_platforms.items():
                supported = any(module_name in m.lower() for m in modules)
                status = "✅" if supported else "❌"
                print(f"  {status} {platform_name}")
                support_results.append({
                    "platform": platform_name,
                    "supported": supported
                })
            
            return support_results
        else:
            print(f"❌ 获取站点列表失败")
            return []
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        return []


def test_playwright():
    """测试Playwright - 动态页面渲染"""
    print("\n" + "="*80)
    print("🎯 测试 Playwright - 动态页面渲染")
    print("="*80)
    
    test_urls = [
        ("https://www.baidu.com", "百度首页（简单页面）"),
        ("https://movie.douban.com/chart", "豆瓣电影（动态加载）"),
    ]
    
    results = []
    
    test_code = """
import sys
from playwright.sync_api import sync_playwright

url = sys.argv[1]

try:
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=['--no-sandbox'])
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    page = context.new_page()
    page.goto(url, wait_until="networkidle", timeout=15000)
    
    title = page.title()
    content = page.inner_text("body")
    
    print(f"SUCCESS|{title}|{len(content)}")
    browser.close()
    pw.stop()
except Exception as e:
    print(f"ERROR|{str(e)}|0")
"""
    
    for url, desc in test_urls:
        print(f"\n🌐 测试: {desc}")
        print(f"URL: {url}")
        
        try:
            # 写入临时文件
            tmp_file = TEST_DIR / "test_pw.py"
            tmp_file.write_text(test_code)
            
            result = subprocess.run(
                ["python3", str(tmp_file), url],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout.strip()
            if output.startswith("SUCCESS"):
                parts = output.split("|")
                title = parts[1]
                content_len = int(parts[2])
                print(f"✅ 成功")
                print(f"  标题: {title}")
                print(f"  内容长度: {content_len} 字符")
                results.append({"page": desc, "success": True, "title": title})
            else:
                print(f"❌ 失败: {output}")
                results.append({"page": desc, "success": False})
        except Exception as e:
            print(f"❌ 异常: {str(e)}")
            results.append({"page": desc, "success": False, "error": str(e)})
    
    return results


def test_archivebox():
    """评估ArchiveBox - 网页归档"""
    print("\n" + "="*80)
    print("🎯 评估 ArchiveBox - 网页归档引擎")
    print("="*80)
    
    print("\n📦 ArchiveBox需要:")
    print("  - Docker或Python环境")
    print("  - SQLite/PostgreSQL数据库")
    print("  - 多个依赖工具（wget, curl, singlefile等）")
    print("\n⚠️ 评估结果:")
    print("  - 功能强大但重量级，适合长期归档")
    print("  - 对于知识炼金术Agent的实时抓取场景过重")
    print("  - 建议：暂不集成，后续需要长期存储时再考虑")
    
    return {"recommendation": "暂不集成", "reason": "重量级，适合长期归档而非实时抓取"}


def main():
    """运行所有测试"""
    print("🚀 开始测试第一优先级工具")
    
    # 测试各个工具
    ytdlp_results = test_ytdlp()
    gallery_dl_results = test_gallery_dl()
    playwright_results = test_playwright()
    archivebox_eval = test_archivebox()
    
    # 汇总报告
    print("\n" + "="*80)
    print("📊 测试汇总报告")
    print("="*80)
    
    print("\n1️⃣ yt-dlp - 视频/音频下载:")
    for r in ytdlp_results:
        status = "✅" if r.get("success") else "❌"
        print(f"   {status} {r.get('platform')}: {r.get('title', r.get('error', ''))}")
    
    print("\n2️⃣ gallery-dl - 图片/社交媒体:")
    for r in gallery_dl_results:
        status = "✅" if r.get("supported") else "❌"
        print(f"   {status} {r.get('platform')}")
    
    print("\n3️⃣ Playwright - 动态页面渲染:")
    for r in playwright_results:
        status = "✅" if r.get("success") else "❌"
        print(f"   {status} {r.get('page')}: {r.get('title', '')}")
    
    print("\n4️⃣ ArchiveBox - 网页归档:")
    print(f"   建议: {archivebox_eval.get('recommendation')}")
    print(f"   原因: {archivebox_eval.get('reason')}")
    
    print("\n" + "="*80)
    print("💡 集成建议:")
    print("="*80)
    print("✅ yt-dlp: 推荐集成，支持1000+平台")
    print("✅ gallery-dl: 推荐集成，补充图片抓取能力")
    print("✅ Playwright: 已集成，动态页面必备")
    print("⏸️ ArchiveBox: 暂不集成，重量级")


if __name__ == "__main__":
    main()
