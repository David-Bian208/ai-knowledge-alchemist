"""
信源有效性验证脚本
检查所有enabled=true的信源是否可访问
"""
import yaml
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def check_source(source):
    """检查单个信源是否可访问"""
    url = source.get('url', '')
    name = source.get('name', '')
    source_id = source.get('id', '')
    source_type = source.get('type', '')
    
    if not url:
        return {
            'id': source_id,
            'name': name,
            'url': url,
            'status': 'no_url',
            'reachable': False,
            'error': '无URL'
        }
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        
        # RSS源使用HEAD请求，web源使用GET
        if source_type == 'rss':
            response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        else:
            response = requests.get(url, headers=headers, timeout=10, stream=True)
            # 只读取前1KB
            response.content[:1024]
        
        status_code = response.status_code
        reachable = status_code < 400
        
        return {
            'id': source_id,
            'name': name,
            'url': url,
            'status': status_code,
            'reachable': reachable,
            'error': None if reachable else f'HTTP {status_code}'
        }
    except requests.exceptions.Timeout:
        return {
            'id': source_id,
            'name': name,
            'url': url,
            'status': 'timeout',
            'reachable': False,
            'error': '超时'
        }
    except requests.exceptions.ConnectionError:
        return {
            'id': source_id,
            'name': name,
            'url': url,
            'status': 'connection_error',
            'reachable': False,
            'error': '连接失败'
        }
    except Exception as e:
        return {
            'id': source_id,
            'name': name,
            'url': url,
            'status': 'error',
            'reachable': False,
            'error': str(e)[:50]
        }

def main():
    # 加载信源配置
    config_path = '/home/admin/.openclaw/workspace/behavior_recorder_service/ai-pulse/config/sources.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    sources = config.get('sources', [])
    
    # 只检查enabled=true的信源
    enabled_sources = [s for s in sources if s.get('enabled', False)]
    print(f"找到 {len(enabled_sources)} 个已启用的信源")
    
    # 使用线程池并发检查
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_source, source): source for source in enabled_sources}
        
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            status_icon = '✅' if result['reachable'] else '❌'
            print(f"{status_icon} [{result['id']}] {result['name']}: {result['status']} {result['error'] or ''}")
    
    # 统计结果
    reachable = [r for r in results if r['reachable']]
    unreachable = [r for r in results if not r['reachable']]
    
    print(f"\n=== 验证结果 ===")
    print(f"总计: {len(results)}")
    print(f"可访问: {len(reachable)}")
    print(f"不可访问: {len(unreachable)}")
    
    if unreachable:
        print(f"\n=== 不可访问的信源列表 ===")
        for r in unreachable:
            print(f"[{r['id']}] {r['name']}: {r['error']} ({r['url']})")
    
    # 保存验证报告
    report_path = '/home/admin/.openclaw/workspace/behavior_recorder_service/ai-pulse/config/source_validation_report.yaml'
    with open(report_path, 'w', encoding='utf-8') as f:
        yaml.dump({
            'validation_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total': len(results),
            'reachable': len(reachable),
            'unreachable': len(unreachable),
            'unreachable_sources': unreachable
        }, f, allow_unicode=True, default_flow_style=False)
    
    print(f"\n验证报告已保存到: {report_path}")

if __name__ == '__main__':
    main()
