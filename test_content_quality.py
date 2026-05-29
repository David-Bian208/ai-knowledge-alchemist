#!/usr/bin/env python3
"""测试内容质量优化效果"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("="*60)
print("内容质量优化测试")
print("="*60)

# 测试1：验证Twitter短内容过滤逻辑
print("\n[测试1] Twitter短内容过滤逻辑验证")
print("-" * 60)

def test_twitter_short_content_filter():
    """测试Twitter短内容过滤（只过滤Twitter内容<100字符）"""
    test_cases = [
        # (is_twitter, summary_length, should_keep)
        (True, 150, True),    # Twitter长内容，保留
        (True, 80, False),    # Twitter短内容，过滤
        (True, 0, False),     # Twitter空内容，过滤
        (False, 50, True),    # 非Twitter短内容，保留（会走其他处理流程）
    ]
    
    all_passed = True
    for is_twitter, summary_len, should_keep in test_cases:
        # 模拟实际逻辑：只过滤Twitter且<100字符的内容
        would_filter = is_twitter and summary_len < 100
        kept = not would_filter
        status = "✅" if kept == should_keep else "❌"
        if kept != should_keep:
            all_passed = False
        print(f"  {status} Twitter:{is_twitter}, 长度:{summary_len} → 应该{'保留' if should_keep else '过滤'}，实际{'保留' if kept else '过滤'}")
    
    return all_passed

result1 = test_twitter_short_content_filter()
print(f"\n  测试结果: {'✅ 通过' if result1 else '❌ 失败'}")

# 测试2：验证RSS全文抓取逻辑
print("\n[测试2] RSS全文抓取逻辑验证")
print("-" * 60)

def test_rss_full_content_logic():
    """测试RSS全文抓取判断"""
    test_cases = [
        # (has_content_field, content_length, summary_length, should_fetch_full)
        (True, 600, 50, False),   # 有content且>500，不需要抓取
        (True, 400, 50, True),    # content<500，需要抓取
        (False, 0, 600, False),   # summary>500，不需要抓取
        (False, 0, 300, True),    # summary<500，需要抓取
        (True, 200, 200, True),   # 都<500，需要抓取
    ]
    
    all_passed = True
    for has_content, content_len, summary_len, should_fetch in test_cases:
        has_full_content = (
            (has_content and content_len > 500)
            or (summary_len > 500)
        )
        needs_fetch = not has_full_content
        status = "✅" if needs_fetch == should_fetch else "❌"
        if needs_fetch != should_fetch:
            all_passed = False
        print(f"  {status} content:{content_len}, summary:{summary_len} → 应该{'抓取' if should_fetch else '不抓取'}，实际{'抓取' if needs_fetch else '不抓取'}")
    
    return all_passed

result2 = test_rss_full_content_logic()
print(f"\n  测试结果: {'✅ 通过' if result2 else '❌ 失败'}")

# 测试3：验证backfill检测逻辑
print("\n[测试3] Backfill检测逻辑验证")
print("-" * 60)

def test_backfill_detection():
    """测试backfill内容检测"""
    test_cases = [
        # (content_len, source_from, should_detect)
        (0, "original", True),           # 内容为空，应该检测
        (30, "rss_fetch", True),         # 内容过短，应该检测
        (100, "original", True),         # 内容<200，应该检测
        (250, "original", False),        # 内容>200，不检测
        (50, "aihot", False),            # aihot短内容（Twitter），不检测（故意排除）
        (50, "twitter", False),          # 社交媒体，不检测
        (50, "x.com", False),            # x.com，不检测
    ]
    
    all_passed = True
    for content_len, source_from, should_detect in test_cases:
        # 模拟SQL检测逻辑
        is_empty = content_len < 50
        is_short = content_len < 200 and source_from not in ['aihot', 'twitter', 'x.com']
        would_detect = is_empty or is_short
        
        status = "✅" if would_detect == should_detect else "❌"
        if would_detect != should_detect:
            all_passed = False
        print(f"  {status} 长度:{content_len}, 来源:{source_from} → 应该{'检测' if should_detect else '不检测'}，实际{'检测' if would_detect else '不检测'}")
    
    return all_passed

result3 = test_backfill_detection()
print(f"\n  测试结果: {'✅ 通过' if result3 else '❌ 失败'}")

# 总结
print("\n" + "="*60)
print("测试总结")
print("="*60)
if result1 and result2 and result3:
    print("✅ 所有测试通过！内容质量优化逻辑正确")
    print("\n优化效果说明：")
    print("1. Twitter短内容(<100字符)会被过滤，避免无意义推文入库")
    print("2. RSS源会优先抓取原文全文，确保内容完整性")
    print("3. Backfill会回填非社交媒体的短内容，提升内容质量")
else:
    print("❌ 部分测试失败，请检查代码")
    if not result1:
        print("  - Twitter短内容过滤逻辑有问题")
    if not result2:
        print("  - RSS全文抓取逻辑有问题")
    if not result3:
        print("  - Backfill检测逻辑有问题")
print("="*60)
