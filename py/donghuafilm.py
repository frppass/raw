# -*- coding: utf-8 -*-
import re, sys, os, requests, html as htmlmod, json, datetime, random, time
from urllib.parse import urlparse, urljoin, quote, unquote
from bs4 import BeautifulSoup
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.site = 'https://donghuafilm.com'
        
        self.site_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': f'{self.site}/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        
        self.cache = {}
        self.session = requests.Session()
        
        # Mapping kategori berdasarkan struktur website
        self.category_map = {
            # Halaman utama - menggunakan filter
            'trending': '/anime/',
            'terbaru': '/anime/?order=latest',
            'update': '/anime/?order=update',
            'populer': '/anime/?order=popular',
            
            # Status
            'ongoing': '/anime/?status=ongoing',
            'completed': '/anime/?status=completed',
            'upcoming': '/anime/?status=upcoming',
            'hiatus': '/anime/?status=hiatus',
            
            # Type
            'donghua': '/anime/?type=donghua',
            'ona': '/anime/?type=ona',
            'ova': '/anime/?type=ova',
            'movie': '/anime/?type=movie',
            'special': '/anime/?type=special',
            'bd': '/anime/?type=bd',
            'live-action': '/anime/?type=live action',
            'music': '/anime/?type=music',
            
            # Genres
            'action': '/anime/?genre[]=action',
            'adventure': '/anime/?genre[]=adventure',
            'comedian': '/anime/?genre[]=comedian',
            'comedy': '/anime/?genre[]=comedy',
            'demon': '/anime/?genre[]=demon',
            'drama': '/anime/?genre[]=drama',
            'fanstasy': '/anime/?genre[]=fanstasy',
            'fantasy': '/anime/?genre[]=fantasy',
            'historical': '/anime/?genre[]=historical',
            'isekai': '/anime/?genre[]=isekai',
            'martial-arts': '/anime/?genre[]=martial-arts',
            'mystery': '/anime/?genre[]=mystery',
            'reincarnation': '/anime/?genre[]=reincarnation',
            'romance': '/anime/?genre[]=romance',
            'school': '/anime/?genre[]=school',
            'sci-fi': '/anime/?genre[]=sci-fi',
            'super-power': '/anime/?genre[]=super-power',
            'supranatural': '/anime/?genre[]=supranatural',
            'xuanhuan': '/anime/?genre[]=xuanhuan',
            
            # Subtitle
            'sub': '/anime/?sub=sub',
            'dub': '/anime/?sub=dub',
        }
        
        self.log("DONGHUAFILM Spider initialized")
    
    def getName(self):
        return "🐉 DONGHUAFILM"
    
    def isVideoFormat(self, url):
        return any(ext in url.lower() for ext in ['.m3u8', '.mp4', '.mkv', '.avi'])
    
    def manualVideoCheck(self):
        return True
    
    def clean_image_url(self, url):
        """Bersihkan URL gambar dari parameter resize dan pastikan formatnya benar"""
        if not url:
            return ''
        
        # Hapus parameter resize
        if '?resize=' in url:
            url = url.split('?')[0]
        
        # Hapus parameter lain
        if '?' in url:
            url = url.split('?')[0]
        
        # Pastikan URL lengkap
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = self.site + url
        
        return url
    
    def get_title(self, article, link):
        """
        Mendapatkan judul yang benar tanpa duplikasi
        """
        # Prioritas 1: Ambil dari atribut title di link (paling lengkap dan benar)
        title = link.get('title', '')
        
        # Prioritas 2: Jika tidak ada, coba dari div.tt dengan hati-hati
        if not title:
            tt_div = article.find('div', class_='tt')
            if tt_div:
                # Coba ambil dari h2 dulu (biasanya judul bersih)
                h2_tag = tt_div.find('h2')
                if h2_tag:
                    title = h2_tag.get_text(strip=True)
                else:
                    # Jika tidak ada h2, ambil teks langsung tapi bersihkan
                    title = tt_div.get_text(strip=True)
        
        # Prioritas 3: Fallback ke teks link
        if not title:
            title = link.get_text(strip=True)
        
        # Bersihkan judul dari duplikasi (misal: "Azure LegacyAzure Legacy" -> "Azure Legacy")
        # Cek apakah judul terdiri dari 2 bagian yang sama
        if len(title) > 10:  # Hanya cek judul yang cukup panjang
            half_len = len(title) // 2
            if title[:half_len] == title[half_len:]:
                title = title[:half_len]
        
        # Hapus episode number dari judul jika ada
        title = re.sub(r'\s*(?:Episode|Ep)\s*\d+.*$', '', title, flags=re.I)
        
        return title.strip()
    
    def homeContent(self, filter):
        """Kategori home"""
        return {
            'class': [
                {'type_name': '🔥 Trending', 'type_id': 'trending'},
                {'type_name': '🆕 Terbaru', 'type_id': 'terbaru'},
                {'type_name': '📺 Update', 'type_id': 'update'},
                {'type_name': '⭐ Populer', 'type_id': 'populer'},
                {'type_name': '⚔️ Action', 'type_id': 'action'},
                {'type_name': '🌿 Fantasy', 'type_id': 'fantasy'},
                {'type_name': '🌋 Xuanhuan', 'type_id': 'xuanhuan'},
                {'type_name': '💕 Romance', 'type_id': 'romance'},
                {'type_name': '✅ Ongoing', 'type_id': 'ongoing'},
                {'type_name': '🏁 Completed', 'type_id': 'completed'},
                {'type_name': '🎬 Movie', 'type_id': 'movie'},
                {'type_name': '📺 Donghua', 'type_id': 'donghua'},
                {'type_name': '📱 ONA', 'type_id': 'ona'},
                {'type_name': '🔊 Sub Indo', 'type_id': 'sub'},
            ],
            'filters': {}
        }
    
    def homeVideoContent(self):
        """Home video content - Latest Releases"""
        try:
            if 'home' in self.cache:
                return self.cache['home']
            
            self.log("Fetching home page...")
            html = self.fetch(self.site).text
            soup = BeautifulSoup(html, 'html.parser')
            
            items = []
            seen = set()
            
            # Cari di section listupd untuk Latest Release
            listupd_sections = soup.find_all('div', class_='listupd')
            listupd = listupd_sections[1] if len(listupd_sections) > 1 else listupd_sections[0]
            
            for article in listupd.find_all('article', class_='bs'):
                try:
                    link = article.find('a', href=True)
                    if not link:
                        continue
                    
                    href = link.get('href')
                    if not href or href in seen:
                        continue
                    
                    # Judul - menggunakan fungsi get_title
                    title = self.get_title(article, link)
                    
                    if not title:
                        continue
                    
                    # GAMBAR
                    img_url = ''
                    limit_div = article.find('div', class_='limit')
                    if limit_div:
                        img = limit_div.find('img')
                        if img:
                            img_url = img.get('data-src') or img.get('src') or ''
                            img_url = self.clean_image_url(img_url)
                    
                    # Remarks
                    remarks = ''
                    epx_span = article.find('span', class_='epx')
                    if epx_span:
                        remarks = epx_span.text.strip()
                    
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
                
                if len(items) >= 30:
                    break
            
            self.log(f"Found {len(items)} items on home")
            
            result = {'list': items}
            self.cache['home'] = result
            return result
            
        except Exception as e:
            self.log(f"Home error: {e}")
            return {'list': []}
    
    def categoryContent(self, tid, pg, filter, extend):
        """Konten kategori dengan pagination"""
        try:
            # Cari URL berdasarkan tid
            url = self.site
            
            if tid in self.category_map and self.category_map[tid]:
                url = self.site + self.category_map[tid]
            else:
                url = self.site + '/anime/'
            
            # Bersihkan URL dari parameter page yang mungkin sudah ada
            url = re.sub(r'&?page=\d+', '', url)
            
            # Handle pagination
            if int(pg) > 1:
                if '?' in url:
                    url += f"&page={pg}"
                else:
                    url += f"?page={pg}"
            
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
                    
                    # Judul - menggunakan fungsi get_title
                    title = self.get_title(article, link)
                    
                    if not title:
                        continue
                    
                    # GAMBAR
                    img_url = ''
                    limit_div = article.find('div', class_='limit')
                    if limit_div:
                        img = limit_div.find('img')
                        if img:
                            img_url = img.get('data-src') or img.get('src') or ''
                            img_url = self.clean_image_url(img_url)
                    
                    # Remarks
                    remarks = ''
                    epx_span = article.find('span', class_='epx')
                    if epx_span:
                        remarks = epx_span.text.strip()
                    
                    # Status badge
                    status_div = article.find('div', class_='status')
                    if status_div and not remarks:
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
            
            # Hitung total halaman
            total_pages = int(pg)
            hpage = soup.find('div', class_='hpage')
            if hpage:
                next_link = hpage.find('a', class_='r') or hpage.find('a', string=re.compile(r'Next|›|»', re.I))
                if next_link:
                    total_pages = max(total_pages, int(pg) + 1)
                    next_href = next_link.get('href', '')
                    page_match = re.search(r'page[=/](\d+)', next_href)
                    if page_match:
                        next_page = int(page_match.group(1))
                        total_pages = max(total_pages, next_page)
            
            if total_pages == int(pg) and len(items) > 0:
                if int(pg) == 1:
                    total_pages = 10
                else:
                    total_pages = int(pg)
            
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
        """Detail konten dan episode"""
        try:
            url = ids[0]
            if not url.startswith('http'):
                url = self.site + url if url.startswith('/') else self.site + '/' + url
            
            self.log(f"Fetching detail: {url}")
            
            html = self.fetch(url).text
            soup = BeautifulSoup(html, 'html.parser')
            
            # === INFO DASAR ===
            # Title dari h1
            title = ''
            h1_elem = soup.find('h1', class_='entry-title')
            if not h1_elem:
                h1_elem = soup.find('h1')
            if h1_elem:
                title = h1_elem.text.strip()
            
            # GAMBAR
            img = ''
            meta_img = soup.find('meta', property='og:image')
            if meta_img:
                img = meta_img.get('content', '')
                img = self.clean_image_url(img)
            
            if not img:
                img_elem = soup.find('img', class_='wp-post-image')
                if img_elem:
                    img = img_elem.get('data-src') or img_elem.get('src') or ''
                    img = self.clean_image_url(img)
            
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
            
            # === AMBIL EPISODE ===
            episode_dict = {}
            
            # Cari di div.eplister
            eplister = soup.find('div', class_='eplister')
            if eplister:
                for li in eplister.find_all('li'):
                    link = li.find('a', href=True)
                    if not link:
                        continue
                    
                    ep_href = link.get('href')
                    ep_num = None
                    
                    # Coba dari div.epl-num
                    num_div = li.find('div', class_='epl-num')
                    if num_div:
                        num_text = num_div.text.strip()
                        numbers = re.findall(r'\d+', num_text)
                        if numbers:
                            ep_num = numbers[0]
                    
                    # Coba dari div.epl-title
                    if not ep_num:
                        title_div = li.find('div', class_='epl-title')
                        if title_div:
                            title_text = title_div.text.strip()
                            numbers = re.findall(r'\d+', title_text)
                            if numbers:
                                ep_num = numbers[0]
                    
                    # Coba dari teks link
                    if not ep_num:
                        link_text = link.get_text(strip=True)
                        numbers = re.findall(r'\d+', link_text)
                        if numbers:
                            ep_num = numbers[0]
                    
                    # Fallback dari URL
                    if not ep_num:
                        url_match = re.search(r'episode[-\s]*(\d+)', ep_href, re.I)
                        if url_match:
                            ep_num = url_match.group(1)
                        else:
                            numbers = re.findall(r'/(\d+)(?:-end)?/?$', ep_href)
                            if numbers:
                                ep_num = numbers[0]
                            else:
                                all_numbers = re.findall(r'(\d+)', ep_href)
                                if all_numbers:
                                    ep_num = all_numbers[-1]
                    
                    if ep_num:
                        try:
                            ep_int = int(ep_num)
                            episode_dict[ep_int] = ep_href
                        except ValueError:
                            if ep_num not in episode_dict.values():
                                episode_dict[ep_num] = ep_href
            
            # Konversi ke list
            episodes = []
            sorted_keys = sorted(episode_dict.keys())
            
            for ep_key in sorted_keys:
                ep_href = episode_dict[ep_key]
                episodes.append(f"{ep_key}${ep_href}")
            
            if not episodes:
                episodes.append(f"1${url}")
            else:
                self.log(f"Found {len(episodes)} unique episodes")
            
            play_url = '#'.join(episodes)
            
            # Status
            status = 'Ongoing'
            status_elem = soup.find('div', class_='status')
            if status_elem:
                status = status_elem.text.strip()
            
            result = {
                'list': [{
                    'vod_id': url,
                    'vod_name': title or 'Unknown',
                    'vod_pic': img,
                    'vod_year': year,
                    'vod_content': desc,
                    'vod_remarks': status,
                    'vod_play_from': 'DONGHUAFILM',
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
                    
                    # Judul - menggunakan fungsi get_title
                    title = self.get_title(article, link)
                    
                    if not title:
                        continue
                    
                    # GAMBAR
                    img_url = ''
                    limit_div = article.find('div', class_='limit')
                    if limit_div:
                        img = limit_div.find('img')
                        if img:
                            img_url = img.get('data-src') or img.get('src') or ''
                            img_url = self.clean_image_url(img_url)
                    
                    # Remarks
                    remarks = ''
                    epx_span = article.find('span', class_='epx')
                    if epx_span:
                        remarks = epx_span.text.strip()
                    
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
            
            total_pages = int(pg)
            hpage = soup.find('div', class_='hpage')
            if hpage:
                next_link = hpage.find('a', class_='r') or hpage.find('a', string=re.compile(r'Next|›|»', re.I))
                if next_link:
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
        """Player content - Dengan dukungan Dailymotion CDN dan Pixeldrain"""
        try:
            self.log(f"Player for: {id}")
            
            session = requests.Session()
            session.headers.update(self.site_headers)
            
            # Header untuk Dailymotion
            dm_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.dailymotion.com/',
                'Origin': 'https://www.dailymotion.com',
                'Accept': '*/*',
            }
            
            # Header untuk Pixeldrain
            pd_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://pixeldrain.com/',
                'Origin': 'https://pixeldrain.com',
                'Accept': '*/*',
            }
            
            resp = session.get(id, timeout=15)
            html = resp.text
            
            # === CEK PIXELDRAIN ===
            if 'pixeldrain.com' in id:
                self.log("Detected Pixeldrain URL")
                pd_match = re.search(r'pixeldrain\.com/(?:api/)?file/([a-zA-Z0-9]+)', id)
                if pd_match:
                    file_id = pd_match.group(1)
                    direct_url = f"https://pixeldrain.com/api/file/{file_id}"
                    return {'parse': 0, 'url': direct_url, 'header': pd_headers}
            
            if 'pixeldrain.com' in html:
                self.log("Found Pixeldrain link in HTML")
                pd_patterns = [
                    r'(https?://pixeldrain\.com/api/file/[a-zA-Z0-9]+)',
                    r'(https?://pixeldrain\.com/[a-zA-Z0-9]+)',
                ]
                
                for pattern in pd_patterns:
                    pd_matches = re.findall(pattern, html, re.I)
                    for pd_url in pd_matches:
                        if pd_url:
                            return {'parse': 0, 'url': pd_url, 'header': pd_headers}
            
            # 1. M3U8 Dailymotion CDN
            dm_patterns = [
                r'(https?://cdndirector\.dailymotion\.com[^\s"\']+\.m3u8[^\s"\']*)',
                r'(https?://cdn[^\s]*\.dailymotion\.com[^\s"\']+\.m3u8[^\s"\']*)',
                r'(https?://[^\s"\']*dailymotion[^\s"\']*\.m3u8[^\s"\']*)',
            ]
            
            for pattern in dm_patterns:
                matches = re.findall(pattern, html, re.I)
                for match in matches:
                    if match and match.startswith('http'):
                        return {'parse': 1, 'url': match, 'header': dm_headers}
            
            # 2. Iframe Dailymotion
            iframe_patterns = [
                r'<iframe.*?src=["\'](https?://geo\.dailymotion\.com/player/[^"\']+\?video=([^"\']+))["\']',
                r'<iframe.*?src=["\'](https?://(?:www\.)?dailymotion\.com/embed/video/([^"\']+))["\']',
            ]
            
            for pattern in iframe_patterns:
                dm_match = re.search(pattern, html, re.I)
                if dm_match:
                    iframe_url = dm_match.group(1)
                    if len(dm_match.groups()) >= 2:
                        video_id = dm_match.group(2)
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
                                                    return {'parse': 1, 'url': stream['url'], 'header': dm_headers}
                        except:
                            pass
                    return {'parse': 1, 'url': iframe_url, 'header': dm_headers}
            
            # 3. M3U8 umum
            m3u8_patterns = [
                r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
                r'"(https?://[^"]+\.m3u8[^"]*)"',
                r"'(https?://[^']+\.m3u8[^']*)'",
                r'source\s*src=["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
            ]
            
            for pattern in m3u8_patterns:
                matches = re.findall(pattern, html, re.I)
                for match in matches:
                    if match and match.startswith('http'):
                        return {'parse': 1, 'url': match}
            
            # 4. Iframe umum
            iframe_patterns = [
                r'<iframe.*?src=["\'](https?://[^"\']+)["\']',
                r'<iframe.*?src=["\'](//[^"\']+)["\']',
            ]
            
            for pattern in iframe_patterns:
                iframe_matches = re.findall(pattern, html, re.I | re.S)
                for iframe_url in iframe_matches:
                    if iframe_url.startswith('//'):
                        return {'parse': 1, 'url': 'https:' + iframe_url}
                    elif iframe_url.startswith('http'):
                        return {'parse': 1, 'url': iframe_url}
            
            # 5. MP4 langsung
            mp4_patterns = [
                r'(https?://[^\s"\']+\.mp4[^\s"\']*)',
                r'file:"([^"]+\.mp4[^"]*)"',
                r'video\s+src=["\'](https?://[^"\']+\.mp4[^"\']*)["\']',
            ]
            
            for pattern in mp4_patterns:
                matches = re.findall(pattern, html, re.I)
                for match in matches:
                    if match and match.startswith('http'):
                        return {'parse': 0, 'url': match}
            
            # Fallback
            return {'parse': 1, 'url': id}
            
        except Exception as e:
            self.log(f"Player error: {e}")
            return {'parse': 1, 'url': id}
    
    def fetch(self, url, headers=None, timeout=15):
        """Fetch URL dengan error handling"""
        headers = headers or self.site_headers
        
        try:
            time.sleep(random.uniform(0.5, 1.5))
            resp = self.session.get(url, headers=headers, timeout=timeout)
            return resp
        except Exception as e:
            self.log(f"Fetch error for {url}: {e}")
            class Dummy:
                text = ''
                status_code = 500
            return Dummy()
    
    def log(self, msg):
        print(f"[DONGHUAFILM] {msg}")
    
    def destroy(self):
        if self.session:
            self.session.close()