# -*- coding: utf-8 -*-
import re, sys, os, requests, html as htmlmod, json, datetime, random, time
from urllib.parse import urlparse, urljoin, quote, unquote
from bs4 import BeautifulSoup
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.site = 'https://donghub.vip'
        
        self.site_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': f'{self.site}/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        
        self.cache = {}
        self.session = requests.Session()
        
        # Mapping kategori berdasarkan struktur website yang sudah diverifikasi
        self.category_map = {
            # Halaman utama
            'trending': '/anime/',
            'terbaru': '/anime/?sub=&order=latest',
            'update': '/anime/?sub=&order=update',
            'populer': '/anime/?sub=&order=popular',
            
            # Status
            'ongoing': '/anime/?status=ongoing',
            'completed': '/anime/?status=completed',
            'upcoming': '/anime/?status=upcoming',
            'hiatus': '/anime/?status=hiatus',
            
            # Type
            'tv': '/anime/?type=tv',
            'ona': '/anime/?type=ona',
            'ova': '/anime/?type=ova',
            'movie': '/anime/?type=movie',
            'special': '/anime/?type=special',
            'bd': '/anime/?type=bd',
            'live-action': '/anime/?type=live action',
            'music': '/anime/?type=music',
            
            # Genres - menggunakan format array []
            'action': '/anime/?genre[]=action',
            'adventure': '/anime/?genre[]=adventure',
            'comedy': '/anime/?genre[]=comedy',
            'cultivation': '/anime/?genre[]=cultivation',
            'drama': '/anime/?genre[]=drama',
            'fantasy': '/anime/?genre[]=fantasy',
            'historical': '/anime/?genre[]=historical',
            'martial-arts': '/anime/?genre[]=martial-arts',
            'mystery': '/anime/?genre[]=mystery',
            'psychological': '/anime/?genre[]=psychological',
            'reincarnation': '/anime/?genre[]=reincarnation',
            'romance': '/anime/?genre[]=romance',
            'sci-fi': '/anime/?genre[]=sci-fi',
            'super-power': '/anime/?genre[]=super-power',
            'supranatural': '/anime/?genre[]=supranatural',
            'urban-fantasy': '/anime/?genre[]=urban-fantasy',
            'war': '/anime/?genre[]=war',
            
            # Sub - sesuai URL: ?sub=sub
            'sub': '/anime/?sub=sub',
            'dub': '/anime/?sub=dub',
            'raw': '/anime/?sub=raw',
        }
        
        self.log("DONGHUB Spider initialized dengan semua kategori termasuk Sub")
    
    def getName(self):
        return "🐉 DONGHUB"
    
    def isVideoFormat(self, url):
        return any(ext in url.lower() for ext in ['.m3u8', '.mp4', '.mkv', '.avi'])
    
    def manualVideoCheck(self):
        return True
    
    def homeContent(self, filter):
        """Kategori home"""
        return {
            'class': [
                {'type_name': '🔥 Trending', 'type_id': 'trending'},
                {'type_name': '🆕 Terbaru', 'type_id': 'terbaru'},
                {'type_name': '📺 Update', 'type_id': 'update'},
                {'type_name': '⭐ Populer', 'type_id': 'populer'},
                {'type_name': '⚔️ Action', 'type_id': 'action'},
                {'type_name': '🌿 Cultivation', 'type_id': 'cultivation'},
                {'type_name': '🎋 Fantasy', 'type_id': 'fantasy'},
                {'type_name': '⚡ Martial Arts', 'type_id': 'martial-arts'},
                {'type_name': '💕 Romance', 'type_id': 'romance'},
                {'type_name': '✅ Ongoing', 'type_id': 'ongoing'},
                {'type_name': '🏁 Completed', 'type_id': 'completed'},
                {'type_name': '🎬 Movie', 'type_id': 'movie'},
                {'type_name': '📺 TV Series', 'type_id': 'tv'},
                {'type_name': '📱 ONA', 'type_id': 'ona'},
                {'type_name': '🔊 Sub Indo', 'type_id': 'sub'},
                {'type_name': '🎤 Dub', 'type_id': 'dub'},
            ],
            'filters': {}
        }
    
    def homeVideoContent(self):
        """Home video content"""
        try:
            if 'home' in self.cache:
                return self.cache['home']
            
            self.log("Fetching home page...")
            html = self.fetch(self.site).text
            soup = BeautifulSoup(html, 'html.parser')
            
            items = []
            seen = set()
            
            # Cari di section listupd
            listupd = soup.find('div', class_='listupd')
            if not listupd:
                listupd = soup
            
            for article in listupd.find_all('article', class_='bs'):
                try:
                    link = article.find('a', href=True)
                    if not link:
                        continue
                    
                    href = link.get('href')
                    if not href or href in seen:
                        continue
                    
                    # Judul
                    title_elem = article.find('div', class_='tt')
                    title = title_elem.text.strip() if title_elem else ''
                    
                    if not title:
                        title = link.get('title', '')
                    
                    if not title or len(title) < 2:
                        continue
                    
                    # Bersihkan judul
                    title = re.sub(r'\s*(?:Episode|Ep)\s*\d+.*$', '', title, flags=re.I)
                    title = title.strip()
                    
                    # Gambar
                    img_url = ''
                    limit_div = article.find('div', class_='limit')
                    if limit_div:
                        img = limit_div.find('img')
                        if img:
                            img_url = img.get('src') or img.get('data-src') or ''
                            if img_url and not img_url.startswith('http'):
                                img_url = self.site + img_url
                    
                    # Status/Episode
                    remarks = 'Ongoing'
                    epx = article.find('span', class_='epx')
                    if epx:
                        remarks = epx.text.strip()
                    
                    # Hot badge
                    if article.find('div', class_='hotbadge'):
                        remarks = '🔥 ' + remarks
                    
                    item = {
                        'vod_id': href,
                        'vod_name': title,
                        'vod_pic': img_url,
                        'vod_remarks': remarks
                    }
                    
                    seen.add(href)
                    items.append(item)
                    
                except:
                    continue
                
                if len(items) >= 36:
                    break
            
            self.log(f"Found {len(items)} items")
            
            result = {'list': items}
            self.cache['home'] = result
            return result
            
        except Exception as e:
            self.log(f"Home error: {e}")
            return {'list': []}
    
    def categoryContent(self, tid, pg, filter, extend):
        """Konten kategori dengan pagination untuk semua kategori (mendukung banyak halaman)"""
        try:
            # Cari URL berdasarkan tid
            url = self.site
            
            if tid in self.category_map and self.category_map[tid]:
                url = self.site + self.category_map[tid]
            else:
                url = self.site + '/anime/'
            
            # Bersihkan URL dari parameter page yang mungkin sudah ada
            url = re.sub(r'&?page=\d+', '', url)
            
            # Handle pagination - semua kategori menggunakan format ?page=N&parameter=lainnya
            if int(pg) > 1:
                if '?' in url:
                    base_url, query = url.split('?', 1)
                    url = f"{base_url}?page={pg}&{query}"
                else:
                    url = f"{url}?page={pg}"
            
            self.log(f"Fetching category '{tid}' page {pg}: {url}")
            
            html = self.fetch(url).text
            soup = BeautifulSoup(html, 'html.parser')
            
            items = []
            seen = set()
            
            # Cari di div.listupd
            listupd = soup.find('div', class_='listupd')
            if not listupd:
                listupd = soup
            
            for article in listupd.find_all('article', class_='bs'):
                try:
                    link = article.find('a', href=True)
                    if not link:
                        continue
                    
                    href = link.get('href')
                    if not href or href in seen:
                        continue
                    
                    # Judul
                    title_elem = article.find('div', class_='tt')
                    title = title_elem.text.strip() if title_elem else ''
                    
                    if not title:
                        title = link.get('title', '')
                    
                    if not title:
                        continue
                    
                    title = re.sub(r'\s*(?:Episode|Ep)\s*\d+.*$', '', title, flags=re.I)
                    title = title.strip()
                    
                    # Gambar
                    img_url = ''
                    limit_div = article.find('div', class_='limit')
                    if limit_div:
                        img = limit_div.find('img')
                        if img:
                            img_url = img.get('src') or img.get('data-src') or ''
                    
                    # Remarks
                    remarks = 'Ongoing'
                    epx = article.find('span', class_='epx')
                    if epx:
                        remarks = epx.text.strip()
                    
                    # Cek status dari div.status
                    status_div = article.find('div', class_='status')
                    if status_div and status_div.text.strip():
                        remarks = status_div.text.strip()
                    
                    # Hot badge
                    if article.find('div', class_='hotbadge'):
                        remarks = '🔥 ' + remarks
                    
                    item = {
                        'vod_id': href,
                        'vod_name': title,
                        'vod_pic': img_url,
                        'vod_remarks': remarks
                    }
                    
                    seen.add(href)
                    items.append(item)
                    
                except Exception as e:
                    continue
            
            # Hitung total halaman dari elemen pagination
            total_pages = int(pg)  # Default ke halaman saat ini
            
            # Cari elemen pagination
            hpage = soup.find('div', class_='hpage')
            if hpage:
                # Cari semua link nomor halaman
                page_links = hpage.find_all('a')
                for link in page_links:
                    link_text = link.text.strip()
                    # Jika link berisi angka (nomor halaman)
                    if link_text.isdigit():
                        page_num = int(link_text)
                        if page_num > total_pages:
                            total_pages = page_num
                
                # Cari link "Next" (biasanya class 'r' atau teks "Next"/"›")
                next_link = hpage.find('a', class_='r') or hpage.find('a', string=re.compile(r'Next|›|»', re.I))
                if next_link:
                    # Jika ada next link, pastikan total_pages setidaknya pg+1
                    total_pages = max(total_pages, int(pg) + 1)
                    
                    # Coba ekstrak dari href next link untuk mendapatkan halaman terakhir
                    next_href = next_link.get('href', '')
                    # Cari pattern page=N di URL
                    page_match = re.search(r'page[=/](\d+)', next_href)
                    if page_match:
                        next_page = int(page_match.group(1))
                        total_pages = max(total_pages, next_page)
                
                # Cari link "Last" jika ada
                last_link = hpage.find('a', string=re.compile(r'Last|Akhir|»»', re.I))
                if last_link:
                    last_href = last_link.get('href', '')
                    page_match = re.search(r'page[=/](\d+)', last_href)
                    if page_match:
                        last_page = int(page_match.group(1))
                        total_pages = max(total_pages, last_page)
            
            # Jika tidak ada informasi pagination, asumsikan ada banyak halaman
            if total_pages == int(pg) and len(items) > 0:
                # Jika ini halaman 1 dan ada items, asumsikan minimal 5 halaman
                if int(pg) == 1:
                    total_pages = 5
                else:
                    # Jika ini halaman >1, asumsikan ada halaman berikutnya
                    total_pages = int(pg) + 1
            
            self.log(f"Found {len(items)} items for '{tid}', page {pg}/{total_pages}")
            
            return {
                'list': items,
                'page': int(pg),
                'pagecount': total_pages,
                'limit': 30,
                'total': len(items) * total_pages if total_pages > 0 else len(items)
            }
            
        except Exception as e:
            self.log(f"Category error for '{tid}': {e}")
            return {'list': []}
    
    def detailContent(self, ids):
        """
        Detail konten dan episode - hanya menampilkan angka
        """
        try:
            url = ids[0]
            if not url.startswith('http'):
                url = self.site + url if url.startswith('/') else self.site + '/' + url
            
            self.log(f"Fetching detail: {url}")
            
            html = self.fetch(url).text
            soup = BeautifulSoup(html, 'html.parser')
            
            # === CEK APAKAH INI HALAMAN EPISODE ===
            is_episode_page = False
            series_url = url
            
            episode_patterns = [
                r'/episode[-\s]*(\d+)',
                r'-episode[-\s]*(\d+)',
                r'(\d+)-subtitle-indonesia',
                r'episode-(\d+)-',
            ]
            
            for pattern in episode_patterns:
                if re.search(pattern, url, re.I):
                    is_episode_page = True
                    break
            
            # Jika ini halaman episode, cari link ke series
            if is_episode_page:
                breadcrumb = soup.find('div', class_='ts-breadcrumb')
                if breadcrumb:
                    links = breadcrumb.find_all('a')
                    if len(links) >= 2:
                        series_url = links[1].get('href')
                        if not series_url.startswith('http'):
                            series_url = self.site + series_url
                        
                        # Fetch halaman series
                        html = self.fetch(series_url).text
                        soup = BeautifulSoup(html, 'html.parser')
            
            # === INFO DASAR ===
            # Title
            title = ''
            title_elem = soup.find('h1', class_='entry-title')
            if not title_elem:
                title_elem = soup.find('h1')
            if title_elem:
                title = title_elem.text.strip()
            
            # Image
            img = ''
            meta_img = soup.find('meta', property='og:image')
            if meta_img:
                img = meta_img.get('content', '')
            if not img:
                img_elem = soup.find('img', class_='wp-post-image')
                if img_elem:
                    img = img_elem.get('src') or img_elem.get('data-src') or ''
            
            # Description
            desc = ''
            content_div = soup.find('div', class_='entry-content')
            if content_div:
                desc = content_div.get_text(strip=True)[:500]
            
            # Year
            year = ''
            year_match = re.search(r'\b(20\d{2})\b', html)
            if year_match:
                year = year_match.group(1)
            
            # === AMBIL EPISODE - HANYA ANGKA ===
            episodes = []
            episode_numbers = set()
            
            # Cari di div.eplister
            eplister = soup.find('div', class_='eplister')
            if eplister:
                for li in eplister.find_all('li'):
                    link = li.find('a', href=True)
                    if not link:
                        continue
                    
                    ep_href = link.get('href')
                    ep_num = None
                    
                    # 1. Coba dari div.epl-num
                    num_div = li.find('div', class_='epl-num')
                    if num_div:
                        num_text = num_div.text.strip()
                        numbers = re.findall(r'\d+', num_text)
                        if numbers:
                            ep_num = numbers[0]
                    
                    # 2. Coba dari div.epl-title
                    if not ep_num:
                        title_div = li.find('div', class_='epl-title')
                        if title_div:
                            title_text = title_div.text.strip()
                            numbers = re.findall(r'\d+', title_text)
                            if numbers:
                                ep_num = numbers[0]
                    
                    # 3. Coba dari teks link
                    if not ep_num:
                        link_text = link.get_text(strip=True)
                        numbers = re.findall(r'\d+', link_text)
                        if numbers:
                            ep_num = numbers[0]
                    
                    # 4. Fallback dari URL
                    if not ep_num:
                        url_match = re.search(r'episode[-\s]*(\d+)', ep_href, re.I)
                        if url_match:
                            ep_num = url_match.group(1)
                    
                    # Tambahkan jika dapat nomor
                    if ep_num and ep_num not in episode_numbers:
                        episode_numbers.add(ep_num)
                        episodes.append(f"{ep_num}${ep_href}")
            
            # Urutkan dari kecil ke besar
            episodes.sort(key=lambda x: int(x.split('$')[0]) if x.split('$')[0].isdigit() else 0)
            
            # Jika masih kosong, tambahkan default
            if not episodes:
                episodes.append(f"1${series_url}")
            
            play_url = '#'.join(episodes)
            
            # Status/Remarks
            status = 'Ongoing'
            status_elem = soup.find('span', text=re.compile(r'Status:', re.I))
            if status_elem:
                status_text = status_elem.find_next('span')
                if status_text:
                    status = status_text.text.strip()
            
            result = {
                'list': [{
                    'vod_id': series_url,
                    'vod_name': title or 'Unknown',
                    'vod_pic': img,
                    'vod_year': year,
                    'vod_content': desc,
                    'vod_remarks': status,
                    'vod_play_from': 'DONGHUB',
                    'vod_play_url': play_url
                }]
            }
            
            return result
            
        except Exception as e:
            self.log(f"Detail error: {e}")
            return {'list': []}
    
    def searchContent(self, key, quick, pg="1"):
        """Pencarian dengan pagination"""
        try:
            url = f"{self.site}/?s={quote(key)}"
            if int(pg) > 1:
                url += f"&page={pg}"
            
            self.log(f"Search page {pg}: {url}")
            
            html = self.fetch(url).text
            soup = BeautifulSoup(html, 'html.parser')
            
            items = []
            seen = set()
            
            listupd = soup.find('div', class_='listupd')
            if not listupd:
                listupd = soup
            
            for article in listupd.find_all('article', class_='bs'):
                try:
                    link = article.find('a', href=True)
                    if not link:
                        continue
                    
                    href = link.get('href')
                    if not href or href in seen:
                        continue
                    
                    # Title
                    title_elem = article.find('div', class_='tt')
                    title = title_elem.text.strip() if title_elem else ''
                    
                    if not title:
                        title = link.get('title', '')
                    
                    if not title:
                        continue
                    
                    title = re.sub(r'\s*(?:Episode|Ep)\s*\d+.*$', '', title, flags=re.I)
                    title = title.strip()
                    
                    # Image
                    img_url = ''
                    limit_div = article.find('div', class_='limit')
                    if limit_div:
                        img = limit_div.find('img')
                        if img:
                            img_url = img.get('src') or img.get('data-src') or ''
                    
                    # Remarks
                    remarks = ''
                    epx = article.find('span', class_='epx')
                    if epx:
                        remarks = epx.text.strip()
                    
                    item = {
                        'vod_id': href,
                        'vod_name': title,
                        'vod_pic': img_url,
                        'vod_remarks': remarks
                    }
                    
                    seen.add(href)
                    items.append(item)
                    
                except:
                    continue
            
            # Hitung total pages dari pagination
            total_pages = int(pg)
            hpage = soup.find('div', class_='hpage')
            if hpage:
                # Cari semua link nomor halaman
                page_links = hpage.find_all('a')
                for link in page_links:
                    link_text = link.text.strip()
                    if link_text.isdigit():
                        page_num = int(link_text)
                        if page_num > total_pages:
                            total_pages = page_num
                
                # Cari link "Next"
                next_link = hpage.find('a', class_='r') or hpage.find('a', string=re.compile(r'Next|›|»', re.I))
                if next_link and total_pages == int(pg):
                    total_pages = int(pg) + 1
            
            self.log(f"Search found {len(items)} items, page {pg}/{total_pages}")
            
            return {
                'list': items,
                'page': int(pg),
                'pagecount': total_pages
            }
            
        except Exception as e:
            self.log(f"Search error: {e}")
            return {'list': []}
    
    def playerContent(self, flag, id, vipFlags):
        """Player content"""
        try:
            self.log(f"Player for: {id}")
            
            session = requests.Session()
            session.headers.update(self.site_headers)
            session.get(self.site, timeout=10)
            
            resp = session.get(id, timeout=15)
            html = resp.text
            soup = BeautifulSoup(html, 'html.parser')
            
            # Headers untuk Dailymotion
            dm_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.dailymotion.com/',
                'Origin': 'https://www.dailymotion.com',
                'Accept': '*/*',
            }
            
            # 1. M3U8 langsung
            m3u8_patterns = [
                r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
                r'"(https?://[^"]+\.m3u8[^"]*)"',
                r"'(https?://[^']+\.m3u8[^']*)'",
            ]
            
            for pattern in m3u8_patterns:
                matches = re.findall(pattern, html, re.I)
                for match in matches:
                    if match and match.startswith('http'):
                        return {'parse': 1, 'url': match, 'header': dm_headers}
            
            # 2. Iframe Dailymotion
            dm_patterns = [
                r'<iframe.*?src=["\'](https?://geo\.dailymotion\.com/player/[^"\']+\?video=([^"\']+))["\']',
                r'<iframe.*?src=["\'](https?://(?:www\.)?dailymotion\.com/embed/video/([^"\']+))["\']',
                r'<iframe.*?src=["\'](https?://[^"\']*dailymotion[^"\']+)["\']',
            ]
            
            for pattern in dm_patterns:
                dm_match = re.search(pattern, html, re.I)
                if dm_match:
                    iframe_url = dm_match.group(1)
                    
                    # Ekstrak video ID
                    video_id = None
                    if len(dm_match.groups()) >= 2:
                        video_id = dm_match.group(2)
                    
                    if video_id:
                        # Coba API Dailymotion
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
                                                    return {
                                                        'parse': 1,
                                                        'url': stream['url'],
                                                        'header': dm_headers
                                                    }
                        except:
                            pass
                    
                    return {'parse': 1, 'url': iframe_url, 'header': dm_headers}
            
            # 3. Iframe umum
            iframe_pattern = r'<iframe.*?src=["\'](.*?)["\']'
            iframe_matches = re.findall(iframe_pattern, html, re.I | re.S)
            
            for iframe_url in iframe_matches:
                if iframe_url.startswith('//'):
                    return {'parse': 1, 'url': 'https:' + iframe_url, 'header': self.site_headers}
                elif iframe_url.startswith('http'):
                    return {'parse': 1, 'url': iframe_url, 'header': self.site_headers}
            
            # 4. Video MP4
            mp4_patterns = [
                r'(https?://[^\s"\']+\.mp4[^\s"\']*)',
                r'file:"([^"]+\.mp4[^"]*)"',
            ]
            
            for pattern in mp4_patterns:
                matches = re.findall(pattern, html, re.I)
                for match in matches:
                    if match and match.startswith('http'):
                        return {'parse': 0, 'url': match, 'header': self.site_headers}
            
            # Fallback
            return {'parse': 1, 'url': id, 'header': self.site_headers}
            
        except Exception as e:
            self.log(f"Player error: {e}")
            return {'parse': 1, 'url': id, 'header': self.site_headers}
    
    def fetch(self, url, headers=None, timeout=15):
        """Fetch URL dengan error handling"""
        headers = headers or self.site_headers
        
        try:
            resp = self.session.get(url, headers=headers, timeout=timeout)
            return resp
        except Exception as e:
            self.log(f"Fetch error: {e}")
            class Dummy:
                text = ''
                status_code = 500
            return Dummy()
    
    def log(self, msg):
        print(f"[DONGHUB] {msg}")
    
    def destroy(self):
        if self.session:
            self.session.close()