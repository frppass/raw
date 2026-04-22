# -*- coding: utf-8 -*-
import re, sys, requests, json, base64, time, html
from urllib.parse import urljoin, quote, urlparse, parse_qs, unquote
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.site = 'https://s13.nontonanimeid.boats'
        self.site_domain = 'nontonanimeid.boats'
        self.cdn_domain = 'cdn2.kotakanimeid.link'
        self.player_domain = 's1.kotakanimeid.link'
        
        # Ajax URL untuk load more
        self.ajax_url = 'https://s11.nontonanimeid.boats/wp-admin/admin-ajax.php'
        
        self.site_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.site,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en;q=0.8',
        }
        
        self.cache = {}
        self.session = requests.Session()
        self.session.headers.update(self.site_headers)
        
        print("✅ NONTONANIMEID Spider untuk OK影视 initialized")
    
    def getName(self):
        return "🇮🇩 NONTONANIMEID"
    
    def getVersion(self):
        return "8.0.0"
    
    def getType(self):
        return "Anime"
    
    def isVideoFormat(self, url):
        return any(ext in url.lower() for ext in ['.m3u8', '.mp4', '.mkv', '.webm'])
    
    def manualVideoCheck(self):
        return True
    
    def _clean_text(self, text):
        """Membersihkan teks dari HTML entities dan whitespace berlebih"""
        if not text:
            return ""
        text = html.unescape(text)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _clean_title(self, title):
        """
        Membersihkan judul dari tambahan seperti:
        - "Sub Indo Terbaru"
        - "Subtitle Indonesia"
        - "Episode" dll
        """
        if not title:
            return ""
        
        # Pola-pola yang ingin dihapus
        patterns_to_remove = [
            r'\s*Sub\s+Indo\s+Terbaru.*$',
            r'\s*Subtitle\s+Indonesia.*$',
            r'\s*Sub\s+Indo.*$',
            r'\s*Episode\s+\d+.*$',
            r'\s*-\s*Nonton.*$',
            r'\s*-\s*Streaming.*$',
            r'\s*-\s*Download.*$',
            r'\s*-\s*Anime.*$',
            r'\s*BD\s*$',
            r'\s*Batch\s*$',
            r'\s*Complete\s*$',
            r'\s*Ongoing\s*$',
            r'\s*\[\w+\]\s*',  # [Subtitle] pattern
        ]
        
        cleaned = title
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.I)
        
        # Hapus spasi berlebih
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def homeContent(self, filter):
        """
        Menu kategori dari HTML situs - LENGKAP
        Berdasarkan analisis navbar dan halaman genres
        """
        return {
            'class': [
                # ===== MENU UTAMA (dari navbar) =====
                
                {'type_id': 'anime-list', 'type_name': '📋 Anime List'},
                
                # ===== GENRE (dari halaman genres) =====
                {'type_id': 'action', 'type_name': '⚔️ Action'},
                {'type_id': 'adult-cast', 'type_name': '👤 Adult Cast'},
                {'type_id': 'adventure', 'type_name': '🧭 Adventure'},
                {'type_id': 'anthropomorphic', 'type_name': '🐾 Anthropomorphic'},
                {'type_id': 'avant-garde', 'type_name': '🎨 Avant Garde'},
                {'type_id': 'award-winning', 'type_name': '🏆 Award Winning'},
                {'type_id': 'boys-love', 'type_name': '💙 Boys Love'},
                {'type_id': 'cgdct', 'type_name': '👧 CGDCT'},
                {'type_id': 'childcare', 'type_name': '🍼 Childcare'},
                {'type_id': 'combat-sports', 'type_name': '🥊 Combat Sports'},
                {'type_id': 'comedy', 'type_name': '😂 Comedy'},
                {'type_id': 'crossdressing', 'type_name': '👘 Crossdressing'},
                {'type_id': 'delinquents', 'type_name': '😈 Delinquents'},
                {'type_id': 'detective', 'type_name': '🕵️ Detective'},
                {'type_id': 'drama', 'type_name': '🎭 Drama'},
                {'type_id': 'ecchi', 'type_name': '🔞 Ecchi'},
                {'type_id': 'educational', 'type_name': '📚 Educational'},
                {'type_id': 'erotica', 'type_name': '💋 Erotica'},
                {'type_id': 'fantasy', 'type_name': '🧚 Fantasy'},
                {'type_id': 'gag-humor', 'type_name': '😄 Gag Humor'},
                {'type_id': 'girls-love', 'type_name': '💗 Girls Love'},
                {'type_id': 'gore', 'type_name': '🩸 Gore'},
                {'type_id': 'gourmet', 'type_name': '🍜 Gourmet'},
                {'type_id': 'harem', 'type_name': '👥 Harem'},
                {'type_id': 'high-stakes-game', 'type_name': '🎲 High Stakes Game'},
                {'type_id': 'historical', 'type_name': '🏯 Historical'},
                {'type_id': 'horror', 'type_name': '👻 Horror'},
                {'type_id': 'idols-female', 'type_name': '👩 Idols (Female)'},
                {'type_id': 'idols-male', 'type_name': '👨 Idols (Male)'},
                {'type_id': 'isekai', 'type_name': '🚪 Isekai'},
                {'type_id': 'iyashikei', 'type_name': '🌸 Iyashikei'},
                {'type_id': 'josei', 'type_name': '👩 Josei'},
                {'type_id': 'kids', 'type_name': '🧒 Kids'},
                {'type_id': 'love-polygon', 'type_name': '🔺 Love Polygon'},
                {'type_id': 'love-status-quo', 'type_name': '💕 Love Status Quo'},
                {'type_id': 'magical-sex-shift', 'type_name': '✨ Magical Sex Shift'},
                {'type_id': 'mahou-shoujo', 'type_name': '✨ Mahou Shoujo'},
                {'type_id': 'martial-arts', 'type_name': '🥋 Martial Arts'},
                {'type_id': 'mecha', 'type_name': '🤖 Mecha'},
                {'type_id': 'medical', 'type_name': '🏥 Medical'},
                {'type_id': 'military', 'type_name': '🎖️ Military'},
                {'type_id': 'music', 'type_name': '🎵 Music'},
                {'type_id': 'mystery', 'type_name': '🔍 Mystery'},
                {'type_id': 'mythology', 'type_name': '🏛️ Mythology'},
                {'type_id': 'organized-crime', 'type_name': '💼 Organized Crime'},
                {'type_id': 'otaku-culture', 'type_name': '🎮 Otaku Culture'},
                {'type_id': 'parody', 'type_name': '🎭 Parody'},
                {'type_id': 'performing-arts', 'type_name': '🎪 Performing Arts'},
                {'type_id': 'pets', 'type_name': '🐾 Pets'},
                {'type_id': 'psychological', 'type_name': '🧠 Psychological'},
                {'type_id': 'racing', 'type_name': '🏎️ Racing'},
                {'type_id': 'reincarnation', 'type_name': '🔄 Reincarnation'},
                {'type_id': 'reverse-harem', 'type_name': '👥 Reverse Harem'},
                {'type_id': 'romance', 'type_name': '❤️ Romance'},
                {'type_id': 'samurai', 'type_name': '⚔️ Samurai'},
                {'type_id': 'school', 'type_name': '🏫 School'},
                {'type_id': 'sci-fi', 'type_name': '🚀 Sci-Fi'},
                {'type_id': 'seinen', 'type_name': '👨 Seinen'},
                {'type_id': 'shoujo', 'type_name': '👧 Shoujo'},
                {'type_id': 'shounen', 'type_name': '💪 Shounen'},
                {'type_id': 'showbiz', 'type_name': '🎬 Showbiz'},
                {'type_id': 'slice-of-life', 'type_name': '🏡 Slice of Life'},
                {'type_id': 'space', 'type_name': '🌌 Space'},
                {'type_id': 'sports', 'type_name': '⚽ Sports'},
                {'type_id': 'strategy-game', 'type_name': '♟️ Strategy Game'},
                {'type_id': 'super-power', 'type_name': '⚡ Super Power'},
                {'type_id': 'supernatural', 'type_name': '👻 Supernatural'},
                {'type_id': 'survival', 'type_name': '🏕️ Survival'},
                {'type_id': 'suspense', 'type_name': '😨 Suspense'},
                {'type_id': 'team-sports', 'type_name': '🏀 Team Sports'},
                {'type_id': 'time-travel', 'type_name': '⏰ Time Travel'},
                {'type_id': 'urban-fantasy', 'type_name': '🏙️ Urban Fantasy'},
                {'type_id': 'vampire', 'type_name': '🧛 Vampire'},
                {'type_id': 'video-game', 'type_name': '🎮 Video Game'},
                {'type_id': 'villainess', 'type_name': '👑 Villainess'},
                {'type_id': 'visual-arts', 'type_name': '🎨 Visual Arts'},
                {'type_id': 'workplace', 'type_name': '💼 Workplace'},
                
            ],
            'filters': {}
        }
    
    def _get_page_url(self, tid, pg):
        """
        Buat URL untuk kategori berdasarkan type_id
        - Untuk genre: menggunakan format /genres/nama-genre/ dengan pagination page/{pg}/
        - Untuk lainnya: menggunakan format sebelumnya
        """
        
        # Daftar genre yang menggunakan URL pattern /genres/nama-genre/
        genre_list = [
            'action', 'adult-cast', 'adventure', 'anthropomorphic', 'avant-garde',
            'award-winning', 'boys-love', 'cgdct', 'childcare', 'combat-sports',
            'comedy', 'crossdressing', 'delinquents', 'detective', 'drama',
            'ecchi', 'educational', 'erotica', 'fantasy', 'gag-humor',
            'girls-love', 'gore', 'gourmet', 'harem', 'high-stakes-game',
            'historical', 'horror', 'idols-female', 'idols-male', 'isekai',
            'iyashikei', 'josei', 'kids', 'love-polygon', 'love-status-quo',
            'magical-sex-shift', 'mahou-shoujo', 'martial-arts', 'mecha',
            'medical', 'military', 'music', 'mystery', 'mythology',
            'organized-crime', 'otaku-culture', 'parody', 'performing-arts',
            'pets', 'psychological', 'racing', 'reincarnation', 'reverse-harem',
            'romance', 'samurai', 'school', 'sci-fi', 'seinen', 'shoujo',
            'shounen', 'showbiz', 'slice-of-life', 'space', 'sports',
            'strategy-game', 'super-power', 'supernatural', 'survival',
            'suspense', 'team-sports', 'time-travel', 'urban-fantasy',
            'vampire', 'video-game', 'villainess', 'visual-arts', 'workplace'
        ]
        
        # Jika tid termasuk dalam genre_list, gunakan URL pattern /genres/nama-genre/
        if tid in genre_list:
            if int(pg) > 1:
                # Format pagination: /genres/nama-genre/page/2/
                return f"{self.site}/genres/{tid}/page/{pg}/"
            else:
                return f"{self.site}/genres/{tid}/"
        
        # Mapping untuk kategori non-genre
        url_mapping = {
            # ===== MENU UTAMA =====
            'home': '/',
            'anime-list': '/anime/',
            'ongoing-list': '/ongoing-list/',
            'popular-series': '/popular-series/',
            'jadwal-rilis': '/jadwal-rilis/',
            'genres': '/genres/',
            'bookmark': '/bookmark/',
            
            # ===== TYPE =====
            'movie': '/anime/?type=Movie',
            'tv': '/anime/?type=TV',
            'ona': '/anime/?type=ONA',
            'ova': '/anime/?type=OVA',
            'special': '/anime/?type=Special',
            
            # ===== STATUS =====
            'ongoing': '/anime/?status=Currently%20Airing',
            'completed': '/anime/?status=Finished%20Airing',
            'upcoming': '/anime/?status=Not%20yet%20aired',
            
            # ===== SEASON =====
            'winter-2026': '/anime/?season=winter-2026',
            'fall-2025': '/anime/?season=fall-2025',
            'summer-2025': '/anime/?season=summer-2025',
            'spring-2025': '/anime/?season=spring-2025',
        }
        
        base_path = url_mapping.get(tid, '/anime/')
        
        # Handle pagination untuk non-genre
        if int(pg) > 1:
            if '?' in base_path:
                return f"{self.site}{base_path}&page={pg}"
            else:
                if base_path.endswith('/'):
                    return f"{self.site}{base_path}page/{pg}/"
                else:
                    return f"{self.site}{base_path}?page={pg}"
        
        return f"{self.site}{base_path}"
    
    def homeVideoContent(self):
        """
        Mengambil anime dari halaman utama - HALAMAN 1
        """
        try:
            cache_key = 'home_content_page_1'
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            print("📥 Mengambil halaman utama page 1...")
            url = f"{self.site}/"
            html = self.fetch(url).text
            
            items = self._parse_home_articles(html)
            
            # Ambil nonce dari HTML untuk AJAX request
            nonce_match = re.search(r'var misha_loadmore_params\s*=\s*{\s*"ajaxurl"\s*:\s*"[^"]+"\s*,\s*"nonce"\s*:\s*"([^"]+)"', html)
            nonce = nonce_match.group(1) if nonce_match else None
            
            # Cek apakah ada tombol Load More
            load_more = re.search(r'class="misha_loadmore loadmore_button load_more"', html)
            
            if load_more:
                print("✅ Tombol Load More ditemukan - ada halaman berikutnya")
                if nonce:
                    print(f"✅ Nonce ditemukan: {nonce}")
                    self.cache['home_nonce'] = nonce
                total_pages = 10  # Asumsi 10 halaman
            else:
                total_pages = 1
            
            result = {
                'list': items,
                'page': 1,
                'pagecount': total_pages,
                'limit': len(items),
                'total': len(items) * total_pages
            }
            
            self.cache[cache_key] = result
            return result
            
        except Exception as e:
            print(f"❌ Home error: {e}")
            import traceback
            traceback.print_exc()
            return {'list': []}
    
    def _parse_home_articles(self, html):
        """Parse artikel dari HTML halaman home"""
        items = []
        seen = set()
        
        # Pattern untuk artikel di halaman utama
        article_pattern = r'<article[^>]*class="animeseries[^"]*"[^>]*>(.*?)</article>'
        articles = re.findall(article_pattern, html, re.S | re.I)
        
        print(f"✅ Menemukan {len(articles)} artikel di halaman")
        
        for article_html in articles:
            try:
                # Link
                link_match = re.search(r'<a[^>]*href="([^"]+)"[^>]*>', article_html)
                if not link_match:
                    continue
                href = link_match.group(1)
                
                if href in seen:
                    continue
                
                # Judul dari h3
                title_match = re.search(r'<h3[^>]*class="title[^"]*"[^>]*><span>([^<]+)</span>', article_html, re.S)
                if not title_match:
                    title_match = re.search(r'<h3[^>]*class="title[^"]*"[^>]*>([^<]+)</h3>', article_html, re.S)
                
                raw_title = title_match.group(1) if title_match else "Unknown"
                title = self._clean_title(raw_title)
                
                # Gambar
                img = ''
                img_match = re.search(r'<img[^>]*src="([^"]+)"[^>]*>', article_html)
                if img_match:
                    img = img_match.group(1)
                
                # Remarks (jumlah episode)
                remarks = ''
                
                # Cek span dengan class "types episodes"
                ep_match = re.search(r'<span[^>]*class="types episodes"[^>]*><span[^>]*class="dashicons dashicons-plus-alt"[^>]*></span>(\d+)', article_html)
                if ep_match:
                    remarks = f"Ep {ep_match.group(1)}"
                
                # Cek status (UC = Ongoing)
                if 'types status' in article_html:
                    status_match = re.search(r'<span[^>]*class="types status"[^>]*><span[^>]*class="dashicons[^"]*"[^>]*></span>([^<]+)', article_html)
                    if status_match:
                        status = status_match.group(1).strip()
                        if status == 'UC':
                            remarks = 'Ongoing'
                        elif status == 'Complete':
                            remarks = 'Complete'
                        elif status == 'Dub JP':
                            remarks = 'Dub JP'
                
                # Cek apakah ada badge streaming
                if 'dashicons-video-alt3' in article_html:
                    if remarks:
                        remarks += ' ▶️'
                    else:
                        remarks = 'Streaming'
                
                items.append({
                    'vod_id': href,
                    'vod_name': title,
                    'vod_pic': urljoin(self.site, img),
                    'vod_remarks': remarks
                })
                seen.add(href)
                
            except Exception as e:
                print(f"⚠️ Error parsing article: {e}")
                continue
        
        return items
    
    def _load_more_page(self, page):
        """
        Memuat halaman berikutnya menggunakan AJAX load more
        """
        try:
            print(f"📥 Load more page {page}...")
            
            # Ambil nonce dari cache
            nonce = self.cache.get('home_nonce')
            
            # Data untuk AJAX request - format yang benar
            data = {
                'action': 'loadmore',
                'page': page,
                'nonce': nonce if nonce else '',
                'current_page': page
            }
            
            headers = {
                'User-Agent': self.site_headers['User-Agent'],
                'Referer': self.site,
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            print(f"📤 Mengirim AJAX request dengan data: {data}")
            
            # Kirim AJAX request
            response = self.session.post(self.ajax_url, data=data, headers=headers, timeout=15)
            
            if response.status_code == 200:
                print(f"✅ AJAX response status: {response.status_code}")
                
                # Cek response
                try:
                    result = response.json()
                    
                    if isinstance(result, dict):
                        if 'html' in result:
                            print(f"✅ Mendapatkan HTML dari response")
                            # Parse HTML dari response
                            html_content = result['html']
                            return self._parse_home_articles(html_content)
                        elif 'data' in result:
                            print(f"✅ Mendapatkan data dari response")
                            if isinstance(result['data'], str):
                                return self._parse_home_articles(result['data'])
                    elif isinstance(result, str):
                        print(f"✅ Response berupa string HTML")
                        return self._parse_home_articles(result)
                        
                except json.JSONDecodeError:
                    print(f"⚠️ Response bukan JSON, coba parse sebagai HTML")
                    # Jika bukan JSON, mungkin langsung HTML
                    return self._parse_home_articles(response.text)
            else:
                print(f"⚠️ AJAX request gagal: {response.status_code}")
                
            # Fallback ke URL biasa jika AJAX gagal
            print(f"⚠️ Menggunakan fallback URL: {self.site}/page/{page}/")
            url = f"{self.site}/page/{page}/"
            html = self.fetch(url).text
            return self._parse_home_articles(html)
                
        except Exception as e:
            print(f"⚠️ Load more error: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback ke URL biasa
            try:
                url = f"{self.site}/page/{page}/"
                print(f"⚠️ Fallback ke URL: {url}")
                html = self.fetch(url).text
                return self._parse_home_articles(html)
            except:
                return []
    
    def _parse_category_articles(self, html):
        """Parse artikel dari halaman kategori/archive"""
        items = []
        seen = set()
        
        # Pattern untuk anime di halaman archive (as-anime-card)
        anime_pattern = r'<a[^>]*href="([^"]+)"[^>]*class="as-anime-card[^"]*"[^>]*>.*?<img[^>]*src="([^"]+)"[^>]*alt="([^"]+)"[^>]*>.*?<h3[^>]*class="as-anime-title"[^>]*>([^<]+)</h3>'
        
        anime_matches = re.findall(anime_pattern, html, re.S | re.I)
        
        if anime_matches:
            print(f"✅ Menemukan {len(anime_matches)} anime dengan format as-anime-card")
            for match in anime_matches:
                try:
                    href = match[0]
                    img = match[1]
                    alt_title = match[2]
                    raw_title = match[3]
                    
                    # Bersihkan judul
                    title = self._clean_title(raw_title)
                    if not title:
                        title = self._clean_title(alt_title)
                    
                    if href in seen:
                        continue
                    
                    items.append({
                        'vod_id': href,
                        'vod_name': title,
                        'vod_pic': urljoin(self.site, img),
                        'vod_remarks': ''
                    })
                    seen.add(href)
                    
                except Exception as e:
                    continue
        
        # Fallback: pattern artikel biasa
        if not items:
            article_pattern = r'<article[^>]*class="animeseries[^"]*"[^>]*>(.*?)</article>'
            articles = re.findall(article_pattern, html, re.S | re.I)
            
            print(f"✅ Menemukan {len(articles)} artikel dengan format animeseries")
            for article_html in articles:
                try:
                    link_match = re.search(r'<a[^>]*href="([^"]+)"[^>]*>', article_html)
                    if not link_match:
                        continue
                    href = link_match.group(1)
                    
                    if href in seen:
                        continue
                    
                    title_match = re.search(r'<h3[^>]*class="title[^"]*"[^>]*><span>([^<]+)</span>', article_html, re.S)
                    if not title_match:
                        title_match = re.search(r'<h3[^>]*class="title[^"]*"[^>]*>([^<]+)</h3>', article_html, re.S)
                    
                    raw_title = title_match.group(1) if title_match else "Unknown"
                    title = self._clean_title(raw_title)
                    
                    img = ''
                    img_match = re.search(r'<img[^>]*src="([^"]+)"[^>]*>', article_html)
                    if img_match:
                        img = img_match.group(1)
                    
                    items.append({
                        'vod_id': href,
                        'vod_name': title,
                        'vod_pic': urljoin(self.site, img),
                        'vod_remarks': ''
                    })
                    seen.add(href)
                    
                except Exception as e:
                    continue
        
        return items
    
    def categoryContent(self, tid, pg, filter, extend):
        """Mengambil konten kategori"""
        try:
            # Skip separator
            if tid.startswith('separator'):
                return {
                    'list': [],
                    'page': int(pg),
                    'pagecount': 1,
                    'limit': 0,
                    'total': 0
                }
            
            # Untuk home, gunakan homeVideoContent untuk page 1 dan load more untuk page > 1
            if tid == 'home':
                if int(pg) == 1:
                    result = self.homeVideoContent()
                    return result
                else:
                    print(f"📥 Mengambil home page {pg} menggunakan load more...")
                    items = self._load_more_page(int(pg))
                    
                    # Cek apakah ada tombol Load More di halaman pertama
                    has_load_more = 'home_nonce' in self.cache
                    
                    return {
                        'list': items,
                        'page': int(pg),
                        'pagecount': 10 if has_load_more else int(pg),
                        'limit': len(items),
                        'total': len(items) * (10 if has_load_more else 1)
                    }
            
            # Untuk kategori lain (termasuk genre), gunakan URL yang sudah ditentukan
            url = self._get_page_url(tid, pg)
            print(f"📥 Mengambil kategori '{tid}' halaman {pg}: {url}")
            
            html = self.fetch(url).text
            
            items = self._parse_category_articles(html)
            
            # Pagination
            total_pages = int(pg)
            
            # Cek pagination dari URL parameter atau link
            pagination_pattern = r'<a[^>]*class="page-numbers"[^>]*href="[^"]*page[/=](\d+)[^"]*"[^>]*>'
            pages = re.findall(pagination_pattern, html, re.I)
            if pages:
                total_pages = max([int(p) for p in pages] + [int(pg)])
            elif len(items) >= 20:
                # Jika ada banyak item, asumsikan ada halaman berikutnya
                total_pages = max(int(pg), int(pg) + 1)
            
            # Untuk genre, biasanya pagination menggunakan format page/{pg}/
            # Cek apakah ada link "Next" atau nomor halaman terakhir
            next_link = re.search(r'<a[^>]*class="next page-numbers"[^>]*href="[^"]*page[/=](\d+)"', html)
            if next_link:
                total_pages = max(total_pages, int(next_link.group(1)))
            
            print(f"📊 Halaman {pg} - Ditemukan {len(items)} item")
            
            return {
                'list': items,
                'page': int(pg),
                'pagecount': total_pages,
                'limit': 30,
                'total': len(items) * total_pages
            }
            
        except Exception as e:
            print(f"❌ Category error: {e}")
            import traceback
            traceback.print_exc()
            return {'list': []}
    
    def searchContent(self, key, quick, pg="1"):
        """Pencarian anime"""
        try:
            url = f"{self.site}/?s={quote(key)}"
            if int(pg) > 1:
                url += f"&page={pg}"
            
            print(f"📥 Mencari: {key}")
            html = self.fetch(url).text
            
            items = self._parse_category_articles(html)
            
            return {'list': items, 'page': int(pg), 'pagecount': 1}
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            return {'list': []}
    
    # ===== DETAIL CONTENT DENGAN EPLISTER UNTUK EPISODE =====
    def detailContent(self, ids):
        """
        Detail anime dan episode - MENGGUNAKAN EPLISTER UNTUK EPISODE LENGKAP
        """
        try:
            url = ids[0]
            if not url.startswith('http'):
                url = urljoin(self.site, url)
            
            print(f"📥 Mengambil detail: {url}")
            
            html = self.fetch(url).text
            
            # ===== INFO DASAR =====
            
            # 1. Judul Anime - DIBERSIHKAN
            raw_title = ''
            
            # Coba dari meta tag og:title
            og_title_match = re.search(r'<meta[^>]*property="og:title"[^>]*content="([^"]+)"', html, re.I)
            if og_title_match:
                raw_title = og_title_match.group(1)
            
            # Coba dari h1 class entry-title
            if not raw_title:
                h1_match = re.search(r'<h1[^>]*class="entry-title"[^>]*>(.*?)</h1>', html, re.S | re.I)
                if h1_match:
                    raw_title = h1_match.group(1)
            
            # Coba dari h1 class title
            if not raw_title:
                h1_title_match = re.search(r'<h1[^>]*class="title"[^>]*>(.*?)</h1>', html, re.S | re.I)
                if h1_title_match:
                    raw_title = h1_title_match.group(1)
            
            # Bersihkan judul
            title = self._clean_title(raw_title)
            
            # Fallback: jika masih kosong, gunakan URL terakhir
            if not title:
                # Ambil dari URL
                url_path = urlparse(url).path
                last_part = url_path.strip('/').split('/')[-1]
                title = last_part.replace('-', ' ').title()
            
            print(f"📌 Raw title: {raw_title}")
            print(f"📌 Clean title: {title}")
            
            # 2. Gambar
            img = ''
            og_img_match = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html, re.I)
            if og_img_match:
                img = og_img_match.group(1)
            
            if not img:
                thumb_img = re.search(r'<div[^>]*class="thumbnail"[^>]*>.*?<img[^>]*src="([^"]+)"', html, re.S | re.I)
                if thumb_img:
                    img = thumb_img.group(1)
            
            # 3. Deskripsi
            desc = ''
            meta_desc = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html, re.I)
            if meta_desc:
                desc = self._clean_text(meta_desc.group(1))
            
            if not desc or len(desc) < 50:
                content_match = re.search(r'<div[^>]*class="entry-content[^"]*"[^>]*>(.*?)</div>', html, re.S | re.I)
                if content_match:
                    content_text = re.sub(r'<[^>]+>', ' ', content_match.group(1))
                    content_text = re.sub(r'\s+', ' ', content_text).strip()
                    if content_text:
                        desc = content_text[:500]
            
            # 4. Tahun
            year = ''
            year_match = re.search(r'Year:\s*(\d{4})', html, re.I)
            if year_match:
                year = year_match.group(1)
            
            if not year:
                year_match = re.search(r'20\d{2}', html)
                if year_match:
                    year = year_match.group(0)
            
            # 5. Total Episode
            total_episodes = ''
            ep_info = re.search(r'(\d+)\s*Episode', html, re.I)
            if ep_info:
                total_episodes = ep_info.group(1)
            
            # 6. Site/Studio
            site_info = ''
            site_match = re.search(r'Site:\s*([^<\n]+)', html, re.I)
            if site_match:
                site_info = site_match.group(1).strip()
            
            # ===== EPISODE LIST - PRIORITAS EPLISTER =====
            episodes = []
            
            print("🔍 Mencari daftar episode di EPLISTER...")
            
            # ===== PATTERN 1: EPLISTER (class eplister) =====
            eplister_pattern = r'<div[^>]*class="eplister"[^>]*>(.*?)</div>'
            eplister_match = re.search(eplister_pattern, html, re.S | re.I)
            
            if eplister_match:
                eplister_html = eplister_match.group(1)
                print("✅ Menemukan EPLISTER")
                
                # Pattern untuk link episode di eplister
                li_pattern = r'<li[^>]*data-index="\d+"[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>.*?<div[^>]*class="epl-num"[^>]*>(.*?)</div>.*?</a>.*?</li>'
                li_matches = re.findall(li_pattern, eplister_html, re.S | re.I)
                
                for href, ep_num in li_matches:
                    ep_num_clean = re.sub(r'[^0-9]', '', ep_num.strip())
                    if ep_num_clean:
                        episode_url = href if href.startswith('http') else urljoin(self.site, href)
                        episodes.append(f"{ep_num_clean}${episode_url}")
                        print(f"  Episode {ep_num_clean}: {episode_url}")
            
            # ===== PATTERN 2: EPLISTER alternatif (class list_eps_stream) =====
            if not episodes:
                list_eps_pattern = r'<div[^>]*class="list_eps_stream"[^>]*>(.*?)</div>'
                list_eps_match = re.search(list_eps_pattern, html, re.S | re.I)
                
                if list_eps_match:
                    list_html = list_eps_match.group(1)
                    print("✅ Menemukan list_eps_stream")
                    
                    # Cari href di dalam li
                    href_pattern = r'<li[^>]*class="select-eps"[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>.*?(?:Episode\s*)?(\d+).*?</a>'
                    href_matches = re.findall(href_pattern, list_html, re.S | re.I)
                    
                    for href, ep_num in href_matches:
                        ep_num_clean = ep_num.strip()
                        if ep_num_clean:
                            episode_url = href if href.startswith('http') else urljoin(self.site, href)
                            episodes.append(f"{ep_num_clean}${episode_url}")
                            print(f"  Episode {ep_num_clean}: {episode_url}")
            
            # ===== PATTERN 3: EPISODELIST (class episodelist) =====
            if not episodes:
                eps_pattern = r'<div[^>]*class="episodelist[^"]*"[^>]*>(.*?)</div>'
                eps_match = re.search(eps_pattern, html, re.S | re.I)
                
                if eps_match:
                    eps_html = eps_match.group(1)
                    print("✅ Menemukan episodelist")
                    
                    li_pattern = r'<li[^>]*data-id="\d+"[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>.*?<span>Eps?\s*(\d+).*?</span>.*?</a>.*?</li>'
                    li_matches = re.findall(li_pattern, eps_html, re.S | re.I)
                    
                    for href, ep_num in li_matches:
                        ep_num_clean = ep_num.strip()
                        if ep_num_clean:
                            episode_url = href if href.startswith('http') else urljoin(self.site, href)
                            episodes.append(f"{ep_num_clean}${episode_url}")
                            print(f"  Episode {ep_num_clean}: {episode_url}")
            
            # ===== PATTERN 4: LINK EPISODE LANGSUNG =====
            if not episodes:
                print("⚠️ Mencari link episode...")
                link_pattern = r'<a[^>]*href="([^"]+)"[^>]*>.*?(?:Episode|Eps?)[.\s]*(\d+).*?</a>'
                link_matches = re.findall(link_pattern, html, re.I | re.S)
                
                for href, ep_num in link_matches:
                    if 'episode' in href.lower() or '/episode/' in href:
                        ep_num_clean = re.sub(r'[^0-9]', '', ep_num)
                        if ep_num_clean:
                            episode_url = href if href.startswith('http') else urljoin(self.site, href)
                            episodes.append(f"{ep_num_clean}${episode_url}")
                            print(f"  Episode {ep_num_clean}: {episode_url}")
            
            # Urutkan episode
            if episodes:
                episodes.sort(key=lambda x: int(x.split('$')[0]) if x.split('$')[0].isdigit() else 0)
                print(f"✅ Total episode ditemukan: {len(episodes)}")
            else:
                print(f"⚠️ TIDAK ADA EPISODE! Menggunakan fallback dengan {total_episodes or '1'} episode")
                
                # Buat episode dari 1 sampai total_episodes
                if total_episodes:
                    try:
                        total = int(total_episodes)
                        for i in range(1, total + 1):
                            episode_url = url.rstrip('/') + f'/episode-{i}'
                            episodes.append(f"{i}${episode_url}")
                            print(f"  Episode {i} (generated): {episode_url}")
                    except:
                        episodes.append(f"1${url}")
                else:
                    episodes.append(f"1${url}")
            
            play_url = '#'.join(episodes)
            
            # Buat remarks
            remarks_parts = []
            if total_episodes:
                remarks_parts.append(f"{total_episodes} Episode")
            if site_info:
                remarks_parts.append(site_info)
            if year:
                remarks_parts.append(year)
            
            remarks = ' | '.join(remarks_parts) if remarks_parts else ''
            
            return {
                'list': [{
                    'vod_id': url,
                    'vod_name': title,
                    'vod_pic': img,
                    'vod_year': year,
                    'vod_content': desc or 'No description available.',
                    'vod_remarks': remarks,
                    'vod_play_from': 'NONTONANIMEID',
                    'vod_play_url': play_url
                }]
            }
            
        except Exception as e:
            print(f"❌ Detail error: {e}")
            import traceback
            traceback.print_exc()
            return {'list': []}
    
    # ===== PLAYER YANG SUDAH BISA STREAMING =====
    def playerContent(self, flag, id, vipFlags):
        """
        Player untuk OK影视 - SUDAH BISA STREAMING
        """
        try:
            print(f"📥 Player untuk: {id[:100]}...")
            
            # Jika URL sudah berupa file video langsung
            if self.isVideoFormat(id):
                print(f"✅ Langsung video format")
                # Cek apakah ini URL dari cdn2.kotakanimeid.link
                if 'kotakanimeid.link' in id:
                    return {
                        'parse': 0,
                        'url': id,
                        'header': {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                            'Referer': 'https://s1.kotakanimeid.link/',
                            'Origin': 'https://s1.kotakanimeid.link'
                        }
                    }
                return {
                    'parse': 0,
                    'url': id,
                    'header': self.site_headers
                }
            
            # Coba fetch halaman episode
            try:
                resp = self.session.get(id, timeout=15, allow_redirects=True)
                final_url = resp.url
                html = resp.text
                
                print(f"  Final URL: {final_url}")
                
                # ===== CARI POLA DARI SCREENSHOT =====
                # Pola 1: Mencari URL m3u8 dari cdn2.kotakanimeid.link
                cdn_patterns = [
                    r'(https?://cdn2\.kotakanimeid\.link[^\s"\']+\.m3u8[^\s"\']*)',
                    r'(https?://[^\s"\']*kotakanimeid\.link[^\s"\']+\.m3u8[^\s"\']*)',
                    r'url=(https?://cdn2\.kotakanimeid\.link[^&\s"\']+)',
                    r'src=["\'](https?://cdn2\.kotakanimeid\.link[^"\']+\.m3u8[^"\']*)["\']',
                ]
                
                for pattern in cdn_patterns:
                    matches = re.findall(pattern, html, re.I)
                    if matches:
                        video_url = matches[0] if isinstance(matches[0], str) else matches[0][0]
                        if video_url.startswith('url='):
                            video_url = unquote(video_url[4:])
                        elif not video_url.startswith('http'):
                            video_url = 'https://cdn2.kotakanimeid.link' + video_url
                        
                        print(f"✅ Menemukan video dari CDN: {video_url[:100]}")
                        return {
                            'parse': 0,
                            'url': video_url,
                            'header': {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                                'Referer': 'https://s1.kotakanimeid.link/',
                                'Origin': 'https://s1.kotakanimeid.link'
                            }
                        }
                
                # Pola 2: Mencari iframe ke s1.kotakanimeid.link
                iframe_patterns = [
                    r'<iframe[^>]*src=["\'](https?://s1\.kotakanimeid\.link[^"\']+)["\']',
                    r'<iframe[^>]*src=["\'](//s1\.kotakanimeid\.link[^"\']+)["\']',
                ]
                
                for pattern in iframe_patterns:
                    iframe_match = re.search(pattern, html, re.S | re.I)
                    if iframe_match:
                        iframe_url = iframe_match.group(1)
                        if iframe_url.startswith('//'):
                            iframe_url = 'https:' + iframe_url
                        print(f"✅ Menemukan iframe ke kotakanimeid: {iframe_url}")
                        
                        # Fetch iframe untuk mendapatkan URL m3u8
                        try:
                            iframe_resp = self.session.get(iframe_url, timeout=10, headers={
                                'User-Agent': self.site_headers['User-Agent'],
                                'Referer': final_url
                            })
                            iframe_html = iframe_resp.text
                            
                            # Cari URL m3u8 di iframe
                            for pattern in cdn_patterns:
                                matches = re.findall(pattern, iframe_html, re.I)
                                if matches:
                                    video_url = matches[0] if isinstance(matches[0], str) else matches[0][0]
                                    if video_url.startswith('url='):
                                        video_url = unquote(video_url[4:])
                                    
                                    print(f"✅ Menemukan video dari iframe: {video_url[:100]}")
                                    return {
                                        'parse': 0,
                                        'url': video_url,
                                        'header': {
                                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                                            'Referer': iframe_url,
                                            'Origin': 'https://s1.kotakanimeid.link'
                                        }
                                    }
                        except Exception as e:
                            print(f"⚠️ Gagal fetch iframe: {e}")
                        
                        # Fallback: return iframe
                        return {
                            'parse': 1,
                            'url': iframe_url,
                            'header': {
                                'User-Agent': self.site_headers['User-Agent'],
                                'Referer': final_url,
                            }
                        }
                
                # Pola 3: Cari video langsung biasa
                video_patterns = [
                    r'(https?://[^\s"\']+\.mp4[^\s"\']*)',
                    r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
                ]
                
                for pattern in video_patterns:
                    matches = re.findall(pattern, html, re.I)
                    if matches:
                        video_url = matches[0] if isinstance(matches[0], str) else matches[0][0]
                        print(f"✅ Menemukan video langsung biasa")
                        return {
                            'parse': 0,
                            'url': video_url,
                            'header': self.site_headers
                        }
                
                # Pola 4: Cari iframe biasa
                iframe_match = re.search(r'<iframe[^>]*src=["\'](https?://[^"\']+)["\']', html, re.S | re.I)
                if iframe_match:
                    iframe_url = iframe_match.group(1)
                    if iframe_url.startswith('//'):
                        iframe_url = 'https:' + iframe_url
                    print(f"✅ Menemukan iframe biasa")
                    return {
                        'parse': 1,
                        'url': iframe_url,
                        'header': self.site_headers
                    }
                
                print("⚠️ Tidak menemukan video")
                return {
                    'parse': 1,
                    'url': final_url,
                    'header': self.site_headers
                }
                
            except Exception as e:
                print(f"⚠️ Gagal fetch halaman: {e}")
                return {
                    'parse': 1,
                    'url': id,
                    'header': self.site_headers
                }
            
        except Exception as e:
            print(f"❌ Player error: {e}")
            return {
                'parse': 1,
                'url': id
            }
    
    def fetch(self, url):
        """Fetch URL dengan anti-403"""
        try:
            # Tambahkan header tambahan untuk menghindari 403
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': self.site,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'id-ID,id;q=0.9,en;q=0.8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            return self.session.get(url, timeout=15, headers=headers)
        except Exception as e:
            print(f"Fetch error: {e}")
            class Dummy:
                text = ''
            return Dummy()
    
    def destroy(self):
        """Bersihkan session"""
        self.session.close()