# -*- coding: utf-8 -*-
import re, sys, os, requests, html as htmlmod, json, datetime, time
from urllib.parse import urlparse, urljoin, quote, unquote
from bs4 import BeautifulSoup
import cachetools
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.site = 'https://dramahua.my.id'
        
        self.site_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'referer': f'{self.site}/'
        }
        
        # Cache
        self.cache = cachetools.TTLCache(maxsize=100, ttl=1800)
        self.session = requests.Session()
    
    def getName(self):
        return "DRAMAHUA"
    
    def homeContent(self, filter):
        """Hanya tampilkan kategori yang ADA di website"""
        return {
            'class': [
                
                {'type_name': '📚 Browse All Drama', 'type_id': 'browse'},
                {'type_name': '🔍 Search', 'type_id': 'search'}
            ],
            'filters': {}
        }
    
    def homeVideoContent(self):
        """Homepage - dari halaman utama (/)"""
        try:
            response = self.session.get(self.site, headers=self.site_headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            items = []
            seen_ids = set()  # Gunakan ID untuk deteksi duplikat
            
            # Cari semua card drama di halaman utama
            cards = soup.find_all('div', class_=re.compile(r'col-\d+'))
            for card in cards[:20]:  # Batasi 20 item untuk homepage
                try:
                    item = self._parse_card(card)
                    if item and item['vod_id'] and item['vod_id'] not in seen_ids:
                        seen_ids.add(item['vod_id'])
                        items.append(item)
                except Exception as e:
                    self.log(f"Error parsing card in homepage: {str(e)}", level="DEBUG")
                    continue
            
            return {'list': items}
            
        except Exception as e:
            self.log(f'homeVideoContent error: {str(e)}')
            return {'list': []}
    
    def categoryContent(self, tid, pg, filter, extend):
        """Untuk kategori tertentu - SESUAI WEBSITE"""
        try:
            page = int(pg) if pg else 1
            
            if tid == 'search' and extend.get('keyword'):
                # SEARCH FUNCTION
                keyword = extend['keyword']
                search_url = f"{self.site}/search?q={quote(keyword)}"
                if page > 1:
                    search_url += f"&page={page}"
                
                self.log(f"Searching: {search_url}")
                response = self.session.get(search_url, headers=self.site_headers, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                items = []
                seen_ids = set()
                
                # Parse hasil search
                cards = soup.find_all('div', class_=re.compile(r'col-\d+'))
                for card in cards:
                    item = self._parse_card(card)
                    if item and item['vod_id'] and item['vod_id'] not in seen_ids:
                        seen_ids.add(item['vod_id'])
                        items.append(item)
                
                return {
                    'list': items,
                    'page': page,
                    'pagecount': 9999,
                    'limit': 20,
                    'total': 999999
                }
            
            elif tid == 'browse':
                # BROWSE ALL DRAMA
                if page == 1:
                    url = f"{self.site}/browse"
                else:
                    url = f"{self.site}/browse/page/{page}"
                
                self.log(f"Browsing page {page}: {url}")
                response = self.session.get(url, headers=self.site_headers, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                items = []
                seen_ids = set()
                
                # Parse semua drama dari halaman browse
                cards = soup.find_all('div', class_=re.compile(r'col-\d+'))
                for card in cards:
                    item = self._parse_card(card)
                    if item and item['vod_id'] and item['vod_id'] not in seen_ids:
                        seen_ids.add(item['vod_id'])
                        items.append(item)
                
                return {
                    'list': items,
                    'page': page,
                    'pagecount': 9999,
                    'limit': 20,
                    'total': 999999
                }
            
            else:
                # HOME (default) - dari halaman utama
                if page == 1:
                    url = self.site
                else:
                    # Untuk home page > 1, gunakan browse
                    url = f"{self.site}/browse/page/{page}"
                
                response = self.session.get(url, headers=self.site_headers, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                items = []
                seen_ids = set()
                
                cards = soup.find_all('div', class_=re.compile(r'col-\d+'))
                for card in cards:
                    item = self._parse_card(card)
                    if item and item['vod_id'] and item['vod_id'] not in seen_ids:
                        seen_ids.add(item['vod_id'])
                        items.append(item)
                
                return {
                    'list': items,
                    'page': page,
                    'pagecount': 9999,
                    'limit': 20,
                    'total': 999999
                }
            
        except Exception as e:
            self.log(f'categoryContent error: {str(e)}')
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 20, 'total': 0}
    
    def detailContent(self, ids):
        """DETAIL CONTENT"""
        try:
            vod_id = ids[0]
            if not vod_id:
                return {'list': []}
            
            if not vod_id.startswith('/'):
                vod_id = '/' + vod_id
            
            full_url = f"{self.site}{vod_id}"
            
            self.log(f"Fetching detail: {full_url}")
            response = self.session.get(full_url, headers=self.site_headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Parse judul
            title = "Drama Pendek"
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text(strip=True)
            
            # Parse gambar
            img_src = ""
            img = soup.find('img', class_='rounded')
            if img:
                img_src = img.get('src', '')
            
            # Parse deskripsi
            desc = ""
            p = soup.find('p', class_='text-light')
            if p:
                desc = p.get_text(strip=True)
            
            # Parse episode
            episodes = []
            
            # Cari semua link episode
            episode_links = soup.find_all('a', href=re.compile(r'/watch/\d+/\d+'))
            for i, link in enumerate(episode_links, 1):
                href = link.get('href', '')
                if href:
                    episodes.append({
                        'name': str(i),
                        'url': href if href.startswith('/') else '/' + href
                    })
            
            # Jika tidak ada episode, tambahkan satu default
            if not episodes:
                episodes.append({
                    'name': "1",
                    'url': vod_id
                })
            
            # Format play_url
            play_urls = []
            for ep in episodes[:100]:
                play_urls.append(f"{ep['name']}${ep['url']}")
            
            play_str = '#'.join(play_urls) if play_urls else f"1${vod_id}"
            
            # Format output
            result = {
                'list': [{
                    'vod_id': vod_id,
                    'vod_name': self._clean_text(title),
                    'vod_pic': img_src,
                    'vod_year': str(datetime.datetime.now().year),
                    'vod_area': 'CN',
                    'vod_remarks': f"{len(episodes)} Episode",
                    'vod_content': self._clean_text(desc)[:500],
                    'vod_play_from': 'DRAMAHUA',
                    'vod_play_url': play_str
                }]
            }
            
            self.log(f"Detail parsed: {title} - {len(episodes)} episodes")
            return result
            
        except Exception as e:
            self.log(f'detailContent ERROR: {str(e)}', level="ERROR")
            return {'list': []}
    
    def searchContent(self, key, quick, pg="1"):
        try:
            if not key or len(key) < 2:
                return {'list': []}
            
            page = int(pg) if pg else 1
            search_url = f"{self.site}/search?q={quote(key)}"
            if page > 1:
                search_url += f"&page={page}"
            
            response = self.session.get(search_url, headers=self.site_headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            items = []
            seen_ids = set()
            
            cards = soup.find_all('div', class_=re.compile(r'col-\d+'))
            for card in cards:
                item = self._parse_card(card)
                if item and item['vod_id'] and item['vod_id'] not in seen_ids:
                    seen_ids.add(item['vod_id'])
                    items.append(item)
            
            return {
                'list': items[:40],
                'page': page,
                'pagecount': 9999,
                'limit': 40,
                'total': 999999
            }
            
        except Exception as e:
            self.log(f'searchContent error: {str(e)}')
            return {'list': [], 'page': 1, 'pagecount': 1}
    
    def playerContent(self, flag, id, vipFlags):
        """PLAYER CONTENT"""
        try:
            id = unquote(id)
            
            if not id.startswith('http'):
                play_url = f"{self.site}{id}" if id.startswith('/') else f"{self.site}/{id}"
            else:
                play_url = id
            
            self.log(f'Player resolving: {play_url}')
            
            response = self.session.get(play_url, headers=self.site_headers, timeout=15)
            html = response.text
            
            # Cari iframe
            iframe_match = re.search(r'<iframe[^>]+src="([^"]+)"', html)
            if iframe_match:
                iframe_src = iframe_match.group(1)
                if iframe_src:
                    if not iframe_src.startswith('http'):
                        iframe_src = f"{self.site}{iframe_src}"
                    
                    headers = self.site_headers.copy()
                    headers['Referer'] = play_url
                    
                    return {
                        'parse': 1,
                        'url': iframe_src,
                        'header': headers
                    }
            
            # Jika tidak ada iframe, cari video langsung
            video_url = self._find_video_url(html)
            if video_url:
                return {
                    'parse': 0,
                    'url': video_url,
                    'header': {
                        'User-Agent': self.site_headers['User-Agent'],
                        'Referer': play_url
                    }
                }
            
            return {
                'parse': 1,
                'url': play_url,
                'header': self.site_headers
            }
            
        except Exception as e:
            self.log(f'playerContent error: {str(e)}')
            return {
                'parse': 1,
                'url': id if id.startswith('http') else f"{self.site}{id}",
                'header': self.site_headers
            }
    
    # ==================== HELPER METHODS ====================
    
    def _parse_card(self, card):
        """Parse card item"""
        try:
            # Cari link
            link = card.find('a', href=True)
            if not link:
                return None
            
            href = link.get('href', '').strip()
            if not href:
                return None
            
            # Cari judul
            title = ""
            h6 = card.find('h6')
            if h6:
                title = h6.get_text(strip=True)
            
            if not title:
                img = card.find('img')
                if img:
                    title = img.get('alt', '') or img.get('title', '')
            
            if not title:
                return None
            
            # Cari gambar
            img_src = ""
            img = card.find('img')
            if img:
                img_src = img.get('src', '')
            
            # Generate vod_id
            vod_id = href
            
            # Cari episode count jika ada
            remarks = "Drama Pendek"
            episode_badge = card.find('span', class_=re.compile(r'badge|episode'))
            if episode_badge:
                remarks = episode_badge.get_text(strip=True)
            
            return {
                'vod_id': vod_id if vod_id.startswith('/') else '/' + vod_id,
                'vod_name': self._clean_text(title)[:100],
                'vod_pic': img_src,
                'vod_remarks': remarks[:50]
            }
            
        except Exception as e:
            self.log(f"_parse_card error: {str(e)}", level="DEBUG")
            return None
    
    def _find_video_url(self, html):
        """Cari video URL"""
        patterns = [
            re.compile(r'file:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', re.I),
            re.compile(r'src="(https?://[^"]+\.m3u8[^"]*)"', re.I),
            re.compile(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', re.I)
        ]
        
        for pattern in patterns:
            match = pattern.search(html)
            if match:
                url = match.group(1)
                if url:
                    if url.startswith('//'):
                        return 'https:' + url
                    elif url.startswith('/'):
                        return self.site + url
                    elif url.startswith('http'):
                        return url
        return None
    
    def _clean_text(self, text):
        """Bersihkan text"""
        if not text:
            return ''
        text = htmlmod.unescape(text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def log(self, message, level="INFO"):
        """Logging"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] [{level}] [DRAMAHUA] {message}")
        except:
            print(f"[DRAMAHUA] {message}")