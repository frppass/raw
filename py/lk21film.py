# -*- coding: utf-8 -*-
import re, sys, os, requests, html as htmlmod, json, datetime, time, random
from urllib.parse import urlparse, urljoin, quote, unquote
from bs4 import BeautifulSoup
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.site = 'https://lk21.de'  # Domain utama
        self.alternative_sites = [
            'https://nonton21.link',
            'https://lk21rebahin.net',
            'https://layarkaca21.bid',
            'https://lk21indo.skin'
        ]
        
        self.current_site = self.site
        
        self.site_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://lk21.de/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        self.session = requests.Session()
        self.current_year = datetime.datetime.now().year
        
        # Test koneksi
        self._test_site_connection()
    
    def _test_site_connection(self):
        """Test koneksi ke domain"""
        sites_to_test = [self.site] + self.alternative_sites
        
        for site in sites_to_test:
            try:
                response = self.session.get(site, headers=self.site_headers, timeout=10, verify=False)
                if response.status_code == 200:
                    self.current_site = site
                    self.site_headers['Referer'] = site
                    self.log(f"✓ Terhubung ke: {site}")
                    return True
            except Exception as e:
                self.log(f"✗ Gagal {site}: {e}")
                continue
        
        self.log("✗ Semua domain gagal")
        return False
    
    def log(self, message):
        """Simple logging"""
        print(f"[LK21.de] {message}")
    
    def getName(self):
        return "LK21.de"
    
    def isVideoFormat(self, url):
        video_ext = ['.m3u8', '.mp4', '.mkv', '.avi', '.mov', '.flv', '.webm']
        return any(ext in (url or '').lower() for ext in video_ext)
    
    def manualVideoCheck(self):
        return True
    
    def homeContent(self, filter):
        # KATEGORI FILM SAJA (TANPA SERIES/DRAMA)
        categories = [
            # FILM TERBARU & POPULER
            {'type_name': '🎬 Film Terbaru', 'type_id': 'terbaru'},
            
            # FILM BERDASARKAN NEGARA
            {'type_name': '🇮🇩 Film Indonesia', 'type_id': 'indonesia'},
            {'type_name': '🇺🇸 Film Hollywood', 'type_id': 'hollywood'},
            {'type_name': '🇮🇳 Film India', 'type_id': 'india'},
            {'type_name': '🇨🇳 Film China', 'type_id': 'china'},
            {'type_name': '🇯🇵 Film Jepang', 'type_id': 'japan'},
            {'type_name': '🇹🇭 Film Thailand', 'type_id': 'thailand'},
            {'type_name': '🇹🇷 Film Turki', 'type_id': 'turkey'},
            
            # GENRE FILM
            {'type_name': '💥 Action', 'type_id': 'action'},
            {'type_name': '😂 Comedy', 'type_id': 'comedy'},
            {'type_name': '💖 Romance', 'type_id': 'romance'},
            {'type_name': '😨 Horror', 'type_id': 'horror'},
            {'type_name': '🚀 Sci-Fi', 'type_id': 'sci-fi'},
            {'type_name': '🔫 Crime', 'type_id': 'crime'},
            {'type_name': '🎭 Drama', 'type_id': 'drama'},
            {'type_name': '🕵️‍♂️ Mystery', 'type_id': 'mystery'},
            {'type_name': '⚔️ Adventure', 'type_id': 'adventure'},
            {'type_name': '🎪 Fantasy', 'type_id': 'fantasy'},
            {'type_name': '⚖️ Thriller', 'type_id': 'thriller'},
            {'type_name': '⚽ Sport', 'type_id': 'sport'},
            {'type_name': '👶 Animation', 'type_id': 'animation'},
            {'type_name': '👨‍👩‍👧‍👦 Family', 'type_id': 'family'},
            {'type_name': '🗡️ War', 'type_id': 'war'},
            {'type_name': '💼 Documentary', 'type_id': 'documentary'},
            
            # TAHUN RILIS
            {'type_name': '📅 2024', 'type_id': '2024'},
            {'type_name': '📅 2023', 'type_id': '2023'},
            {'type_name': '📅 2022', 'type_id': '2022'},
            {'type_name': '📅 2021', 'type_id': '2021'},
            {'type_name': '📅 2020', 'type_id': '2020'},
            {'type_name': '📅 2019', 'type_id': '2019'},
            
            # KUALITAS
            {'type_name': '🎥 BluRay', 'type_id': 'bluray'},
            {'type_name': '🌐 WEB-DL', 'type_id': 'webdl'},
            {'type_name': '📹 HDCAM', 'type_id': 'hdcam'},
            
        ]
        return {'class': categories, 'filters': {}}
    
    def homeVideoContent(self):
        try:
            url = self.current_site
            self.log(f"Mengakses homepage: {url}")
            
            response = self.session.get(url, headers=self.site_headers, timeout=15, verify=False)
            
            if response.status_code != 200:
                self.log(f"Gagal mengakses homepage: {response.status_code}")
                return {'list': []}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            videos = []
            titles_set = set()  # Untuk mencegah judul double
            
            # Cari semua item film - filter yang lebih spesifik untuk LK21
            items = soup.select('.ml-mask.jt, .ml-item, .movie-list > article, .item.movies')
            if not items:
                items = soup.select('.box, .film, .post')
            
            for item in items[:30]:
                try:
                    video = self._parse_video_item(item, is_homepage=True)
                    if video:
                        # **FILTER: SKIP SERIES/DRAMA DI HOMEPAGE**
                        if video.get('vod_remarks', '').upper() in ['SERIES', 'DRAMA', 'TV SERIES']:
                            continue
                            
                        # Cek apakah judul sudah ada (mencegah duplikat)
                        title_key = f"{video['vod_name'].lower().strip()}_{video['vod_year']}"
                        if title_key in titles_set:
                            continue
                        
                        titles_set.add(title_key)
                        videos.append(video)
                except:
                    continue
            
            self.log(f"Found {len(videos)} FILM (unique)")
            return {'list': videos}
            
        except Exception as e:
            self.log(f"Error homeVideoContent: {str(e)}")
            return {'list': []}
    
    def _clean_title(self, title):
        """FUNGSI SENTRAL UNTUK MEMBERSIHKAN JUDUL - HANYA HAPUS 'DI' DI AKHIR"""
        if not title:
            return title
        
        original_title = title
        
        # **1. HAPUS SEMUA TEKS DALAM KURUNG & BRACKET**
        clean_title = re.sub(r'\([^)]*\)|\[[^\]]*\]|\{[^}]*\}', '', title)
        
        # **2. HAPUS KUALITAS VIDEO & FORMAT**
        quality_remove = [
            r'\d{3,4}p', 'HD', 'FHD', 'UHD', '4K', '8K', 'HQ',
            'BluRay', 'Blu-ray', 'BRRip', 'BDRip', 'DVDRip',
            'WEB-DL', 'WEB DL', 'WEBRip', 'HDRip', 'HC', 'HDCAM',
            'CAMRip', 'TS', 'TC', 'SCR', 'DVDScr', 'DVD', 'VCD'
        ]
        
        for pattern in quality_remove:
            clean_title = re.sub(fr'\b{pattern}\b', '', clean_title, flags=re.IGNORECASE)
        
        # **3. HAPUS PLATFORM & SITUS (TANPA 'di' KARENA HANYA AKHIR)**
        platform_remove = [
            'Nonton', 'Streaming', 'Online', 'Download', 'Watch',
            'Lk21', 'LK21', 'Layarkaca21', 'Layarkaca', 'Bioskop', 'Cinema',
            'Gratis', 'Free', 'Full Movie', 'Complete', 'Movie', 'Film',
            'Subtitle', 'Sub Indo', 'Subtitle Indonesia', 'Sub ID', 'Sub',
            'Indonesia', 'Indo', 'ID', 'Bahasa Indonesia', 'English',
            'Eng Sub', 'English Subtitle', 'with Subtitle',
        ]
        
        for pattern in platform_remove:
            clean_title = re.sub(fr'\b{pattern}\b', '', clean_title, flags=re.IGNORECASE)
        
        # **4. HAPUS KARAKTER KHUSUS & MULTIPLE SPACES**
        clean_title = re.sub(r'[^\w\s\-&\'":]', ' ', clean_title)
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()
        
        # **5. HANYA HAPUS 'DI' DI AKHIR SAJA (PENTING!)**
        clean_title = re.sub(r'\s+di$', '', clean_title, flags=re.IGNORECASE)
        
        # **6. HAPUS KATA PENGHUBUNG LAIN DI AKHIR**
        end_remove = [' Di', ' the', ' and', ' of', ' in', ' on', ' at']
        for word in end_remove:
            if clean_title.endswith(word):
                clean_title = clean_title[:-len(word)].strip()
        
        # **7. AMBIL JUDUL UTAMA SAJA**
        # Split pada pemisah umum
        separators = [' - ', ' : ', ' | ', ' – ', ' — ', ' // ', ' ~~ ', ' ~ ']
        for sep in separators:
            if sep in clean_title:
                clean_title = clean_title.split(sep)[0].strip()
                break
        
        # **8. FALLBACK: JIKA JUDUL KOSONG, AMBIL DARI ORIGINAL**
        if len(clean_title.strip()) < 2:
            # Ambil kata pertama yang bukan kata umum
            words = original_title.split()
            valid_words = []
            for word in words:
                word_lower = word.lower()
                if (len(word) > 2 and 
                    word_lower not in ['di', 'the', 'and', 'of', 'in', 'on', 'at', 'to'] and
                    not re.match(r'^\d{3,4}p$', word_lower)):
                    valid_words.append(word)
            
            if valid_words:
                clean_title = ' '.join(valid_words[:3])  # Ambil max 3 kata
        
        # **9. KAPITALISASI YANG BENAR**
        if clean_title:
            # Jangan ubah jika judul pendek atau akronim
            if len(clean_title) > 3 and not clean_title.isupper():
                # Kapitalisasi setiap kata
                words = clean_title.split()
                capitalized_words = []
                for word in words:
                    if len(word) > 1:
                        capitalized_words.append(word[0].upper() + word[1:].lower())
                    else:
                        capitalized_words.append(word)
                clean_title = ' '.join(capitalized_words)
        
        return clean_title.strip() if clean_title.strip() else "LK21 Movie"
    
    def _parse_video_item(self, item, is_homepage=False):
        """Parse single video item - TIDAK INCLUDE EPISODE & SERIES"""
        try:
            # Cari link
            link = item.find('a', href=True)
            if not link:
                return None
            
            href = link.get('href', '').strip()
            if not href or 'javascript:' in href:
                return None
            
            # **SKIP EPISODE & SERIES SELAMANYA**
            href_lower = href.lower()
            skip_keywords = [
                '/episode/', '/eps/', '/ep-', 'episode-',
                '/series/', '/drama/', '/tv/', '/season-', 'musim-',
                'drakor', 'dorama'
            ]
            
            if any(keyword in href_lower for keyword in skip_keywords):
                return None
            
            # Cari judul
            title = ''
            title_elem = item.select_one('.mli-info h2, .tt, h2, h3, .entry-title, .title, .name')
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            if not title:
                img = item.find('img')
                if img and img.get('alt'):
                    title = img.get('alt', '').strip()
            
            if not title:
                return None
            
            # **SKIP JIKA JUDUL MENGANDUNG SERIES/DRAMA**
            title_lower = title.lower()
            if any(keyword in title_lower for keyword in ['season', 'musim', 'series', 'drama', 'eps', 'episode']):
                return None
            
            # **GUNAKAN FUNGSI CLEAN_TITLE SENTRAL**
            clean_title = self._clean_title(title)
            
            if not clean_title or clean_title == "LK21 Movie":
                return None
            
            # Skip iklan
            if any(word in clean_title.lower() for word in ['iklan', 'ads', 'banner', 'sponsor', 'promo']):
                return None
            
            # Gambar
            img_url = ''
            img = item.find('img')
            if img:
                for attr in ['src', 'data-src', 'data-lazy-src']:
                    if img.get(attr):
                        img_url = img.get(attr)
                        break
            
            # Tahun - ambil dari judul asli
            year = ''
            year_match = re.search(r'\((\d{4})\)|\b(20\d{2})\b', title)
            if year_match:
                year = year_match.group(1)
            
            # Kualitas
            remarks = ''
            quality_elem = item.select_one('.quality, .type, .label, .mli-eps')
            if quality_elem:
                remarks = quality_elem.get_text(strip=True)
                # **HAPUS REMARKS YANG MENGANDUNG SERIES/EPISODE**
                if any(keyword in remarks.lower() for keyword in ['eps', 'episode', 'season']):
                    remarks = ''
            
            # **SKIP JIKA INI SERIES**
            if '/series/' in href_lower or '/drama/' in href_lower:
                return None
            
            # Buat URL
            if not href.startswith('http'):
                if href.startswith('/'):
                    vod_id = href
                else:
                    vod_id = '/' + href
            else:
                if self.current_site in href:
                    vod_id = href.replace(self.current_site, '')
                else:
                    vod_id = href
            
            # Fix image
            if img_url:
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    img_url = self.current_site + img_url
            
            return {
                'vod_id': vod_id,
                'vod_name': clean_title[:100],
                'vod_pic': img_url[:200] if img_url else '',
                'vod_year': year,
                'vod_remarks': remarks[:20]
            }
            
        except Exception as e:
            return None
    
    def categoryContent(self, tid, pg, filter, extend):
        try:
            # MAPPING KATEGORI FILM SAJA
            category_map = {
                # FILM TERBARU & POPULER
                'terbaru': '/release/',
                
                # FILM BERDASARKAN NEGARA
                'indonesia': '/country/indonesia/',
                'hollywood': '/country/usa/',
                'india': '/country/india/',
                'china': '/country/china/',
                'japan': '/country/japan/',
                'thailand': '/country/thailand/',
                'turkey': '/country/turkey/',
                
                # GENRE FILM
                'action': '/genre/action/',
                'comedy': '/genre/comedy/',
                'romance': '/genre/romance/',
                'horror': '/genre/horror/',
                'sci-fi': '/genre/sci-fi/',
                'crime': '/genre/crime/',
                'drama': '/genre/drama/',
                'mystery': '/genre/mystery/',
                'adventure': '/genre/adventure/',
                'fantasy': '/genre/fantasy/',
                'thriller': '/genre/thriller/',
                'sport': '/genre/sport/',
                'animation': '/genre/animation/',
                'family': '/genre/family/',
                'war': '/genre/war/',
                'documentary': '/genre/documentary/',
                
                # TAHUN RILIS
                '2024': f'/year/{self.current_year}/',
                '2023': '/year/2023/',
                '2022': '/year/2022/',
                '2021': '/year/2021/',
                '2020': '/year/2020/',
                '2019': '/year/2019/',
                
                # KUALITAS
                'bluray': '/quality/bluray/',
                'webdl': '/quality/web-dl/',
                'hdcam': '/quality/hdcam/',
            }
            
            base_path = category_map.get(tid, '/release/')
            url = f"{self.current_site}{base_path}"
            
            if str(pg) != '1':
                url += f"page/{pg}/"
            
            self.log(f"Mengakses kategori FILM: {url}")
            
            response = self.session.get(url, headers=self.site_headers, timeout=15, verify=False)
            
            if response.status_code != 200:
                self.log(f"Gagal mengakses kategori: {response.status_code}")
                return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 40, 'total': 0}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            videos = []
            titles_set = set()  # Track judul unik
            
            items = soup.select('.ml-item, .movie-item, article, .item, .film')
            
            if not items:
                items = soup.select('.post, .entry, .box')
            
            for item in items[:40]:
                video = self._parse_video_item(item)
                if video:
                    # Cek duplikat
                    title_key = f"{video['vod_name'].lower().strip()}_{video['vod_year']}"
                    if title_key not in titles_set:
                        titles_set.add(title_key)
                        videos.append(video)
            
            # **FILTER TAMBAHAN: HAPUS SERIES/DRAMA DARI HASIL KATEGORI**
            filtered_videos = []
            for video in videos:
                # Skip jika remarks mengandung series/drama
                remarks = video.get('vod_remarks', '').lower()
                if any(keyword in remarks for keyword in ['series', 'drama', 'eps', 'season']):
                    continue
                
                # Skip jika judul mengandung series/drama
                title = video.get('vod_name', '').lower()
                if any(keyword in title for keyword in ['season', 'musim', 'series', 'drama']):
                    continue
                    
                filtered_videos.append(video)
            
            # Pagination
            pagecount = 1
            pagination = soup.select('.pagination, .page-numbers')
            if pagination:
                page_numbers = []
                for page in pagination[0].select('a, span'):
                    text = page.get_text(strip=True)
                    if text.isdigit():
                        page_numbers.append(int(text))
                
                if page_numbers:
                    pagecount = max(page_numbers)
            
            return {
                'list': filtered_videos,
                'page': int(pg),
                'pagecount': pagecount,
                'limit': 40,
                'total': 999999
            }
            
        except Exception as e:
            self.log(f"Error categoryContent: {str(e)}")
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 40, 'total': 0}
    
    def detailContent(self, ids):
        """Detail konten - HANYA UNTUK FILM - Prioritas: CAST -> TURBOVIP -> lainnya"""
        try:
            path = ids[0] if ids else ''
            if not path:
                return {'list': []}
            
            path = unquote(path)
            
            if not path.startswith('http'):
                if path.startswith('/'):
                    url = self.current_site + path
                else:
                    url = self.current_site + '/' + path
            else:
                url = path
            
            # **CEK APAKAH INI SERIES/DARAMA - SKIP**
            url_lower = url.lower()
            if any(keyword in url_lower for keyword in ['/series/', '/drama/', '/tv/', '/season-', 'musim-']):
                self.log(f"Skipping series/drama: {url}")
                return {'list': []}
            
            self.log(f"Mengakses detail FILM: {url}")
            
            response = self.session.get(url, headers=self.site_headers, timeout=20, verify=False)
            
            if response.status_code != 200:
                return {'list': []}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Parse detail info
            title = ''
            title_elem = soup.select_one('h1.entry-title, h1.title, h1, .movie-title')
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            if not title:
                title = 'LK21 Movie'
            
            # **SKIP JIKA INI SERIES/DARAMA BERDASARKAN JUDUL**
            title_lower = title.lower()
            if any(keyword in title_lower for keyword in ['season', 'musim', 'series', 'drama']):
                return {'list': []}
            
            # **GUNAKAN FUNGSI CLEAN_TITLE SENTRAL YANG SAMA**
            clean_title = self._clean_title(title)
            
            # **FALLBACK: AMBIL JUDUL DARI PATH URL**
            if not clean_title or clean_title == 'LK21 Movie':
                # Extract dari URL path
                path_parts = path.strip('/').split('/')[-1]
                if path_parts:
                    # Hapus angka tahun dan karakter khusus
                    fallback_title = re.sub(r'-\d{4}$|-\d{4}-', '', path_parts)
                    fallback_title = re.sub(r'[-_]', ' ', fallback_title)
                    fallback_title = fallback_title.replace('-', ' ').replace('_', ' ')
                    fallback_title = ' '.join([w.capitalize() for w in fallback_title.split()])
                    clean_title = self._clean_title(fallback_title)  # Bersihkan lagi
            
            # Image
            img_url = ''
            img_elem = soup.select_one('.poster img, .thumbnail img, meta[property="og:image"]')
            if img_elem:
                if img_elem.name == 'meta':
                    img_url = img_elem.get('content', '')
                else:
                    img_url = img_elem.get('src') or img_elem.get('data-src') or ''
            
            # Year
            year = ''
            year_match = re.search(r'Tahun.*?[:]?\s*(\d{4})', soup.get_text(), re.IGNORECASE)
            if year_match:
                year = year_match.group(1)
            
            if not year:
                year_match = re.search(r'\b(20\d{2})\b', title)
                if year_match:
                    year = year_match.group(1)
            
            # Area
            area = ''
            for elem in soup.select('.info a, .genre a, .country a'):
                text = elem.get_text(strip=True).lower()
                if 'indonesia' in text:
                    area = 'ID'
                elif 'korea' in text:
                    area = 'KR'
                elif 'amerika' in text or 'usa' in text:
                    area = 'US'
                elif 'china' in text:
                    area = 'CN'
            
            # Quality
            remarks = ''
            quality_elem = soup.select_one('.quality, .type, .status')
            if quality_elem:
                remarks = quality_elem.get_text(strip=True)
            
            # Content
            content = ''
            content_elem = soup.select_one('.sinopsis, .desc, .description')
            if content_elem:
                content = content_elem.get_text(strip=True)[:300]
            
            # **HANYA CARI SERVER STREAMING UNTUK FILM**
            play_urls = []
            
            # **1. Cari CAST dan TURBOVIP secara khusus - PRIORITAS: CAST DULU**
            cast_links = []
            turbo_links = []
            other_links = []
            
            # Cari semua link yang mungkin streaming (HANYA FILM)
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '').strip()
                text = link.get_text(strip=True).upper()
                
                if not href or 'javascript:' in href:
                    continue
                
                # **SKIP LINK EPISODE & SERIES**
                href_lower = href.lower()
                if any(keyword in href_lower for keyword in ['/episode/', '/eps/', '/ep-', 'episode-', '/series/', '/drama/']):
                    continue
                
                # Hanya ambil link streaming
                if not any(word in href_lower for word in ['player', 'stream', 'watch', 'embed', 'mirror', 'server']):
                    continue
                
                # Fix URL
                if not href.startswith('http'):
                    if href.startswith('/'):
                        href = self.current_site + href
                    else:
                        href = self.current_site + '/' + href
                
                # Klasifikasikan berdasarkan teks - PRIORITAS CAST DULU
                if 'CAST' in text:
                    cast_links.append(f"CAST${href}")
                elif 'TURBOVIP' in text:
                    turbo_links.append(f"TURBOVIP${href}")
                elif any(word in text for word in ['P2P', 'HYDRAX', 'SERVER', 'STREAM']):
                    other_links.append(f"{text[:20]}${href}")
            
            # **2. Cari di button/div dengan teks CAST/TURBOVIP - PRIORITAS CAST DULU**
            for server_text in ['CAST', 'TURBOVIP']:
                elements = soup.find_all(['a', 'button', 'div'], 
                                       string=lambda text: text and server_text in text.upper())
                
                for elem in elements:
                    # Cari link di element atau parentnya
                    link_elem = elem if elem.name == 'a' else elem.find('a', href=True)
                    if link_elem:
                        href = link_elem.get('href', '').strip()
                        if href and not href.startswith('javascript:'):
                            # Skip episode & series
                            href_lower = href.lower()
                            if any(keyword in href_lower for keyword in ['/episode/', '/eps/', '/ep-', 'episode-', '/series/', '/drama/']):
                                continue
                            
                            if not href.startswith('http'):
                                if href.startswith('/'):
                                    href = self.current_site + href
                                else:
                                    href = self.current_site + '/' + href
                            
                            if server_text == 'CAST':
                                cast_links.append(f"CAST${href}")
                            else:
                                turbo_links.append(f"TURBOVIP${href}")
            
            # **3. Cari di class yang umum untuk server LK21**
            server_selectors = [
                '.mirror-link',
                '.server-item',
                '.download-server',
                '.player-server',
                '.stream-server',
                '.btn-download',
                '.btn-stream'
            ]
            
            for selector in server_selectors:
                for server_div in soup.select(selector):
                    server_text = server_div.get_text(strip=True).upper()
                    server_link = server_div.find('a', href=True)
                    
                    if server_link:
                        href = server_link.get('href', '').strip()
                        if href and not href.startswith('javascript:'):
                            # Skip episode & series
                            href_lower = href.lower()
                            if any(keyword in href_lower for keyword in ['/episode/', '/eps/', '/ep-', 'episode-', '/series/', '/drama/']):
                                continue
                            
                            if not href.startswith('http'):
                                if href.startswith('/'):
                                    href = self.current_site + href
                                else:
                                    href = self.current_site + '/' + href
                            
                            # PRIORITAS CAST DULU
                            if 'CAST' in server_text:
                                cast_links.append(f"CAST${href}")
                            elif 'TURBOVIP' in server_text:
                                turbo_links.append(f"TURBOVIP${href}")
                            elif server_text:
                                other_links.append(f"{server_text[:20]}${href}")
            
            # **4. Gabungkan dengan PRIORITAS: CAST -> TURBOVIP -> lainnya**
            # Hapus duplikat
            cast_links = list(dict.fromkeys(cast_links))
            turbo_links = list(dict.fromkeys(turbo_links))
            other_links = list(dict.fromkeys(other_links))
            
            # **UTAMAKAN CAST dulu (PRIORITAS TERTINGGI)**
            play_urls.extend(cast_links)
            # **Lalu TURBOVIP**
            play_urls.extend(turbo_links)
            # **Terakhir lainnya**
            play_urls.extend(other_links)
            
            # **5. Cari iframe sebagai fallback (TIDAK episode/series)**
            if not play_urls:
                iframe = soup.select_one('iframe[src]')
                if iframe:
                    src = iframe.get('src', '').strip()
                    if src and not any(keyword in src.lower() for keyword in ['/episode/', '/eps/', '/series/', '/drama/']):
                        if not src.startswith('http'):
                            if src.startswith('/'):
                                src = self.current_site + src
                            else:
                                src = self.current_site + '/' + src
                        play_urls.append(f"Embed${src}")
            
            # **6. Fallback: gunakan URL detail dengan CAST**
            if not play_urls:
                play_urls.append(f"CAST${url}")
            
            play_str = '#'.join(play_urls[:15])  # Maksimal 15 links
            
            # Fix image URL
            if img_url and not img_url.startswith('http'):
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    img_url = self.current_site + img_url
            
            return {
                'list': [{
                    'vod_id': path,
                    'vod_name': clean_title[:150],
                    'vod_pic': img_url[:500] if img_url else '',
                    'vod_year': year,
                    'vod_area': area,
                    'vod_remarks': remarks[:50],
                    'vod_content': content,
                    'vod_play_from': 'LK21.de',
                    'vod_play_url': play_str
                }]
            }
            
        except Exception as e:
            self.log(f"Error detailContent: {str(e)}")
            return {'list': []}
    
    def searchContent(self, key, quick, pg="1"):
        try:
            if not key or len(key) < 2:
                return {'list': []}
            
            url = f"{self.current_site}/?s={quote(key)}"
            if str(pg) != '1':
                url += f"&page={pg}"
            
            self.log(f"Searching FILM: {key}")
            
            response = self.session.get(url, headers=self.site_headers, timeout=15, verify=False)
            
            if response.status_code != 200:
                return {'list': []}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            videos = []
            seen_titles = set()
            
            items = soup.select('.ml-item, .movie-item, article, .item')
            
            if not items:
                items = soup.select('.post, .entry, .film')
            
            for item in items[:30]:
                video = self._parse_video_item(item)
                if video:
                    # **FILTER: SKIP SERIES/DRAMA DI SEARCH**
                    # Skip jika remarks mengandung series/drama
                    remarks = video.get('vod_remarks', '').lower()
                    if any(keyword in remarks for keyword in ['series', 'drama', 'eps', 'season']):
                        continue
                    
                    # Skip jika judul mengandung series/drama
                    title = video.get('vod_name', '').lower()
                    if any(keyword in title for keyword in ['season', 'musim', 'series', 'drama']):
                        continue
                    
                    # Hindari duplikat di search
                    title_key = f"{video['vod_name'].lower().strip()}_{video['vod_year']}"
                    if title_key not in seen_titles:
                        seen_titles.add(title_key)
                        videos.append(video)
            
            return {
                'list': videos,
                'page': int(pg),
                'pagecount': 10,
                'limit': 30,
                'total': 999999
            }
            
        except Exception as e:
            self.log(f"Error searchContent: {str(e)}")
            return {'list': []}
    
    def playerContent(self, flag, id, vipFlags):
        """Player dengan PRIORITAS CAST dulu, lalu TURBOVIP - HANYA UNTUK FILM"""
        try:
            id = unquote(id)
            
            if '$' in id:
                url = id.split('$')[-1]
                server_name = id.split('$')[0]
            else:
                url = id
                server_name = 'Main'
            
            # **CEK APAKAH INI EPISODE/SERIES - SKIP**
            url_lower = url.lower()
            if any(keyword in url_lower for keyword in ['/episode/', '/eps/', '/ep-', 'episode-']):
                self.log(f"Skipping episode/series in player: {url}")
                return {'parse': 0, 'url': '', 'header': self.site_headers}
            
            self.log(f"Player FILM: {server_name} -> {url}")
            
            # Jika URL sudah direct video
            if self.isVideoFormat(url):
                return {
                    'parse': 0,
                    'url': url,
                    'header': self.site_headers
                }
            
            # **PRIORITAS CAST dan TURBOVIP: coba extract video langsung**
            if server_name.upper() in ['CAST', 'TURBOVIP']:
                video_url = self._extract_direct_video(url)
                if video_url:
                    self.log(f"✓ Found direct video from {server_name}")
                    return {
                        'parse': 0,
                        'url': video_url,
                        'header': self.site_headers
                    }
            
            # Default: webview parsing
            return {
                'parse': 1,
                'url': url,
                'header': self.site_headers
            }
            
        except Exception as e:
            self.log(f"Error playerContent: {str(e)}")
            return {
                'parse': 1,
                'url': id if id.startswith('http') else self.current_site + '/' + id,
                'header': self.site_headers
            }
    
    def _extract_direct_video(self, url):
        """Extract direct video URL dari CAST/TURBOVIP page"""
        try:
            response = self.session.get(url, headers=self.site_headers, timeout=15, verify=False)
            
            if response.status_code != 200:
                return None
            
            content = response.text
            
            # Pattern untuk mencari video URL
            patterns = [
                # CAST pattern (priority)
                r'player\.setup\({[^}]*file["\']?\s*:\s*["\']([^"\']+)["\']',
                r'jwplayer\([^)]+\)\.setup\({[^}]*file["\']?\s*:\s*["\']([^"\']+)["\']',
                # TURBOVIP pattern
                r'file["\']?\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'src["\']?\s*[:=]\s*["\']([^"\']+\.mp4[^"\']*)["\']',
                r'url["\']?\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                # Umum
                r'https?://[^\s"\']+\.(?:m3u8|mp4|mkv)[^\s"\']*'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if match and any(ext in match.lower() for ext in ['.m3u8', '.mp4', '.mkv']):
                        # Fix relative URL
                        if not match.startswith('http'):
                            if match.startswith('//'):
                                match = 'https:' + match
                            elif match.startswith('/'):
                                match = self.current_site + match
                            else:
                                match = urljoin(url, match)
                        
                        self.log(f"Found video: {match[:100]}...")
                        return match
            
            return None
            
        except Exception as e:
            self.log(f"Error extracting direct video: {e}")
            return None
    
    def localProxy(self, param):
        return []