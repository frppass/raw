# -*- coding: utf-8 -*-
import re, sys, os, requests, json, datetime, time
from urllib.parse import urlparse, urljoin, quote, unquote, parse_qs
from bs4 import BeautifulSoup
from base.spider import Spider
import base64

class Spider(Spider):
    def init(self, extend=""):
        self.site = 'https://tv3.nontondrama.my'
        self.alternative_sites = [
            'https://drama.mu',
            'https://nontondrama.my',
            'https://tv2.nontondrama.my',
            'https://tv1.nontondrama.my'
        ]
        
        self.current_site = self.site
        self.session = requests.Session()
        
        # Headers untuk simulasi browser
        self.site_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.site,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        self.current_year = datetime.datetime.now().year
        print(f"[NontonDrama] Spider initialized for {self.current_site}")
    
    def getName(self):
        return "NontonDrama.my"
    
    def homeContent(self, filter):
        categories = [
            {'type_name': '📺 Series Terbaru', 'type_id': 'latest'},
            {'type_name': '🔥 Series Terpopuler', 'type_id': 'populer'},
            {'type_name': '🌎 Series Barat', 'type_id': 'series/west'},
            {'type_name': '🌏 Series Asia', 'type_id': 'series/asian'},
            {'type_name': '⏳ Series Ongoing', 'type_id': 'series/ongoing'},
            {'type_name': '✅ Series Complete', 'type_id': 'series/complete'},
            {'type_name': '💥 Action', 'type_id': 'genre/action'},
            {'type_name': '😂 Comedy', 'type_id': 'genre/comedy'},
            {'type_name': '💖 Romance', 'type_id': 'genre/romance'},
            {'type_name': '😨 Horror', 'type_id': 'genre/horror'},
            {'type_name': '🎭 Drama', 'type_id': 'genre/drama'},
            {'type_name': '🇰🇷 Korea', 'type_id': 'country/south-korea'},
            {'type_name': '🇨🇳 China', 'type_id': 'country/china'},
            {'type_name': '🇹🇭 Thailand', 'type_id': 'country/thailand'},
            {'type_name': f'📅 {self.current_year}', 'type_id': f'year/{self.current_year}'},
            {'type_name': '📅 2024', 'type_id': 'year/2024'},
        ]
        return {'class': categories, 'filters': {}}
    
    def homeVideoContent(self):
        try:
            url = self.current_site
            print(f"[NontonDrama] Mengakses homepage: {url}")
            
            response = self.session.get(url, headers=self.site_headers, timeout=15)
            
            if response.status_code != 200:
                print(f"[NontonDrama] Gagal mengakses homepage")
                return {'list': []}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            videos = []
            
            # Cari artikel di post-container
            articles = soup.select('#post-container article')
            print(f"[NontonDrama] Found {len(articles)} articles")
            
            for article in articles[:15]:
                video = self._parse_video_item(article)
                if video:
                    videos.append(video)
            
            # Jika masih sedikit, cari di slider
            if len(videos) < 5:
                sliders = soup.select('.slider')
                for slider in sliders[:10]:
                    video = self._parse_video_item(slider)
                    if video:
                        videos.append(video)
            
            print(f"[NontonDrama] Total videos found: {len(videos)}")
            return {'list': videos}
            
        except Exception as e:
            print(f"[NontonDrama] Error homeVideoContent: {e}")
            return {'list': []}
    
    def _parse_video_item(self, item):
        """Parse item video"""
        try:
            # Cari link
            link = item.find('a', href=True)
            if not link:
                return None
            
            href = link.get('href', '').strip()
            if not href or href == '#' or 'javascript:' in href:
                return None
            
            # Cari judul - PERBAIKAN SELECTOR
            title = ''
            
            # Priority 1: Poster title
            title_elem = item.select_one('.poster-title')
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # Priority 2: h3 atau h2
            if not title:
                for tag in ['h3', 'h2', 'h4']:
                    title_elem = item.find(tag)
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if title:
                            break
            
            # Priority 3: Class khusus
            if not title:
                selectors = ['.tt', '.pop-movie-title', '.title', '.entry-title', 'figcaption h3']
                for selector in selectors:
                    title_elem = item.select_one(selector)
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if title:
                            break
            
            # Priority 4: img alt
            if not title:
                img = item.find('img')
                if img and img.get('alt'):
                    title = img.get('alt', '').strip()
            
            # Priority 5: text dari link
            if not title and link:
                title = link.get_text(strip=True)
            
            if not title:
                return None
            
            # Clean title - GUNAKAN CLEAN TEXT YANG SAMA UNTUK SEMUA
            title = self._clean_text(title)
            
            # Cari gambar
            img_url = ''
            img = item.find('img')
            if img:
                for attr in ['src', 'data-src', 'data-lazy-src']:
                    if img.get(attr):
                        img_url = img.get(attr)
                        break
            
            # Cari episode info
            episode_text = ''
            ep_elem = item.select_one('.episode, .eps')
            if ep_elem:
                ep_text = ep_elem.get_text(strip=True)
                if 'EPS' in ep_text or 'Ep' in ep_text:
                    ep_match = re.search(r'(\d+)', ep_text)
                    if ep_match:
                        episode_text = f"Eps {ep_match.group(1)}"
            
            # Cari tahun
            year = ''
            year_elem = item.select_one('.year')
            if year_elem:
                year_text = year_elem.get_text(strip=True)
                if year_text.isdigit() and len(year_text) == 4:
                    year = year_text
            else:
                # Coba extract tahun dari judul
                year_match = re.search(r'\((\d{4})\)', title)
                if year_match:
                    year = year_match.group(1)
            
            # Fix URLs
            if not href.startswith('http'):
                if href.startswith('/'):
                    href = self.current_site + href
                else:
                    href = self.current_site + '/' + href
            
            if img_url:
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    img_url = self.current_site + img_url
                elif not img_url.startswith('http'):
                    img_url = urljoin(self.current_site, img_url)
            
            # vod_id dari path
            parsed = urlparse(href)
            vod_id = parsed.path
            
            return {
                'vod_id': vod_id,
                'vod_name': title[:100],
                'vod_pic': img_url[:300] if img_url else '',
                'vod_year': year,
                'vod_remarks': episode_text[:30]
            }
            
        except Exception as e:
            print(f"[NontonDrama] Error parse_video_item: {e}")
            return None
    
    def _clean_text(self, text):
        """Bersihkan teks - UNTUK SEMUA JUDUL (home, category, detail, search)"""
        if not text:
            return ""
        
        # **PERBAIKAN BESAR: HAPUS SEMUA "Sub Indo" dan variasi dengan atau tanpa tahun**
        
        # Langkah 1: Hapus SEMUA pola dengan "Sub Indo" dan variasi
        subtitle_patterns = [
            # Dengan tahun
            r'[Ss]ub\s*[Ii]ndo\s*\(\s*\d{4}\s*\)',
            r'[Ss]ub\s*[Ii]ndo\s*\(\s*tahun\s*\)',
            r'[Ss]ub\s*[Ii]ndo\s*\(\s*\d+\s*\)',
            
            # Tanpa tahun
            r'[Ss]ub\s*[Ii]ndo',
            r'[Ss]ub\s*[Ii]ndonesia',
            r'[Ii]ndo\s*[Ss]ub',
            r'[Ii]ndonesia\s*[Ss]ubtitle',
            
            # Variasi lain
            r'[Ss]ubtitle\s*[Ii]ndo',
            r'[Ss]ubtitle\s*[Ii]ndonesia',
            r'[Bb]ahasa\s*[Ii]ndo',
            r'[Bb]ahasa\s*[Ii]ndonesia',
            r'[Ii]ndo\s*[Dd]ubbing',
            r'[Ii]ndonesia\s*[Dd]ubbing',
            
            # Dengan kwalitas
            r'[Ss]ub\s*[Ii]ndo\s*[Hh][Dd]',
            r'[Ss]ub\s*[Ii]ndo\s*[Ff]ull\s*[Hh][Dd]',
            r'[Ss]ub\s*[Ii]ndo\s*\d+[Pp]',
            r'[Ss]ub\s*[Ii]ndo\s*[Mm][Pp]4',
            
            # English subtitle
            r'[Ee]nglish\s*[Ss]ubtitle',
            r'[Ee]ng\s*[Ss]ub',
            r'[Ee]ngsub',
            r'[Ee]nglish\s*[Dd]ub',
        ]
        
        for pattern in subtitle_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Langkah 2: Hapus semua tanda kurung dan isinya yang mengandung kata subtitle
        text = re.sub(r'\([^)]*[Ss]ub[^)]*\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\([^)]*[Ii]ndo[^)]*\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\([^)]*[Ee]ng[^)]*\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[[^\]]*[Ss]ub[^\]]*\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[[^\]]*[Ii]ndo[^\]]*\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[[^\]]*[Ee]ng[^\]]*\]', '', text, flags=re.IGNORECASE)
        
        # Langkah 3: Ekstrak semua tahun dari teks
        years = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
        main_year = years[-1] if years else ""
        
        # Langkah 4: Hapus SEMUA pola (tahun) dari teks
        text = re.sub(r'\s*\(\s*\d{4}\s*\)', '', text)
        
        # Langkah 5: Hapus prefix di awal judul
        prefix_patterns = [
            # Bahasa Indonesia
            r'^[Ss]erial\s+',
            r'^[Nn]onton\s+', 
            r'^[Ss]treaming\s+',
            r'^[Dd]ownload\s+',
            r'^[Bb]ioskop\s+',
            r'^[Ff]ilm\s+',
            r'^[Mm]ovie\s+',
            r'^[Ss]eries\s+',
            r'^[Tt]ayang\s+',
            r'^[Ll]ive\s+',
            r'^[Ww]atch\s+',
            r'^[Ss]ubtitle\s+',
            r'^[Ss]ub\s+',
            r'^[Ii]ndo\s+',
            r'^[Ee]ngsub\s+',
            r'^[Dd]rama\s+',
            r'^[Ss]inopsis\s+',
            r'^[Tt]railer\s+',
            r'^[Rr]eview\s+',
            r'^[Pp]review\s+',
            r'^[Ee]pisode\s+',
            r'^[Mm]usim\s+',
            r'^[Ss]eason\s+',
            
            # Bahasa Inggris
            r'^[Ww]atch\s+',
            r'^[Ss]tream\s+',
            r'^[Dd]ownload\s+',
            r'^[Ff]ull\s+',
            r'^[Cc]omplete\s+',
            r'^[Nn]ew\s+',
            r'^[Ll]atest\s+',
            r'^[Hh]d\s+',
            r'^[Hh]igh\s+[Qq]uality\s+',
            r'^[Ff]ree\s+',
            r'^[Oo]nline\s+',
        ]
        
        for pattern in prefix_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Hapus HTML entities
        text = re.sub(r'&[a-zA-Z]+;', ' ', text)
        
        # Langkah 6: Hapus suffix/situs di akhir judul
        suffix_patterns = [
            # Situs/website
            r'\s*[-–|]\s*NontonDrama.*$',
            r'\s*[-–|]\s*Nonton Drama.*$',
            r'\s*[-–|]\s*Drama\.mu.*$',
            r'\s*[-–|]\s*Streaming.*$',
            r'\s*[-–|]\s*Download.*$',
            r'\s*[-–|]\s*Sub Indo.*$',
            r'\s*[-–|]\s*IndoSub.*$',
            r'\s*[-–|]\s*Subtitle.*$',
            r'\s*[-–|]\s*English.*$',
            r'\s*[-–|]\s*HD.*$',
            r'\s*[-–|]\s*1080p.*$',
            r'\s*[-–|]\s*720p.*$',
            r'\s*[-–|]\s*480p.*$',
            r'\s*[-–|]\s*360p.*$',
            r'\s*[-–|]\s*Full.*$',
            r'\s*[-–|]\s*Complete.*$',
        ]
        
        for pattern in suffix_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Langkah 7: Hapus kata-kata tidak perlu di mana saja dalam teks
        unwanted_words = [
            # Bahasa Indonesia
            r'\s*[Ss]erial\s+',
            r'\s*[Nn]onton\s+',
            r'\s*[Ss]treaming\s+',
            r'\s*[Dd]ownload\s+',
            r'\s*[Bb]ioskop\s+',
            r'\s*[Ff]ilm\s+',
            r'\s*[Mm]ovie\s+',
            r'\s*[Ss]eries\s+',
            r'\s*[Tt]ayang\s+',
            r'\s*[Ll]ive\s+[Aa]ction\s+',
            r'\s*[Ww]atch\s+',
            r'\s*[Ss]ubtitle\s+',
            r'\s*[Ss]ub\s+[Ii]ndo\s+',
            r'\s*[Ii]ndo[Ss]ub\s+',
            r'\s*[Ee]ngsub\s+',
            r'\s*[Ee]nglish\s+[Ss]ubtitle\s+',
            r'\s*[Dd]rama\s+',
            r'\s*[Ss]inopsis\s+',
            r'\s*[Tt]railer\s+',
            r'\s*[Rr]eview\s+',
            r'\s*[Pp]review\s+',
            r'\s*[Ee]pisode\s+\d+',
            r'\s*[Ee]ps\s+\d+',
            r'\s*[Mm]usim\s+\d+',
            r'\s*[Ss]eason\s+\d+',
            
            # Bahasa Inggris
            r'\s*[Ss]eason\s+\d+',
            r'\s*[Ss]\d+\s*[Ee]\d+',
            r'\s*[Ee]pisode\s+\d+',
            r'\s*[Ee]p\s+\d+',
            r'\s*[Pp]art\s+\d+',
            r'\s*[Vv]olume\s+\d+',
            r'\s*[Cc]hapter\s+\d+',
            r'\s*[Ff]ull\s+',
            r'\s*[Cc]omplete\s+',
            r'\s*[Uu]ncut\s+',
            r'\s*[Ee]xtended\s+',
            r'\s*[Dd]irector[`\'`]?s\s+[Cc]ut\s+',
            r'\s*[Hh]d\s+',
            r'\s*[Ff]hd\s+',
            r'\s*[Uu]hd\s+',
            r'\s*[Ww]eb[-\s]?[Dd][Ll]\s+',
            r'\s*[Bb][Ll][Uu][-\s]?[Rr]ay\s+',
            r'\s*[Dd][Vv][Dd]\s+',
            r'\s*[Bb][Dd]\s+',
            r'\s*[Rr]ip\s+',
            r'\s*[Dd]ual\s+[Aa]udio\s+',
            r'\s*[Mm]ulti[-\s]?[Ss]ub\s+',
            r'\s*[Ss]ubbed\s+',
            r'\s*[Dd]ubbed\s+',
        ]
        
        for pattern in unwanted_words:
            text = re.sub(pattern, ' ', text, flags=re.IGNORECASE)
        
        # Langkah 8: Hapus teks dalam kurung/bracket yang umum
        bracket_patterns = [
            r'\[[^\]]*[Ss]ub[^\]]*\]',
            r'\[[^\]]*[Ii]ndo[^\]]*\]',
            r'\[[^\]]*[Ee]ng[^\]]*\]',
            r'\[[^\]]*[Hh]d[^\]]*\]',
            r'\[[^\]]*[Ff]ull[^\]]*\]',
            r'\[[^\]]*[Cc]omplete[^\]]*\]',
            r'\[[^\]]*[Ss]erial[^\]]*\]',
            r'\[[^\]]*[Mm]ovie[^\]]*\]',
            r'\[[^\]]*[Ff]ilm[^\]]*\]',
            r'\[[^\]]*[Dd]rama[^\]]*\]',
            r'\[[^\]]*[Tt]erbaru[^\]]*\]',
            r'\[[^\]]*[Ll]engkap[^\]]*\]',
            r'\([^)]*[Ss]ub[^)]*\)',
            r'\([^)]*[Ii]ndo[^)]*\)',
            r'\([^)]*[Ee]ng[^)]*\)',
            r'\([^)]*[Hh]d[^)]*\)',
            r'\([^)]*[Ff]ull[^)]*\)',
            r'\([^)]*[Cc]omplete[^)]*\)',
            r'\([^)]*[Ss]erial[^)]*\)',
            r'\([^)]*[Mm]ovie[^)]*\)',
            r'\([^)]*[Ff]ilm[^)]*\)',
            r'\([^)]*[Dd]rama[^)]*\)',
        ]
        
        for pattern in bracket_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Langkah 9: Hapus multiple spaces dan trim
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Langkah 10: Tambahkan tahun kembali jika ada
        if main_year:
            text = f"{text} ({main_year})"
        
        return text[:150]
    
    def categoryContent(self, tid, pg, filter, extend):
        try:
            # Buat URL
            if tid.startswith('/'):
                base_url = tid
            else:
                base_url = f'/{tid}'
            
            url = f"{self.current_site}{base_url}"
            if str(pg) != '1':
                url += f"/page/{pg}/"
            
            print(f"[NontonDrama] Category: {url}")
            
            response = self.session.get(url, headers=self.site_headers, timeout=15)
            
            if response.status_code != 200:
                return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 40, 'total': 0}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            videos = []
            
            # Cari semua artikel
            articles = soup.select('article')
            for article in articles[:40]:
                video = self._parse_video_item(article)
                if video:
                    videos.append(video)
            
            # Jika masih sedikit, cari di sliders
            if len(videos) < 10:
                sliders = soup.select('.slider')
                for slider in sliders[:20]:
                    video = self._parse_video_item(slider)
                    if video:
                        videos.append(video)
            
            # Pagination
            pagecount = 1
            page_links = soup.select('.page-numbers a, .pagination a')
            page_numbers = []
            for page in page_links:
                text = page.get_text(strip=True)
                if text.isdigit():
                    page_numbers.append(int(text))
            
            if page_numbers:
                pagecount = max(page_numbers)
            
            print(f"[NontonDrama] Found {len(videos)} videos in category")
            return {
                'list': videos,
                'page': int(pg),
                'pagecount': pagecount,
                'limit': 40,
                'total': len(videos) * pagecount
            }
            
        except Exception as e:
            print(f"[NontonDrama] Error categoryContent: {e}")
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 40, 'total': 0}
    
    def detailContent(self, ids):
        """Detail series - PERBAIKAN PARSING JUDUL"""
        try:
            vod_id = ids[0] if ids else ''
            if not vod_id:
                return {'list': []}
            
            vod_id = unquote(vod_id)
            
            # Buat URL
            if vod_id.startswith('http'):
                url = vod_id
            elif vod_id.startswith('/'):
                url = self.current_site + vod_id
            else:
                url = self.current_site + '/' + vod_id
            
            print(f"[NontonDrama] Detail URL: {url}")
            
            response = self.session.get(url, headers=self.site_headers, timeout=20)
            
            if response.status_code != 200:
                print(f"[NontonDrama] Failed to load detail page: {response.status_code}")
                return {'list': []}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # **PERBAIKAN PARSING JUDUL - MULTI METHOD**
            title = ''
            original_title = ''  # Simpan judul asli untuk ekstraksi tahun
            
            # Method 1: Entry title (utama)
            title_elem = soup.select_one('h1.entry-title')
            if title_elem:
                title = title_elem.get_text(strip=True)
                original_title = title
                print(f"[NontonDrama] Title from h1.entry-title: {title}")
            
            # Method 2: Title class
            if not title:
                title_elem = soup.select_one('h1.title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    original_title = title
                    print(f"[NontonDrama] Title from h1.title: {title}")
            
            # Method 3: Any h1
            if not title:
                title_elem = soup.select_one('h1')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    original_title = title
                    print(f"[NontonDrama] Title from any h1: {title}")
            
            # Method 4: Meta og:title
            if not title:
                meta_title = soup.select_one('meta[property="og:title"]')
                if meta_title:
                    title = meta_title.get('content', '')
                    original_title = title
                    print(f"[NontonDrama] Title from og:title: {title}")
            
            # Method 5: Title tag
            if not title:
                title_elem = soup.find('title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    original_title = title
                    print(f"[NontonDrama] Title from title tag: {title}")
            
            # Method 6: Poster title
            if not title:
                title_elem = soup.select_one('.poster-title, .movie-title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    original_title = title
                    print(f"[NontonDrama] Title from poster-title: {title}")
            
            if not title:
                title = "Series"
            
            # **BERSIHKAN JUDUL DENGAN FUNGSI YANG SAMA**
            clean_title = self._clean_text(title)
            print(f"[NontonDrama] Cleaned title: {clean_title}")
            
            # **PERBAIKAN PARSING TAHUN**
            year = ''
            
            # Method 1: Extract from original title
            years = re.findall(r'\b(19\d{2}|20\d{2})\b', original_title)
            if years:
                year = years[-1]  # Ambil tahun terakhir
                print(f"[NontonDrama] Year from original title: {year}")
            
            # Method 2: Year class
            if not year:
                year_elem = soup.select_one('.year')
                if year_elem:
                    year_text = year_elem.get_text(strip=True)
                    if year_text.isdigit() and (len(year_text) == 4):
                        year = year_text
                        print(f"[NontonDrama] Year from .year: {year}")
            
            # Method 3: Cari di info
            if not year:
                info_section = soup.select_one('.info, .details, .movie-info')
                if info_section:
                    info_text = info_section.get_text()
                    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', info_text)
                    if year_match:
                        year = year_match.group(1)
                        print(f"[NontonDrama] Year from info section: {year}")
            
            # Method 4: Cari di meta
            if not year:
                meta_year = soup.select_one('meta[property="video:release_date"], meta[name="year"]')
                if meta_year:
                    year_text = meta_year.get('content', '')
                    if year_text.isdigit() and (len(year_text) == 4):
                        year = year_text
                        print(f"[NontonDrama] Year from meta: {year}")
            
            # **PERBAIKAN PARSING GENRE**
            genres = []
            
            # Method 1: Genre class
            genre_elems = soup.select('.genre a, .tags a, .category a')
            for elem in genre_elems:
                genre = elem.get_text(strip=True)
                if genre and genre.lower() not in ['series', 'drama', 'movie', 'film', 'serial']:
                    genres.append(genre)
            
            # Method 2: Cari di info
            if not genres:
                info_section = soup.select_one('.info, .details')
                if info_section:
                    # Cari teks "Genre:" atau "Kategori:"
                    info_text = info_section.get_text()
                    genre_match = re.search(r'[Gg]enre[:\s]+([^\n]+)', info_text)
                    if genre_match:
                        genre_text = genre_match.group(1)
                        # Split by comma or slash
                        genre_split = re.split(r'[,\/]', genre_text)
                        for g in genre_split:
                            g_clean = g.strip()
                            if g_clean and g_clean.lower() not in ['series', 'drama', 'movie', 'film', 'serial']:
                                genres.append(g_clean)
            
            genre_text = ', '.join(genres) if genres else ''
            print(f"[NontonDrama] Genres: {genre_text}")
            
            # **PERBAIKAN PARSING SINopsis**
            content = ''
            
            # Method 1: Sinopsis class
            content_elem = soup.select_one('.sinopsis, .desc, .description, .synopsis')
            if content_elem:
                content = content_elem.get_text(strip=True)
                print(f"[NontonDrama] Synopsis found: {content[:100]}...")
            
            # Method 2: Entry content
            if not content:
                content_elem = soup.select_one('.entry-content')
                if content_elem:
                    # Ambil paragraf pertama
                    first_p = content_elem.find('p')
                    if first_p:
                        content = first_p.get_text(strip=True)
            
            # Method 3: Meta description
            if not content:
                meta_desc = soup.select_one('meta[property="og:description"], meta[name="description"]')
                if meta_desc:
                    content = meta_desc.get('content', '')
            
            # Batasi panjang
            if content:
                content = content[:400]
            
            # Gambar
            img_url = ''
            img_elem = soup.select_one('meta[property="og:image"]')
            if img_elem:
                img_url = img_elem.get('content', '')
                print(f"[NontonDrama] Image from og:image: {img_url[:80]}...")
            
            if not img_url:
                img_elem = soup.select_one('.poster img, .thumbnail img, .wp-post-image')
                if img_elem:
                    for attr in ['src', 'data-src', 'data-lazy-src']:
                        if img_elem.get(attr):
                            img_url = img_elem.get(attr)
                            print(f"[NontonDrama] Image from img element: {img_url[:80]}...")
                            break
            
            # Parse episodes
            play_str = self._parse_episodes_simple(soup, url)
            
            # Fix image URL
            if img_url and not img_url.startswith('http'):
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    img_url = self.current_site + img_url
                elif not img_url.startswith('http'):
                    img_url = urljoin(self.current_site, img_url)
            
            episode_count = len(play_str.split('#')) if play_str else 0
            print(f"[NontonDrama] Found {episode_count} episodes")
            
            # **PERBAIKAN: TAMBAHKAN TAHUN HANYA JIKA BELUM ADA DI JUDUL**
            final_title = clean_title
            if year and f"({year})" not in clean_title:
                final_title = f"{clean_title} ({year})"
            
            return {
                'list': [{
                    'vod_id': vod_id,
                    'vod_name': final_title[:150],
                    'vod_pic': img_url[:300] if img_url else '',
                    'vod_year': year,
                    'vod_area': '',
                    'vod_remarks': '',
                    'vod_content': f"Genre: {genre_text}\n\n{content}" if genre_text else content,
                    'vod_play_from': 'NontonDrama',
                    'vod_play_url': play_str,
                    'vod_director': '',
                    'vod_actor': '',
                    'vod_duration': ''
                }]
            }
            
        except Exception as e:
            print(f"[NontonDrama] Error detailContent: {e}")
            import traceback
            traceback.print_exc()
            return {'list': []}
    
    def _parse_episodes_simple(self, soup, base_url):
        """Parse episode - NOMOR URUT SAJA"""
        episodes_dict = {}
        
        print(f"[NontonDrama] Parsing episodes...")
        
        # 1. Cari JSON season-data
        season_script = soup.find('script', id='season-data')
        if season_script and season_script.string:
            try:
                print(f"[NontonDrama] Found season-data JSON")
                json_text = season_script.string.strip()
                json_text = re.sub(r'^.*?{', '{', json_text, flags=re.DOTALL)
                season_data = json.loads(json_text)
                
                for season_num, episodes in season_data.items():
                    if isinstance(episodes, list):
                        for ep_data in episodes:
                            if isinstance(ep_data, dict):
                                ep_slug = ep_data.get('slug', '')
                                ep_number = ep_data.get('episode_no', 0)
                                
                                if ep_slug and ep_number > 0:
                                    if ep_slug.startswith('/'):
                                        ep_url = self.current_site + ep_slug
                                    elif ep_slug.startswith('http'):
                                        ep_url = ep_slug
                                    else:
                                        ep_url = self.current_site + '/' + ep_slug
                                    
                                    # NAMA EPISODE: NOMOR SAJA
                                    ep_name = str(ep_number)
                                    
                                    if ep_url not in episodes_dict:
                                        episodes_dict[ep_url] = (ep_number, f"{ep_name}${ep_url}")
                                        print(f"[NontonDrama] Episode {ep_number}: {ep_url[:80]}...")
                                        
            except Exception as e:
                print(f"[NontonDrama] Error JSON: {e}")
        
        # 2. Cari player options
        player_options = soup.select('.player-options a[data-url], .player-options button[data-url]')
        if player_options:
            print(f"[NontonDrama] Found {len(player_options)} player options")
            
            episode_counter = 1
            
            for option in player_options:
                player_url = option.get('data-url', '')
                button_text = option.get_text(strip=True).lower()
                
                if player_url:
                    # Fix URL jika perlu
                    if not player_url.startswith('http'):
                        if player_url.startswith('/'):
                            player_url = self.current_site + player_url
                        else:
                            player_url = urljoin(base_url, player_url)
                    
                    # NAMA EPISODE: NOMOR SAJA
                    ep_name = str(episode_counter)
                    
                    if player_url not in episodes_dict:
                        episodes_dict[player_url] = (episode_counter, f"{ep_name}${player_url}")
                        print(f"[NontonDrama] Player option: {button_text} -> {player_url[:80]}...")
                        episode_counter += 1
        
        # 3. Cari semua link episode
        if not episodes_dict:
            all_links = soup.find_all('a', href=True)
            episode_counter = 1
            
            for link in all_links:
                href = link.get('href', '')
                if not href:
                    continue
                
                if any(pattern in href.lower() for pattern in ['episode', 'eps', '/ep-', '?ep=', '&ep=']):
                    if not href.startswith('http'):
                        if href.startswith('/'):
                            href = self.current_site + href
                        else:
                            href = urljoin(base_url, href)
                    
                    ep_name = str(episode_counter)
                    
                    if href not in episodes_dict:
                        episodes_dict[href] = (episode_counter, f"{ep_name}${href}")
                        episode_counter += 1
                        if episode_counter > 50:
                            break
        
        # Convert to sorted list
        episodes_list = list(episodes_dict.values())
        
        # Sort by number
        if episodes_list:
            episodes_list.sort(key=lambda x: x[0])
            episodes_final = [ep_str for _, ep_str in episodes_list]
        else:
            episodes_final = []
        
        # Jika masih kosong
        if not episodes_final:
            print(f"[NontonDrama] Creating dummy episodes")
            for i in range(1, 6):
                ep_url = f"{base_url}?episode={i}"
                episodes_final.append(f"{i}${ep_url}")
        
        episodes_final = episodes_final[:50]
        
        print(f"[NontonDrama] Total episodes: {len(episodes_final)}")
        
        return '#'.join(episodes_final)
    
    def searchContent(self, key, quick, pg="1"):
        try:
            if not key:
                return {'list': []}
            
            url = f"{self.current_site}/?s={quote(key)}"
            if str(pg) != '1':
                url += f"&page={pg}"
            
            print(f"[NontonDrama] Search: {key}")
            
            response = self.session.get(url, headers=self.site_headers, timeout=15)
            
            if response.status_code != 200:
                return {'list': []}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            videos = []
            
            # Cari hasil search
            items = soup.select('article, .slider')
            for item in items[:30]:
                video = self._parse_video_item(item)
                if video:
                    videos.append(video)
            
            return {
                'list': videos,
                'page': int(pg),
                'pagecount': 10,
                'limit': 30,
                'total': len(videos) * 10
            }
            
        except Exception as e:
            print(f"[NontonDrama] Error searchContent: {e}")
            return {'list': []}
    
    def playerContent(self, flag, id, vipFlags):
        """Player Content - URUTAN: Cast > Turbo > Hydrax"""
        try:
            # Decode ID
            id = unquote(id)
            
            # Parse ID
            if '$' in id:
                parts = id.split('$', 1)
                if len(parts) == 2:
                    episode_num = parts[0]
                    url = parts[1]
                else:
                    episode_num = "1"
                    url = id
            else:
                episode_num = "1"
                url = id
            
            print(f"[NontonDrama] Player - Episode: {episode_num}")
            print(f"[NontonDrama] Player URL: {url}")
            
            # **URUTAN PRIORITAS PLAYER:**
            # 1. CAST (Google Cast / Chromecast)
            # 2. TURBO (Turbovip)
            # 3. HYDRAX
            
            # Headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://nontondrama.my/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate'
            }
            
            # Coba get halaman
            try:
                response = self.session.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    content = response.text
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # **CARI PLAYER OPTIONS**
                    player_options = soup.select('.player-options a, .player-options button')
                    
                    if player_options:
                        print(f"[NontonDrama] Found {len(player_options)} player options")
                        
                        # **URUTAN PRIORITAS: CAST > TURBO > HYDRAX**
                        priority_players = [
                            ('cast', 'CAST'),           # Priority 1
                            ('turbovip', 'TURBO'),      # Priority 2  
                            ('hydrax', 'HYDRAX'),       # Priority 3
                        ]
                        
                        # Kumpulkan semua player yang ditemukan
                        found_players = []
                        
                        for button in player_options:
                            button_text = button.get_text(strip=True).upper()
                            data_url = button.get('data-url', '')
                            button_id = button.get('id', '')
                            
                            if data_url:
                                # Fix URL jika perlu
                                if not data_url.startswith('http'):
                                    if data_url.startswith('/'):
                                        data_url = self.current_site + data_url
                                    else:
                                        data_url = urljoin(url, data_url)
                                
                                # Cek tipe player berdasarkan teks atau ID
                                player_info = self._identify_player_type(button_text, button_id, data_url)
                                
                                if player_info:
                                    player_type, player_name = player_info
                                    found_players.append({
                                        'type': player_type,
                                        'name': player_name,
                                        'url': data_url,
                                        'priority': self._get_player_priority(player_type),
                                        'button_text': button_text
                                    })
                        
                        # **URUTKAN BERDASARKAN PRIORITAS**
                        found_players.sort(key=lambda x: x['priority'])
                        
                        for player in found_players:
                            print(f"[NontonDrama] Trying {player['name']} (priority: {player['priority']})")
                            
                            # Ekstrak video URL dari player
                            video_url = self._extract_from_player_smart(player['url'], player['type'])
                            
                            if video_url:
                                print(f"[NontonDrama] ✓ Success with {player['name']}: {video_url[:80]}...")
                                
                                # Buat header sesuai player type
                                player_headers = {
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                                    'Referer': player['url'],
                                    'Origin': urlparse(player['url']).scheme + '://' + urlparse(player['url']).netloc,
                                    'Accept': '*/*',
                                    'Accept-Language': 'en-US,en;q=0.9'
                                }
                                
                                # Tambahkan headers khusus untuk beberapa player
                                if 'hydrax' in player['type']:
                                    player_headers.update({
                                        'Accept': 'application/json, text/javascript, */*; q=0.01',
                                        'X-Requested-With': 'XMLHttpRequest'
                                    })
                                
                                return {
                                    'parse': 0,  # Direct play jika dapat URL
                                    'url': video_url,
                                    'header': player_headers
                                }
                        
                        # Jika semua player gagal, coba player pertama sebagai webview
                        if found_players:
                            print(f"[NontonDrama] Using webview for {found_players[0]['name']}")
                            return {
                                'parse': 1,  # Webview
                                'url': found_players[0]['url'],
                                'header': headers
                            }
                    
                    # **JIKA TIDAK ADA PLAYER OPTIONS, CARI IFRAME UTAMA**
                    main_iframe = soup.find('iframe', id='main-player')
                    if not main_iframe:
                        main_iframe = soup.select_one('iframe[src*="player"], iframe[src*="embed"]')
                    
                    if main_iframe and main_iframe.get('src'):
                        iframe_src = main_iframe.get('src')
                        print(f"[NontonDrama] Found main iframe: {iframe_src}")
                        
                        # Coba identifikasi tipe player dari iframe URL
                        iframe_player_type = self._identify_player_from_url(iframe_src)
                        print(f"[NontonDrama] Iframe player type: {iframe_player_type}")
                        
                        # Coba ekstrak video dari iframe
                        video_url = self._extract_from_player_smart(iframe_src, iframe_player_type)
                        
                        if video_url:
                            print(f"[NontonDrama] ✓ Extracted from iframe: {video_url[:80]}...")
                            return {
                                'parse': 0,
                                'url': video_url,
                                'header': {
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                                    'Referer': iframe_src,
                                    'Origin': urlparse(iframe_src).scheme + '://' + urlparse(iframe_src).netloc
                                }
                            }
                        
                        # Fallback ke webview iframe
                        return {
                            'parse': 1,
                            'url': iframe_src,
                            'header': headers
                        }
                        
            except Exception as e:
                print(f"[NontonDrama] Error processing page: {e}")
            
            # **FALLBACK: Webview ke URL asli**
            print(f"[NontonDrama] Using webview to original URL")
            
            return {
                'parse': 1,
                'url': url,
                'header': headers
            }
            
        except Exception as e:
            print(f"[NontonDrama] Error playerContent: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'parse': 1,
                'url': id if isinstance(id, str) else '',
                'header': headers
            }
    
    def _identify_player_type(self, button_text, button_id, player_url):
        """Identifikasi tipe player berdasarkan text, id, atau URL"""
        button_text_upper = button_text.upper()
        player_url_lower = player_url.lower()
        
        # **URUTAN PRIORITAS:**
        
        # 1. CAST (Google Cast / Chromecast)
        if any(keyword in button_text_upper for keyword in ['CAST', 'CHROME', 'CHROMECAST', 'GOOGLE']):
            return ('cast', 'CAST Player')
        
        # 2. TURBO (Turbovip)
        elif any(keyword in button_text_upper for keyword in ['TURBO', 'TURBOVIP', 'TURBO VIP']):
            return ('turbovip', 'TURBOVIP')
        elif 'turbovip' in player_url_lower:
            return ('turbovip', 'TURBOVIP')
        
        # 3. HYDRAX
        elif 'HYDRAX' in button_text_upper:
            return ('hydrax', 'HYDRAX')
        elif 'hydrax' in player_url_lower:
            return ('hydrax', 'HYDRAX')
        
        # 4. P2P (jika masih ada)
        elif 'P2P' in button_text_upper or 'p2p' in player_url_lower:
            return ('p2p', 'P2P Player')
        
        # 5. Default based on button text
        elif button_text_upper:
            # Coba tebak dari text
            for keyword, player_type in [('CAST', 'cast'), ('TURBO', 'turbovip'), ('HYDRAX', 'hydrax')]:
                if keyword in button_text_upper:
                    return (player_type, f"{keyword} Player")
        
        return None
    
    def _get_player_priority(self, player_type):
        """Get priority number (lebih kecil = lebih tinggi prioritas)"""
        priority_map = {
            'cast': 1,      # Priority 1
            'turbovip': 2,  # Priority 2
            'hydrax': 3,    # Priority 3
            'p2p': 4,       # Priority 4
            'other': 99     # Priority terakhir
        }
        return priority_map.get(player_type, 99)
    
    def _identify_player_from_url(self, url):
        """Identifikasi player dari URL iframe"""
        url_lower = url.lower()
        
        if 'cast' in url_lower or 'chromecast' in url_lower:
            return 'cast'
        elif 'turbovip' in url_lower:
            return 'turbovip'
        elif 'hydrax' in url_lower:
            return 'hydrax'
        elif 'p2p' in url_lower:
            return 'p2p'
        else:
            return 'unknown'
    
    def _extract_from_player_smart(self, player_url, player_type):
        """Ekstrak video URL sesuai tipe player"""
        try:
            print(f"[NontonDrama] Smart extract from {player_type}: {player_url[:80]}...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://nontondrama.my/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7'
            }
            
            response = self.session.get(player_url, headers=headers, timeout=15)
            if response.status_code != 200:
                return None
            
            content = response.text
            
            # **EKSTRAKSI BERDASARKAN TIPE PLAYER**
            
            # 1. CAST Player (Google Cast)
            if player_type == 'cast':
                # Cast biasanya menggunakan m3u8 langsung
                cast_patterns = [
                    r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
                    r'src=["\'](https?://[^"\']+\.m3u8)["\']',
                    r'file\s*:\s*["\'](https?://[^"\']+\.m3u8)["\']',
                ]
            
            # 2. TURBOVIP Player
            elif player_type == 'turbovip':
                # Turbovip sering pakai JavaScript encoded
                turbovip_patterns = [
                    r'file["\']?\s*:\s*["\'](https?://[^"\']+\.(?:m3u8|mp4))["\']',
                    r'sources\s*:\s*\[.*?file["\']?\s*:\s*["\']([^"\']+\.(?:m3u8|mp4))["\']',
                    r'atob\(["\']([A-Za-z0-9+/=]+)["\']',  # Base64 encoded
                ]
                
                # Coba decode base64 jika ada
                base64_match = re.search(r'atob\(["\']([A-Za-z0-9+/=]+)["\']', content)
                if base64_match:
                    try:
                        decoded = base64.b64decode(base64_match.group(1)).decode('utf-8')
                        # Cari URL dalam decoded string
                        url_match = re.search(r'https?://[^\s"\']+\.(?:m3u8|mp4)', decoded)
                        if url_match:
                            return url_match.group(0)
                    except:
                        pass
            
            # 3. HYDRAX Player
            elif player_type == 'hydrax':
                # Hydrax sering pakai API endpoint
                hydrax_patterns = [
                    r'file["\']?\s*:\s*["\'](https?://[^"\']+\.(?:m3u8|mp4))["\']',
                    r'https?://hydrax\.net/v/[^"\']+',
                    r'https?://[^/]+/v/[^"\']+',
                ]
                
                # Cari Hydrax video ID
                hydrax_id_match = re.search(r'hydrax\.net/v/([^"\']+)', content)
                if hydrax_id_match:
                    video_id = hydrax_id_match.group(1)
                    # Coba build Hydrax API URL
                    hydrax_api_url = f"https://hydrax.net/v/{video_id}"
                    return hydrax_api_url
            
            # PATTERN UMUM untuk semua player
            common_patterns = [
                # m3u8 patterns
                r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
                r'file\s*:\s*["\'](https?://[^"\']+\.m3u8)["\']',
                r'src=["\'](https?://[^"\']+\.m3u8)["\']',
                
                # mp4 patterns  
                r'["\'](https?://[^"\']+\.mp4[^"\']*)["\']',
                r'file\s*:\s*["\'](https?://[^"\']+\.mp4)["\']',
                r'src=["\'](https?://[^"\']+\.mp4)["\']',
                
                # Video element
                r'<video[^>]+src=["\']([^"\']+)["\']',
                r'<source[^>]+src=["\']([^"\']+)["\']',
                
                # JWPlayer
                r'jwplayer\([^)]+\)\.setup\([^}]+file["\']?\s*:\s*["\']([^"\']+)["\']',
            ]
            
            # Coba semua pattern
            for pattern in common_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    if isinstance(match, str) and any(ext in match.lower() for ext in ['.m3u8', '.mp4', '.m3u']):
                        video_url = match.strip()
                        
                        # Fix URL
                        if video_url.startswith('//'):
                            video_url = 'https:' + video_url
                        elif video_url.startswith('/'):
                            video_url = urlparse(player_url).scheme + '://' + urlparse(player_url).netloc + video_url
                        elif not video_url.startswith('http'):
                            video_url = urljoin(player_url, video_url)
                        
                        if self._is_valid_video_url(video_url):
                            print(f"[NontonDrama] ✓ Found video in {player_type} player")
                            return video_url
            
            return None
            
        except Exception as e:
            print(f"[NontonDrama] Error smart extract: {e}")
            return None
    
    def _is_valid_video_url(self, url):
        """Cek apakah URL video valid"""
        if not url or ' ' in url:
            return False
        
        url_lower = url.lower()
        video_patterns = [
            '.m3u8',
            '.mp4',
            '.mkv',
            '.webm',
            '.ts',
            '.m3u',
        ]
        
        for pattern in video_patterns:
            if pattern in url_lower:
                return True
        
        return False
    
    def isVideoFormat(self, url):
        """Cek apakah URL video"""
        return self._is_valid_video_url(url)
    
    def manualVideoCheck(self):
        return True
    
    def localProxy(self, param):
        return []