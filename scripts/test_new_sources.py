"""
小批量测试新信源（每个方向5-10个）
验证内容质量和抓取成功率
"""
import yaml
import requests
from bs4 import BeautifulSoup
import feedparser
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# 选择要测试的信源（每个方向5-10个，优先选RSS源和有明确URL的博客）
TEST_SOURCE_IDS = [
    # 决策思维类 (direction: decision)
    '201',  # 刘润
    '203',  # Farnam Street (RSS)
    '204',  # James Clear (RSS)
    '205',  # Paul Graham (RSS)
    '206',  # 辉哥奇谭
    '208',  # Stratechery (RSS)
    '210',  # Morgan Housel (RSS)
    
    # 个人系统类 (direction: personal)
    '301',  # 少数派
    '303',  # Cal Newport (RSS)
    '306',  # 利器社区
    '308',  # Tiago Forte (RSS)
    '310',  # warfalcon
    
    # 中层管理类 (direction: management)
    '401',  # 华章管理
    '402',  # 哈佛商业评论
    '403',  # 中欧商业评论
    '404',  # 混沌学园
    '405',  # 笔记侠
]

def fetch_rss_content(url, max_items=5):
    """抓取RSS源内容"""
    try:
        feed = feedparser.parse(url)
        if feed.entries:
            entries = []
            for entry in feed.entries[:max_items]:
                entries.append({
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'summary': entry.get('summary', '')[:200] if entry.get('summary') else ''
                })
            return {
                'success': True,
                'type': 'rss',
                'count': len(entries),
                'items': entries
            }
        return {'success': False, 'type': 'rss', 'count': 0, 'error': '无内容'}
    except Exception as e:
        return {'success': False, 'type': 'rss', 'count': 0, 'error': str(e)[:100]}

def fetch_web_content(url, max_items=5):
    """抓取网页内容"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 尝试提取标题和链接
        titles = []
        for a in soup.find_all('a', href=True):
            title = a.get_text(strip=True)
            if title and len(title) > 10:
                titles.append({
                    'title': title[:100],
                    'link': a['href']
                })
        
        return {
            'success': True,
            'type': 'web',
            'count': len(titles[:max_items]),
            'items': titles[:max_items]
        }
    except Exception as e:
        return {'success': False, 'type': 'web', 'count': 0, 'error': str(e)[:100]}

def test_source(source):
    """测试单个信源"""
    source_id = source.get('id', '')
    name = source.get('name', '')
    url = source.get('url', '')
    source_type = source.get('type', '')
    direction = source.get('direction', '')
    
    print(f"\n🔍 测试 [{source_id}] {name} ({direction})")
    print(f"   URL: {url}")
    
    # 先检查URL是否可访问
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        if source_type == 'rss':
            response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        else:
            response = requests.get(url, headers=headers, timeout=10, stream=True)
            response.content[:1024]
        
        if response.status_code >= 400:
            return {
                'id': source_id,
                'name': name,
                'url': url,
                'direction': direction,
                'reachable': False,
                'status': response.status_code,
                'error': f'HTTP {response.status_code}'
            }
    except Exception as e:
        return {
            'id': source_id,
            'name': name,
            'url': url,
            'direction': direction,
            'reachable': False,
            'status': 'error',
            'error': str(e)[:50]
        }
    
    # 抓取内容
    if source_type == 'rss':
        result = fetch_rss_content(url)
    else:
        result = fetch_web_content(url)
    
    return {
        'id': source_id,
        'name': name,
        'url': url,
        'direction': direction,
        'reachable': True,
        'status': 'success',
        'content_success': result['success'],
        'content_count': result['count'],
        'content_type': result['type'],
        'error': result.get('error'),
        'sample_items': result.get('items', [])[:3]
    }

def main():
    # 加载信源配置
    config_path = '/home/admin/.openclaw/workspace/behavior_recorder_service/ai-pulse/config/sources.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    sources = config.get('sources', [])
    
    # 筛选要测试的信源
    test_sources = [s for s in sources if s.get('id') in TEST_SOURCE_IDS]
    
    print(f"=== 开始测试 {len(test_sources)} 个候选信源 ===")
    print(f"决策思维类: {len([s for s in test_sources if s.get('direction') == 'decision'])} 个")
    print(f"个人系统类: {len([s for s in test_sources if s.get('direction') == 'personal'])} 个")
    print(f"中层管理类: {len([s for s in test_sources if s.get('direction') == 'management'])} 个")
    
    # 使用线程池并发测试
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(test_source, source): source for source in test_sources}
        
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            
            status_icon = '✅' if result['reachable'] and result.get('content_success') else '❌'
            print(f"\n{status_icon} [{result['id']}] {result['name']} ({result['direction']})")
            if result['reachable']:
                print(f"   内容获取: {'成功' if result.get('content_success') else '失败'} ({result.get('content_count', 0)}条)")
                if result.get('sample_items'):
                    for item in result['sample_items'][:2]:
                        print(f"   - {item.get('title', '')[:60]}")
            else:
                print(f"   错误: {result['error']}")
    
    # 统计结果
    reachable = [r for r in results if r['reachable'] and r.get('content_success')]
    unreachable = [r for r in results if not r['reachable'] or not r.get('content_success')]
    
    print(f"\n\n=== 测试总结 ===")
    print(f"总计测试: {len(results)}")
    print(f"可用信源: {len(reachable)}")
    print(f"不可用信源: {len(unreachable)}")
    
    if unreachable:
        print(f"\n=== 不可用的信源 ===")
        for r in unreachable:
            print(f"[{r['id']}] {r['name']} ({r['direction']}): {r.get('error', '未知错误')}")
    
    if reachable:
        print(f"\n=== 推荐启用的信源 ===")
        for r in reachable:
            print(f"[{r['id']}] {r['name']} ({r['direction']}): {r.get('content_count', 0)}条内容")
    
    # 保存测试报告
    report_path = '/home/admin/.openclaw/workspace/behavior_recorder_service/ai-pulse/config/source_test_report.yaml'
    with open(report_path, 'w', encoding='utf-8') as f:
        yaml.dump({
            'test_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total': len(results),
            'reachable': len(reachable),
            'unreachable': len(unreachable),
            'recommended_sources': reachable,
            'unreachable_sources': unreachable
        }, f, allow_unicode=True, default_flow_style=False)
    
    print(f"\n测试报告已保存到: {report_path}")

if __name__ == '__main__':
    main()
