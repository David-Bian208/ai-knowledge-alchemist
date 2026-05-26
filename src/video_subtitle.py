"""
视频字幕提取模块（三层降级管道）
第1层：B站官方API / YouTube字幕 → 直接提取
第2层：yt-dlp抽音频 → Whisper ASR转写
第3层：标记"无法提取"，返回视频基本信息

用于将视频内容转为文字后进入 AI 评分流程
"""
import logging
import re
import json
from typing import Optional, Dict, List
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


class VideoSubtitleExtractor:
    """视频字幕提取器"""
    
    def __init__(self):
        self._yt_dlp_available = self._check_yt_dlp()
        self._whisper_available = False  # 默认不启用ASR
    
    def _check_yt_dlp(self) -> bool:
        """检查yt-dlp是否可用"""
        try:
            import yt_dlp
            return True
        except ImportError:
            logger.warning("yt-dlp 未安装，降级管道不可用")
            return False
    
    @property
    def available(self) -> bool:
        return self._yt_dlp_available
    
    def detect_platform(self, url: str) -> str:
        """检测视频平台"""
        try:
            parsed = urlparse(url)
            hostname = (parsed.hostname or "").lower()
            if "bilibili.com" in hostname:
                return "bilibili"
            elif "b23.tv" in hostname:
                return "bilibili_short"
            elif "youtube.com" in hostname:
                return "youtube"
            elif "youtu.be" in hostname:
                return "youtube_short"
            elif "douyin.com" in hostname or "iesdouyin.com" in hostname:
                return "douyin"
            elif "kuaishou.com" in hostname:
                return "kuaishou"
            return "unknown"
        except:
            return "unknown"
    
    def extract_subtitle(self, url: str) -> Dict:
        """
        提取视频字幕（三层降级管道）
        
        第1层：平台原生字幕（B站API / YouTube字幕）
        第2层：抽音频 + Whisper ASR
        第3层：返回视频基本信息
        
        Returns:
            {
                "success": bool,
                "title": str,
                "author": str,
                "subtitle_text": str,
                "subtitle_json": list,
                "has_subtitle": bool,
                "platform": str,
                "tier": int,  # 1=原生字幕, 2=ASR转写, 3=基本信息
                "error": str
            }
        """
        platform = self.detect_platform(url)
        logger.info(f"提取字幕: {url} (平台: {platform})")
        
        # ===== 第1层：原生字幕 =====
        if platform == "bilibili" or platform == "bilibili_short":
            return self._extract_bilibili(url)
        elif platform in ("youtube", "youtube_short"):
            return self._extract_youtube(url)
        
        # ===== 第2层：ASR转写（抖音/快手等） =====
        if self._yt_dlp_available:
            return self._extract_asr_fallback(url, platform)
        
        # ===== 第3层：无法提取 =====
        return {
            "success": False,
            "title": "",
            "author": "",
            "subtitle_text": "",
            "subtitle_json": [],
            "has_subtitle": False,
            "platform": platform,
            "tier": 3,
            "error": f"平台 {platform} 不支持自动提取"
        }
    
    # ===== B站官方API字幕提取 =====
    
    def _extract_bilibili(self, url: str) -> Dict:
        """
        B站字幕提取：调官方API
        链路：URL → bvid → aid/cid → 字幕JSON → 纯文本
        """
        try:
            # 解析bvid
            bvid = self._parse_bilibili_bvid(url)
            if not bvid:
                return self._error_result(url, "无法解析B站视频ID")
            
            logger.info(f"B站字幕提取: bvid={bvid}")
            
            # 获取视频信息（aid, cid, title）
            video_info = self._get_bilibili_video_info(bvid)
            if not video_info:
                return self._error_result(url, "无法获取B站视频信息")
            
            aid = video_info.get("aid")
            cid = video_info.get("cid")
            title = video_info.get("title", "")
            author = video_info.get("owner", {}).get("name", "")
            
            logger.info(f"B站视频: {title} (aid={aid}, cid={cid})")
            
            # 获取字幕列表
            subtitles = self._get_bilibili_subtitles(aid, cid)
            if not subtitles:
                # 无字幕，返回视频基本信息
                logger.info(f"B站视频无字幕: {title}")
                return {
                    "success": True,
                    "title": title,
                    "author": author,
                    "subtitle_text": "",
                    "subtitle_json": [],
                    "has_subtitle": False,
                    "platform": "bilibili",
                    "tier": 3,
                    "description": video_info.get("desc", "")[:500],
                }
            
            # 下载并解析字幕
            for sub in subtitles:
                subtitle_url = sub.get("subtitle_url", "")
                if subtitle_url:
                    if not subtitle_url.startswith("http"):
                        subtitle_url = "https:" + subtitle_url
                    
                    subtitle_json = self._download_json(subtitle_url)
                    if subtitle_json:
                        parsed = self._parse_bilibili_subtitle(subtitle_json)
                        logger.info(f"B站字幕提取成功: {title} ({len(parsed['text'])}字)")
                        return {
                            "success": True,
                            "title": title,
                            "author": author,
                            "subtitle_text": parsed["text"],
                            "subtitle_json": parsed["segments"],
                            "has_subtitle": True,
                            "platform": "bilibili",
                            "tier": 1,
                        }
            
            return self._error_result(url, "字幕下载失败")
            
        except Exception as e:
            logger.error(f"B站字幕提取异常: {e}")
            return self._error_result(url, str(e))
    
    def _parse_bilibili_bvid(self, url: str) -> Optional[str]:
        """从URL解析B站bvid"""
        # 匹配 /video/BVxxxxxx 格式
        match = re.search(r'/video/(BV\w+)', url)
        if match:
            return match.group(1)
        # 匹配 BVxxxxxx 直接出现在URL中
        match = re.search(r'(BV\w{10})', url)
        if match:
            return match.group(1)
        return None
    
    def _get_bilibili_video_info(self, bvid: str) -> Optional[Dict]:
        """获取B站视频信息"""
        import requests
        try:
            url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.bilibili.com/",
            }
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    return data.get("data", {})
            return None
        except Exception as e:
            logger.warning(f"获取B站视频信息失败: {e}")
            return None
    
    def _get_bilibili_subtitles(self, aid: int, cid: int) -> Optional[List[Dict]]:
        """获取B站字幕列表"""
        import requests
        try:
            url = f"https://api.bilibili.com/x/player/v2?aid={aid}&cid={cid}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.bilibili.com/",
            }
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    subtitle_data = data.get("data", {}).get("subtitle", {})
                    subtitles = subtitle_data.get("subtitles", [])
                    if subtitles:
                        logger.info(f"找到 {len(subtitles)} 条字幕")
                    return subtitles
            return None
        except Exception as e:
            logger.warning(f"获取B站字幕列表失败: {e}")
            return None
    
    def _parse_bilibili_subtitle(self, subtitle_json: Dict) -> Dict:
        """解析B站字幕JSON"""
        segments = []
        body = subtitle_json.get("body", [])
        
        for item in body:
            segments.append({
                "start": item.get("from", 0),
                "end": item.get("to", 0),
                "text": item.get("content", "")
            })
        
        text = "\n".join(s["text"] for s in segments if s["text"].strip())
        return {"text": text, "segments": segments}
    
    # ===== YouTube字幕提取 =====
    
    def _extract_youtube(self, url: str) -> Dict:
        """YouTube字幕提取（通过yt-dlp）"""
        if not self._yt_dlp_available:
            return self._error_result(url, "yt-dlp未安装")
        
        import yt_dlp
        try:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["zh-Hans", "zh-CN", "zh", "en"],
                "subtitlesformat": "vtt",
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    return self._error_result(url, "无法获取视频信息")
                
                title = info.get("title", "")
                author = info.get("uploader", "")
                
                # 获取字幕
                subtitles = info.get("subtitles", {}) or {}
                auto_captions = info.get("automatic_captions", {}) or {}
                
                zh_subtitle = None
                for lang in ["zh-Hans", "zh-CN", "zh"]:
                    if lang in subtitles:
                        zh_subtitle = subtitles[lang]
                        break
                
                if not zh_subtitle:
                    for lang in ["zh-Hans", "zh-CN", "zh", "en"]:
                        if lang in auto_captions:
                            zh_subtitle = auto_captions[lang]
                            break
                
                if not zh_subtitle:
                    logger.info(f"YouTube视频无字幕: {title}")
                    return {
                        "success": True,
                        "title": title,
                        "author": author,
                        "subtitle_text": "",
                        "subtitle_json": [],
                        "has_subtitle": False,
                        "platform": "youtube",
                        "tier": 3,
                        "description": (info.get("description") or "")[:500],
                    }
                
                # 下载字幕
                for sub in zh_subtitle:
                    if sub.get("ext") in ("vtt", "srt"):
                        sub_url = sub.get("url", "")
                        if sub_url:
                            subtitle_text = self._download_subtitle(sub_url)
                            if subtitle_text:
                                parsed = self._parse_subtitle(subtitle_text, sub.get("ext", "vtt"))
                                logger.info(f"YouTube字幕提取成功: {title} ({len(parsed['text'])}字)")
                                return {
                                    "success": True,
                                    "title": title,
                                    "author": author,
                                    "subtitle_text": parsed["text"],
                                    "subtitle_json": parsed["segments"],
                                    "has_subtitle": True,
                                    "platform": "youtube",
                                    "tier": 1,
                                }
                
                return self._error_result(url, "字幕下载失败")
                
        except Exception as e:
            logger.error(f"YouTube字幕提取异常: {e}")
            return self._error_result(url, str(e))
    
    # ===== 降级管道：抽音频 + ASR =====
    
    def _extract_asr_fallback(self, url: str, platform: str) -> Dict:
        """降级管道：yt-dlp抽音频 → Whisper ASR转写"""
        # 此方法需要部署Whisper模型，默认不启用
        # 可通过配置开关启用
        return self._error_result(url, f"平台 {platform} 需要ASR服务，暂未启用")
    
    # ===== 通用工具方法 =====
    
    def _download_json(self, url: str) -> Optional[Dict]:
        """下载并解析JSON"""
        import requests
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception as e:
            logger.warning(f"下载JSON失败: {e}")
            return None
    
    def _download_subtitle(self, url: str) -> Optional[str]:
        """下载字幕文件"""
        import requests
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                return resp.text
            return None
        except Exception as e:
            logger.warning(f"下载字幕失败: {e}")
            return None
    
    def _parse_subtitle(self, subtitle_text: str, ext: str) -> Dict:
        """解析字幕文件（VTT/SRT）"""
        segments = []
        
        if ext == "vtt":
            segments = self._parse_vtt(subtitle_text)
        elif ext == "srt":
            segments = self._parse_srt(subtitle_text)
        else:
            segments = self._parse_vtt(subtitle_text)
        
        text = "\n".join(s["text"] for s in segments if s["text"].strip())
        return {"text": text, "segments": segments}
    
    def _parse_vtt(self, text: str) -> list:
        """解析 VTT 字幕"""
        segments = []
        lines = text.strip().split("\n")
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            if "-->" in line:
                time_parts = line.split("-->")
                if len(time_parts) == 2:
                    start = self._parse_timestamp(time_parts[0].strip())
                    end = self._parse_timestamp(time_parts[1].strip())
                    i += 1
                    text_lines = []
                    while i < len(lines) and lines[i].strip() and "-->" not in lines[i]:
                        text_lines.append(lines[i].strip())
                        i += 1
                    if text_lines:
                        segments.append({
                            "start": start,
                            "end": end,
                            "text": " ".join(text_lines)
                        })
                    continue
            i += 1
        
        return segments
    
    def _parse_srt(self, text: str) -> list:
        """解析 SRT 字幕"""
        segments = []
        lines = text.strip().split("\n")
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            if line.isdigit():
                i += 1
                if i < len(lines) and "-->" in lines[i]:
                    time_parts = lines[i].split("-->")
                    start = self._parse_srt_timestamp(time_parts[0].strip())
                    end = self._parse_srt_timestamp(time_parts[1].strip())
                    i += 1
                    text_lines = []
                    while i < len(lines) and lines[i].strip():
                        text_lines.append(lines[i].strip())
                        i += 1
                    if text_lines:
                        segments.append({
                            "start": start,
                            "end": end,
                            "text": " ".join(text_lines)
                        })
            else:
                i += 1
        
        return segments
    
    def _parse_timestamp(self, ts: str) -> float:
        """解析 VTT 时间戳"""
        try:
            parts = ts.replace(",", ".").split(":")
            if len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + float(s)
            elif len(parts) == 2:
                m, s = parts
                return int(m) * 60 + float(s)
            return 0
        except:
            return 0
    
    def _parse_srt_timestamp(self, ts: str) -> float:
        """解析 SRT 时间戳"""
        return self._parse_timestamp(ts)
    
    def _error_result(self, url: str, error: str) -> Dict:
        """构造错误结果"""
        platform = self.detect_platform(url)
        return {
            "success": False,
            "title": "",
            "author": "",
            "subtitle_text": "",
            "subtitle_json": [],
            "has_subtitle": False,
            "platform": platform,
            "tier": 0,
            "error": error
        }
