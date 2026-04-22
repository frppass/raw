# -*- coding: utf-8 -*-
import re, sys, os, requests, html as htmlmod, json, datetime
from urllib.parse import urlparse, urljoin, quote, unquote
import lxml.html, pyquery, jsonpath, cachetools
from bs4 import BeautifulSoup
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
        
        self.drama_sources = [
            'https://dramacool.ps',
            'https://asianload.io',
            'https://kissasian.lu',
            'https://myasiantv.cc'
        ]
        
        self.cache = cachetools.TTLCache(maxsize=100, ttl=3600)
        self.seen_titles = set()
        
        # Tahun saat ini untuk validasi
        self.current_year = datetime.datetime.now().year
        
        # Init cookies
        self.session = requests.Session()
        
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
        pass
    
    def fetch(self, url, headers=None, timeout=20, retry=2):
        """Custom fetch dengan retry dan session"""
        headers = headers or self.site_headers
        
        for i in range(retry + 1):
            try:
                if hasattr(self, 'session'):
                    response = self.session.get(url, headers=headers, timeout=timeout, verify=False)
                else:
                    response = requests.get(url, headers=headers, timeout=timeout, verify=False)
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.Timeout:
                self.log(f"Timeout error, retry {i+1}/{retry+1}: {url}")
                if i == retry:
                    raise
            except requests.exceptions.RequestException as e:
                self.log(f"Request error: {e}")
                if i == retry:
                    raise
                import time
                time.sleep(1)
    
    def homeContent(self, filter):
        # KATEGORI BERDASARKAN HTML MENU OPPADRAMA
        return {
            'class': [
                # Menu utama dari HTML
                
                {'type_name': 'Ongoing', 'type_id': 'ongoing'},
                {'type_name': 'Completed', 'type_id': 'completed'},
                
                # Submenu Drama (dari HTML)
                {'type_name': 'Drama Korea', 'type_id': 'drama-korea'},
                {'type_name': 'Drama China', 'type_id': 'drama-china'},
                {'type_name': 'Drama Thailand', 'type_id': 'drama-thailand'},
                {'type_name': 'Drama Jepang', 'type_id': 'drama-jepang'},
                {'type_name': 'Drama Taiwan', 'type_id': 'drama-taiwan'},
                {'type_name': 'Drama Filipina', 'type_id': 'drama-filipina'},
                {'type_name': 'Series Barat', 'type_id': 'series-barat'},
                {'type_name': 'Netflix', 'type_id': 'netflix'},
                
                # Submenu Film (dari HTML)
                {'type_name': 'Film Korea', 'type_id': 'film-korea'},
                {'type_name': 'Film China', 'type_id': 'film-china'},
                {'type_name': 'Film Hong Kong', 'type_id': 'film-hongkong'},
                {'type_name': 'Film Thailand', 'type_id': 'film-thailand'},
                {'type_name': 'Film Jepang', 'type_id': 'film-jepang'},
                {'type_name': 'Film Taiwan', 'type_id': 'film-taiwan'},
                {'type_name': 'Film Filipina', 'type_id': 'film-filipina'},
                {'type_name': 'Film India', 'type_id': 'film-india'},
                {'type_name': 'Film Barat', 'type_id': 'film-barat'},
                
                # Kategori lainnya dari HTML
                {'type_name': 'Variety Show', 'type_id': 'variety-show'},
                {'type_name': 'Animasi', 'type_id': 'animasi'},
                {'type_name': 'Jadwal', 'type_id': 'jadwal'},
                {'type_name': 'Bookmark', 'type_id': 'bookmark'},
                
                # Kategori tambahan untuk navigasi
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
            html = self.fetch(self.site + '/', headers=self.site_headers, timeout=15).text
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Hapus sidebar, widget, dan notifikasi
            unwanted_selectors = [
                '#sidebar', '.widget_text', '.announ', '.kln', '.footercopyright',
                '.notification', '.pemberitahuan', '[class*="notif"]', '[class*="pengumuman"]',
                '.mobsearch', '.reklam', '.adsbygoogle', 'ins', '.ad-container',
                'script', 'style', 'iframe', '.disclaimer', '.telegram-box'
            ]
            
            for selector in unwanted_selectors:
                for elem in soup.select(selector):
                    elem.decompose()
            
            # Hapus elemen dengan teks notifikasi
            for elem in soup.find_all(text=lambda text: text and any(keyword in text.lower() 
                                                                     for keyword in ['notification', 'pemberitahuan', 'announcement'])):
                elem.parent.decompose()
            
            self.seen_titles.clear()
            
            # Coba parsing dengan berbagai metode
            items = []
            
            # Metode 1: Parse dari konten utama
            main_content = soup.select_one('.postbody, .listupd, .bixbox, #content, main')
            if main_content:
                items.extend(self._parse_oppa_articles(str(main_content)))
            
            # Metode 2: Parse dari artikel langsung
            if not items:
                items = self._parse_oppa_articles(str(soup))
            
            # Filter tahun unrealistic
            items = self._filter_future_years(items)
            
            # Tambahkan tahun default jika kosong
            items = self._add_default_year_if_missing(items)
            
            # Filter duplikat
            unique_items = self._filter_duplicate_items(items)
            
            if unique_items:
                self.log(f"DEBUG: Found {len(unique_items)} unique items in homepage")
                return {'list': unique_items[:50]}
            
        except Exception as e:
            self.log(f'Error homeVideoContent: {e}')
        
        # Fallback ke kategori terbaru
        try:
            result = self.categoryContent('terbaru', 1, False, {})
            if 'list' in result:
                result['list'] = result['list'][:30]  # Limit to 30 items
                return result
        except:
            pass
        
        return {'list': []}
    
    def _add_default_year_if_missing(self, items):
        """Tambahkan tahun default jika item tidak memiliki tahun"""
        if not items:
            return items
        
        for item in items:
            if not item:
                continue
                
            # Jika tidak ada tahun, tambahkan tahun default
            if not item.get('vod_year'):
                title = item.get('vod_name', '')
                
                # Coba ekstrak tahun dari judul
                year_match = re.search(r'\b(19\d{2}|20\d{2})\b', title)
                if year_match:
                    year = year_match.group(1)
                    if not self._is_unrealistic_year(year):
                        item['vod_year'] = year
                else:
                    # Gunakan tahun default (tahun sebelumnya untuk series lama)
                    item['vod_year'] = str(self.current_year - 1)
        
        return items
    
    def _filter_future_years(self, items):
        """Filter item dengan tahun yang tidak realistic (terlalu jauh ke depan)"""
        if not items:
            return []
        
        filtered_items = []
        for item in items:
            if not item:
                continue
                
            # Cek tahun di vod_year
            year = item.get('vod_year', '')
            if year:
                if self._is_unrealistic_year(year):
                    item['vod_year'] = ''
            
            # Cek tahun di remarks
            remarks = item.get('vod_remarks', '')
            if remarks:
                # Hapus tahun yang unrealistic dari remarks
                years = re.findall(r'\b(20\d{2})\b', remarks)
                for found_year in years:
                    if self._is_unrealistic_year(found_year):
                        remarks = remarks.replace(found_year, 'Upcoming')
                        item['vod_remarks'] = remarks
            
            filtered_items.append(item)
        
        return filtered_items
    
    def _is_unrealistic_year(self, year_str):
        """Cek apakah tahun unrealistic (terlalu jauh ke depan)"""
        try:
            year = int(year_str)
            # Terima tahun dari 1900 sampai 3 tahun ke depan
            if year < 1900 or year > self.current_year + 3:
                return True
        except:
            pass
        return False
    
    def _filter_duplicate_items(self, items):
        """Filter item yang duplikat berdasarkan judul atau URL"""
        if not items:
            return []
        
        unique_items = []
        seen_urls = set()
        seen_titles = set()
        
        for item in items:
            if not item:
                continue
                
            vod_id = item.get('vod_id', '')
            vod_name = item.get('vod_name', '')
            
            # Skip notifikasi
            if vod_id and self._is_notification_link(vod_id):
                continue
            
            if vod_name and self._is_notification_title(vod_name):
                continue
            
            # Gunakan URL sebagai primary key
            url_key = vod_id.lower() if vod_id else ''
            
            # Cek URL
            if url_key and url_key in seen_urls:
                continue
            
            # Cek judul (dengan toleransi similarity)
            title_key = self._normalize_title(vod_name) if vod_name else ''
            if title_key:
                # Cek similarity dengan judul yang sudah ada
                is_duplicate = False
                for seen_title in seen_titles:
                    if self._title_similarity(title_key, seen_title) > 0.8:
                        is_duplicate = True
                        break
                
                if is_duplicate:
                    continue
            
            # Validasi dan tambahkan
            if 'vod_year' in item:
                item['vod_year'] = self._validate_year(item['vod_year'])
            
            unique_items.append(item)
            
            if url_key:
                seen_urls.add(url_key)
            if title_key:
                seen_titles.add(title_key)
        
        return unique_items
    
    def _normalize_title(self, title):
        """Normalisasi judul untuk perbandingan"""
        if not title:
            return ''
        
        # Lowercase
        title = title.lower()
        
        # Hapus karakter spesial
        title = re.sub(r'[^\w\s]', '', title)
        
        # Hapus kata umum
        common_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
        words = title.split()
        words = [w for w in words if w not in common_words]
        
        return ' '.join(words)
    
    def _title_similarity(self, title1, title2):
        """Cek similarity antara dua judul"""
        if not title1 or not title2:
            return 0
        
        # Simple Jaccard similarity
        set1 = set(title1.split())
        set2 = set(title2.split())
        
        if not set1 or not set2:
            return 0
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0
    
    def categoryContent(self, tid, pg, filter, extend):
        try:
            # MAP KATEGORI BERDASARKAN HTML MENU OPPADRAMA
            category_map = {
                # Menu utama
                
                'ongoing': '/series/?status=Ongoing&type=&order=update',
                'completed': '/series/?status=Completed&type=Drama&order=update',  # UPDATED: Ditambah &type=Drama
                
                # Drama categories
                'drama-korea': '/series/?country%5B%5D=south-korea&status=&type=Drama&order=update',
                'drama-china': '/series/?country%5B%5D=china&type=Drama&order=update',
                'drama-thailand': '/series/?country%5B%5D=thailand&status=&type=Drama&order=update',
                'drama-jepang': '/series/?country%5B%5D=japan&type=Drama&order=update',
                'drama-taiwan': '/series/?country%5B%5D=taiwan&status=&type=Drama&order=update',
                'drama-filipina': '/series/?country%5B%5D=philippines&type=Drama&order=update',
                'series-barat': '/series/?country%5B%5D=usa&type=Drama&order=update',
                'netflix': '/network/netflix/',  # UPDATED: Gunakan network/netflix/
                
                # Film categories
                'film-korea': '/series/?country%5B%5D=south-korea&status=&type=Movie&order=update',
                'film-china': '/series/?country%5B%5D=china&type=Movie&order=update',
                'film-hongkong': '/series/?country%5B%5D=hong-kong&type=Movie&order=update',
                'film-thailand': '/series/?country%5B%5D=thailand&status=&type=Movie&order=update',
                'film-jepang': '/series/?country%5B%5D=japan&type=Movie&order=update',
                'film-taiwan': '/series/?country%5B%5D=taiwan&status=&type=Movie&order=update',
                'film-filipina': '/series/?country%5B%5D=philippines&type=Movie&order=update',
                'film-india': '/series/?country%5B%5D=india&status=&type=Movie&order=update',
                'film-barat': '/series/?country%5B%5D=united-states&status=&type=Movie&order=update',  # UPDATED: united-states bukan usa
                
                # Other categories
                'variety-show': '/series/?type=TV+Show&order=update',  # UPDATED: TV+Show bukan Variety
                'animasi': '/series/?page=1&genre%5B0%5D=animation&type=&order=update',
                'jadwal': '/jadwal/',  # UPDATED: Jadwal schedule
                'bookmark': '/bookmark/',  # NEW: Bookmark page
                
                # Kategori umum
                'terbaru': f'/release-year/{self.current_year}/',
                'populer': '/imdb/?imdb=7.5-10',
                'series': '/series/?status=&type=Drama&order=update',  # Semua series
                'movie': '/series/?type=Movie&order=update',
                'anime': '/series/?genre%5B0%5D=animation&type=&order=update'
            }
            
            base_path = category_map.get(tid, '/')
            url = f"{self.site}{base_path}"
            
            # Handle special cases for bookmark and jadwal (external links)
            if tid in ['jadwal', 'bookmark']:
                # These might be external links, use as is
                if base_path.startswith('http'):
                    url = base_path
                else:
                    url = f"{self.site}{base_path}"
            
            if str(pg) != '1' and tid not in ['jadwal', 'bookmark']:  # Skip pagination for schedule and bookmark
                if '?' in url:
                    url += f"&page={pg}"
                else:
                    url += f"page/{pg}/"
            
            self.log(f'Fetching category {tid}: {url}')
            response = self.fetch(url, headers=self.site_headers, timeout=15)
            html = response.text
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Hapus elemen yang tidak perlu
            for elem in soup.select('#sidebar, .widget_text, .announ, .kln, .footercopyright, .mobsearch, script, style, iframe'):
                elem.decompose()
            
            items = self._parse_oppa_articles(str(soup))
            
            # Filter dan proses items
            items = self._filter_future_years(items)
            items = self._add_default_year_if_missing(items)
            unique_items = self._filter_duplicate_items(items)
            
            # Untuk jadwal dan bookmark, mungkin tidak ada item
            if tid in ['jadwal', 'bookmark'] and not unique_items:
                return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 40, 'total': 0}
            
            return {
                'list': unique_items,
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
            if not path:
                return {'list': []}
            
            # Skip jika path adalah notifikasi
            if self._is_notification_link(path):
                self.log(f"Skipping notification path: {path}")
                return {'list': []}
            
            # Decode URL jika diperlukan
            path = unquote(path)
            
            if not path.startswith('http'):
                full_url = f"{self.site}{path}" if path.startswith('/') else f"{self.site}/{path}"
            else:
                full_url = path
            
            cache_key = f"detail_{hash(full_url)}"
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            self.log(f'Fetching detail: {full_url}')
            response = self.fetch(full_url, headers=self.site_headers, timeout=20)
            html = response.text
            
            detail = self._parse_oppa_detail(html, full_url)
            
            # Validasi tahun
            if detail.get('year'):
                detail['year'] = self._validate_year(detail['year'])
            
            # Ambil data TMDB jika ada API key
            if self.tmdb_key and detail.get('title'):
                try:
                    title = detail.get('title', '')
                    year = detail.get('year', '')
                    
                    if title:
                        media_type, tmdb_id = self._tmdb_from_title(title, year)
                        if tmdb_id:
                            v = self.fetch(
                                f'{self.tmdb_host}/{media_type}/{tmdb_id}',
                                params={'api_key': self.tmdb_key, 'language': 'id-ID'},
                                headers=self.tmdb_headers
                            ).json()
                            
                            # Update detail dengan data TMDB
                            if v.get('title') or v.get('name'):
                                detail['title'] = v.get('title') or v.get('name') or detail['title']
                            
                            if not detail['pic'] and v.get('poster_path'):
                                detail['pic'] = f"{self.phost}{v.get('poster_path')}"
                            
                            if v.get('overview'):
                                detail['content'] = v.get('overview') or detail['content']
                            
                            if v.get('original_language'):
                                detail['area'] = v.get('original_language', '').upper()
                            
                            # Validasi tahun dari TMDB
                            release_date = v.get('release_date') or v.get('first_air_date')
                            if release_date:
                                tmdb_year = release_date.split('-')[0]
                                detail['year'] = self._validate_year(tmdb_year)
                except Exception as e:
                    self.log(f"TMDB error: {e}")
            
            # Parse episode
            episodes = self._parse_oppa_episodes(html)
            
            # Format play URL
            play_urls = []
            if episodes:
                sorted_episodes = self._sort_episodes(episodes)
                for ep in sorted_episodes:
                    play_urls.append(f"{ep['name']}${ep['url']}")
                play_str = '#'.join(play_urls)
                detail['remarks'] = f"{len(episodes)} Episode | {detail.get('remarks', '')}"
            else:
                # Jika tidak ada episode, gunakan URL utama
                play_str = f"Play${full_url}"
            
            result = {
                'list': [{
                    'vod_id': path,
                    'vod_name': detail.get('title', 'OPPADRAMA'),
                    'vod_pic': detail.get('pic', ''),
                    'vod_year': detail.get('year', ''),
                    'vod_area': detail.get('area', ''),
                    'vod_remarks': detail.get('remarks', ''),
                    'vod_content': detail.get('content', ''),
                    'vod_play_from': 'OPPADRAMA',
                    'vod_play_url': play_str
                }]
            }
            
            # Cache result
            self.cache[cache_key] = result
            return result
            
        except Exception as e:
            self.log(f'Error detailContent: {e}', level="ERROR")
            return {'list': []}
    
    def searchContent(self, key, quick, pg="1"):
        try:
            if not key or len(key) < 2:
                return {'list': [], 'page': 1, 'pagecount': 1}
                
            search_url = f"{self.site}/?s={quote(key)}"
            if str(pg) != '1':
                search_url += f"&page={pg}"
            
            self.log(f'Searching: {search_url}')
            response = self.fetch(search_url, headers=self.site_headers, timeout=15)
            html = response.text
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Hapus elemen tidak perlu
            for elem in soup.select('#sidebar, .widget_text, .announ, .kln, .footercopyright, script, style'):
                elem.decompose()
            
            items = self._parse_oppa_articles(str(soup))
            
            # Filter dan proses
            items = self._filter_future_years(items)
            items = self._add_default_year_if_missing(items)
            unique_items = self._filter_duplicate_items(items)
            
            return {
                'list': unique_items,
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
            
            response = self.fetch(play_url, headers=self.site_headers, timeout=20)
            html = response.text
            
            video_url, headers = self._parse_oppa_video(html, play_url)
            
            if video_url:
                return {
                    'parse': 0,
                    'url': video_url,
                    'header': headers,
                    'subs': self._get_oppa_subtitles(html)
                }
            
            # Jika tidak ditemukan video, coba cari di embed
            return {
                'parse': 1,
                'url': play_url,
                'header': self._get_oppa_headers(),
                'subs': []
            }
            
        except Exception as e:
            self.log(f'Error playerContent: {e}')
            return {
                'parse': 1,
                'url': id if id.startswith('http') else f"{self.site}{id}",
                'header': self._get_oppa_headers(),
                'subs': []
            }
    
    def localProxy(self, param):
        pass
    
    def _parse_oppa_articles(self, html):
        """Parse semua artikel dari HTML"""
        items = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Cari semua elemen yang mungkin berisi konten
        content_selectors = [
            'article.bs', 'article.stylefor', '.bsx', '.listupd article',
            '.items article', '.list-series article', '.movie-item',
            '.post-item', '.list-item', '.grid-item'
        ]
        
        articles = []
        for selector in content_selectors:
            found = soup.select(selector)
            if found:
                articles.extend(found)
        
        if not articles:
            # Fallback: cari semua article tags
            articles = soup.select('article')
        
        for article in articles[:100]:  # Limit untuk performa
            try:
                item = self._parse_oppa_article(article)
                if item:
                    items.append(item)
            except Exception as e:
                self.log(f"Error parsing article: {e}")
                continue
        
        return items
    
    def _parse_oppa_article(self, article):
        """Parse single artikel OPPADRAMA"""
        try:
            # Cari link
            link_elem = article.select_one('a[href]')
            if not link_elem:
                return None
            
            href = link_elem.get('href', '').strip()
            if not href:
                return None
            
            # Skip link yang jelas bukan konten
            if self._is_bad_link(href):
                return None
            
            # Ambil judul
            title = ''
            title_selectors = [
                '.tt h2', 'h2[itemprop="headline"]', '.ttt .tt', 
                'h2', '.tt h3', 'h3', '.title h3', '.tt',
                'h4', '.entry-title', '.post-title', '.movie-title'
            ]
            
            for selector in title_selectors:
                title_elem = article.select_one(selector)
                if title_elem and title_elem.text.strip():
                    title = title_elem.text.strip()
                    break
            
            # Fallback: cari dari alt text gambar
            if not title:
                img_elem = article.select_one('img')
                if img_elem and img_elem.get('alt'):
                    title = img_elem.get('alt', '').strip()
            
            # Fallback: cari dari title attribute
            if not title and link_elem.get('title'):
                title = link_elem.get('title', '').strip()
            
            if not title:
                return None
            
            # Skip judul notifikasi
            if self._is_notification_title(title):
                return None
            
            # Ambil gambar
            img_src = ''
            img_elem = article.select_one('img')
            if img_elem:
                img_src = (img_elem.get('src') or 
                          img_elem.get('data-src') or 
                          img_elem.get('data-cfsrc') or 
                          img_elem.get('data-lazy-src') or '')
            
            # Cari tahun
            year = self._extract_year_from_element(article)
            
            # Jika tidak ada tahun, coba dari URL
            if not year:
                url_year_match = re.search(r'/(\d{4})/', href)
                if url_year_match:
                    potential_year = url_year_match.group(1)
                    if not self._is_unrealistic_year(potential_year):
                        year = potential_year
            
            # Ambil remarks/status
            remarks = ''
            ep_selectors = ['.epx', '.bt span', '.typez', '.quality', '.status', 
                           '.num', '.episode', '.eps', '.ep', '.limit', '.year']
            
            for selector in ep_selectors:
                ep_elem = article.select_one(selector)
                if ep_elem and ep_elem.text.strip():
                    text = ep_elem.text.strip()
                    # Hapus tahun dari remarks jika ada
                    text = re.sub(r'\b(19\d{2}|20\d{2})\b', '', text).strip()
                    if text:
                        remarks = text
                        break
            
            # Hapus pipe dan trim
            if remarks:
                remarks = re.sub(r'^\||\|$', '', remarks).strip()
            
            # Clean title
            title = self._clean_html_text(title)
            
            return {
                'vod_id': self._make_relative_path(href),
                'vod_name': title[:200],
                'vod_pic': self._abs_url_oppa(img_src),
                'vod_year': year,
                'vod_remarks': remarks[:100]
            }
            
        except Exception as e:
            self.log(f"Error parsing article: {e}")
            return None
    
    def _extract_year_from_element(self, element):
        """Ekstrak tahun dari element HTML"""
        if not element:
            return ""
        
        # Cari di text content
        text = element.get_text()
        year_match = re.search(r'\b(19\d{2}|20\d{2})\b', text)
        if year_match:
            year = year_match.group(1)
            if not self._is_unrealistic_year(year):
                return year
        
        # Cari di class dan id
        element_str = str(element)
        year_match = re.search(r'year-(\d{4})', element_str, re.IGNORECASE)
        if year_match:
            year = year_match.group(1)
            if not self._is_unrealistic_year(year):
                return year
        
        return ""
    
    def _parse_oppa_detail(self, html, url):
        """Parse detail page OPPADRAMA"""
        result = {
            'title': '',
            'pic': '',
            'year': '',
            'area': '',
            'remarks': '',
            'content': ''
        }
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Ambil judul
            title_selectors = [
                'h1.entry-title', 'h1.title', 'h1.post-title', 
                '.entry-title', '.title', '.post-title',
                'h1', '.movie-title h1', '.series-title h1'
            ]
            
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem and title_elem.text.strip():
                    result['title'] = title_elem.text.strip()
                    break
            
            # Fallback: meta og:title
            if not result['title']:
                meta_title = soup.find('meta', property='og:title')
                if meta_title:
                    result['title'] = meta_title.get('content', '').split('|')[0].strip()
            
            # Ambil gambar
            img_selectors = [
                '.poster img', '.thumbnail img', '.featured-img img',
                '.movie-poster img', '.series-poster img', 
                'meta[property="og:image"]'
            ]
            
            for selector in img_selectors:
                if selector.startswith('meta'):
                    meta_img = soup.select_one(selector)
                    if meta_img:
                        result['pic'] = meta_img.get('content', '')
                        break
                else:
                    img_elem = soup.select_one(selector)
                    if img_elem:
                        result['pic'] = img_elem.get('src') or img_elem.get('data-src') or ''
                        break
            
            # Cari tahun
            year_patterns = [
                r'Tahun.*?[:]?\s*(\d{4})',
                r'Year.*?[:]?\s*(\d{4})',
                r'Release.*?[:]?\s*(\d{4})',
                r'Rilis.*?[:]?\s*(\d{4})',
                r'Released.*?[:]?\s*(\d{4})',
                r'\b(\d{4})\s+Movie',
                r'\bMovie\s+(\d{4})',
                r'\b(\d{4})\s+Drama',
                r'\bDrama\s+(\d{4})'
            ]
            
            # Cari di metadata
            metadata_selectors = ['.metadata', '.info', '.details', '.specs', '.infox']
            for selector in metadata_selectors:
                meta_elem = soup.select_one(selector)
                if meta_elem:
                    meta_text = meta_elem.get_text()
                    for pattern in year_patterns:
                        year_match = re.search(pattern, meta_text, re.IGNORECASE)
                        if year_match:
                            year = year_match.group(1)
                            if not self._is_unrealistic_year(year):
                                result['year'] = year
                                break
                    if result['year']:
                        break
            
            # Cari di seluruh page
            if not result['year']:
                for pattern in year_patterns:
                    year_match = re.search(pattern, html, re.IGNORECASE)
                    if year_match:
                        year = year_match.group(1)
                        if not self._is_unrealistic_year(year):
                            result['year'] = year
                            break
            
            # Cari dari judul
            if not result['year']:
                year_match = re.search(r'\b(20\d{2})\b', result['title'])
                if year_match:
                    year = year_match.group(1)
                    if not self._is_unrealistic_year(year):
                        result['year'] = year
            
            # Default tahun
            if not result['year']:
                result['year'] = str(self.current_year - 1)
            
            # Ambil area/negara
            area_map = {
                'korea': 'KR', 'korean': 'KR', 'south korea': 'KR',
                'china': 'CN', 'chinese': 'CN', 'mandarin': 'CN',
                'thailand': 'TH', 'thai': 'TH',
                'japan': 'JP', 'japanese': 'JP',
                'indonesia': 'ID', 'indonesian': 'ID',
                'taiwan': 'TW', 'taiwanese': 'TW',
                'philippines': 'PH', 'filipina': 'PH',
                'india': 'IN', 'indian': 'IN',
                'hong kong': 'HK', 'hongkong': 'HK',
                'usa': 'US', 'united states': 'US', 'america': 'US'
            }
            
            # Cari di genre/country links
            for elem in soup.select('a[href*="country"], a[href*="genre"], .infox a, .genre a'):
                text = elem.text.lower()
                for key, code in area_map.items():
                    if key in text:
                        result['area'] = code
                        break
                if result['area']:
                    break
            
            # Ambil remarks
            remarks_parts = []
            status_selectors = ['.status', '.completed', '.ongoing', '.quality', '.hd', '.rating']
            for selector in status_selectors:
                elem = soup.select_one(selector)
                if elem and elem.text.strip():
                    text = elem.text.strip()
                    # Hapus tahun dari remarks
                    text = re.sub(r'\b(19\d{2}|20\d{2})\b', '', text).strip()
                    if text:
                        remarks_parts.append(text)
            
            result['remarks'] = ' | '.join(remarks_parts[:3])  # Max 3 parts
            
            # Ambil sinopsis
            content_selectors = [
                '.entry-content', '.description', '.sinopsis', '.plot',
                '.infox .content', '.bigcontent .infox', '.wp-content',
                '.summary', '.synopsis', '.storyline'
            ]
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    text = content_elem.text.strip()
                    if len(text) > 100:  # Minimal 100 karakter
                        result['content'] = self._clean_html_text(text[:1000])
                        break
            
            # Clean semua teks
            result['title'] = self._clean_html_text(result['title'])
            result['content'] = self._clean_html_text(result['content'])
            result['remarks'] = self._clean_html_text(result['remarks'])
            
        except Exception as e:
            self.log(f'Error _parse_oppa_detail: {e}')
        
        return result
    
    def _parse_oppa_episodes(self, html):
        """Parse episode list dari halaman drama"""
        episodes = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Cari container episode
            episode_containers = [
                '.episode-list', '.list-episode', '.episodes',
                '.eplister', '.epwrap', '.episodelist',
                '#chapterlist', '.season', '.episode-area',
                '.episode-container', '.eplist', '.listeps',
                '.epgrid', '.episode-grid', '.eps-list'
            ]
            
            container = None
            for selector in episode_containers:
                container = soup.select_one(selector)
                if container:
                    break
            
            # Jika tidak ditemukan, cari semua links dengan pattern episode
            if not container:
                all_links = soup.select('a[href]')
                episode_links = []
                
                for link in all_links:
                    href = link.get('href', '').lower()
                    text = link.text.strip().lower()
                    
                    # Cek pattern episode
                    ep_patterns = [
                        r'/episode-', r'/eps-', r'/ep-',
                        r'/\d+-episode-', r'/\d+-eps-', r'/\d+-ep-',
                        r'episode\s*\d+', r'eps\s*\d+', r'ep\.?\s*\d+'
                    ]
                    
                    is_episode = False
                    for pattern in ep_patterns:
                        if re.search(pattern, href) or re.search(pattern, text):
                            is_episode = True
                            break
                    
                    if is_episode and not self._is_bad_link(href):
                        episode_links.append(link)
                
                if episode_links:
                    container = soup.new_tag('div')
                    for link in episode_links[:100]:  # Limit 100 episode
                        container.append(link)
            
            if not container:
                return episodes
            
            # Parse episode dari container
            episode_items = container.select('a[href], li a, .episode-item a, .eps-item a')
            if not episode_items:
                episode_items = container.select('a[href]')
            
            for ep_elem in episode_items[:150]:  # Max 150 episode
                try:
                    ep_url = ep_elem.get('href', '').strip()
                    if not ep_url:
                        continue
                    
                    # Skip bad links
                    if self._is_bad_link(ep_url):
                        continue
                    
                    ep_text = ep_elem.text.strip()
                    if not ep_text:
                        # Coba dari alt atau title
                        ep_text = (ep_elem.get('title') or 
                                  ep_elem.get('alt') or 
                                  ep_elem.get('data-title') or 'Episode')
                    
                    # Format nama episode (hanya angka)
                    episode_name = self._format_episode_name(ep_text)
                    
                    episodes.append({
                        'name': episode_name,
                        'url': self._make_relative_path(ep_url),
                        'original_text': ep_text
                    })
                    
                except Exception as e:
                    continue
            
            self.log(f"Parsed {len(episodes)} episodes")
            
        except Exception as e:
            self.log(f'Error parsing episodes: {e}')
        
        return episodes
    
    def _format_episode_name(self, text):
        """Format nama episode HANYA ANGKA saja"""
        if not text:
            return "1"
        
        text = text.lower()
        
        # Pattern: Episode 24, Eps 24, Ep. 24, etc
        patterns = [
            r'(?:episode|eps|ep\.|ep)\s*(\d+)',
            r'ep\s*(\d+)',
            r'eps\s*(\d+)',
            r'bagian\s*(\d+)',
            r'part\s*(\d+)',
            r'#\s*(\d+)',
            r'(\d+)\s*(?:end|finale)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        # Cari angka pertama
        numbers = re.findall(r'\d+', text)
        if numbers:
            return numbers[0]
        
        return "1"
    
    def _sort_episodes(self, episodes):
        """Mengurutkan episode dari 1 ke atas"""
        if not episodes:
            return []
        
        def extract_ep_number(ep):
            name = ep.get('name', '')
            
            # Coba parse dari name
            if name.isdigit():
                return int(name)
            
            # Coba dari original text
            original = ep.get('original_text', '').lower()
            patterns = [
                r'(?:episode|eps|ep\.|ep)\s*(\d+)',
                r'ep\s*(\d+)',
                r'eps\s*(\d+)',
                r'\b(\d+)\b'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, original)
                if match:
                    try:
                        return int(match.group(1))
                    except:
                        continue
            
            return 99999  # Default untuk yang tidak bisa di-parse
        
        # Sort berdasarkan nomor episode
        try:
            sorted_episodes = sorted(episodes, key=extract_ep_number)
        except:
            sorted_episodes = episodes
        
        # Hapus original_text
        for ep in sorted_episodes:
            if 'original_text' in ep:
                del ep['original_text']
        
        return sorted_episodes
    
    def _parse_oppa_video(self, html, referer):
        """Parse video URL dari halaman OPPADRAMA"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Cari iframe
            iframe_selectors = [
                'iframe[src*="embed"]', 'iframe[src*="player"]',
                'iframe[src*="video"]', 'iframe[src*="stream"]',
                'iframe[src*="play"]', 'iframe[src*="watch"]'
            ]
            
            for selector in iframe_selectors:
                iframe = soup.select_one(selector)
                if iframe:
                    iframe_src = iframe.get('src', '')
                    if iframe_src:
                        if not iframe_src.startswith('http'):
                            iframe_src = urljoin(referer, iframe_src)
                        
                        self.log(f"Found iframe: {iframe_src}")
                        
                        # Coba fetch iframe content
                        try:
                            iframe_html = self.fetch(iframe_src, headers={
                                **self.site_headers,
                                'referer': referer
                            }, timeout=15).text
                            
                            # Cari video di iframe
                            video_url = self._find_video_in_html(iframe_html)
                            if video_url:
                                return video_url, {
                                    'User-Agent': self.site_headers['User-Agent'],
                                    'Referer': iframe_src,
                                    'Origin': urlparse(iframe_src).scheme + '://' + urlparse(iframe_src).netloc
                                }
                        except Exception as e:
                            self.log(f"Error fetching iframe: {e}")
                            continue
            
            # Cari video langsung di halaman
            video_url = self._find_video_in_html(html)
            if video_url:
                return video_url, {
                    'User-Agent': self.site_headers['User-Agent'],
                    'Referer': referer
                }
            
        except Exception as e:
            self.log(f'Error _parse_oppa_video: {e}')
        
        return None, None
    
    def _find_video_in_html(self, html):
        """Cari URL video dalam HTML"""
        # Pattern untuk video
        video_patterns = [
            r'file\s*:\s*["\']([^"\']+\.(?:m3u8|mp4|mkv|avi|mov|flv|webm)[^"\']*)["\']',
            r'src\s*:\s*["\']([^"\']+\.(?:m3u8|mp4|mkv|avi|mov|flv|webm)[^"\']*)["\']',
            r'video_url\s*:\s*["\']([^"\']+\.(?:m3u8|mp4|mkv|avi|mov|flv|webm)[^"\']*)["\']',
            r'url\s*:\s*["\']([^"\']+\.(?:m3u8|mp4|mkv|avi|mov|flv|webm)[^"\']*)["\']',
            r'(https?://[^\s"\']+\.(?:m3u8|mp4|mkv|avi|mov|flv|webm)[^\s"\']*)',
            r'data-video="([^"]+)"',
            r'data-src="([^"]+)"'
        ]
        
        for pattern in video_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                if match and 'google' not in match.lower() and 'youtube' not in match.lower():
                    return match
        
        # Cari source tag
        soup = BeautifulSoup(html, 'html.parser')
        source_tags = soup.select('source[src]')
        for source in source_tags:
            src = source.get('src', '')
            if src and self.isVideoFormat(src):
                return src
        
        return None
    
    def _get_oppa_subtitles(self, html):
        """Parse subtitle dari HTML"""
        subtitles = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Cari track elements
            track_elements = soup.select('track[srclang]')
            for track in track_elements:
                src = track.get('src', '')
                label = track.get('label', '')
                lang = track.get('srclang', '')
                
                if src:
                    if not src.startswith('http'):
                        src = urljoin(self.site, src)
                    
                    subtitles.append({
                        'url': src,
                        'name': f'Subtitle {label or lang.upper()}',
                        'lang': lang or 'en',
                        'format': 'text/vtt' if src.endswith('.vtt') else 'application/x-subrip'
                    })
            
            # Cari di script
            sub_patterns = [
                r'subtitle.*?src=["\']([^"\']+\.(?:srt|vtt|ass))["\']',
                r'track.*?src=["\']([^"\']+\.(?:srt|vtt|ass))["\']',
                r'file.*?label.*?sub.*?file.*?["\']([^"\']+\.(?:srt|vtt|ass))["\']'
            ]
            
            for pattern in sub_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for sub_url in matches:
                    if sub_url:
                        if sub_url.startswith('//'):
                            sub_url = 'https:' + sub_url
                        elif not sub_url.startswith('http'):
                            sub_url = urljoin(self.site, sub_url)
                        
                        lang = self._detect_subtitle_language(sub_url)
                        
                        subtitles.append({
                            'url': sub_url,
                            'name': f'Subtitle {lang.upper()}',
                            'lang': lang,
                            'format': 'application/x-subrip' if sub_url.endswith('.srt') else 'text/vtt'
                        })
            
        except Exception as e:
            self.log(f"Error getting subtitles: {e}")
        
        return subtitles
    
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
            '/contact', '/about', '/donate'
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
            '/channel', '/broadcast', '/info=', '/notif=',
            '/announce=', '/pemberitahuan='
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
            'info:', 'update:', 'important:',
            'pemberitahuan penting', 'important announcement'
        ]
        
        if any(keyword in title_lower for keyword in notification_keywords):
            return True
        
        # Cek pattern
        patterns = [
            r'pemberitahuan\s*\d+',
            r'notif\s*\d+',
            r'update\s*:\s*',
            r'info\s*:\s*',
            r'penting\s*:\s*',
            r'alert\s*:\s*'
        ]
        
        for pattern in patterns:
            if re.search(pattern, title_lower):
                return True
        
        return False
    
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
            if parsed.netloc and parsed.netloc in ['oppa.biz', 'www.oppa.biz', 'oppadrama.biz', '45.11.57.125']:
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
        """Clean HTML text"""
        if not text:
            return ''
        
        try:
            # Unescape HTML entities
            text = htmlmod.unescape(text)
            
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', ' ', text)
            
            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', text)
            
            # Remove control characters
            text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
            
            return text.strip()
            
        except:
            return text or ''
    
    def _get_oppa_headers(self):
        """Get headers for OPPADRAMA"""
        headers = self.site_headers.copy()
        
        # Remove sensitive headers
        for header in ['authorization', 'cookie']:
            if header in headers:
                del headers[header]
        
        return headers
    
    def _detect_subtitle_language(self, url):
        """Detect subtitle language from URL or filename"""
        if not url:
            return 'id'
        
        url_lower = url.lower()
        
        lang_map = {
            'indonesia': 'id', 'indonesian': 'id', 'ind': 'id', 'idn': 'id',
            'english': 'en', 'eng': 'en', 'en.': 'en', 'us': 'en',
            'chinese': 'zh', 'chi': 'zh', 'zh-cn': 'zh', 'cn': 'zh',
            'korean': 'ko', 'kor': 'ko', 'kr': 'ko', 'kor.': 'ko',
            'japanese': 'ja', 'jap': 'ja', 'jp': 'ja', 'jpn': 'ja',
            'thai': 'th', 'thailand': 'th', 'th.': 'th',
            'vietnamese': 'vi', 'vie': 'vi', 'vn': 'vi',
            'spanish': 'es', 'spa': 'es', 'es.': 'es',
            'arabic': 'ar', 'ara': 'ar', 'ar.': 'ar',
            'taiwan': 'tw', 'taiwanese': 'tw',
            'filipina': 'ph', 'philippines': 'ph',
            'india': 'in', 'indian': 'in'
        }
        
        for key, lang in lang_map.items():
            if key in url_lower:
                return lang
        
        return 'id'
    
    def _tmdb_from_title(self, title, year=''):
        """Search TMDB by title"""
        if not self.tmdb_key or not title:
            return None, None
            
        try:
            # Cari dulu sebagai TV series
            params = {
                'query': title,
                'api_key': self.tmdb_key,
                'language': 'id-ID',
                'page': 1,
                'include_adult': 'false'
            }
            
            if year:
                params['first_air_date_year'] = year
            
            response = self.fetch(
                f'{self.tmdb_host}/search/tv',
                params=params,
                headers=self.tmdb_headers,
                timeout=10
            ).json()
            
            if response.get('results'):
                result = response['results'][0]
                return 'tv', result.get('id')
            
            # Jika tidak ditemukan sebagai TV, cari sebagai movie
            if year:
                params['year'] = year
                del params['first_air_date_year']
            
            response = self.fetch(
                f'{self.tmdb_host}/search/movie',
                params=params,
                headers=self.tmdb_headers,
                timeout=10
            ).json()
            
            if response.get('results'):
                result = response['results'][0]
                return 'movie', result.get('id')
                
        except Exception as e:
            self.log(f"TMDB search error: {e}")
        
        return None, None
    
    def _validate_year(self, year_str):
        """Validasi tahun yang realistic"""
        try:
            year = int(year_str)
            # Batasi tahun dari 1900 sampai 3 tahun ke depan
            if 1900 <= year <= self.current_year + 3:
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