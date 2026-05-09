#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
崩坏3官方百科爬虫
支持爬取 https://baike.mihoyo.com/bh3/wiki/ 网站内容
由于网站使用Nuxt.js动态加载内容，需要浏览器自动化工具
"""

import logging
import asyncio
import json
import re
import time
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin, urlparse, parse_qs
from dataclasses import dataclass
from enum import Enum

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class CrawlerMode(Enum):
    """爬虫模式"""
    REQUESTS = "requests"      # 使用requests库（适用于静态内容）
    PLAYWRIGHT = "playwright"  # 使用playwright（适用于动态内容）
    AUTO = "auto"              # 自动选择


@dataclass
class WikiPage:
    """百科页面数据"""
    url: str
    title: str
    content: str
    category: str = ""
    metadata: Dict[str, Any] = None
    links: List[str] = None
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.links is None:
            self.links = []
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class HonkaiWikiCrawler:
    """崩坏3百科爬虫"""
    
    def __init__(
        self,
        base_url: str = "https://baike.mihoyo.com/bh3/wiki",
        mode: CrawlerMode = CrawlerMode.AUTO,
        headless: bool = True,
        timeout: int = 30,
        max_pages: int = 100
    ):
        """
        初始化爬虫
        
        Args:
            base_url: 百科基础URL
            mode: 爬虫模式
            headless: 是否使用无头浏览器（仅playwright模式）
            timeout: 超时时间（秒）
            max_pages: 最大爬取页面数
        """
        self.base_url = base_url.rstrip('/')
        self.mode = mode
        self.headless = headless
        self.timeout = timeout
        self.max_pages = max_pages
        
        self.visited_urls = set()
        self.pages: List[WikiPage] = []
        
        # 尝试导入playwright，如果不可用则禁用playwright模式
        self.playwright_available = False
        if mode in [CrawlerMode.PLAYWRIGHT, CrawlerMode.AUTO]:
            try:
                from playwright.async_api import async_playwright
                self.playwright_available = True
                logger.info("Playwright可用")
            except ImportError:
                logger.warning("Playwright不可用，将使用requests模式")
                self.playwright_available = False
        
        logger.info(f"崩坏3百科爬虫初始化完成，模式: {mode.value}")
    
    async def crawl(self, start_path: str = "/channel/?bbs_presentation_style=no_header") -> List[WikiPage]:
        """
        开始爬取崩坏3百科内容
        
        Args:
            start_path: 起始路径，默认为/channel/页面（所有内容总网址）
            
        Returns:
            爬取的页面列表
        """
        start_url = urljoin(self.base_url, start_path)
        
        # 根据模式选择爬取方法
        if self.mode == CrawlerMode.REQUESTS:
            await self._crawl_with_requests(start_url)
        elif self.mode == CrawlerMode.PLAYWRIGHT:
            await self._crawl_with_playwright(start_url)
        else:  # AUTO模式
            # 先尝试requests，如果失败再尝试playwright
            try:
                logger.info("尝试使用requests爬取...")
                await self._crawl_with_requests(start_url)
            except Exception as e:
                logger.warning(f"requests爬取失败: {e}，尝试使用playwright")
                if self.playwright_available:
                    await self._crawl_with_playwright(start_url)
                else:
                    raise RuntimeError("无法爬取网站内容：requests失败且playwright不可用")
        
        logger.info(f"爬取完成，共获取 {len(self.pages)} 个页面")
        return self.pages
    
    async def _crawl_with_requests(self, start_url: str):
        """使用requests爬取"""
        logger.info(f"开始使用requests爬取: {start_url}")
        
        # 获取起始页面
        page = await self._fetch_page_with_requests(start_url)
        if page:
            self.pages.append(page)
            
            # 提取链接并递归爬取
            await self._process_links(page)
    
    async def _fetch_page_with_requests(self, url: str) -> Optional[WikiPage]:
        """使用requests获取页面"""
        if url in self.visited_urls:
            return None
        
        self.visited_urls.add(url)
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            }
            
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            # 检查内容类型
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type:
                logger.warning(f"非HTML内容: {url}, 类型: {content_type}")
                return None
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取标题
            title = soup.title.string if soup.title else ""
            
            # 提取主要内容
            content = self._extract_content(soup)
            
            # 提取链接
            links = self._extract_links(soup, url)
            
            # 提取分类信息
            category = self._extract_category(url, soup)
            
            page = WikiPage(
                url=url,
                title=title.strip(),
                content=content.strip(),
                category=category,
                links=links,
                metadata={
                    'content_type': content_type,
                    'status_code': response.status_code,
                    'content_length': len(response.text)
                }
            )
            
            logger.info(f"获取页面成功: {title[:50]}...")
            return page
            
        except Exception as e:
            logger.error(f"获取页面失败 {url}: {e}")
            return None
    
    async def _crawl_with_playwright(self, start_url: str):
        """使用playwright爬取（支持JavaScript动态内容）"""
        if not self.playwright_available:
            raise RuntimeError("Playwright不可用")
        
        logger.info(f"开始使用playwright爬取: {start_url}")
        
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            # 启动浏览器
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context()
            page = await context.new_page()
            
            if True:
                # 访问起始页面
                await page.goto(start_url, wait_until='networkidle', timeout=90000)  # 增加超时到90秒
                
                # 等待更长时间确保SPA内容加载（崩坏3百科需要较长时间）
                logger.info(f"等待页面内容加载: {start_url}")
                await page.wait_for_timeout(15000)  # 等待15秒
                
                # 智能等待策略：检测并等待所有可能的加载指示器
                loading_indicators = [
                    # 文本指示器 - 主要加载文本
                    ':has-text("数据加载中")',
                    ':has-text("加载中")', 
                    ':has-text("Loading")',
                    ':has-text("loading")',
                    ':has-text("请稍候")',
                    ':has-text("稍等")',
                    
                    # CSS类指示器
                    '[class*="loading"]',
                    '[class*="Loading"]',
                    '[class*="spinner"]',
                    '[class*="loader"]',
                    '[class*="progress"]',
                    '[class*="wait"]',
                    
                    # 属性指示器
                    '[aria-busy="true"]',
                    '[aria-label*="loading"]',
                    '[aria-label*="Loading"]',
                    '[data-loading="true"]',
                    
                    # 视觉指示器（旋转、动画等）
                    '.spinner',
                    '.loader',
                    '.progress-bar',
                    '.loading-indicator'
                ]
                
                # 第一轮：检查并等待加载指示器消失（但忽略用户登录加载组件）
            logger.info("检查页面加载状态...")
            loading_detected = False
            
            for selector in loading_indicators:
                try:
                    # 快速检查是否有加载元素
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        if element:
                            # 检查元素是否可见且不在用户登录加载组件中
                            is_visible = await element.is_visible()
                            if is_visible:
                                # 检查是否在用户登录加载组件中
                                parent_html = await element.evaluate('(element) => element.parentElement?.outerHTML || ""')
                                if 'user-model-loading' in parent_html or 'mhy-login-platform' in parent_html:
                                    logger.info(f"忽略用户登录加载指示器: {selector}")
                                    continue
                                    
                                loading_detected = True
                                logger.info(f"发现加载指示器: {selector}")
                                
                                # 等待它消失（最多30秒）
                                try:
                                    await page.wait_for_selector(selector, state='hidden', timeout=30000)
                                    logger.info(f"加载指示器 {selector} 已消失")
                                except Exception as e:
                                    logger.warning(f"等待加载指示器消失超时: {selector}, {e}")
                except Exception as e:
                    logger.debug(f"检查加载指示器 {selector} 时出错: {e}")
            
            # 等待页面标题变化（表明SPA已加载内容）
            logger.info("等待页面标题稳定...")
            initial_title = await page.title()
            title_stable_checks = 0
            required_title_stable_checks = 2
            
            for _ in range(30):  # 最多等待30秒
                await page.wait_for_timeout(1000)
                current_title = await page.title()
                
                if current_title and current_title != initial_title:
                    logger.info(f"页面标题已变化: '{current_title[:50]}...'")
                    break
                
                if current_title and "圣芙蕾雅档案馆-崩坏3WIKI" in current_title:
                    # 初始标题，继续等待
                    continue
            
            # 第二轮：等待主要内容区域出现
            logger.info("等待主要内容区域...")
            content_selectors = [
                'main', '.main-content', '#content', '.content',
                'article', '.article', '.wiki-content', '.page-content',
                '.detail-content', '.content-detail', '.article-content',
                '[class*="wiki"]', '[class*="detail"]', '[class*="article"]'
            ]
            
            main_content_element = None
            for selector in content_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=30000)
                    element = await page.query_selector(selector)
                    if element:
                        is_visible = await element.is_visible()
                        if is_visible:
                            main_content_element = element
                            logger.info(f"找到主要内容区域: {selector}")
                            break
                except:
                    continue
            
            # 如果没找到特定内容区域，使用body
            if not main_content_element:
                logger.warning("未找到标准内容区域，使用body")
                main_content_element = await page.query_selector('body')
            
            # 第三轮：等待内容真正稳定
            logger.info("检查内容稳定性...")
            max_wait_time = 60000  # 最大总等待时间60秒
            start_time = asyncio.get_event_loop().time()
            stable_checks_passed = 0
            required_stable_checks = 2
            last_content = ""
            
            while (asyncio.get_event_loop().time() - start_time) < max_wait_time:
                await page.wait_for_timeout(3000)  # 每3秒检查一次
                
                # 获取当前内容
                if main_content_element:
                    current_content = await main_content_element.text_content()
                else:
                    content_element = await page.query_selector('body')
                    current_content = await content_element.text_content() if content_element else ""
                
                # 过滤掉用户登录加载文本
                filtered_content = current_content
                if "数据加载中" in filtered_content:
                    # 检查是否在主要内容中（不是用户登录组件）
                    if main_content_element:
                        # 评估是否在主要内容元素内
                        has_loading_in_main = await main_content_element.evaluate('''(element) => {
                            const text = element.textContent || "";
                            return text.includes("数据加载中");
                        }''')
                        if not has_loading_in_main:
                            # 加载文本不在主要内容中，可以忽略
                            filtered_content = filtered_content.replace("数据加载中", "")
                            logger.debug("忽略非主要内容区的'数据加载中'文本")
                
                # 检查内容长度和质量（过滤后）
                if len(filtered_content.strip()) < 300:
                    logger.warning(f"内容过短 ({len(filtered_content.strip())} 字符)，可能未加载完成")
                    continue
                
                # 检查内容变化（过滤后）
                if filtered_content.strip() == last_content.strip():
                    stable_checks_passed += 1
                    logger.info(f"内容稳定检查通过 {stable_checks_passed}/{required_stable_checks}")
                else:
                    stable_checks_passed = 0
                    logger.info(f"内容仍在变化，重置稳定检查 (长度: {len(filtered_content.strip())})")
                
                last_content = filtered_content.strip()
                
                if stable_checks_passed >= required_stable_checks:
                    logger.info(f"页面内容已稳定 ({len(filtered_content.strip())} 字符)")
                    break
                
                # 如果接近超时但内容仍然很短，尝试强制等待
                time_remaining = max_wait_time - (asyncio.get_event_loop().time() - start_time)
                if time_remaining < 15000 and len(filtered_content.strip()) < 500:
                    logger.warning("接近超时但内容仍然很短，额外等待10秒...")
                    await page.wait_for_timeout(10000)
            
            # 最终检查：确保主要内容已加载
            final_content = ""
            if main_content_element:
                final_content = await main_content_element.text_content()
            else:
                content_element = await page.query_selector('body')
                final_content = await content_element.text_content() if content_element else ""
            
            # 检查最终内容质量
            if len(final_content.strip()) < 300:
                logger.error(f"最终内容过短 ({len(final_content.strip())} 字符)，可能未加载完成")
            else:
                # 检查是否包含主要占位符（过滤用户登录组件）
                has_loading = "数据加载中" in final_content
                if has_loading:
                    # 检查是否在主要内容中
                    if main_content_element:
                        has_in_main = await main_content_element.evaluate('''(element) => {
                            const text = element.textContent || "";
                            return text.includes("数据加载中");
                        }''')
                        if not has_in_main:
                            logger.info(f"最终检查：内容加载完成 ({len(final_content.strip())} 字符，忽略用户登录加载)")
                        else:
                            logger.warning(f"最终检查：主要内容仍包含'数据加载中'")
                    else:
                        logger.warning(f"最终检查：内容仍包含'数据加载中'")
                else:
                    logger.info(f"最终检查：内容加载完成 ({len(final_content.strip())} 字符)")
                
                # 获取页面内容
                wiki_page = await self._fetch_page_with_playwright(page, start_url)
                if wiki_page:
                    self.pages.append(wiki_page)
                    
                    # 提取链接并递归爬取
                    await self._process_links(wiki_page)
            
            if True:
                await browser.close()
    
    async def _fetch_page_with_playwright(self, page, url: str) -> Optional[WikiPage]:
        """使用playwright获取页面"""
        if url in self.visited_urls:
            return None
        
        self.visited_urls.add(url)
        
        try:
            # 获取页面HTML
            html = await page.content()
            
            # 使用BeautifulSoup解析
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取标题
            title = await page.title()
            
            # 提取主要内容（尝试获取渲染后的文本）
            content_element = await page.query_selector('body')
            content = await content_element.text_content() if content_element else ""
            
            # 提取链接
            links = []
            link_elements = await page.query_selector_all('a')
            for link_element in link_elements[:100]:  # 限制数量
                href = await link_element.get_attribute('href')
                if href:
                    full_url = urljoin(url, href)
                    if self._is_valid_url(full_url):
                        links.append(full_url)
            
            # 提取分类信息
            category = self._extract_category(url, soup)
            
            wiki_page = WikiPage(
                url=url,
                title=title.strip(),
                content=content.strip(),
                category=category,
                links=links,
                metadata={
                    'method': 'playwright',
                    'html_length': len(html)
                }
            )
            
            logger.info(f"获取页面成功: {title[:50]}...")
            return wiki_page
            
        except Exception as e:
            logger.error(f"获取页面失败 {url}: {e}")
            return None
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """提取主要内容"""
        # 尝试查找主要内容区域
        content_selectors = [
            'main', '.main-content', '#content', '.content', 
            'article', '.article', '.wiki-content', '.page-content'
        ]
        
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(separator='\n', strip=True)
        
        # 如果没有找到特定区域，返回body内容
        body = soup.body
        if body:
            return body.get_text(separator='\n', strip=True)
        
        return ""
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """提取页面中的链接"""
        links = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            full_url = urljoin(base_url, href)
            
            if self._is_valid_url(full_url):
                links.append(full_url)
        
        return list(set(links))  # 去重
    
    def _extract_category(self, url: str, soup: BeautifulSoup) -> str:
        """提取页面分类"""
        # 从URL路径推断分类
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        query = parsed_url.query.lower()
        
        # 特殊页面类型
        if '/search' in path:
            return 'search'
        elif '/content/' in path and '/detail' in path:
            return 'content_detail'
        elif '/channel/map/' in path:
            return 'channel_map'
        elif '/channel/position/' in path:
            return 'channel_position'
        elif '/channel' in path and '/map' not in path and '/position' not in path:
            return 'channel'
        elif '/character' in path or '/女武神' in path:
            return 'character'
        elif '/weapon' in path or '/武器' in path:
            return 'weapon'
        elif '/stigmata' in path or '/圣痕' in path:
            return 'stigmata'
        elif '/guide' in path or '/攻略' in path:
            return 'guide'
        elif '/event' in path or '/活动' in path:
            return 'event'
        
        # 通用分类匹配
        categories = {
            'character': ['角色', '女武神', 'character', 'kiana', 'mei', 'bronya'],
            'weapon': ['武器', 'weapon', '枪', '炮', '剑', '刀'],
            'stigmata': ['圣痕', 'stigmata', '圣遗物'],
            'item': ['道具', '物品', 'item', 'material', '材料'],
            'mission': ['任务', '关卡', 'mission', 'stage', '副本'],
            'event': ['活动', 'event', '限时'],
            'guide': ['攻略', '指南', 'guide', '教程', 'tip'],
            'story': ['剧情', '故事', 'story', '主线', '支线'],
            'version': ['版本', '更新', 'version', 'update'],
            'system': ['系统', '机制', 'system', '机制']
        }
        
        # 从URL路径推断
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in path or keyword in query:
                    return category
        
        # 从页面标题推断
        title = soup.title.string.lower() if soup.title else ""
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in title:
                    return category
        
        # 从页面内容推断（前500字符）
        content_preview = soup.get_text()[:500].lower() if soup.get_text() else ""
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in content_preview:
                    return category
        
        return "unknown"
    
    def _is_valid_url(self, url: str) -> bool:
        """检查URL是否有效"""
        # 只爬取同域名下的页面
        parsed_url = urlparse(url)
        base_domain = urlparse(self.base_url).netloc
        
        if parsed_url.netloc and parsed_url.netloc != base_domain:
            return False
        
        # 排除一些不需要爬取的URL
        exclude_patterns = [
            r'\.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$',
            r'^javascript:',
            r'^mailto:',
            r'^tel:',
            r'^#',
            r'\?bbs_presentation_style='
        ]
        
        for pattern in exclude_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        return True
    
    async def _process_links(self, page: WikiPage):
        """处理页面链接"""
        if len(self.pages) >= self.max_pages:
            logger.info(f"达到最大页面数限制: {self.max_pages}")
            return
        
        for link in page.links:
            if len(self.pages) >= self.max_pages:
                break
            
            if link not in self.visited_urls:
                # 根据当前模式选择获取方法
                if self.mode == CrawlerMode.REQUESTS:
                    new_page = await self._fetch_page_with_requests(link)
                elif self.mode == CrawlerMode.PLAYWRIGHT:
                    # 对于playwright模式，需要新打开页面
                    # 这里简化处理，使用requests
                    new_page = await self._fetch_page_with_requests(link)
                else:
                    new_page = await self._fetch_page_with_requests(link)
                
                if new_page:
                    self.pages.append(new_page)
                    await self._process_links(new_page)
    
    def save_to_file(self, filename: str = "honkai_wiki_data.json"):
        """保存爬取的数据到文件"""
        data = []
        for page in self.pages:
            page_data = {
                'url': page.url,
                'title': page.title,
                'content': page.content,
                'category': page.category,
                'metadata': page.metadata,
                'links': page.links,
                'timestamp': page.timestamp
            }
            data.append(page_data)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"数据已保存到: {filename}")
    
    @classmethod
    async def test_crawl(cls, url: str = None, mode: CrawlerMode = CrawlerMode.AUTO):
        """测试爬取功能"""
        if url is None:
            url = "https://baike.mihoyo.com/bh3/wiki/?bbs_presentation_style=no_header"
        
        crawler = cls(base_url=url, mode=mode, max_pages=5)
        pages = await crawler.crawl()
        
        print(f"爬取测试完成，获取 {len(pages)} 个页面")
        for i, page in enumerate(pages[:3]):
            print(f"\n页面 {i+1}: {page.title}")
            print(f"URL: {page.url}")
            print(f"分类: {page.category}")
            print(f"内容预览: {page.content[:200]}...")
        
        return pages


# 同步接口（便于在非异步环境中使用）
def sync_crawl(
    start_url: str = "https://baike.mihoyo.com/bh3/wiki/?bbs_presentation_style=no_header",
    mode: str = "auto",
    max_pages: int = 10,
    timeout: int = 60,
    headless: bool = True
) -> List[WikiPage]:
    """
    同步爬取接口
    
    Args:
        start_url: 起始URL
        mode: 爬虫模式 ('requests', 'playwright', 'auto')
        max_pages: 最大页面数
        timeout: 超时时间（秒）
        headless: 是否使用无头模式
        
    Returns:
        爬取的页面列表
    """
    crawler_mode = CrawlerMode(mode)
    crawler = HonkaiWikiCrawler(mode=crawler_mode, max_pages=max_pages, timeout=timeout, headless=headless)
    
    # 运行异步爬取
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        pages = loop.run_until_complete(crawler.crawl(start_url))
        return pages
    finally:
        loop.close()


if __name__ == "__main__":
    # 测试代码
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        print("崩坏3百科爬虫测试")
        print("=" * 60)
        
        # 测试requests模式
        print("\n测试requests模式...")
        try:
            pages = await HonkaiWikiCrawler.test_crawl(mode=CrawlerMode.REQUESTS)
            if not pages:
                print("requests模式未能获取内容，网站可能使用JavaScript动态加载")
        except Exception as e:
            print(f"requests模式测试失败: {e}")
        
        # 测试playwright模式（如果可用）
        print("\n测试playwright模式...")
        try:
            pages = await HonkaiWikiCrawler.test_crawl(mode=CrawlerMode.PLAYWRIGHT)
        except Exception as e:
            print(f"playwright模式测试失败: {e}")
    
    asyncio.run(main())