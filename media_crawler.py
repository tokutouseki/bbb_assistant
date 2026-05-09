"""
媒体资源爬取脚本
================
功能说明：
1. 读取指定目录下所有JSON文件
2. 提取文件中media_resources字段记录的媒体资源网址
3. 下载对应的图片资源到JSON文件所在目录的media子文件夹中
4. 下载的图片使用对应JSON文件名命名
5. 重复文件使用"_*"格式重命名（*为数字序号，从1开始递增）
6. 包含完善的错误处理和详细的日志记录
7. 支持下载速度限制，防止占用过多带宽
8. 支持断点续传，按Ctrl+C暂停并保存进度，下次继续

使用方法：
    python media_crawler.py [--data-dir DATA_DIR] [--max-speed MAX_SPEED] [--resume]

参数说明：
    --data-dir: JSON文件所在目录，默认为脚本所在目录的data文件夹
    --max-speed: 最大下载速度，单位MB/s，默认为1.0
    --resume: 从上次断点继续下载

示例：
    python media_crawler.py --data-dir "d:\\TokusCode\\bbb_assistant\\data"
    python media_crawler.py --data-dir "d:\\TokusCode\\bbb_assistant\\data" --max-speed 2.0
    python media_crawler.py --data-dir "d:\\TokusCode\\bbb_assistant\\data" --resume

作者：AI Assistant
创建时间：2024
"""

import os
import sys
import json
import argparse
import logging
import hashlib
import time
import re
import signal
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set
from urllib.parse import urlparse, unquote
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("错误：缺少requests库，请运行: pip install requests")
    sys.exit(1)


class SpeedLimiter:
    """下载速度限制器"""
    
    def __init__(self, max_speed_bytes_per_sec: float):
        self.max_speed = max_speed_bytes_per_sec
        self.lock = threading.Lock()
        self.last_check_time = time.time()
        self.bytes_downloaded = 0
    
    def wait_if_needed(self, chunk_size: int):
        """如果下载速度超过限制，则等待"""
        with self.lock:
            current_time = time.time()
            self.bytes_downloaded += chunk_size
            
            elapsed = current_time - self.last_check_time
            
            if elapsed >= 0.1:
                current_speed = self.bytes_downloaded / elapsed
                
                if current_speed > self.max_speed:
                    expected_time = self.bytes_downloaded / self.max_speed
                    sleep_time = expected_time - elapsed
                    
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                
                self.last_check_time = time.time()
                self.bytes_downloaded = 0


class CheckpointManager:
    """断点管理器"""
    
    def __init__(self, checkpoint_file: Path):
        self.checkpoint_file = checkpoint_file
        self.lock = threading.Lock()
        self.downloaded_urls: Set[str] = set()
        self._save_counter = 0
        self._save_interval = 10
        self._last_save_time = time.time()
        self._save_min_interval = 5
        self._load_checkpoint()
    
    def _load_checkpoint(self):
        """加载断点文件"""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.downloaded_urls = set(data.get('downloaded_urls', []))
            except (json.JSONDecodeError, IOError):
                self.downloaded_urls = set()
    
    def save_checkpoint(self, stats: Dict = None, force: bool = False):
        """保存断点文件"""
        with self.lock:
            try:
                self._save_counter += 1
                current_time = time.time()
                time_since_last_save = current_time - self._last_save_time
                
                if not force and self._save_counter < self._save_interval and time_since_last_save < self._save_min_interval:
                    return
                
                self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
                
                data = {
                    'last_update': datetime.now().isoformat(),
                    'downloaded_urls': list(self.downloaded_urls),
                    'statistics': stats or {}
                }
                with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                self._save_counter = 0
                self._last_save_time = current_time
            except IOError:
                pass
    
    def is_downloaded(self, url: str) -> bool:
        """检查URL是否已下载"""
        with self.lock:
            return url in self.downloaded_urls
    
    def mark_downloaded(self, url: str, stats: Dict = None):
        """标记URL为已下载并尝试保存断点"""
        with self.lock:
            self.downloaded_urls.add(url)
            self._save_counter += 1
            
            current_time = time.time()
            time_since_last_save = current_time - self._last_save_time
            
            if self._save_counter >= self._save_interval or time_since_last_save >= self._save_min_interval:
                try:
                    self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
                    data = {
                        'last_update': datetime.now().isoformat(),
                        'downloaded_urls': list(self.downloaded_urls),
                        'statistics': stats or {}
                    }
                    with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    self._save_counter = 0
                    self._last_save_time = current_time
                except IOError:
                    pass
    
    def get_progress(self) -> Tuple[int, int]:
        """获取进度信息：已下载数量，总数量"""
        with self.lock:
            return len(self.downloaded_urls), 0


class MediaCrawler:
    """媒体资源爬取器"""
    
    def __init__(self, data_dir: str, max_workers: int = 5, timeout: int = 30, 
                 max_speed_mb: float = 1.0, resume: bool = False,
                 subdir_filter: str = None,
                 video_only: bool = False):
        self.data_dir = Path(data_dir)
        self.max_workers = max_workers
        self.timeout = timeout
        self.max_speed_bytes = max_speed_mb * 1024 * 1024
        self.resume = resume
        self.subdir_filter = subdir_filter
        self.video_only = video_only
        
        self.session = self._create_session()
        
        self.lock = threading.Lock()
        
        self.speed_limiter = SpeedLimiter(self.max_speed_bytes)
        
        checkpoint_file = self.data_dir / 'logs' / 'checkpoint.json'
        self.checkpoint = CheckpointManager(checkpoint_file)
        
        self.stats = {
            'total_files': 0,
            'total_resources': 0,
            'success_count': 0,
            'failed_count': 0,
            'skipped_count': 0,
            'duplicate_count': 0,
            'already_exists_count': 0,
            'categories': {}
        }
        
        self.download_log: List[Dict] = []
        
        self._stop_event = threading.Event()
        self._setup_signal_handler()
        
        self._setup_logging()
    
    def _setup_signal_handler(self):
        """设置信号处理器，用于捕获Ctrl+C"""
        self._original_sigint = signal.getsignal(signal.SIGINT)
        self._original_sigterm = signal.getsignal(signal.SIGTERM)
        
        def signal_handler(signum, frame):
            self._handle_interrupt(signum, frame)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _handle_interrupt(self, signum, frame):
        """处理中断信号"""
        if not self._stop_event.is_set():
            self._stop_event.set()
            self.logger.warning("")
            self.logger.warning("=" * 60)
            self.logger.warning("收到中断信号，正在保存断点...")
            self.logger.warning("请稍候，等待当前下载完成...")
            self.logger.warning("=" * 60)
        else:
            self.logger.warning("强制退出...")
            if self._original_sigint:
                signal.signal(signal.SIGINT, self._original_sigint)
                os.kill(os.getpid(), signal.SIGINT)
    
    def _create_session(self) -> requests.Session:
        """创建带有重试机制的请求会话"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://baike.mihoyo.com/'
        })
        
        return session
    
    def _setup_logging(self):
        """配置日志系统"""
        log_dir = self.data_dir / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = log_dir / f'crawl_{timestamp}.log'
        
        self.logger = logging.getLogger('MediaCrawler')
        self.logger.setLevel(logging.DEBUG)
        
        self.logger.handlers.clear()
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.log_file = log_file
    
    def _get_file_hash(self, file_path: Path) -> str:
        """计算文件的MD5哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _get_extension_from_url(self, url: str, resource_type: str = 'image') -> str:
        """从URL中提取文件扩展名"""
        parsed = urlparse(url)
        path = unquote(parsed.path)
        
        ext = Path(path).suffix.lower()
        
        image_exts = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg']
        video_exts = ['.mp4', '.webm', '.avi', '.mov', '.mkv', '.flv', '.wmv']
        
        if resource_type == 'video':
            if ext in video_exts:
                return ext
            return '.mp4'
        
        if ext in image_exts:
            return ext
        
        return '.png'
    
    def _get_media_output_dir(self, json_file_path: Path) -> Path:
        """获取JSON文件对应的media输出目录"""
        json_parent_dir = json_file_path.parent
        media_dir = json_parent_dir / 'media'
        return media_dir
    
    def _generate_unique_filename(self, base_name: str, extension: str, output_dir: Path) -> Tuple[Path, bool]:
        """
        生成唯一的文件名
        返回：(文件路径, 是否为重复文件)
        """
        filename = f"{base_name}{extension}"
        file_path = output_dir / filename
        
        if not file_path.exists():
            return file_path, False
        
        counter = 1
        while True:
            filename = f"{base_name}_{counter}{extension}"
            file_path = output_dir / filename
            if not file_path.exists():
                return file_path, True
            counter += 1
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除非法字符"""
        illegal_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(illegal_chars, '_', filename)
        sanitized = sanitized.strip('. ')
        if not sanitized:
            sanitized = 'unnamed'
        return sanitized
    
    def _get_category_path(self, json_file_path: Path) -> str:
        """获取JSON文件相对于data目录的分类路径"""
        try:
            relative_path = json_file_path.relative_to(self.data_dir)
            parts = list(relative_path.parts[:-1])
            if parts:
                return '/'.join(parts)
            return 'root'
        except ValueError:
            return 'unknown'
    
    def _download_resource(self, url: str, json_file_path: Path, resource_index: int, resource_type: str = 'image') -> Dict:
        """
        下载单个资源
        返回下载结果字典
        """
        result = {
            'json_file': str(json_file_path),
            'url': url,
            'status': 'pending',
            'local_path': None,
            'error_message': None,
            'file_size': None,
            'is_duplicate': False,
            'resource_type': resource_type,
            'timestamp': datetime.now().isoformat()
        }
        
        if self._stop_event.is_set():
            result['status'] = 'interrupted'
            result['error_message'] = '任务被中断'
            return result
        
        if self.checkpoint.is_downloaded(url):
            result['status'] = 'already_exists'
            with self.lock:
                self.stats['already_exists_count'] += 1
            self.logger.debug(f"跳过已下载: {url}")
            return result
        
        try:
            json_filename = json_file_path.stem
            base_name = self._sanitize_filename(json_filename)
            
            if resource_index > 0:
                base_name = f"{base_name}_{resource_index}"
            
            extension = self._get_extension_from_url(url, resource_type)
            
            output_dir = self._get_media_output_dir(json_file_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            category = self._get_category_path(json_file_path)
            
            self.logger.debug(f"开始下载{resource_type}: {url} -> {category}")
            
            response = self.session.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '')
            image_exts = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg']
            video_exts = ['.mp4', '.webm', '.avi', '.mov', '.mkv', '.flv', '.wmv']
            
            if resource_type == 'video':
                if 'video' not in content_type and not any(ext in url.lower() for ext in video_exts):
                    self.logger.warning(f"URL可能不是视频资源: {url} (Content-Type: {content_type})")
            else:
                if 'image' not in content_type and not any(ext in url.lower() for ext in image_exts):
                    self.logger.warning(f"URL可能不是图片资源: {url} (Content-Type: {content_type})")
            
            file_path, is_duplicate = self._generate_unique_filename(base_name, extension, output_dir)
            
            chunk_size = 8192
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if self._stop_event.is_set():
                        f.close()
                        if file_path.exists():
                            file_path.unlink()
                        result['status'] = 'interrupted'
                        result['error_message'] = '任务被中断'
                        return result
                    
                    if chunk:
                        f.write(chunk)
                        self.speed_limiter.wait_if_needed(len(chunk))
            
            file_size = file_path.stat().st_size
            
            result['status'] = 'success'
            result['local_path'] = str(file_path)
            result['file_size'] = file_size
            result['is_duplicate'] = is_duplicate
            result['category'] = category
            
            self.checkpoint.mark_downloaded(url, self.stats)
            
            with self.lock:
                self.stats['success_count'] += 1
                if is_duplicate:
                    self.stats['duplicate_count'] += 1
                if category not in self.stats['categories']:
                    self.stats['categories'][category] = {'success': 0, 'failed': 0}
                self.stats['categories'][category]['success'] += 1
            
            relative_output = file_path.relative_to(self.data_dir)
            self.logger.info(f"下载成功: {relative_output} ({self._format_size(file_size)})")
            
        except requests.exceptions.Timeout:
            result['status'] = 'failed'
            result['error_message'] = '请求超时'
            with self.lock:
                self.stats['failed_count'] += 1
            self.logger.error(f"下载失败 (超时): {url}")
            
        except requests.exceptions.ConnectionError as e:
            result['status'] = 'failed'
            result['error_message'] = f'连接错误: {str(e)}'
            with self.lock:
                self.stats['failed_count'] += 1
            self.logger.error(f"下载失败 (连接错误): {url} - {e}")
            
        except requests.exceptions.HTTPError as e:
            result['status'] = 'failed'
            result['error_message'] = f'HTTP错误: {str(e)}'
            with self.lock:
                self.stats['failed_count'] += 1
            self.logger.error(f"下载失败 (HTTP错误): {url} - {e}")
            
        except IOError as e:
            result['status'] = 'failed'
            result['error_message'] = f'文件写入错误: {str(e)}'
            with self.lock:
                self.stats['failed_count'] += 1
            self.logger.error(f"下载失败 (文件写入错误): {url} - {e}")
            
        except Exception as e:
            result['status'] = 'failed'
            result['error_message'] = f'未知错误: {str(e)}'
            with self.lock:
                self.stats['failed_count'] += 1
            self.logger.error(f"下载失败 (未知错误): {url} - {e}")
        
        return result
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"
    
    def _process_json_file(self, json_path: Path) -> List[Dict]:
        """处理单个JSON文件，提取并下载所有媒体资源"""
        results = []
        
        if self._stop_event.is_set():
            return results
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            media_resources = data.get('media_resources', [])
            
            if not media_resources:
                self.logger.debug(f"文件无媒体资源: {json_path.name}")
                with self.lock:
                    self.stats['skipped_count'] += 1
                return results
            
            with self.lock:
                self.stats['total_resources'] += len(media_resources)
            
            for idx, resource in enumerate(media_resources):
                if self._stop_event.is_set():
                    break
                
                url = resource.get('url', '')
                resource_type = resource.get('type', 'image')
                
                if not url:
                    self.logger.warning(f"资源缺少URL: {json_path.name} - 索引 {idx}")
                    continue
                
                if self.video_only and resource_type != 'video':
                    self.logger.debug(f"跳过非视频资源: {url} (类型: {resource_type})")
                    continue
                
                if resource_type not in ['image', 'video']:
                    self.logger.debug(f"跳过不支持的资源类型: {url} (类型: {resource_type})")
                    continue
                
                result = self._download_resource(url, json_path, idx, resource_type)
                results.append(result)
                
                time.sleep(0.1)
                
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析错误: {json_path} - {e}")
        except IOError as e:
            self.logger.error(f"文件读取错误: {json_path} - {e}")
        except Exception as e:
            self.logger.error(f"处理文件时发生错误: {json_path} - {e}")
        
        return results
    
    def crawl(self):
        """执行爬取任务"""
        start_time = datetime.now()
        
        self.logger.info("=" * 60)
        self.logger.info("媒体资源爬取任务开始")
        self.logger.info(f"数据目录: {self.data_dir}")
        self.logger.info(f"下载速度限制: {self.max_speed_bytes / 1024 / 1024:.2f} MB/s")
        
        if self.subdir_filter:
            self.logger.info(f"目录过滤: {self.subdir_filter}")
        
        if self.video_only:
            self.logger.info("仅下载视频资源")
        
        self.logger.info("媒体资源保存到各JSON文件所在目录的media子文件夹中")
        
        if self.resume:
            already_downloaded = len(self.checkpoint.downloaded_urls)
            self.logger.info(f"断点续传模式: 已下载 {already_downloaded} 个资源")
        
        self.logger.info("=" * 60)
        
        if not self.data_dir.exists():
            self.logger.error(f"数据目录不存在: {self.data_dir}")
            return
        
        json_files = list(self.data_dir.rglob('*.json'))
        json_files = [f for f in json_files if 'logs' not in f.parts]
        
        if self.subdir_filter:
            filter_path = self.subdir_filter.replace('\\', '/')
            json_files = [f for f in json_files if filter_path in str(f).replace('\\', '/')]
        
        self.stats['total_files'] = len(json_files)
        
        self.logger.info(f"发现 {len(json_files)} 个JSON文件")
        
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self._process_json_file, json_file): json_file
                    for json_file in json_files
                }
                
                for future in as_completed(futures):
                    if self._stop_event.is_set():
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    
                    json_file = futures[future]
                    try:
                        results = future.result()
                        with self.lock:
                            self.download_log.extend(results)
                    except Exception as e:
                        self.logger.error(f"处理文件时发生异常: {json_file} - {e}")
        
        except KeyboardInterrupt:
            pass
        
        finally:
            end_time = datetime.now()
            duration = end_time - start_time
            
            self.checkpoint.save_checkpoint(self.stats)
            
            if self._stop_event.is_set():
                self.logger.warning("")
                self.logger.warning("=" * 60)
                self.logger.warning("任务已暂停，断点已保存")
                self.logger.warning("使用 --resume 参数继续下载")
                self.logger.warning("=" * 60)
            
            self._generate_report(start_time, end_time, duration)
    
    def _generate_report(self, start_time: datetime, end_time: datetime, duration):
        """生成爬取报告"""
        report_lines = [
            "",
            "=" * 60,
            "爬取任务完成报告" if not self._stop_event.is_set() else "爬取任务暂停报告",
            "=" * 60,
            f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"总耗时: {duration}",
            "",
            "统计信息:",
            f"  - 处理JSON文件数: {self.stats['total_files']}",
            f"  - 发现媒体资源数: {self.stats['total_resources']}",
            f"  - 成功下载数: {self.stats['success_count']}",
            f"  - 下载失败数: {self.stats['failed_count']}",
            f"  - 跳过文件数: {self.stats['skipped_count']}",
            f"  - 重复文件数: {self.stats['duplicate_count']}",
            f"  - 已存在跳过数: {self.stats['already_exists_count']}",
            "",
            "分类统计:",
        ]
        
        for category, counts in sorted(self.stats['categories'].items()):
            report_lines.append(f"  - {category}: 成功 {counts['success']}, 失败 {counts.get('failed', 0)}")
        
        report_lines.append("=" * 60)
        
        report = '\n'.join(report_lines)
        self.logger.info(report)
        
        log_dir = self.data_dir / 'logs'
        report_file = log_dir / f'report_{end_time.strftime("%Y%m%d_%H%M%S")}.json'
        report_data = {
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': duration.total_seconds(),
            'statistics': self.stats,
            'download_log': self.download_log
        }
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            self.logger.info(f"详细报告已保存: {report_file}")
        except IOError as e:
            self.logger.error(f"保存报告失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='媒体资源爬取脚本 - 从JSON文件中提取并下载媒体资源',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python media_crawler.py
  python media_crawler.py --data-dir "d:\\TokusCode\\bbb_assistant\\data"
  python media_crawler.py --data-dir "d:\\TokusCode\\bbb_assistant\\data" --max-speed 2.0
  python media_crawler.py --data-dir "d:\\TokusCode\\bbb_assistant\\data" --resume
  python media_crawler.py --workers 10 --timeout 60 --max-speed 0.5 --resume
        """
    )
    
    parser.add_argument(
        '--data-dir',
        type=str,
        default=None,
        help='JSON文件所在目录（默认为脚本所在目录的data文件夹）'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=5,
        help='并发下载线程数（默认: 5）'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='请求超时时间，单位秒（默认: 30）'
    )
    
    parser.add_argument(
        '--max-speed',
        type=float,
        default=1.0,
        help='最大下载速度限制，单位MB/s（默认: 1.0）'
    )
    
    parser.add_argument(
        '--resume',
        action='store_true',
        help='从上次断点继续下载'
    )
    
    parser.add_argument(
        '--subdir',
        type=str,
        default=None,
        help='只处理指定子目录下的JSON文件（如: 档案/动画短片）'
    )
    
    parser.add_argument(
        '--video-only',
        action='store_true',
        help='仅下载视频资源'
    )
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent
    
    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        data_dir = script_dir / 'data'
    
    crawler = MediaCrawler(
        data_dir=str(data_dir),
        max_workers=args.workers,
        timeout=args.timeout,
        max_speed_mb=args.max_speed,
        resume=args.resume,
        subdir_filter=args.subdir,
        video_only=args.video_only
    )
    
    crawler.crawl()


if __name__ == '__main__':
    main()
