# -*- coding: utf-8 -*-
import re, sys, os, requests, json, datetime, random, time, base64
from urllib.parse import urlparse, urljoin, quote, unquote, parse_qs, urlencode
from bs4 import BeautifulSoup
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.site = 'https://anichin.watch'
        
        self.site_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': f'{self.site}/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        
        self.cache = {}
        self.session = requests.Session()
        
        # Mapping kategori
        self.category_map = {
            'home': '/',
            'ongoing': '/ongoing/',
            'completed': '/completed/',
            'movie': '/anime/?type=Movie&order=update',
            'action': '/genres/action/',
            'adventure': '/genres/adventure/',
            'cultivation': '/genres/cultivation/',
            'fantasy': '/genres/fantasy/',
            'martial-arts': '/genres/martial-arts/',
            'romance': '/genres/romance/',
            'comedy': '/genres/comedy/',
            'drama': '/genres/drama/',
            'historical': '/genres/historical/',
            'mystery': '/genres/mystery/',
            'psychological': '/genres/psychological/',
            'reincarnation': '/genres/reincarnation/',
            'sci-fi': '/genres/sci-fi/',
            'super-power': '/genres/super-power/',
            'supernatural': '/genres/supernatural/',
            'urban-fantasy': '/genres/urban-fantasy/',
            'harem': '/genres/harem/',
            'school': '/genres/school/',
            'slice-of-life': '/genres/slice-of-life/',
            '2026': '/season/2026/',
            '2025': '/season/2025/',
            '2024': '/season/2024/',
            '2023': '/season/2023/',
        }
        
        self.log("✅ ANICHIN Spider Final Version initialized")
    
    def getName(self):
        return "🐉 ANICHIN"
    
    def isVideoFormat(self, url):
        return any(ext in url.lower() for ext in ['.m3u8', '.mp4', '.mkv', '.avi'])
    
    def manualVideoCheck(self):
        return True
    
    def homeContent(self, filter):
        return {
            'class': [
                
                {'type_name': '▶️ Ongoing', 'type_id': 'ongoing'},
                {'type_name': '✅ Completed', 'type_id': 'completed'},
                {'type_name': '🎬 Movie', 'type_id': 'movie'},
                {'type_name': '⚔️ Action', 'type_id': 'action'},
                {'type_name': '🌿 Cultivation', 'type_id': 'cultivation'},
                {'type_name': '🎋 Fantasy', 'type_id': 'fantasy'},
                {'type_name': '⚡ Martial Arts', 'type_id': 'martial-arts'},
                {'type_name': '💕 Romance', 'type_id': 'romance'},
                {'type_name': '😂 Comedy', 'type_id': 'comedy'},
                {'type_name': '🎭 Drama', 'type_id': 'drama'},
                {'type_name': '🔍 Mystery', 'type_id': 'mystery'},
                {'type_name': '🧠 Psychological', 'type_id': 'psychological'},
                {'type_name': '🤖 Sci-Fi', 'type_id': 'sci-fi'},
                {'type_name': '👻 Supernatural', 'type_id': 'supernatural'},
                {'type_name': '🏫 School', 'type_id': 'school'},
                {'type_name': '👥 Harem', 'type_id': 'harem'},
                {'type_name': '2026', 'type_id': '2026'},
                {'type_name': '2025', 'type_id': '2025'},
                {'type_name': '2024', 'type_id': '2024'},
                {'type_name': '2023', 'type_id': '2023'},
            ],
            'filters': {}
        }
    
    def homeVideoContent(self):
        try:
            if 'home' in self.cache:
                return self.cache['home']
            
            self.log("Fetching home page...")
            html = self.fetch(self.site).text
            soup = BeautifulSoup(html, 'html.parser')
            
            items = []
            seen = set()
            
            # Ambil dari Latest Release
            listupd = soup.find('div', class_='listupd')
            if listupd:
                for article in listupd.find_all('article', class_='bs'):
                    try:
                        link = article.find('a', href=True)
                        if not link:
                            continue
                        
                        href = link.get('href')
                        if not href or href in seen:
                            continue
                        
                        # Judul
                        title = ''
                        tt_div = article.find('div', class_='tt')
                        if tt_div:
                            title = tt_div.text.strip()
                        
                        h2_tag = article.find('h2', itemprop='headline')
                        if h2_tag and not title:
                            title = h2_tag.text.strip()
                        
                        if not title:
                            title = link.get('title', '')
                        
                        if not title:
                            continue
                        
                        title = re.sub(r'\s*(?:Subtitle|Sub|Indonesia|Indo).*$', '', title, flags=re.I)
                        title = title.strip()
                        
                        # Gambar
                        img_url = ''
                        limit_div = article.find('div', class_='limit')
                        if limit_div:
                            img = limit_div.find('img')
                            if img:
                                img_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or ''
                                if img_url:
                                    if img_url.startswith('//'):
                                        img_url = 'https:' + img_url
                                    elif img_url.startswith('/'):
                                        img_url = self.site + img_url
                        
                        if not img_url:
                            img = article.find('img')
                            if img:
                                img_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or ''
                                if img_url:
                                    if img_url.startswith('//'):
                                        img_url = 'https:' + img_url
                                    elif img_url.startswith('/'):
                                        img_url = self.site + img_url
                        
                        # Remarks dengan episode
                        remarks = ''
                        
                        # Status
                        status_div = article.find('div', class_='status')
                        if status_div:
                            remarks = status_div.text.strip()
                        
                        # Episode
                        epx = article.find('span', class_='epx')
                        if epx and epx.text.strip():
                            ep_text = epx.text.strip()
                            ep_match = re.search(r'(\d+)', ep_text)
                            if ep_match:
                                ep_num = ep_match.group(1)
                                if remarks:
                                    remarks = f"{remarks} • Ep {ep_num}"
                                else:
                                    remarks = f"Ep {ep_num}"
                            else:
                                if ep_text and not remarks:
                                    remarks = ep_text
                        
                        # Sub badge
                        sb_span = article.find('span', class_='sb')
                        if sb_span and 'Sub' in sb_span.text:
                            if remarks:
                                remarks += ' [Sub]'
                            else:
                                remarks = 'Sub'
                        
                        if not remarks:
                            remarks = 'Ongoing'
                        
                        item = {
                            'vod_id': href,
                            'vod_name': title,
                            'vod_pic': img_url or 'https://via.placeholder.com/200x300?text=No+Image',
                            'vod_remarks': remarks
                        }
                        
                        seen.add(href)
                        items.append(item)
                        
                    except Exception as e:
                        continue
            
            self.log(f"Found {len(items)} items")
            result = {'list': items}
            self.cache['home'] = result
            return result
            
        except Exception as e:
            self.log(f"Home error: {e}")
            return {'list': []}
    
    def categoryContent(self, tid, pg, filter, extend):
        try:
            if tid in self.category_map and self.category_map[tid]:
                url = self.site + self.category_map[tid]
            else:
                url = self.site + '/'
            
            if int(pg) > 1:
                if '/page/' in url:
                    url = re.sub(r'/page/\d+', f'/page/{pg}', url)
                elif '?' in url:
                    base_url, query = url.split('?', 1)
                    url = f"{base_url}?page={pg}&{query}"
                else:
                    if url.endswith('/'):
                        url = f"{url}page/{pg}/"
                    else:
                        url = f"{url}/page/{pg}/"
            
            self.log(f"Fetching category '{tid}' page {pg}: {url}")
            
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
                    
                    # Judul
                    title = ''
                    tt_div = article.find('div', class_='tt')
                    if tt_div:
                        title = tt_div.text.strip()
                    
                    if not title:
                        title = link.get('title', '')
                    
                    if not title:
                        continue
                    
                    title = re.sub(r'\s*(?:Subtitle|Sub|Indonesia|Indo).*$', '', title, flags=re.I)
                    title = title.strip()
                    
                    # Gambar
                    img_url = ''
                    limit_div = article.find('div', class_='limit')
                    if limit_div:
                        img = limit_div.find('img')
                        if img:
                            img_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or ''
                            if img_url:
                                if img_url.startswith('//'):
                                    img_url = 'https:' + img_url
                                elif img_url.startswith('/'):
                                    img_url = self.site + img_url
                    
                    if not img_url:
                        img = article.find('img')
                        if img:
                            img_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or ''
                            if img_url:
                                if img_url.startswith('//'):
                                    img_url = 'https:' + img_url
                                elif img_url.startswith('/'):
                                    img_url = self.site + img_url
                    
                    # Remarks dengan episode
                    remarks = ''
                    
                    # Status
                    status_div = article.find('div', class_='status')
                    if status_div:
                        remarks = status_div.text.strip()
                    
                    # Episode
                    epx = article.find('span', class_='epx')
                    if epx:
                        ep_text = epx.text.strip()
                        ep_match = re.search(r'(\d+)', ep_text)
                        if ep_match:
                            ep_num = ep_match.group(1)
                            if remarks:
                                remarks = f"{remarks} • Ep {ep_num}"
                            else:
                                remarks = f"Ep {ep_num}"
                        else:
                            if ep_text and not remarks:
                                remarks = ep_text
                    
                    # Sub badge
                    sb_span = article.find('span', class_='sb')
                    if sb_span and 'Sub' in sb_span.text:
                        if remarks:
                            remarks += ' [Sub]'
                        else:
                            remarks = 'Sub'
                    
                    if not remarks:
                        remarks = 'Ongoing'
                    
                    item = {
                        'vod_id': href,
                        'vod_name': title,
                        'vod_pic': img_url or 'https://via.placeholder.com/200x300?text=No+Image',
                        'vod_remarks': remarks
                    }
                    
                    seen.add(href)
                    items.append(item)
                    
                except Exception as e:
                    continue
            
            # Pagination
            total_pages = int(pg)
            hpage = soup.find('div', class_='hpage')
            if hpage:
                for link in hpage.find_all('a'):
                    link_text = link.text.strip()
                    if link_text.isdigit():
                        page_num = int(link_text)
                        if page_num > total_pages:
                            total_pages = page_num
                
                next_link = hpage.find('a', class_='r') or hpage.find('a', string=re.compile(r'Next|›|»', re.I))
                if next_link and total_pages == int(pg):
                    total_pages = int(pg) + 1
            
            if total_pages == int(pg) and len(items) > 0:
                if int(pg) == 1:
                    total_pages = 5
                else:
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
            
            # Cek dari breadcrumb
            breadcrumb = soup.find('div', class_='ts-breadcrumb')
            if breadcrumb:
                links = breadcrumb.find_all('a')
                for i, link in enumerate(links):
                    href = link.get('href', '')
                    if i == 1 and href and ('donghua/' in href or '/anime/' in href):
                        series_url = href
                        is_episode_page = True
                        self.log(f"Found series URL: {series_url}")
                        break
            
            # Jika halaman episode, fetch halaman series
            if is_episode_page and series_url != url:
                if not series_url.startswith('http'):
                    series_url = self.site + series_url if series_url.startswith('/') else self.site + '/' + series_url
                
                self.log(f"Fetching series page: {series_url}")
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
                thumb_div = soup.find('div', class_='thumb')
                if thumb_div:
                    img_tag = thumb_div.find('img')
                    if img_tag:
                        img = img_tag.get('src') or img_tag.get('data-src') or ''
            if not img:
                img_elem = soup.find('img', class_='wp-post-image')
                if img_elem:
                    img = img_elem.get('src') or img_elem.get('data-src') or ''
            
            if img:
                if img.startswith('//'):
                    img = 'https:' + img
                elif img.startswith('/'):
                    img = self.site + img
                img = re.sub(r'\?resize=[^&]+', '', img)
            else:
                img = 'https://via.placeholder.com/200x300?text=No+Image'
            
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
            
            # === AMBIL EPISODE DARI EPLISTER ===
            episodes = []
            
            # Cari di div.eplister
            eplister = soup.find('div', class_='eplister')
            if eplister:
                episode_items = eplister.find_all('li')
                self.log(f"Found eplister with {len(episode_items)} episodes")
                
                for item in episode_items:
                    link = item.find('a', href=True)
                    if not link:
                        continue
                    
                    ep_href = link.get('href')
                    
                    # Ambil nomor episode dari div.epl-num
                    ep_num_div = item.find('div', class_='epl-num')
                    if ep_num_div:
                        ep_num = ep_num_div.text.strip()
                        # Bersihkan dari karakter non-digit
                        ep_num = re.sub(r'[^0-9]', '', ep_num)
                        if ep_num and ep_num.isdigit():
                            ep_num = str(int(ep_num))  # Hapus leading zero
                            episodes.append((int(ep_num), f"{ep_num}${ep_href}"))
                            self.log(f"  Episode {ep_num}")
            
            # Urutkan episode
            if episodes:
                episodes.sort(key=lambda x: x[0])
                final_episodes = [ep[1] for ep in episodes]
                self.log(f"Total episodes: {len(final_episodes)}")
                episodes = final_episodes
            
            # Fallback
            if not episodes:
                self.log("No episodes found, using fallback")
                ep_num_match = re.search(r'episode[-\s]*(\d+)', url, re.I)
                if ep_num_match:
                    ep_num = ep_num_match.group(1)
                    episodes.append(f"{ep_num}${url}")
                else:
                    episodes.append(f"1${url}")
            
            play_url = '#'.join(episodes)
            
            # Status
            status = 'Ongoing'
            status_span = soup.find('span', text=re.compile(r'Status:', re.I))
            if status_span:
                status_text = status_span.find_next('span')
                if status_text:
                    status = status_text.text.strip()
            
            result = {
                'list': [{
                    'vod_id': series_url if is_episode_page else url,
                    'vod_name': title or 'Unknown',
                    'vod_pic': img,
                    'vod_year': year,
                    'vod_content': desc,
                    'vod_remarks': status,
                    'vod_play_from': 'ANICHIN',
                    'vod_play_url': play_url
                }]
            }
            
            return result
            
        except Exception as e:
            self.log(f"Detail error: {e}")
            return {'list': []}
    
    def searchContent(self, key, quick, pg="1"):
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
                    
                    title = ''
                    tt_div = article.find('div', class_='tt')
                    if tt_div:
                        title = tt_div.text.strip()
                    
                    if not title:
                        title = link.get('title', '')
                    
                    if not title:
                        continue
                    
                    title = re.sub(r'\s*(?:Subtitle|Sub|Indonesia|Indo).*$', '', title, flags=re.I)
                    title = title.strip()
                    
                    img_url = ''
                    limit_div = article.find('div', class_='limit')
                    if limit_div:
                        img = limit_div.find('img')
                        if img:
                            img_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or ''
                            if img_url:
                                if img_url.startswith('//'):
                                    img_url = 'https:' + img_url
                                elif img_url.startswith('/'):
                                    img_url = self.site + img_url
                    
                    # Remarks dengan episode
                    remarks = ''
                    
                    # Status
                    status_div = article.find('div', class_='status')
                    if status_div:
                        remarks = status_div.text.strip()
                    
                    # Episode
                    epx = article.find('span', class_='epx')
                    if epx:
                        ep_text = epx.text.strip()
                        ep_match = re.search(r'(\d+)', ep_text)
                        if ep_match:
                            ep_num = ep_match.group(1)
                            if remarks:
                                remarks = f"{remarks} • Ep {ep_num}"
                            else:
                                remarks = f"Ep {ep_num}"
                        else:
                            if ep_text and not remarks:
                                remarks = ep_text
                    
                    # Sub badge
                    sb_span = article.find('span', class_='sb')
                    if sb_span and 'Sub' in sb_span.text:
                        if remarks:
                            remarks += ' [Sub]'
                        else:
                            remarks = 'Sub'
                    
                    if not remarks:
                        remarks = 'Ongoing'
                    
                    item = {
                        'vod_id': href,
                        'vod_name': title,
                        'vod_pic': img_url or 'https://via.placeholder.com/200x300?text=No+Image',
                        'vod_remarks': remarks
                    }
                    
                    seen.add(href)
                    items.append(item)
                    
                except Exception as e:
                    continue
            
            total_pages = int(pg)
            hpage = soup.find('div', class_='hpage')
            if hpage:
                for link in hpage.find_all('a'):
                    link_text = link.text.strip()
                    if link_text.isdigit():
                        page_num = int(link_text)
                        if page_num > total_pages:
                            total_pages = page_num
                
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
    
    # ========== PLAYER ALA DONGHUB (YANG TERBUKTI BERHASIL) ==========
    def playerContent(self, flag, id, vipFlags):
        """
        Player ala Donghub - Multi-source streaming
        """
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
                r'src:\s*[\'"]([^\'"]+\.m3u8[^\'"]*)[\'"]',
                r'file:\s*[\'"]([^\'"]+\.m3u8[^\'"]*)[\'"]',
            ]
            
            for pattern in m3u8_patterns:
                matches = re.findall(pattern, html, re.I)
                for match in matches:
                    if match and match.startswith('http'):
                        self.log(f"Found m3u8: {match}")
                        return {'parse': 1, 'url': match, 'header': dm_headers}
            
            # 2. Cari di element #embed_holder
            embed_holder = soup.find('div', id='embed_holder')
            if embed_holder:
                iframe = embed_holder.find('iframe')
                if iframe and iframe.get('src'):
                    src = iframe.get('src')
                    self.log(f"Found iframe in embed_holder: {src}")
                    
                    # Cek apakah ini Dailymotion
                    if 'dailymotion.com' in src or 'dailymotion' in src:
                        # Extract video ID
                        video_id = None
                        
                        # Pola: /video/xyz123
                        id_match = re.search(r'/video/([a-zA-Z0-9]+)', src)
                        if id_match:
                            video_id = id_match.group(1)
                        
                        # Pola: embed/xyz123
                        if not video_id:
                            embed_match = re.search(r'embed[/=]([a-zA-Z0-9]+)', src)
                            if embed_match:
                                video_id = embed_match.group(1)
                        
                        if video_id:
                            self.log(f"Video ID: {video_id}")
                            
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
                                                        return {'parse': 1, 'url': stream['url'], 'header': dm_headers}
                            except:
                                pass
                    
                    # Return iframe URL jika bukan Dailymotion atau gagal API
                    if src.startswith('//'):
                        src = 'https:' + src
                    return {'parse': 1, 'url': src, 'header': self.site_headers}
            
            # 3. Iframe umum
            iframe = soup.find('iframe', src=True)
            if iframe:
                src = iframe.get('src')
                if src:
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        src = self.site + src
                    self.log(f"Found iframe: {src}")
                    return {'parse': 1, 'url': src, 'header': self.site_headers}
            
            # 4. Video MP4
            mp4_patterns = [
                r'(https?://[^\s"\']+\.mp4[^\s"\']*)',
                r'file:"([^"]+\.mp4[^"]*)"',
                r'src:\s*[\'"]([^\'"]+\.mp4[^\'"]*)[\'"]',
            ]
            
            for pattern in mp4_patterns:
                matches = re.findall(pattern, html, re.I)
                for match in matches:
                    if match and match.startswith('http'):
                        self.log(f"Found mp4: {match}")
                        return {'parse': 0, 'url': match, 'header': self.site_headers}
            
            # 5. Script video
            video_scripts = soup.find_all('script', text=re.compile(r'(player|video|source|m3u8|mp4)'))
            for script in video_scripts:
                script_text = script.string
                if script_text:
                    url_match = re.search(r'(https?://[^\s"\']+\.(?:m3u8|mp4)[^\s"\']*)', script_text)
                    if url_match:
                        self.log(f"Found video in script: {url_match.group(1)}")
                        return {'parse': 1, 'url': url_match.group(1), 'header': dm_headers}
            
            # Fallback
            self.log("No video source found, returning original URL")
            return {'parse': 1, 'url': id, 'header': self.site_headers}
            
        except Exception as e:
            self.log(f"Player error: {e}")
            return {'parse': 1, 'url': id, 'header': self.site_headers}
    
    def fetch(self, url, headers=None, timeout=15):
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
        print(f"[ANICHIN] {msg}")
    
    def destroy(self):
        if self.session:
            self.session.close()