"""
批量启用测试通过的信源
"""
import yaml

# 测试通过需要启用的信源ID列表
ENABLE_SOURCE_IDS = [
    '203',  # Farnam Street
    '204',  # James Clear
    '208',  # Stratechery
    '301',  # 少数派
    '303',  # Cal Newport
    '306',  # 利器社区
    '403',  # 中欧商业评论
    '308',  # Tiago Forte
]

config_path = '/home/admin/.openclaw/workspace/behavior_recorder_service/ai-pulse/config/sources.yaml'

with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

sources = config.get('sources', [])

# 启用测试通过的信源
for source in sources:
    if source.get('id') in ENABLE_SOURCE_IDS:
        old_enabled = source.get('enabled', False)
        if not old_enabled:
            source['enabled'] = True
            # 设置较长的抓取间隔，因为这些是RSS源
            if source.get('type') == 'rss':
                source['fetch_interval'] = 120
            print(f"✅ 启用 [{source['id']}] {source['name']} (interval: {source['fetch_interval']}min)")

# 保存配置
with open(config_path, 'w', encoding='utf-8') as f:
    yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

print(f"\n已更新配置文件: {config_path}")
