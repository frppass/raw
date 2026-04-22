# -*- coding: utf-8 -*-
import re, sys, os, requests, html as htmlmod, json, datetime
from urllib.parse import urlparse, urljoin, quote, unquote
import lxml.html, pyquery, jsonpath, cachetools
from bs4 import BeautifulSoup, SoupStrainer
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.site = 'https://oppa.biz'
        self.site_secondary = 'https://oppadrama.biz'
        self.tmdb_host = 'https://api.themoviedb.org/3'
        self.tmdb_key = ''  # Kosongkan atau gunakan environment variable
        self.phost = 'https://image.tmdb.org/t/p/w500'
        
        # Dapatkan API key dari environment variable atau konfigurasi
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
        
        self.tmdb_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            'accept': 'application/json',
            'accept-language': 'id-ID,id;q=0.9'
        }
        
        # Strainer untuk parsing cepat
        self.article_strainer = SoupStrainer(['article', 'div'], 
            class_=['bsx', 'listupd', 'items', 'list-series', 'movie-item', 'post-item', 'list-item', 'grid-item'])
        
        self.detail_strainer = SoupStrainer(['main', 'div', 'section'],
            class_=['postbody', 'content', 'main-content', 'movie-detail', 'series-detail'])
        
        self.episode_strainer = SoupStrainer(['div', 'ul'],
            class_=['episode-list', 'list-episode', 'episodes', 'eplister', 'epwrap', 'episodelist', 'chapterlist'])
        
        self.meta_strainer = SoupStrainer('meta', 
            property=['og:title', 'og:image', 'og:description'])
        
        self.iframe_strainer = SoupStrainer('iframe', 
            src=re.compile(r'(embed|player|video|stream|play|watch)', re.I))
        
        # Pre-compile regex patterns untuk performa lebih cepat
        self.video_patterns_compiled = [
            re.compile(r'file\s*:\s*["\']([^"\']+\.(?:m3u8|mp4|mkv)[^"\']*)["\']', re.I),
            re.compile(r'src\s*:\s*["\']([^"\']+\.(?:m3u8|mp4|mkv)[^"\']*)["\']', re.I),
            re.compile(r'(https?://[^\s"\']+\.(?:m3u8|mp4|mkv)[^\s"\']*)', re.I),
            re.compile(r'data-video="([^"]+)"', re.I)
        ]
        
        self.year_patterns_compiled = [
            re.compile(r'\b(20\d{2}|19\d{2})\b'),
            re.compile(r'(?:Tahun|Year|Release|Rilis|Released)[\s:]*(\d{4})', re.I)
        ]
        
        self.episode_patterns_compiled = [
            re.compile(r'(?:episode|eps|ep\.|ep)\s*(\d+)', re.I),
            re.compile(r'ep\s*(\d+)', re.I),
            re.compile(r'eps\s*(\d+)', re.I),
            re.compile(r'bagian\s*(\d+)', re.I),
            re.compile(r'part\s*(\d+)', re.I),
            re.compile(r'#\s*(\d+)', re.I),
            re.compile(r'(\d+)\s*(?:end|finale)', re.I)
        ]
        
        # Cache yang lebih besar dan efisien
        self.cache = cachetools.TTLCache(maxsize=300, ttl=7200)  # 2 jam
        self.url_cache = cachetools.LRUCache(maxsize=500)
        
        # Session dengan connection pooling
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=2
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # Tahun saat ini untuk validasi
        self.current_year = datetime.datetime.now().year
        
        # Init session dengan cookie
        try:
            self.session.get(self.site, headers=self.site_headers, timeout=3, verify=False)
        except:
            pass
    
    def getName(self):
        return "OPPADRAMA"
    
    def isVideoFormat(self, url):
        video_ext = ['.m3u8', '.mp4', '.mkv', '.avi', '.mov', '.flv', '.webm']
        return any(ext in (url or '').lower() for ext in video_ext)
    
    def manualVideoCheck(self):
        return True
    
    def destroy(self):
        if hasattr(self, 'session'):
            self.session.close()
        if hasattr(self, 'cache'):
            self.cache.clear()
        if hasattr(self, 'url_cache'):
            self.url_cache.clear()
    
    def fetch(self, url, headers=None, timeout=15, retry=2, stream=False):
        """Custom fetch dengan retry, cache, dan session"""
        cache_key = f"fetch_{hash(url)}"
        if cache_key in self.url_cache:
            return self.url_cache[cache_key]
        
        headers = headers or self.site_headers
        
        for attempt in range(retry + 1):
            try:
                if attempt > 0:
                    import time
                    time.sleep(0.3 * attempt)  # Exponential backoff
                
                response = self.session.get(
                    url, 
                    headers=headers, 
                    timeout=timeout, 
                    verify=False,
                    stream=stream,
                    allow_redirects=True
                )
                
                response.raise_for_status()
                
                # Cache response text untuk URL yang sering diakses
                if not stream and len(response.content) < 500000:  # Cache < 500KB
                    self.url_cache[cache_key] = response
                
                return response
                
            except requests.exceptions.Timeout:
                self.log(f"Timeout error, retry {attempt+1}/{retry+1}: {url}")
                if attempt == retry:
                    raise
            except requests.exceptions.RequestException as e:
                self.log(f"Request error: {e}")
                if attempt == retry:
                    raise
    
    def homeContent(self, filter):
        return {
            'class': [
                {'type_name': 'Ongoing', 'type_id': 'ongoing'},
                {'type_name': 'Completed', 'type_id': 'completed'},
                {'type_name': 'Drama Korea', 'type_id': 'drama-korea'},
                {'type_name': 'Drama China', 'type_id': 'drama-china'},
                {'type_name': 'Drama Thailand', 'type_id': 'drama-thailand'},
                {'type_name': 'Drama Jepang', 'type_id': 'drama-jepang'},
                {'type_name': 'Drama Taiwan', 'type_id': 'drama-taiwan'},
                {'type_name': 'Drama Filipina', 'type_id': 'drama-filipina'},
                {'type_name': 'Series Barat', 'type_id': 'series-barat'},
                {'type_name': 'Netflix', 'type_id': 'netflix'},
                {'type_name': 'Film Korea', 'type_id': 'film-korea'},
                {'type_name': 'Film China', 'type_id': 'film-china'},
                {'type_name': 'Film Hong Kong', 'type_id': 'film-hongkong'},
                {'type_name': 'Film Thailand', 'type_id': 'film-thailand'},
                {'type_name': 'Film Jepang', 'type_id': 'film-jepang'},
                {'type_name': 'Film Taiwan', 'type_id': 'film-taiwan'},
                {'type_name': 'Film Filipina', 'type_id': 'film-filipina'},
                {'type_name': 'Film India', 'type_id': 'film-india'},
                {'type_name': 'Film Barat', 'type_id': 'film-barat'},
                {'type_name': 'Variety Show', 'type_id': 'variety-show'},
                {'type_name': 'Animasi', 'type_id': 'animasi'},
                {'type_name': 'Jadwal', 'type_id': 'jadwal'},
                {'type_name': 'Bookmark', 'type_id': 'bookmark'},
                {'type_name': 'Terbaru', 'type_id': 'terbaru'},
                {'type_name': 'Populer', 'type_id': 'populer'},
                {'type_name': 'Series', 'type_id': 'series'},
                {'type_name': 'Movie', 'type_id': 'movie'},
                {'type_name': 'Anime', 'type_id': 'anime'}
            ],
            'filters': {}
        }
    
    def homeVideoContent(self):
        try:
            response = self.fetch(self.site + '/', timeout=10)
            
            # Parsing cepat dengan SoupStrainer
            soup = BeautifulSoup(response.text, 'html.parser', 
                               parse_only=self.article_strainer)
            
            items = []
            seen_ids = set()
            
            # Parsing artikel dengan loop cepat
            for article in soup.find_all(['article', 'div'], limit=60):
                try:
                    item = self._parse_article_fast(article)
                    if item and item['vod_id'] not in seen_ids:
                        seen_ids.add(item['vod_id'])
                        
                        # Validasi dan tambahkan default year jika perlu
                        if not item.get('vod_year'):
                            item['vod_year'] = str(self.current_year - 1)
                        else:
                            item['vod_year'] = self._validate_year(item['vod_year'])
                        
                        items.append(item)
                        
                        if len(items) >= 40:  # Limit items
                            break
                except Exception as e:
                    continue
            
            if items:
                self.log(f"Found {len(items)} items in homepage")
                return {'list': items}
                
        except Exception as e:
            self.log(f'Error homeVideoContent: {e}')
        
        # Fallback ke kategori terbaru
        try:
            result = self.categoryContent('terbaru', 1, False, {})
            if 'list' in result:
                return {'list': result['list'][:30]}
        except:
            pass
        
        return {'list': []}
    
    def categoryContent(self, tid, pg, filter, extend):
        try:
            # Mapping kategori
            category_map = {
                'ongoing': '/series/?status=Ongoing&type=&order=update',
                'completed': '/series/?status=Completed&type=Drama&order=update',
                'drama-korea': '/series/?country%5B%5D=south-korea&status=&type=Drama&order=update',
                'drama-china': '/series/?country%5B%5D=china&type=Drama&order=update',
                'drama-thailand': '/series/?country%5B%5D=thailand&status=&type=Drama&order=update',
                'drama-jepang': '/series/?country%5B%5D=japan&type=Drama&order=update',
                'drama-taiwan': '/series/?country%5B%5D=taiwan&status=&type=Drama&order=update',
                'drama-filipina': '/series/?country%5B%5D=philippines&type=Drama&order=update',
                'series-barat': '/series/?country%5B%5D=usa&type=Drama&order=update',
                'netflix': '/network/netflix/',
                'film-korea': '/series/?country%5B%5D=south-korea&status=&type=Movie&order=update',
                'film-china': '/series/?country%5B%5D=china&type=Movie&order=update',
                'film-hongkong': '/series/?country%5B%5D=hong-kong&type=Movie&order=update',
                'film-thailand': '/series/?country%5B%5D=thailand&status=&type=Movie&order=update',
                'film-jepang': '/series/?country%5B%5D=japan&type=Movie&order=update',
                'film-taiwan': '/series/?country%5B%5D=taiwan&status=&type=Movie&order=update',
                'film-filipina': '/series/?country%5B%5D=philippines&type=Movie&order=update',
                'film-india': '/series/?country%5B%5D=india&status=&type=Movie&order=update',
                'film-barat': '/series/?country%5B%5D=united-states&status=&type=Movie&order=update',
                'variety-show': '/series/?type=TV+Show&order=update',
                'animasi': '/series/?page=1&genre%5B0%5D=animation&type=&order=update',
                'jadwal': '/jadwal/',
                'bookmark': '/bookmark/',
                'terbaru': f'/release-year/{self.current_year}/',
                'populer': '/imdb/?imdb=7.5-10',
                'series': '/series/?status=&type=Drama&order=update',
                'movie': '/series/?type=Movie&order=update',
                'anime': '/series/?genre%5B0%5D=animation&type=&order=update'
            }
            
            base_path = category_map.get(tid, '/')
            url = f"{self.site}{base_path}"
            
            if str(pg) != '1' and tid not in ['jadwal', 'bookmark']:
                if '?' in url:
                    url += f"&page={pg}"
                else:
                    url += f"page/{pg}/"
            
            self.log(f'Fetching category {tid}: {url}')
            response = self.fetch(url, timeout=12)
            
            # Parsing cepat dengan SoupStrainer
            soup = BeautifulSoup(response.text, 'html.parser', 
                               parse_only=self.article_strainer)
            
            items = []
            seen_ids = set()
            
            # Batch parsing untuk performa lebih baik
            for article in soup.find_all(['article', 'div'], limit=60):
                try:
                    item = self._parse_article_fast(article)
                    if item and item['vod_id'] not in seen_ids:
                        seen_ids.add(item['vod_id'])
                        
                        # Validasi tahun
                        if item.get('vod_year'):
                            item['vod_year'] = self._validate_year(item['vod_year'])
                        else:
                            item['vod_year'] = str(self.current_year - 1)
                        
                        items.append(item)
                except Exception as e:
                    continue
            
            return {
                'list': items[:40],
                'page': int(pg),
                'pagecount': 9999,
                'limit': 40,
                'total': 999999
            }
            
        except Exception as e:
            self.log(f'Error categoryContent {tid}: {e}')
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 40, 'total': 0}
    
    def detailContent(self, ids):
        try:
            path = ids[0]
            if not path or self._is_notification_link(path):
                return {'list': []}
            
            # Decode URL
            path = unquote(path)
            
            if not path.startswith('http'):
                full_url = f"{self.site}{path}" if path.startswith('/') else f"{self.site}/{path}"
            else:
                full_url = path
            
            # Cache check dengan TTL lebih pendek untuk detail
            cache_key = f"detail_{hash(full_url)}"
            if cache_key in self.cache:
                cached_result = self.cache[cache_key]
                # Refresh cache jika lebih dari 1 jam
                import time
                if time.time() - cached_result.get('_cached_time', 0) < 3600:
                    return cached_result['data']
            
            self.log(f'Fetching detail: {full_url}')
            response = self.fetch(full_url, timeout=15)
            
            # Parsing detail dengan strainer terpisah untuk efisiensi
            detail_soup = BeautifulSoup(response.text, 'html.parser', 
                                      parse_only=self.detail_strainer)
            
            # Parsing meta tags secara terpisah
            meta_soup = BeautifulSoup(response.text, 'html.parser',
                                    parse_only=self.meta_strainer)
            
            # Parse detail
            detail = self._parse_detail_fast(detail_soup, meta_soup)
            
            # Parse episodes dengan strainer khusus
            episode_soup = BeautifulSoup(response.text, 'html.parser',
                                       parse_only=self.episode_strainer)
            episodes = self._parse_episodes_fast(episode_soup)
            
            # Ambil data TMDB jika ada API key (async untuk tidak blocking)
            if self.tmdb_key and detail.get('title'):
                try:
                    import threading
                    tmdb_thread = threading.Thread(
                        target=self._fetch_tmdb_data,
                        args=(detail['title'], detail.get('year'), detail),
                        daemon=True
                    )
                    tmdb_thread.start()
                except:
                    pass
            
            # Format play URL
            play_urls = []
            if episodes:
                sorted_episodes = self._sort_episodes_fast(episodes)
                for ep in sorted_episodes[:80]:  # Max 80 episodes
                    play_urls.append(f"{ep['name']}${ep['url']}")
                play_str = '#'.join(play_urls)
                detail['remarks'] = f"{len(episodes)} Episode | {detail.get('remarks', '')}"
            else:
                play_str = f"Play${full_url}"
            
            result_data = {
                'list': [{
                    'vod_id': path,
                    'vod_name': detail.get('title', 'OPPADRAMA'),
                    'vod_pic': detail.get('pic', ''),
                    'vod_year': detail.get('year', str(self.current_year - 1)),
                    'vod_area': detail.get('area', ''),
                    'vod_remarks': detail.get('remarks', ''),
                    'vod_content': detail.get('content', ''),
                    'vod_play_from': 'OPPADRAMA',
                    'vod_play_url': play_str
                }]
            }
            
            # Cache result dengan timestamp
            result_to_cache = {
                'data': result_data,
                '_cached_time': time.time() if 'time' in locals() else 0
            }
            self.cache[cache_key] = result_to_cache
            
            return result_data
            
        except Exception as e:
            self.log(f'Error detailContent: {e}', level="ERROR")
            return {'list': []}
    
    def searchContent(self, key, quick, pg="1"):
        try:
            if not key or len(key) < 2:
                return {'list': []}
                
            search_url = f"{self.site}/?s={quote(key)}"
            if str(pg) != '1':
                search_url += f"&page={pg}"
            
            self.log(f'Searching: {search_url}')
            response = self.fetch(search_url, timeout=12)
            
            # Parsing cepat
            soup = BeautifulSoup(response.text, 'html.parser', 
                               parse_only=self.article_strainer)
            
            items = []
            seen_ids = set()
            
            for article in soup.find_all(['article', 'div'], limit=50):
                try:
                    item = self._parse_article_fast(article)
                    if item and item['vod_id'] not in seen_ids:
                        seen_ids.add(item['vod_id'])
                        
                        if item.get('vod_year'):
                            item['vod_year'] = self._validate_year(item['vod_year'])
                        
                        items.append(item)
                except Exception as e:
                    continue
            
            return {
                'list': items[:40],
                'page': int(pg),
                'pagecount': 9999,
                'limit': 40,
                'total': 999999
            }
            
        except Exception as e:
            self.log(f'Error searchContent: {e}')
            return {'list': [], 'page': 1, 'pagecount': 1}
    
    def playerContent(self, flag, id, vipFlags):
        try:
            # Decode ID
            id = unquote(id)
            
            if not id.startswith('http'):
                play_url = f"{self.site}{id}" if id.startswith('/') else f"{self.site}/{id}"
            else:
                play_url = id
            
            self.log(f'Resolving player: {play_url}')
            
            response = self.fetch(play_url, timeout=15)
            html = response.text
            
            # Cari iframe terlebih dahulu dengan strainer
            iframe_soup = BeautifulSoup(html, 'html.parser', 
                                      parse_only=self.iframe_strainer)
            
            iframe = iframe_soup.find('iframe')
            if iframe:
                iframe_src = iframe.get('src', '')
                if iframe_src:
                    if not iframe_src.startswith('http'):
                        iframe_src = urljoin(play_url, iframe_src)
                    
                    # Coba fetch iframe content
                    try:
                        iframe_response = self.fetch(iframe_src, 
                                                   headers={'Referer': play_url},
                                                   timeout=10)
                        
                        # Cari video di iframe dengan regex pre-compiled
                        video_url = self._find_video_fast(iframe_response.text)
                        if video_url:
                            return {
                                'parse': 0,
                                'url': video_url,
                                'header': {
                                    'User-Agent': self.site_headers['User-Agent'],
                                    'Referer': iframe_src,
                                    'Origin': urlparse(iframe_src).scheme + '://' + urlparse(iframe_src).netloc
                                }
                            }
                    except Exception as e:
                        self.log(f"Iframe fetch error: {e}")
            
            # Jika tidak ada iframe atau tidak berhasil, cari langsung
            video_url = self._find_video_fast(html)
            if video_url:
                return {
                    'parse': 0,
                    'url': video_url,
                    'header': {
                        'User-Agent': self.site_headers['User-Agent'],
                        'Referer': play_url
                    }
                }
            
            # Fallback ke parse 1
            return {
                'parse': 1,
                'url': play_url,
                'header': {
                    'User-Agent': self.site_headers['User-Agent'],
                    'Referer': self.site
                }
            }
            
        except Exception as e:
            self.log(f'Error playerContent: {e}')
            return {
                'parse': 1,
                'url': id if id.startswith('http') else f"{self.site}{id}",
                'header': self.site_headers
            }
    
    def localProxy(self, param):
        pass
    
    # ==================== HELPER METHODS ====================
    
    def _parse_article_fast(self, article):
        """Parsing cepat artikel dengan minimal processing"""
        try:
            # Cari link utama
            link = article.find('a', href=True)
            if not link:
                return None
            
            href = link.get('href', '').strip()
            if not href or self._is_bad_link(href):
                return None
            
            # Cari judul
            title = ''
            title_elem = article.find(['h2', 'h3', 'h4'])
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            if not title:
                img = article.find('img')
                if img and img.get('alt'):
                    title = img.get('alt', '').strip()
            
            if not title or self._is_notification_title(title):
                return None
            
            # Cari gambar
            img_src = ''
            img = article.find('img')
            if img:
                for attr in ['src', 'data-src', 'data-lazy-src']:
                    if img.get(attr):
                        img_src = img.get(attr)
                        break
            
            # Cari tahun dengan regex pre-compiled
            year = ''
            text_content = article.get_text()
            for pattern in self.year_patterns_compiled:
                match = pattern.search(text_content)
                if match:
                    year = match.group(1)
                    break
            
            # Cari remarks
            remarks = ''
            status_elem = article.find(class_=['epx', 'bt', 'typez', 'quality', 'status'])
            if status_elem:
                remarks = status_elem.get_text(strip=True)
            
            # Clean dan return
            return {
                'vod_id': self._make_relative_path(href),
                'vod_name': self._clean_html_text(title[:200]),
                'vod_pic': self._abs_url_oppa(img_src),
                'vod_year': year,
                'vod_remarks': remarks[:100] if remarks else ''
            }
            
        except Exception as e:
            return None
    
    def _parse_detail_fast(self, detail_soup, meta_soup):
        """Parsing cepat detail page"""
        result = {
            'title': '',
            'pic': '',
            'year': '',
            'area': '',
            'remarks': '',
            'content': ''
        }
        
        try:
            # Judul dari detail atau meta
            title_elem = detail_soup.find(['h1', 'h2'])
            if title_elem:
                result['title'] = title_elem.get_text(strip=True)
            
            if not result['title']:
                og_title = meta_soup.find('meta', property='og:title')
                if og_title:
                    result['title'] = og_title.get('content', '').split('|')[0].strip()
            
            # Gambar dari meta atau detail
            og_image = meta_soup.find('meta', property='og:image')
            if og_image:
                result['pic'] = og_image.get('content', '')
            
            if not result['pic']:
                img_elem = detail_soup.find('img')
                if img_elem:
                    for attr in ['src', 'data-src', 'data-lazy-src']:
                        if img_elem.get(attr):
                            result['pic'] = img_elem.get(attr)
                            break
            
            # Tahun dengan regex cepat
            text_content = detail_soup.get_text()
            for pattern in self.year_patterns_compiled:
                match = pattern.search(text_content)
                if match:
                    result['year'] = match.group(1)
                    break
            
            # Area/negara
            area_map = {
                'korea': 'KR', 'korean': 'KR',
                'china': 'CN', 'chinese': 'CN',
                'thailand': 'TH', 'thai': 'TH',
                'japan': 'JP', 'japanese': 'JP',
                'indonesia': 'ID', 'indonesian': 'ID',
                'taiwan': 'TW', 'taiwanese': 'TW',
                'philippines': 'PH', 'filipino': 'PH',
                'usa': 'US', 'america': 'US',
                'india': 'IN', 'indian': 'IN',
                'hong kong': 'HK', 'hongkong': 'HK'
            }
            
            for elem in detail_soup.find_all(text=True, recursive=False):
                text = elem.lower()
                for key, code in area_map.items():
                    if key in text:
                        result['area'] = code
                        break
                if result['area']:
                    break
            
            # Status/remarks
            status_elem = detail_soup.find(class_=['status', 'completed', 'ongoing'])
            if status_elem:
                result['remarks'] = status_elem.get_text(strip=True)
            
            # Content/sinopsis
            content_elem = detail_soup.find(class_=['entry-content', 'description', 'sinopsis'])
            if content_elem:
                result['content'] = content_elem.get_text(strip=True)[:800]
            
            # Clean text
            result['title'] = self._clean_html_text(result['title'])
            result['content'] = self._clean_html_text(result['content'])
            result['remarks'] = self._clean_html_text(result['remarks'])
            
        except Exception as e:
            self.log(f'_parse_detail_fast error: {e}')
        
        return result
    
    def _parse_episodes_fast(self, episode_soup):
        """Parsing cepat episode list"""
        episodes = []
        
        try:
            # Cari semua link
            links = episode_soup.find_all('a', href=True)
            
            for link in links[:150]:  # Max 150 episodes
                try:
                    href = link.get('href', '').strip()
                    if not href or self._is_bad_link(href):
                        continue
                    
                    text = link.get_text(strip=True)
                    if not text:
                        continue
                    
                    # Format nama episode dengan regex pre-compiled
                    ep_name = '1'
                    for pattern in self.episode_patterns_compiled:
                        match = pattern.search(text.lower())
                        if match:
                            ep_name = match.group(1)
                            break
                    
                    episodes.append({
                        'name': ep_name,
                        'url': self._make_relative_path(href)
                    })
                    
                except Exception as e:
                    continue
            
        except Exception as e:
            self.log(f'_parse_episodes_fast error: {e}')
        
        return episodes
    
    def _sort_episodes_fast(self, episodes):
        """Mengurutkan episode dari 1 ke atas dengan cepat"""
        if not episodes:
            return []
        
        try:
            return sorted(episodes, key=lambda x: int(x['name']) if x['name'].isdigit() else 99999)
        except:
            return episodes
    
    def _find_video_fast(self, html):
        """Cari video URL dengan regex pre-compiled"""
        for pattern in self.video_patterns_compiled:
            match = pattern.search(html)
            if match:
                url = match.group(1)
                if url and 'google' not in url.lower() and 'youtube' not in url.lower():
                    return url
        return None
    
    def _fetch_tmdb_data(self, title, year, detail_dict):
        """Fetch TMDB data secara async"""
        try:
            if not self.tmdb_key:
                return
            
            params = {
                'query': title,
                'api_key': self.tmdb_key,
                'language': 'id-ID',
                'page': 1,
                'include_adult': 'false'
            }
            
            # Coba TV dulu
            response = self.fetch(
                f'{self.tmdb_host}/search/tv',
                params=params,
                headers=self.tmdb_headers,
                timeout=8
            ).json()
            
            if response.get('results'):
                result = response['results'][0]
                # Update detail dict
                detail_dict['title'] = result.get('name') or detail_dict['title']
                if result.get('poster_path'):
                    detail_dict['pic'] = f"{self.phost}{result.get('poster_path')}"
                if result.get('overview'):
                    detail_dict['content'] = result.get('overview')
                
                if result.get('first_air_date'):
                    tmdb_year = result.get('first_air_date').split('-')[0]
                    detail_dict['year'] = self._validate_year(tmdb_year)
                    
                return
            
        except Exception as e:
            self.log(f"TMDB fetch error: {e}")
    
    def _is_bad_link(self, href):
        """Cek apakah link buruk/tidak valid"""
        if not href:
            return True
        
        href_lower = href.lower()
        
        bad_keywords = [
            'javascript:', '#', '?s=', '/wp-content/', 'disclaimer',
            '/tag/', '/category/', '/author/', '/page/', '/feed/',
            'notification', 'pemberitahuan', 'announcement',
            'pengumuman', 'telegram', 't.me', 'whatsapp',
            'facebook.com', 'twitter.com', 'instagram.com',
            '/search/', 'wp-login.php', '/comments/',
            '/privacy-policy', '/terms-of-service',
            '/contact', '/about', '/donate', '#respond',
            '#comments', 'mailto:', 'tel:'
        ]
        
        return any(bad in href_lower for bad in bad_keywords)
    
    def _is_notification_link(self, href):
        """Cek apakah link adalah notifikasi"""
        if not href:
            return False
        
        href_lower = href.lower()
        
        notification_keywords = [
            '/notification', '/pemberitahuan', '/announcement',
            '/pengumuman', '/disclaimer', '/telegram',
            '/channel', '/broadcast', '#announce'
        ]
        
        return any(keyword in href_lower for keyword in notification_keywords)
    
    def _is_notification_title(self, title):
        """Cek apakah judul adalah notifikasi"""
        if not title:
            return False
        
        title_lower = title.lower()
        
        notification_keywords = [
            'notification', 'pemberitahuan', 'announcement',
            'pengumuman', '📢', '🔔', '⚡', '🚨',
            'info:', 'update:', 'important:', 'penting:',
            'pemberitahuan penting', 'important announcement',
            'announ:', 'notif:', 'info penting'
        ]
        
        return any(keyword in title_lower for keyword in notification_keywords)
    
    def _abs_url_oppa(self, src):
        """Convert relative URL to absolute"""
        if not src or src.strip() == '':
            return ''
        
        src = src.strip()
        
        if src.startswith('http'):
            return src
        elif src.startswith('//'):
            return 'https:' + src
        elif src.startswith('/'):
            return self.site + src
        else:
            return self.site + '/' + src
    
    def _make_relative_path(self, href):
        """Convert full URL to relative path"""
        try:
            parsed = urlparse(href)
            site_domains = ['oppa.biz', 'www.oppa.biz', 'oppadrama.biz', '45.11.57.125']
            
            if parsed.netloc and any(domain in parsed.netloc for domain in site_domains):
                path = parsed.path
                if parsed.query:
                    path += '?' + parsed.query
                return path
            elif not parsed.netloc:
                return href if href.startswith('/') else '/' + href
            else:
                return href
        except:
            return href if href.startswith('/') else '/' + href
    
    def _clean_html_text(self, text):
        """Clean HTML text dengan cepat"""
        if not text:
            return ''
        
        try:
            text = htmlmod.unescape(text)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
        except:
            return text or ''
    
    def _validate_year(self, year_str):
        """Validasi tahun yang realistic"""
        try:
            year = int(year_str)
            if 1900 <= year <= self.current_year + 2:
                return str(year)
        except:
            pass
        return ""
    
    def log(self, message, level="INFO"):
        """Simple logging method"""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_message = f"[{timestamp}] [{level}] [OPPADRAMA] {message}"
            print(log_message)
        except:
            print(f"[OPPADRAMA] {message}")