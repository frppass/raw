# -*- coding: utf-8 -*-
import re, sys, os, requests, html as htmlmod, json, datetime, random, time
from urllib.parse import urlparse, urljoin, quote, unquote
import lxml.html, pyquery, jsonpath, cachetools
from bs4 import BeautifulSoup
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.site = 'https://s24.anichin.blog'
        self.site_secondary = 'https://anichin.blog'
        self.hls_domain = 'https://rmb.anichin.bio'
        self.tmdb_host = 'https://api.themoviedb.org/3'
        self.tmdb_key = ''
        
        import os
        if not self.tmdb_key:
            self.tmdb_key = os.getenv('TMDB_API_KEY', '')
        
        self.site_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            'referer': f'{self.site}/',
            'origin': self.site,
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'accept-language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'max-age=0',
            'sec-ch-ua': '"Chromium";v="136", "Not-A.Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1'
        }
        
        self.cache = cachetools.TTLCache(maxsize=100, ttl=1800)
        self.session = requests.Session()
        
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.enable_debug = True
        
        self._compile_regex_patterns()
        
        self.log("ANICHIN Spider initialized")
    
    def _compile_regex_patterns(self):
        """Kompilasi regex patterns"""
        self.dm_patterns = {
            'video_id': re.compile(r'(?:dailymotion\.com/(?:video|embed/video)|dai\.ly)/([a-z0-9]{6,})', re.I),
            'video_id_attr': re.compile(r'videoId["\']\s*:\s*["\']([^"\']+)["\']', re.I),
            'xid': re.compile(r'"xid":\s*"([^"]+)"', re.I),
            'data_id': re.compile(r'data-video-id=["\']([^"\']+)["\']', re.I)
        }
        
        self.year_pattern = re.compile(r'\b(19\d{2}|20\d{2})\b')
        
        # Episode patterns
        self.episode_patterns = [
            re.compile(r'(?:Episode|Episod|Eps|Ep\.?)\s*[:\.]?\s*(\d+)', re.I),
            re.compile(r'Ep\s*[\.:]?\s*(\d+)', re.I),
            re.compile(r'Eps\s*[\.:]?\s*(\d+)', re.I),
            re.compile(r'[#№]\s*(\d+)', re.I),
            re.compile(r'No\.?\s*(\d+)', re.I),
            re.compile(r'Nomor\s*(\d+)', re.I),
            re.compile(r'(?:Batch|Part|Chapter|Bab)\s*(\d+)', re.I),
            re.compile(r'^\s*(\d{1,3})\s*$'),
            re.compile(r'[-–]\s*(?:Episode\s*)?(\d+)', re.I),
            re.compile(r'[\(\[]\s*(\d+)\s*[\)\]]'),
            re.compile(r'Season\s*\d+\s*(?:Episode|Ep)\s*(\d+)', re.I),
            re.compile(r'EP\s*(\d+)', re.I),
            re.compile(r'\d+p\s*(?:Episode|Ep)\s*(\d+)', re.I),
            re.compile(r'Sub\s*(?:Indo|ID)?\s*(?:Episode|Ep)\s*(\d+)', re.I),
            re.compile(r'^(\d{1,3})\s*$'),
            re.compile(r'Episode\s*(\d+)', re.I),
            re.compile(r'Eps\.\s*(\d+)', re.I),
            re.compile(r'Ep\.\s*(\d+)', re.I)
        ]
        
        # Clean title patterns
        self.clean_title_patterns = [
            re.compile(r'\s*[-–]\s*(?:Episode|Eps|EP|Ep\.?)\s*\d+.*$', re.I),
            re.compile(r'\s*\(\d{4}\)$'),
            re.compile(r'\s*\[\d{4}\]$'),
            re.compile(r'\s*-\s*\d+$'),
            re.compile(r'\s*\[\d+\]$'),
            re.compile(r'\s*#\d+$'),
            re.compile(r'\s*-\s*Subtitle\s+Indonesia.*$', re.I),
            re.compile(r'\s*-\s*Batch.*$', re.I),
            re.compile(r'\s*-\s*Complete.*$', re.I),
            re.compile(r'\s*-\s*Ongoing.*$', re.I),
            re.compile(r'\s*-\s*Movie.*$', re.I),
            re.compile(r'\s*-\s*OVA.*$', re.I),
            re.compile(r'\s*-\s*ONA.*$', re.I),
            re.compile(r'\s*-\s*Special.*$', re.I)
        ]
        
        # Image patterns
        self.img_patterns = [
            re.compile(r'src=["\']([^"\']+\.(?:jpg|jpeg|png|webp|gif))["\']', re.I),
            re.compile(r'data-src=["\']([^"\']+\.(?:jpg|jpeg|png|webp|gif))["\']', re.I),
            re.compile(r'data-lazy-src=["\']([^"\']+\.(?:jpg|jpeg|png|webp|gif))["\']', re.I),
            re.compile(r'data-cfsrc=["\']([^"\']+\.(?:jpg|jpeg|png|webp|gif))["\']', re.I)
        ]
    
    def getName(self):
        return "ANICHIN"
    
    def isVideoFormat(self, url):
        video_ext = ['.m3u8', '.mp4', '.mkv', '.avi', '.mov', '.flv', '.webm', '.mpd']
        video_hosts = ['dailymotion.com', 'dmcdn.net', 'dai.ly', 'anichin.bio', 'google.com']
        
        url_lower = (url or '').lower()
        
        if any(ext in url_lower for ext in video_ext):
            return True
        
        if any(host in url_lower for host in video_hosts):
            return True
        
        return False
    
    def manualVideoCheck(self):
        return True
    
    def homeContent(self, filter):
        """Home categories"""
        return {
            'class': [
                {'type_name': '🎬 Anime Terbaru', 'type_id': 'terbaru'},
                {'type_name': '🔄 Anime Update', 'type_id': 'update'},
                {'type_name': '🔥 Anime Populer', 'type_id': 'populer'},
                {'type_name': '📺 Anime Ongoing', 'type_id': 'ongoing'},
                {'type_name': '✅ Anime Selesai', 'type_id': 'completed'},
                {'type_name': '⚔️ Action', 'type_id': 'action'},
                {'type_name': '🧭 Adventure', 'type_id': 'adventure'},
                {'type_name': '😂 Comedy', 'type_id': 'comedy'},
                {'type_name': '😢 Drama', 'type_id': 'drama'},
                {'type_name': '🧚 Fantasy', 'type_id': 'fantasy'},
                {'type_name': '👻 Horror', 'type_id': 'horror'},
                {'type_name': '🔍 Mystery', 'type_id': 'mystery'},
                {'type_name': '❤️ Romance', 'type_id': 'romance'},
                {'type_name': '🚀 Sci-Fi', 'type_id': 'sci-fi'},
                {'type_name': '🍜 Slice of Life', 'type_id': 'slice-of-life'},
                {'type_name': '✨ Supernatural', 'type_id': 'supernatural'},
                {'type_name': '😱 Thriller', 'type_id': 'thriller'},
                {'type_name': '📅 Anime 2024', 'type_id': '2024'},
                {'type_name': '📅 Anime 2023', 'type_id': '2023'},
                {'type_name': '📅 Anime 2022', 'type_id': '2022'},
                {'type_name': '📅 Anime 2021', 'type_id': '2021'},
                {'type_name': '📅 Anime 2020', 'type_id': '2020'},
                {'type_name': '🎥 Movie', 'type_id': 'movie'},
                {'type_name': '📼 OVA', 'type_id': 'ova'},
                {'type_name': '🌐 ONA', 'type_id': 'ona'},
                {'type_name': '⭐ Special', 'type_id': 'special'},
                {'type_name': '📦 Batch Anime', 'type_id': 'batch'},
                {'type_name': '🇮🇩 Subtitle Indonesia', 'type_id': 'sub-indo'},
                {'type_name': '🇰🇷 Drama Korea', 'type_id': 'drama-korea'},
                {'type_name': '🇨🇳 Drama China', 'type_id': 'drama-china'},
                {'type_name': '🇯🇵 Drama Jepang', 'type_id': 'drama-jepang'},
                {'type_name': '🇹🇭 Drama Thailand', 'type_id': 'drama-thailand'},
                {'type_name': '🎭 Live Action', 'type_id': 'live-action'},
                {'type_name': '🌟 Recommended', 'type_id': 'recommended'},
                {'type_name': '🏆 Top Rated', 'type_id': 'top-rated'},
                {'type_name': '💫 Classic', 'type_id': 'classic'}
            ],
            'filters': {}
        }
    
    def homeVideoContent(self):
        """Home video content"""
        try:
            cache_key = 'home_content'
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            self.log("Fetching home page content...")
            response = self.fetch(self.site + '/', headers=self.site_headers, timeout=15)
            html = response.text
            
            soup = BeautifulSoup(html, 'html.parser')
            
            for selector in ['#sidebar', '.widget', '.ads', 'script', 'style', 'iframe', '.announcement', '.notification']:
                for elem in soup.select(selector):
                    elem.decompose()
            
            items = []
            seen_titles = set()
            seen_urls = set()
            
            anime_items = soup.select('.anime-item, .item, .post, .series-item, .list-item, article.post')
            
            if not anime_items:
                anime_items = soup.select('.card, .box, .thumbnail, .post-thumbnail')
            
            if not anime_items:
                anime_items = soup.select('.col, .column, div:has(img)')
            
            self.log(f"Found {len(anime_items)} potential items")
            
            for elem in anime_items[:40]:
                try:
                    item = self._parse_home_item_simple(elem)
                    if item and item.get('vod_name'):
                        title_key = item['vod_name'].lower()
                        url_key = item['vod_id'].lower()
                        
                        if (title_key not in seen_titles and 
                            url_key not in seen_urls and 
                            len(title_key) > 3):
                            
                            if title_key == url_key or url_key.replace('/', '').replace('-', '') in title_key:
                                continue
                            
                            items.append(item)
                            seen_titles.add(title_key)
                            seen_urls.add(url_key)
                            
                            if len(items) >= 30:
                                break
                except Exception as e:
                    self.log(f"Error parsing item: {e}")
                    continue
            
            self.log(f"Successfully parsed {len(items)} items for home")
            
            result = {'list': items}
            self.cache[cache_key] = result
            return result
            
        except Exception as e:
            self.log(f'Home error: {e}', level="ERROR")
            return {'list': []}
    
    def _parse_home_item_simple(self, element):
        """Parse item di homepage"""
        try:
            link_elem = element.find('a', href=True)
            if not link_elem:
                link_elems = element.select('a[href]')
                for link in link_elems:
                    href = link.get('href', '').strip()
                    if href and not self._is_bad_link(href):
                        link_elem = link
                        break
            
            if not link_elem:
                return None
            
            href = link_elem.get('href', '').strip()
            if not href or self._is_bad_link(href):
                return None
            
            title = self._extract_title_simple(element, link_elem)
            if not title or len(title) < 3:
                return None
            
            invalid_keywords = [
                'anichin', 'fansub', 'fans', 'emas', 'gold', 'update',
                'terbaru', 'latest', 'new', 'hot', 'trending', 'popular'
            ]
            
            title_lower = title.lower()
            for keyword in invalid_keywords:
                if keyword in title_lower:
                    if title_lower == keyword or title_lower.startswith(f"{keyword} -") or title_lower == keyword:
                        return None
            
            if len(title) < 4:
                return None
            
            if re.search(r'^[0-9\-\s]+$', title):
                return None
            
            if not self._is_valid_anime_title(title):
                return None
            
            clean_title = self._clean_title(title)
            
            if len(clean_title) < 3:
                return None
            
            img_url = self._extract_image(element)
            
            ep_num = self._extract_episode_number_from_element(element)
            remarks = f"Ep {ep_num}" if ep_num else "Latest"
            
            status = self._extract_status(element)
            quality = self._extract_quality(element)
            
            remarks_parts = [remarks]
            if status:
                remarks_parts.append(status)
            if quality:
                remarks_parts.append(quality)
            
            remarks = ' | '.join(remarks_parts)
            
            vod_id = self._make_relative_url(href)
            
            item = {
                'vod_id': vod_id,
                'vod_name': clean_title[:200],
                'vod_pic': img_url,
                'vod_year': '',
                'vod_remarks': remarks[:120]
            }
            
            if not self._validate_anime_item(item):
                return None
            
            return item
            
        except Exception as e:
            self.log(f"Parse home item error: {e}")
            return None
    
    def _extract_title_simple(self, element, link_elem):
        """Extract judul tanpa tahun"""
        title = ''
        
        title_selectors = [
            '.title', 'h2', 'h3', 'h4',
            '.entry-title', '.post-title', '.anime-title',
            '.judul', '.name', '.item-title', '.card-title',
            '.series-title', '.caption', 'h1.title', 'h2.title',
            '.anime-name', '.series-name', '.post-name'
        ]
        
        for selector in title_selectors:
            title_elem = element.select_one(selector)
            if title_elem and title_elem.text.strip():
                text = title_elem.text.strip()
                
                if any(invalid in text.lower() for invalid in ['anichin', 'fansub', 'fans']):
                    continue
                
                text = re.sub(r'\s*[\(\[]?\d{4}[\)\]]?$', '', text)
                text = re.sub(r'\s*[-–]\s*(?:Episode|Eps|Ep).*$', '', text, flags=re.I)
                if text and len(text) > 2:
                    title = text
                    break
        
        if not title:
            img_elem = element.find('img')
            if img_elem:
                alt_text = img_elem.get('alt', '') or img_elem.get('title', '')
                if alt_text:
                    if any(invalid in alt_text.lower() for invalid in ['anichin', 'fansub', 'fans']):
                        pass
                    else:
                        alt_text = re.sub(r'\s*[\(\[]?\d{4}[\)\]]?$', '', alt_text)
                        alt_text = re.sub(r'\s*[-–]\s*(?:Episode|Eps|Ep).*$', '', alt_text, flags=re.I)
                        title = alt_text
        
        if not title:
            link_text = link_elem.text.strip()
            if link_text:
                if any(invalid in link_text.lower() for invalid in ['anichin', 'fansub', 'fans']):
                    pass
                else:
                    link_text = re.sub(r'\s*[\(\[]?\d{4}[\)\]]?$', '', link_text)
                    link_text = re.sub(r'\s*[-–]\s*(?:Episode|Eps|Ep).*$', '', link_text, flags=re.I)
                    title = link_text
        
        if title:
            title = re.sub(r'^(?:\[.*?\])', '', title)
            title = re.sub(r'\[.*?\]$', '', title)
            title = re.sub(r'\(.*?\)$', '', title)
            
            unwanted_words = ['Batch', 'Complete', 'Ongoing', 'Movie', 'OVA', 'ONA', 'Special']
            for word in unwanted_words:
                title = re.sub(r'\s*-\s*' + re.escape(word) + r'.*$', '', title, flags=re.I)
            
            title = title.strip()
        
        return title.strip()
    
    def _extract_episode_number_from_element(self, element):
        """Extract nomor episode dari elemen"""
        try:
            full_text = element.get_text()
            ep_num = self._extract_episode_number(full_text)
            if ep_num:
                return ep_num
            
            ep_selectors = [
                '.episode', '.eps', '.ep', '.episode-number', 
                '.latest-ep', '.episode-info', '.episode-count',
                '.episode-num', '.ep-num', '.eps-num'
            ]
            
            for selector in ep_selectors:
                ep_elem = element.select_one(selector)
                if ep_elem:
                    ep_num = self._extract_episode_number(ep_elem.text)
                    if ep_num:
                        return ep_num
            
            numbers = re.findall(r'\b(\d{1,3})\b', full_text)
            for num_str in numbers:
                try:
                    num = int(num_str)
                    if 1 <= num <= 999:
                        if 1900 <= num <= datetime.datetime.now().year:
                            continue
                        return num
                except:
                    continue
            
            return None
            
        except Exception as e:
            self.log(f"Extract episode number error: {e}")
            return None
    
    def _extract_status(self, element):
        """Extract status anime"""
        try:
            status_selectors = [
                '.status', '.type', '.label', '.badge', '.tag',
                '.anime-status', '.series-status', '.complete-status'
            ]
            
            for selector in status_selectors:
                status_elem = element.select_one(selector)
                if status_elem:
                    text = status_elem.text.strip().lower()
                    if 'complete' in text or 'selesai' in text or 'tamat' in text:
                        return 'Completed'
                    elif 'ongoing' in text or 'berlangsung' in text or 'lanjut' in text:
                        return 'Ongoing'
                    elif any(x in text for x in ['movie', 'film', 'ova', 'ona', 'special']):
                        return text.title()
            
            return ''
            
        except Exception as e:
            self.log(f"Extract status error: {e}")
            return ''
    
    def _extract_quality(self, element):
        """Extract kualitas video"""
        try:
            quality_selectors = ['.quality', '.resolution', '.hd', '.fullhd']
            
            for selector in quality_selectors:
                quality_elem = element.select_one(selector)
                if quality_elem:
                    text = quality_elem.text.strip()
                    if text and len(text) < 20:
                        return text
            
            full_text = element.get_text()
            if '1080p' in full_text:
                return '1080p'
            elif '720p' in full_text:
                return '720p'
            elif '480p' in full_text:
                return '480p'
            elif 'HD' in full_text or 'High Definition' in full_text:
                return 'HD'
            
            return ''
            
        except Exception as e:
            self.log(f"Extract quality error: {e}")
            return ''
    
    def _is_valid_anime_title(self, title):
        """Validasi apakah ini judul anime yang valid"""
        if not title or len(title) < 3:
            return False
        
        title_lower = title.lower()
        
        invalid_patterns = [
            r'^anichin\b',
            r'\bfansub\b',
            r'\bfans\b',
            r'^emas\b',
            r'^gold\b',
            r'^terbaru\b',
            r'^latest\b',
            r'^update\b',
            r'^new\b',
            r'^hot\b',
            r'^trending\b',
            r'^episode\s+\d+$',
            r'^ep\s+\d+$',
            r'^eps\s+\d+$',
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, title_lower, re.I):
                return False
        
        generic_titles = ['emas', 'gold', 'silver', 'platinum', 'diamond']
        if title_lower in generic_titles:
            return False
        
        return True
    
    def _extract_episode_number(self, text):
        """Extract nomor episode dari teks"""
        if not text:
            return None
        
        for pattern in self.episode_patterns:
            match = pattern.search(text)
            if match:
                try:
                    num = int(match.group(1))
                    if 1 <= num <= 999:
                        return num
                except:
                    continue
        
        return None
    
    def _clean_title(self, title):
        """Bersihkan judul"""
        if not title:
            return ''
        
        cleaned = title.strip()
        
        for pattern in self.clean_title_patterns:
            cleaned = pattern.sub('', cleaned)
        
        cleaned = re.sub(r'\s*[\(\[]?\d{4}[\)\]]?$', '', cleaned)
        
        cleaned = re.sub(r'^[\(\[]\s*[Aa]nichin[^\)\]]*[\)\]]\s*', '', cleaned)
        cleaned = re.sub(r'^\[[^\]]*[Ff]ans[^\]]*\]\s*', '', cleaned)
        
        cleaned = re.sub(r'\s*[-–]\s*[Aa]nichin.*$', '', cleaned)
        cleaned = re.sub(r'\s*\[[^\]]*[Ff]ans[^\]]*\]$', '', cleaned)
        
        cleaned = re.sub(r'[\[\]\(\)\{\}\"\']+', ' ', cleaned)
        
        cleaned = re.sub(r'\s*-\s*(?:Subtitle\s+)?(?:Indonesia|Indo|ID).*$', '', cleaned, flags=re.I)
        
        common_non_title = ['Batch', 'Complete', 'Ongoing', 'Movie', 'OVA', 'ONA', 'Special', 
                           'Subtitle', 'Indonesia', 'Indo', 'English', 'Dub', 'HD', '1080p', '720p']
        
        for word in common_non_title:
            cleaned = re.sub(r'\s*-\s*' + re.escape(word) + r'(?:\s+|$).*', '', cleaned, flags=re.I)
        
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned
    
    def _extract_image(self, element):
        """Extract gambar"""
        img_url = ''
        
        img_elem = element.find('img')
        if img_elem:
            for attr in ['src', 'data-src', 'data-lazy-src', 'data-cfsrc', 'data-original']:
                img_url = img_elem.get(attr, '')
                if img_url:
                    break
        
        if not img_url:
            style = element.get('style', '')
            if style:
                bg_match = re.search(r'background-image:\s*url\(["\']?([^"\'\)]+)["\']?\)', style, re.I)
                if bg_match:
                    img_url = bg_match.group(1)
        
        if not img_url:
            for img in element.select('img'):
                for attr in ['src', 'data-src']:
                    src = img.get(attr, '')
                    if src and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        img_url = src
                        break
                if img_url:
                    break
        
        if img_url:
            img_url = self._make_absolute_url(img_url)
        
        return img_url
    
    def _validate_anime_item(self, item):
        """Validasi item"""
        required_fields = ['vod_id', 'vod_name']
        
        for field in required_fields:
            if field not in item or not item[field]:
                return False
        
        if len(item['vod_name']) < 3:
            return False
        
        name_lower = item['vod_name'].lower()
        bad_keywords = [
            'slot', 'casino', 'bet', 'poker', 'gambling',
            'bonus', 'deposit', 'promo', 'free', 'spin'
        ]
        
        if any(keyword in name_lower for keyword in bad_keywords):
            return False
        
        vod_id = item['vod_id']
        if vod_id.startswith('http'):
            try:
                parsed = urlparse(vod_id)
                if not parsed.netloc:
                    return False
            except:
                return False
        
        return True
    
    def categoryContent(self, tid, pg, filter, extend):
        """Category content"""
        try:
            category_map = {
                'terbaru': '/series/?status=&type=&order=latest',
                'update': '/series/?sub=&order=update',
                'populer': '/series/?status=&type=&sub=&order=popular',
                'ongoing': '/series/?status=ongoing',
                'completed': '/series/?status=completed&order=',
                
                'action': '/genre/action/',
                'adventure': '/genre/adventure/',
                'comedy': '/genre/comedy/',
                'drama': '/genre/drama/',
                'fantasy': '/genre/fantasy/',
                'horror': '/genre/horror/',
                'mystery': '/genre/mystery/',
                'romance': '/genre/romance/',
                'sci-fi': '/genre/sci-fi/',
                'slice-of-life': '/genre/slice-of-life/',
                'supernatural': '/genre/supernatural/',
                'thriller': '/genre/thriller/',
                
                '2024': '/year/2024/',
                '2023': '/year/2023/',
                '2022': '/year/2022/',
                '2021': '/year/2021/',
                '2020': '/year/2020/',
                
                'movie': '/type/movie/',
                'ova': '/type/ova/',
                'ona': '/type/ona/',
                'special': '/type/special/',
                
                'batch': '/batch/',
                'sub-indo': '/subtitle/indonesia/',
                
                'drama-korea': '/genre/drama-korea/',
                'drama-china': '/genre/drama-china/',
                'drama-jepang': '/genre/drama-jepang/',
                'drama-thailand': '/genre/drama-thailand/',
                
                'live-action': '/genre/live-action/',
                
                'recommended': '/series/?order=latest',
                'top-rated': '/series/?order=rating',
                'classic': '/year/2019/'
            }
            
            base_url = category_map.get(tid, '/series/')
            url = f"{self.site}{base_url}"
            
            if int(pg) > 1:
                if '?' in url:
                    url += f"&page={pg}"
                else:
                    url += f"page/{pg}/"
            
            self.log(f"Fetching category {tid} page {pg}: {url}")
            
            response = self.fetch(url, headers=self.site_headers, timeout=15)
            html = response.text
            
            soup = BeautifulSoup(html, 'html.parser')
            
            for selector in ['.ads', 'script', 'style', '.widget']:
                for elem in soup.select(selector):
                    elem.decompose()
            
            items = []
            seen_titles = set()
            
            anime_items = soup.select('.anime-item, article, .post, .item, .series-item')
            
            if not anime_items:
                anime_items = soup.select('.card, .box, .thumbnail')
            
            if not anime_items:
                anime_items = soup.select('div:has(img)')
            
            for elem in anime_items[:60]:
                try:
                    item = self._parse_home_item_simple(elem)
                    if item and item.get('vod_name'):
                        title_key = item['vod_name'].lower()
                        if title_key not in seen_titles:
                            items.append(item)
                            seen_titles.add(title_key)
                except Exception as e:
                    self.log(f"Error parsing category item: {e}")
                    continue
            
            self.log(f"Found {len(items)} items in category {tid}")
            
            return {
                'list': items,
                'page': int(pg),
                'pagecount': 9999,
                'limit': 40,
                'total': 999999
            }
            
        except Exception as e:
            self.log(f'Category error {tid}: {e}', level="ERROR")
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 40, 'total': 0}
    
    def detailContent(self, ids):
        """Detail content - AMBIL EPISODE DARI HALAMAN SERIES"""
        try:
            url = ids[0]
            if not url:
                return {'list': []}
            
            if not url.startswith('http'):
                url = f"{self.site}{url}" if url.startswith('/') else f"{self.site}/{url}"
            
            cache_key = f"detail_{hash(url)}"
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            self.log(f"Fetching detail: {url}")
            
            response = self.fetch(url, headers=self.site_headers, timeout=20)
            html = response.text
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Parse detail anime
            detail = self._parse_detail_page(soup, url)
            
            # Parse episodes dari halaman series
            episodes = self._parse_episodes_from_series(soup, url)
            
            if episodes:
                play_urls = []
                episode_count = len(episodes)
                
                for ep in episodes:
                    ep_num = ep.get('number', '')
                    if ep_num:
                        play_urls.append(f"{ep_num}${ep['url']}")
                    else:
                        # Fallback ke index jika tidak ada nomor
                        play_urls.append(f"{len(play_urls)+1}${ep['url']}")
                
                play_str = '#'.join(play_urls)
                detail['remarks'] = f"{episode_count} Episode | {detail.get('remarks', '')}"
            else:
                # Fallback jika tidak ada episode
                play_str = f"1${url}"
            
            result = {
                'list': [{
                    'vod_id': url,
                    'vod_name': detail.get('title', 'N/A'),
                    'vod_pic': detail.get('image', ''),
                    'vod_year': detail.get('year', ''),
                    'vod_area': detail.get('area', 'JP'),
                    'vod_remarks': detail.get('remarks', ''),
                    'vod_content': detail.get('desc', ''),
                    'vod_play_from': 'ANICHIN',
                    'vod_play_url': play_str
                }]
            }
            
            self.cache[cache_key] = result
            return result
            
        except Exception as e:
            self.log(f'Detail error: {e}', level="ERROR")
            return {'list': []}
    
    def _parse_detail_page(self, soup, url):
        """Parse detail page"""
        result = {
            'title': '',
            'image': '',
            'year': '',
            'area': 'JP',
            'remarks': '',
            'desc': ''
        }
        
        try:
            title_selectors = [
                'h1.entry-title', 'h1.title', 'h1.post-title',
                '.entry-title', '.title', '.post-title',
                'h1', '.anime-title', '.series-title',
                '.video-title', '.movie-title', '.judul'
            ]
            
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem and title_elem.text.strip():
                    result['title'] = title_elem.text.strip()
                    break
            
            if not result['title']:
                meta_title = soup.find('meta', property='og:title')
                if meta_title:
                    result['title'] = meta_title.get('content', '').split('|')[0].strip()
            
            img_selectors = [
                'meta[property="og:image"]',
                '.poster img', '.thumbnail img', '.featured-img img',
                '.wp-post-image', 'img[src*="poster"]', 'img[src*="cover"]',
                '.anime-poster img', '.series-poster img',
                '.thumbook .thumb img'  # Tambahan untuk halaman series
            ]
            
            for selector in img_selectors:
                if selector.startswith('meta'):
                    meta_img = soup.select_one(selector)
                    if meta_img:
                        result['image'] = meta_img.get('content', '')
                        if result['image']:
                            result['image'] = self._make_absolute_url(result['image'])
                            break
                else:
                    img_elem = soup.select_one(selector)
                    if img_elem:
                        for attr in ['src', 'data-src', 'data-original']:
                            img_src = img_elem.get(attr, '')
                            if img_src:
                                result['image'] = img_src
                                result['image'] = self._make_absolute_url(result['image'])
                                break
                        if result['image']:
                            break
            
            # Extract year dari informasi
            info_selectors = ['.info', '.details', '.specs', '.anime-info', '.series-info', '.movie-info', '.infox']
            
            found_year = False
            for selector in info_selectors:
                info_elem = soup.select_one(selector)
                if info_elem:
                    info_text = info_elem.get_text()
                    
                    year_patterns = [
                        r'Tahun\s*[:.]?\s*(\d{4})',
                        r'Year\s*[:.]?\s*(\d{4})',
                        r'Release\s*[:.]?\s*(\d{4})',
                        r'Rilis\s*[:.]?\s*(\d{4})',
                        r'Aired\s*[:.]?\s*(\d{4})',
                        r'Date\s*[:.]?\s*(\d{4})',
                        r'Tanggal\s*[:.]?\s*(\d{4})'
                    ]
                    
                    for pattern in year_patterns:
                        match = re.search(pattern, info_text, re.IGNORECASE)
                        if match:
                            year = match.group(1)
                            current_year = datetime.datetime.now().year
                            if 1900 <= int(year) <= current_year + 1:
                                result['year'] = year
                                found_year = True
                                break
                    
                    if found_year:
                        break
            
            if not result['year']:
                page_text = soup.get_text()
                year_matches = re.findall(r'\b(20\d{2}|19\d{2})\b', page_text)
                
                current_year = datetime.datetime.now().year
                valid_years = []
                
                for year_str in year_matches:
                    try:
                        year = int(year_str)
                        if 1990 <= year <= current_year + 1:
                            valid_years.append(year)
                    except:
                        continue
                
                if valid_years:
                    valid_years.sort()
                    result['year'] = str(valid_years[0])
            
            # Extract description
            content_selectors = [
                '.entry-content', '.description', '.sinopsis',
                '.plot', '.summary', '.synopsis',
                '.anime-description', '.series-description',
                '.movie-description', '.content',
                '.bixbox.synp .entry-content'  # Tambahan untuk halaman series
            ]
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    for tag in content_elem.select('script, style, .ads'):
                        tag.decompose()
                    
                    text = content_elem.get_text(strip=True, separator=' ')
                    if len(text) > 50:
                        result['desc'] = text[:1000]
                        break
            
            result['title'] = self._clean_html_text(result['title'])
            result['desc'] = self._clean_html_text(result['desc'])
            
            # Extract remarks
            remarks_parts = []
            
            status_elem = soup.select_one('.status, .type, .anime-status, .infox .spe span b')
            if status_elem:
                status_text = status_elem.text.strip()
                if status_text and len(status_text) < 30:
                    remarks_parts.append(status_text)
            
            # Cari total episode
            episode_count_elem = soup.select_one('.infox .spe span:contains("Episode:")')
            if episode_count_elem:
                ep_count = episode_count_elem.text.replace('Episode:', '').strip()
                if ep_count:
                    remarks_parts.append(f"{ep_count} Eps")
            
            if remarks_parts:
                result['remarks'] = ' | '.join(remarks_parts)
            
            # Tentukan area
            page_text_lower = soup.get_text().lower()
            if any(keyword in page_text_lower for keyword in ['korea', 'korean', 'drakor']):
                result['area'] = 'KR'
            elif any(keyword in page_text_lower for keyword in ['china', 'chinese', 'cina', 'mandarin']):
                result['area'] = 'CN'
            elif any(keyword in page_text_lower for keyword in ['japan', 'japanese', 'jepang']):
                result['area'] = 'JP'
            elif any(keyword in page_text_lower for keyword in ['thailand', 'thai']):
                result['area'] = 'TH'
            
        except Exception as e:
            self.log(f"Parse detail error: {e}")
        
        return result
    
    def _parse_episodes_from_series(self, soup, url):
        """
        Parse episodes dari halaman series
        SELECTOR UTAMA: .bixbox.bxcl.epcheck .eplister ul li a
        """
        episodes = []
        
        try:
            # Cari container episode
            container_selectors = [
                '.bixbox.bxcl.epcheck .eplister ul',  # SELECTOR UTAMA DARI HTML
                '.bxcl.epcheck .eplister ul',
                '.epcheck .eplister ul',
                '.bxcl ul',
                '.eplister ul',
                '#episode-list ul',
                '.episodelist ul'
            ]
            
            container = None
            for selector in container_selectors:
                container = soup.select_one(selector)
                if container:
                    self.log(f"Found episode container: {selector}")
                    break
            
            if not container:
                self.log("No episode container found")
                return episodes
            
            # Cari semua item episode
            episode_items = container.select('li')
            self.log(f"Found {len(episode_items)} episode items")
            
            for li in episode_items:
                try:
                    link = li.select_one('a[href]')
                    if not link:
                        continue
                    
                    href = link.get('href', '').strip()
                    if not href or self._is_bad_link(href):
                        continue
                    
                    # Ambil nomor episode dari .epl-num
                    num_elem = li.select_one('.epl-num')
                    if not num_elem:
                        num_elem = link.select_one('.epl-num')
                    
                    episode_number = None
                    if num_elem:
                        num_text = num_elem.text.strip()
                        # Ekstrak angka dari teks seperti "01", "06 END", dll
                        num_match = re.search(r'(\d+)', num_text)
                        if num_match:
                            episode_number = int(num_match.group(1))
                    
                    # Ambil judul dari .epl-title
                    title_elem = li.select_one('.epl-title')
                    if not title_elem:
                        title_elem = link.select_one('.epl-title')
                    
                    episode_title = ""
                    if title_elem:
                        episode_title = title_elem.text.strip()
                    else:
                        # Fallback ke teks link
                        episode_title = link.text.strip()
                    
                    # Ambil informasi subtitle
                    sub_elem = li.select_one('.epl-sub .status')
                    if sub_elem:
                        sub_text = sub_elem.text.strip()
                        if sub_text and 'Sub' in episode_title:
                            pass  # Sudah ada di judul
                    
                    # Bersihkan judul
                    clean_title = self._clean_episode_name(episode_title)
                    
                    # Jika tidak ada nomor episode dari .epl-num, coba dari judul
                    if not episode_number:
                        episode_number = self._extract_episode_number(clean_title)
                    
                    # Gunakan episode_number sebagai nama jika tersedia
                    if episode_number:
                        display_name = f"Episode {episode_number}"
                        if clean_title and clean_title != display_name:
                            display_name = clean_title
                    else:
                        display_name = clean_title or f"Episode {len(episodes)+1}"
                    
                    episodes.append({
                        'name': display_name,
                        'url': self._make_relative_url(href),
                        'number': episode_number
                    })
                    
                except Exception as e:
                    self.log(f"Error parsing episode item: {e}")
                    continue
            
            # Urutkan berdasarkan nomor episode (ascending)
            if episodes:
                episodes.sort(key=lambda x: x.get('number', 0) if x.get('number') else 0)
                self.log(f"Successfully parsed {len(episodes)} episodes")
                
                # Debug: tampilkan beberapa episode pertama
                for i, ep in enumerate(episodes[:5]):
                    self.log(f"  Episode {i+1}: {ep['name']} -> {ep['url']}")
            
        except Exception as e:
            self.log(f"Parse episodes error: {e}")
        
        return episodes
    
    def _clean_episode_name(self, name):
        """Bersihkan nama episode"""
        if not name:
            return "Episode"
        
        name = htmlmod.unescape(name)
        
        # Hapus informasi berlebihan
        name = re.sub(r'\s*[\(\[]\d+p[\)\]]', '', name, flags=re.I)
        name = re.sub(r'\s*[\(\[]HD[\)\]]', '', name, flags=re.I)
        name = re.sub(r'\s*[\(\[]Sub.*?[\)\]]', '', name, flags=re.I)
        
        # Bersihkan spasi
        name = re.sub(r'\s+', ' ', name).strip()
        
        if not name:
            return "Episode"
        
        return name[:100]
    
    def searchContent(self, key, quick, pg="1"):
        """Search content"""
        try:
            if not key or len(key) < 2:
                return {'list': [], 'page': 1, 'pagecount': 1}
            
            search_url = f"{self.site}/?s={quote(key)}"
            if int(pg) > 1:
                search_url += f"&page={pg}"
            
            self.log(f"Searching: {search_url}")
            
            response = self.fetch(search_url, headers=self.site_headers, timeout=15)
            html = response.text
            
            soup = BeautifulSoup(html, 'html.parser')
            
            items = []
            seen_titles = set()
            
            results = soup.select('.search-results, .results, article, .post, .search-item')
            
            if not results:
                results = soup.select('.item, .anime-item, div:has(img)')
            
            for elem in results[:50]:
                try:
                    item = self._parse_home_item_simple(elem)
                    if item and item.get('vod_name'):
                        title_key = item['vod_name'].lower()
                        if title_key not in seen_titles:
                            items.append(item)
                            seen_titles.add(title_key)
                except Exception as e:
                    self.log(f"Error parsing search result: {e}")
                    continue
            
            return {
                'list': items,
                'page': int(pg),
                'pagecount': 9999,
                'limit': 40,
                'total': 999999
            }
            
        except Exception as e:
            self.log(f'Search error: {e}', level="ERROR")
            return {'list': [], 'page': 1, 'pagecount': 1}
    
    def playerContent(self, flag, id, vipFlags):
        """Player content"""
        try:
            id = unquote(id)
            
            if not id.startswith('http'):
                play_url = f"{self.site}{id}" if id.startswith('/') else f"{self.site}/{id}"
            else:
                play_url = id
            
            self.log(f"Processing player for: {play_url}")
            
            response = self.fetch(play_url, headers=self.site_headers, timeout=20)
            html = response.text
            
            # Cari Dailymotion video ID
            video_id = self._extract_dailymotion_video_id(html)
            
            if video_id:
                self.log(f"Found Dailymotion video ID: {video_id}")
                
                stream_result = self._get_dailymotion_stream_api(video_id)
                
                if stream_result and stream_result.get('url'):
                    self.log(f"Got stream URL via API")
                    return {
                        'parse': 0,
                        'url': stream_result['url'],
                        'header': stream_result.get('headers', {}),
                        'subs': []
                    }
                else:
                    embed_url = f"https://www.dailymotion.com/embed/video/{video_id}"
                    self.log(f"Using embed URL: {embed_url}")
                    
                    return {
                        'parse': 1,
                        'url': embed_url,
                        'header': self._get_dailymotion_headers(),
                        'subs': []
                    }
            
            direct_url = self._find_direct_video_url(html)
            if direct_url:
                self.log(f"Found direct video URL")
                return {
                    'parse': 0,
                    'url': direct_url,
                    'header': {'Referer': play_url, 'User-Agent': self.site_headers['User-Agent']},
                    'subs': []
                }
            
            self.log("Using page URL for external player")
            return {
                'parse': 1,
                'url': play_url,
                'header': self.site_headers,
                'subs': []
            }
            
        except Exception as e:
            self.log(f"Player error: {e}", level="ERROR")
            return {
                'parse': 1,
                'url': id,
                'header': self.site_headers,
                'subs': []
            }
    
    def _extract_dailymotion_video_id(self, html):
        """Extract Dailymotion video ID"""
        for pattern_name, pattern in self.dm_patterns.items():
            matches = pattern.findall(html)
            for match in matches:
                if match and len(match) >= 6:
                    if re.match(r'^[a-z0-9]+$', match, re.I):
                        return match
        
        url_patterns = [
            r'https?://(?:www\.)?dailymotion\.com/(?:video|embed/video)/([a-z0-9]+)',
            r'https?://dai\.ly/([a-z0-9]+)',
            r'videoId["\']\s*:\s*["\']([^"\']+)["\']'
        ]
        
        for pattern in url_patterns:
            matches = re.findall(pattern, html, re.I)
            for match in matches:
                if match and len(match) >= 6:
                    return match
        
        return None
    
    def _get_dailymotion_stream_api(self, video_id):
        """Get Dailymotion stream via API"""
        try:
            api_url = f"https://www.dailymotion.com/player/metadata/video/{video_id}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': 'https://www.dailymotion.com/',
                'Origin': 'https://www.dailymotion.com',
                'Connection': 'keep-alive'
            }
            
            self.log(f"Fetching Dailymotion API: {api_url}")
            
            response = self.fetch(api_url, headers=headers, timeout=15, verify=True)
            
            if response.status_code != 200:
                self.log(f"API returned status: {response.status_code}")
                return None
            
            data = response.json()
            
            stream_url = None
            
            if 'qualities' in data and isinstance(data['qualities'], dict):
                qualities = data['qualities']
                
                quality_order = ['1080', '720', '480', '360', '240', 'auto']
                
                for quality in quality_order:
                    if quality in qualities and qualities[quality]:
                        for stream in qualities[quality]:
                            if isinstance(stream, dict) and 'url' in stream and stream['url']:
                                stream_url = stream['url']
                                break
                    if stream_url:
                        break
            
            if not stream_url and 'progressive' in data and isinstance(data['progressive'], list):
                progressive_streams = [s for s in data['progressive'] if isinstance(s, dict) and 'url' in s]
                if progressive_streams:
                    for stream in sorted(progressive_streams, key=lambda x: x.get('quality', '0'), reverse=True):
                        if 'url' in stream and stream['url']:
                            stream_url = stream['url']
                            break
            
            if stream_url:
                stream_headers = headers.copy()
                stream_headers['Referer'] = f"https://www.dailymotion.com/video/{video_id}"
                
                return {
                    'url': stream_url,
                    'headers': stream_headers
                }
            
            return None
            
        except Exception as e:
            self.log(f"API method error: {e}")
            return None
    
    def _get_dailymotion_headers(self):
        """Headers for Dailymotion"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.dailymotion.com/',
            'Origin': 'https://www.dailymotion.com'
        }
    
    def _find_direct_video_url(self, html):
        """Find direct video URL"""
        try:
            m3u8_patterns = [
                r'https?://[^\s"\']+\.m3u8[^\s"\']*',
                r'"([^"]+\.m3u8[^"]*)"',
                r"'([^']+\.m3u8[^']*)'"
            ]
            
            for pattern in m3u8_patterns:
                matches = re.findall(pattern, html, re.I)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    
                    if match and 'http' in match:
                        return match
            
            mp4_patterns = [
                r'https?://[^\s"\']+\.mp4[^\s"\']*',
                r'"([^"]+\.mp4[^"]*)"',
                r"'([^']+\.mp4[^']*)'"
            ]
            
            for pattern in mp4_patterns:
                matches = re.findall(pattern, html, re.I)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    
                    if match and 'http' in match:
                        return match
            
        except Exception as e:
            self.log(f"Find video URL error: {e}")
        
        return None
    
    def _make_absolute_url(self, url):
        """Convert to absolute URL"""
        if not url:
            return ''
        
        if url.startswith('http'):
            return url
        elif url.startswith('//'):
            return 'https:' + url
        elif url.startswith('/'):
            return self.site + url
        elif url.startswith('./'):
            return self.site + url[1:]
        elif url.startswith('../'):
            base_path = '/'.join(self.site.split('/')[0:3])
            return base_path + url[2:]
        else:
            return self.site + '/' + url
    
    def _make_relative_url(self, url):
        """Convert to relative URL"""
        try:
            parsed = urlparse(url)
            
            if parsed.netloc and ('anichin.blog' in parsed.netloc or 's24.anichin.blog' in parsed.netloc or 's25.anichin.blog' in parsed.netloc):
                path = parsed.path
                if parsed.query:
                    path += '?' + parsed.query
                return path
            elif not parsed.netloc:
                return url if url.startswith('/') else '/' + url
            else:
                return url
                
        except Exception as e:
            self.log(f"Make relative URL error: {e}")
            return url if url.startswith('/') else '/' + url
    
    def _is_bad_link(self, href):
        """Check if link is bad"""
        if not href:
            return True
        
        href_lower = href.lower()
        
        bad_keywords = [
            'javascript:', '#', '?s=', '/tag/', '/category/', '/author/',
            '/search/', 'wp-login.php', '/comments/', 'facebook.com',
            'twitter.com', 'instagram.com', 'disclaimer', 'privacy',
            'terms', 'contact', 'about', 'ads.txt', '/feed/', '/rss/',
            '.pdf', '.zip', '.rar', '.exe', '.apk', '.dmg',
            '/fansub/', '/group/', '/team/', '/uploader/',
            '/anime-terbaru/', '/anime-update/', '/anime-populer/',
            'anichin-fans', 'emas'
        ]
        
        return any(bad in href_lower for bad in bad_keywords)
    
    def _clean_html_text(self, text):
        """Clean HTML text"""
        if not text:
            return ''
        
        try:
            text = htmlmod.unescape(text)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            
            if len(text) > 1000:
                text = text[:997] + '...'
            
            return text
        except:
            return text or ''
    
    def fetch(self, url, headers=None, timeout=20, retry=2, verify=True):
        """Custom fetch"""
        headers = headers or self.site_headers
        
        for attempt in range(retry + 1):
            try:
                response = self.session.get(
                    url,
                    headers=headers,
                    timeout=timeout,
                    verify=verify
                )
                
                if response.status_code == 200:
                    return response
                else:
                    self.log(f"Fetch returned status {response.status_code} for {url}")
                
                if attempt < retry:
                    wait_time = 1 * (attempt + 1)
                    self.log(f"Retrying {url} in {wait_time} seconds...")
                    time.sleep(wait_time)
                    
            except Exception as e:
                if attempt == retry:
                    self.log(f"Fetch failed for {url}: {e}", level="ERROR")
                    raise
                else:
                    wait_time = 1 * (attempt + 1)
                    self.log(f"Fetch error for {url}, retrying in {wait_time} seconds: {e}")
                    time.sleep(wait_time)
    
    def log(self, message, level="INFO"):
        """Logging"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_msg = f"[{timestamp}] [{level}] [ANICHIN] {message}"
            print(log_msg)
            
            if self.enable_debug:
                try:
                    with open('anichin_debug.log', 'a', encoding='utf-8') as f:
                        f.write(log_msg + '\n')
                except:
                    pass
                    
        except:
            print(f"[{level}] [ANICHIN] {message}")
    
    def destroy(self):
        """Cleanup"""
        if hasattr(self, 'session'):
            self.session.close()
    
    def localProxy(self, param):
        """Local proxy"""
        pass