# -*- coding: utf-8 -*-
import re
import requests
import json
import time
import base64
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.site = 'https://animexin.dev'
        
        self.site_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.google.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }
        
        self.cache = {}
        self.session = requests.Session()
        
        self.log("ANIMEXIN Spider Started")

    def getName(self):
        return "🇨🇳 ANIMEXIN"

    def isVideoFormat(self, url):
        return any(ext in url.lower() for ext in ['.m3u8', '.mp4'])

    def homeContent(self, filter):
        return {
            'class': [
                
                {'type_name': '📋 Donghua List', 'type_id': 'anime'},
                
                {'type_name': '🔥 Trending', 'type_id': 'trending'},
                {'type_name': '🆕 Latest Added', 'type_id': 'latest'},
                {'type_name': '📈 Popular', 'type_id': 'popular'},
                {'type_name': '⏳ Ongoing', 'type_id': 'ongoing'},
                {'type_name': '✅ Completed', 'type_id': 'completed'},
                {'type_name': '🎬 Movie', 'type_id': 'movie'},
                {'type_name': '⚔️ Action', 'type_id': 'action'},
                {'type_name': '🌿 Cultivation', 'type_id': 'cultivation'},
                {'type_name': '💕 Romance', 'type_id': 'romance'},
                {'type_name': '✨ Fantasy', 'type_id': 'fantasy'},
                {'type_name': '🥋 Martial Arts', 'type_id': 'martial-arts'},
                {'type_name': '😂 Comedy', 'type_id': 'comedy'},
                {'type_name': '🎭 Drama', 'type_id': 'drama'},
                {'type_name': '☯️ Xianxia', 'type_id': 'xianxia'},
            ],
            'filters': {}
        }

    def homeVideoContent(self):
        try:
            url = f"{self.site}/"
            html = self.fetch(url).text
            soup = BeautifulSoup(html, 'html.parser')
            
            items = []
            seen = set()
            
            listupd = soup.find('div', class_='listupd') or soup.find('div', class_='releases')
            
            if listupd:
                for article in listupd.find_all('article', class_='bs'):
                    try:
                        link = article.find('a', href=True)
                        if not link: continue
                        
                        href = link.get('href')
                        if href in seen: continue
                        
                        title = ''
                        tt_div = article.find('div', class_='tt')
                        if tt_div:
                            h2 = tt_div.find('h2')
                            title = h2.text.strip() if h2 else tt_div.text.strip()
                        
                        if not title:
                            title = link.get('title', '')
                        
                        img_tag = article.select_one('div.limit img')
                        img = img_tag.get('src') or img_tag.get('data-src') or '' if img_tag else ''
                        
                        epx = article.find('span', class_='epx')
                        remarks = epx.text.strip() if epx else 'Ongoing'
                        
                        items.append({
                            'vod_id': href,
                            'vod_name': title,
                            'vod_pic': urljoin(self.site, img),
                            'vod_remarks': remarks
                        })
                        seen.add(href)
                    except:
                        continue
            
            return {'list': items}
        except Exception as e:
            self.log(f"Home error: {e}")
            return {'list': []}

    def _get_page_url(self, tid, pg):
        base_urls = {
            'home': '/', 'anime': '/anime/', 'release-date': '/release-date/', 'genres': '/genres/',
            'trending': '/anime/?order=popular', 'latest': '/anime/?order=latest',
            'popular': '/anime/?order=popular', 'ongoing': '/anime/?status=ongoing',
            'completed': '/anime/?status=completed', 'movie': '/anime/?type=movie',
            'action': '/anime/?genre[]=action', 'cultivation': '/anime/?genre[]=cultivation',
            'romance': '/anime/?genre[]=romance', 'fantasy': '/anime/?genre[]=fantasy',
            'martial-arts': '/anime/?genre[]=martial-arts', 'comedy': '/anime/?genre[]=comedy',
            'drama': '/anime/?genre[]=drama', 'xianxia': '/anime/?genre[]=xianxia',
        }
        base_path = base_urls.get(tid, '/anime/')
        
        if tid in ['home', 'release-date', 'genres']:
            if int(pg) > 1:
                return f"{self.site}{base_path.rstrip('/')}/page/{pg}/"
            return f"{self.site}{base_path}"
        
        if '?' in base_path:
            base_url, query = base_path.split('?', 1)
            if int(pg) > 1:
                return f"{self.site}{base_url}/?page={pg}&{query}"
            return f"{self.site}{base_url}/?{query}"
        
        if int(pg) > 1:
            return f"{self.site}{base_path}?page={pg}"
        return f"{self.site}{base_path}"

    def categoryContent(self, tid, pg, filter, extend):
        try:
            url = self._get_page_url(tid, pg)
            self.log(f"Category '{tid}' page {pg}: {url}")
            
            html = self.fetch(url).text
            soup = BeautifulSoup(html, 'html.parser')
            
            items = []
            seen = set()
            
            listupd = soup.find('div', class_='listupd') or soup.find('div', class_='releases')
            
            if listupd:
                for article in listupd.find_all('article', class_='bs'):
                    try:
                        link = article.find('a', href=True)
                        if not link: continue
                        
                        href = link.get('href')
                        if href in seen: continue
                        
                        tt_div = article.find('div', class_='tt')
                        title = ''
                        if tt_div:
                            h2 = tt_div.find('h2')
                            title = h2.text.strip() if h2 else tt_div.text.strip()
                        
                        if not title:
                            title = link.get('title', '')
                        
                        img_tag = article.select_one('div.limit img')
                        img = img_tag.get('src') or img_tag.get('data-src') or '' if img_tag else ''
                        
                        epx = article.find('span', class_='epx')
                        remarks = epx.text.strip() if epx else 'Ongoing'
                        
                        items.append({
                            'vod_id': href,
                            'vod_name': title,
                            'vod_pic': urljoin(self.site, img),
                            'vod_remarks': remarks
                        })
                        seen.add(href)
                    except:
                        continue
            
            total_pages = int(pg)
            max_page = 0
            hpage = soup.find('div', class_='hpage')
            if hpage:
                for a in hpage.find_all('a'):
                    if a.text.strip().isdigit():
                        max_page = max(max_page, int(a.text.strip()))
                    href = a.get('href', '')
                    page_match = re.search(r'page[=/](\d+)', href)
                    if page_match:
                        max_page = max(max_page, int(page_match.group(1)))
                if max_page > 0:
                    total_pages = max_page
            
            return {'list': items, 'page': int(pg), 'pagecount': total_pages, 'limit': 30}
        except Exception as e:
            self.log(f"Category error: {e}")
            return {'list': []}

    def detailContent(self, ids):
        try:
            url = ids[0] if ids[0].startswith('http') else urljoin(self.site, ids[0])
            self.log(f"Detail: {url}")
            
            html = self.fetch(url).text
            soup = BeautifulSoup(html, 'html.parser')
            
            title = ''
            title_elem = soup.find('h1', class_='entry-title')
            if title_elem:
                title = title_elem.text.strip()
            
            img = ''
            meta_img = soup.find('meta', property='og:image')
            if meta_img:
                img = meta_img.get('content', '')
            
            desc = ''
            desc_elem = soup.find('div', class_='entry-content')
            if desc_elem:
                desc = desc_elem.get_text(strip=True)[:500]
            
            year = ''
            year_match = re.search(r'20\d{2}', html)
            if year_match:
                year = year_match.group(0)
            
            episodes = []
            eplister = soup.find('div', class_='eplister')
            if eplister:
                for li in eplister.find_all('li'):
                    link = li.find('a', href=True)
                    if not link: continue
                    ep_href = link.get('href')
                    ep_num = None
                    num_div = li.find('div', class_='epl-num')
                    if num_div:
                        nums = re.findall(r'\d+', num_div.text)
                        if nums:
                            ep_num = nums[0]
                    if ep_num:
                        episodes.append(f"{ep_num}${ep_href}")
            
            episodes.sort(key=lambda x: int(x.split('$')[0]))
            play_url = '#'.join(episodes) if episodes else f"1${url}"
            
            return {'list': [{'vod_id': url, 'vod_name': title, 'vod_pic': img, 'vod_year': year, 'vod_content': desc, 'vod_remarks': 'Ongoing', 'vod_play_from': 'ANIMEXIN', 'vod_play_url': play_url}]}
        except Exception as e:
            self.log(f"Detail error: {e}")
            return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        try:
            url = f"{self.site}/page/{pg}/?s={quote(key)}" if int(pg) > 1 else f"{self.site}/?s={quote(key)}"
            html = self.fetch(url).text
            soup = BeautifulSoup(html, 'html.parser')
            
            items = []
            listupd = soup.find('div', class_='listupd')
            if listupd:
                for article in listupd.find_all('article', class_='bs'):
                    try:
                        link = article.find('a', href=True)
                        if not link: continue
                        href = link.get('href')
                        tt_div = article.find('div', class_='tt')
                        title = ''
                        if tt_div:
                            h2 = tt_div.find('h2')
                            title = h2.text.strip() if h2 else tt_div.text.strip()
                        if not title:
                            title = link.get('title', '')
                        img_tag = article.select_one('div.limit img')
                        img = img_tag.get('src') or img_tag.get('data-src') or '' if img_tag else ''
                        epx = article.find('span', class_='epx')
                        remarks = epx.text.strip() if epx else ''
                        items.append({'vod_id': href, 'vod_name': title, 'vod_pic': urljoin(self.site, img), 'vod_remarks': remarks})
                    except:
                        continue
            
            total_pages = int(pg)
            hpage = soup.find('div', class_='hpage')
            if hpage:
                for a in hpage.find_all('a'):
                    if a.text.strip().isdigit():
                        total_pages = max(total_pages, int(a.text.strip()))
            return {'list': items, 'page': int(pg), 'pagecount': total_pages}
        except Exception as e:
            self.log(f"Search error: {e}")
            return {'list': []}

    # ========== PLAYER DENGAN PILIHAN SERVER INDONESIA ==========
    def playerContent(self, flag, id, vipFlags):
        """
        Player - Memilih server Indonesia (Dailymotion atau lainnya)
        """
        try:
            self.log(f"Player for: {id}")
            
            session = requests.Session()
            session.headers.update(self.site_headers)
            session.get(self.site, timeout=10)
            
            resp = session.get(id, timeout=15)
            html = resp.text
            soup = BeautifulSoup(html, 'html.parser')
            
            # Headers untuk streaming
            stream_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.dailymotion.com/',
                'Origin': 'https://www.dailymotion.com',
                'Accept': '*/*',
                'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            }
            
            # ===== CARI SERVER INDONESIA DI MIRROR SELECT =====
            mirror_select = soup.find('select', class_='mirror')
            if mirror_select:
                options = mirror_select.find_all('option')
                
                # Kata kunci untuk server Indonesia
                indonesia_keywords = [
                    'indonesia', 'indo', 'sub indo', 'subtitle indonesia',
                    'hardsub indonesia', 'hardsub indonesia', 'indonesian'
                ]
                
                # PRIORITAS 1: Cari server Indonesia + Dailymotion
                for option in options:
                    option_text = option.text.strip().lower()
                    option_value = option.get('value', '')
                    
                    is_indonesia = any(keyword in option_text for keyword in indonesia_keywords)
                    is_dailymotion = 'dailymotion' in option_text
                    
                    if is_indonesia and is_dailymotion:
                        self.log(f"✅ Server Indonesia Dailymotion: {option.text}")
                        
                        try:
                            decoded = base64.b64decode(option_value).decode('utf-8')
                            src_match = re.search(r'src=["\'](.*?)["\']', decoded)
                            if src_match:
                                video_url = src_match.group(1)
                                if video_url.startswith('//'):
                                    video_url = 'https:' + video_url
                                
                                # Coba API Dailymotion
                                video_id_match = re.search(r'/video/([a-zA-Z0-9]+)', video_url)
                                if video_id_match:
                                    video_id = video_id_match.group(1)
                                    api_url = f"https://www.dailymotion.com/player/metadata/video/{video_id}"
                                    
                                    try:
                                        api_resp = session.get(api_url, timeout=10)
                                        if api_resp.status_code == 200:
                                            api_data = api_resp.json()
                                            if 'qualities' in api_data:
                                                for quality in ['auto', '1080', '720', '480']:
                                                    if quality in api_data['qualities'] and api_data['qualities'][quality]:
                                                        for stream in api_data['qualities'][quality]:
                                                            if 'url' in stream:
                                                                return {'parse': 1, 'url': stream['url'], 'header': stream_headers}
                                    except:
                                        pass
                                
                                return {'parse': 1, 'url': video_url, 'header': stream_headers}
                        except:
                            continue
                
                # PRIORITAS 2: Cari server Indonesia (tanpa Dailymotion)
                for option in options:
                    option_text = option.text.strip().lower()
                    option_value = option.get('value', '')
                    
                    is_indonesia = any(keyword in option_text for keyword in indonesia_keywords)
                    
                    if is_indonesia:
                        self.log(f"✅ Server Indonesia (other): {option.text}")
                        
                        try:
                            decoded = base64.b64decode(option_value).decode('utf-8')
                            src_match = re.search(r'src=["\'](.*?)["\']', decoded)
                            if src_match:
                                video_url = src_match.group(1)
                                if video_url.startswith('//'):
                                    video_url = 'https:' + video_url
                                return {'parse': 1, 'url': video_url, 'header': stream_headers}
                        except:
                            continue
                
                # PRIORITAS 3: Cari server Dailymotion biasa
                for option in options:
                    option_text = option.text.strip().lower()
                    if 'dailymotion' in option_text:
                        self.log(f"Fallback Dailymotion: {option.text}")
                        try:
                            decoded = base64.b64decode(option.get('value')).decode('utf-8')
                            src_match = re.search(r'src=["\'](.*?)["\']', decoded)
                            if src_match:
                                video_url = src_match.group(1)
                                if video_url.startswith('//'):
                                    video_url = 'https:' + video_url
                                return {'parse': 1, 'url': video_url, 'header': stream_headers}
                        except:
                            continue
            
            # ===== FALLBACK: M3U8 LANGSUNG =====
            m3u8_patterns = [
                r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
                r'"(https?://[^"]+\.m3u8[^"]*)"',
                r"'(https?://[^']+\.m3u8[^']*)'",
            ]
            
            for pattern in m3u8_patterns:
                matches = re.findall(pattern, html, re.I)
                for match in matches:
                    if match and match.startswith('http'):
                        return {'parse': 1, 'url': match, 'header': stream_headers}
            
            # ===== FALLBACK: IFRAME =====
            iframe_pattern = r'<iframe.*?src=["\'](.*?)["\']'
            iframe_matches = re.findall(iframe_pattern, html, re.I | re.S)
            for iframe_url in iframe_matches:
                if iframe_url.startswith('//'):
                    return {'parse': 1, 'url': 'https:' + iframe_url, 'header': self.site_headers}
                elif iframe_url.startswith('http'):
                    return {'parse': 1, 'url': iframe_url, 'header': self.site_headers}
            
            return {'parse': 1, 'url': id}
            
        except Exception as e:
            self.log(f"Player error: {e}")
            return {'parse': 1, 'url': id}

    def fetch(self, url, timeout=15, max_retries=3):
        for attempt in range(max_retries):
            try:
                time.sleep(1)
                resp = self.session.get(url, headers=self.site_headers, timeout=timeout)
                resp.raise_for_status()
                return resp
            except Exception as e:
                self.log(f"Fetch attempt {attempt+1} failed: {e}")
                if attempt == max_retries - 1:
                    class Dummy:
                        text = ''
                    return Dummy()
                time.sleep(2)

    def log(self, msg):
        print(f"[ANIMEXIN] {msg}")

    def destroy(self):
        if self.session:
            self.session.close()