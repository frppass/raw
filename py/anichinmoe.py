# -*- coding: utf-8 -*-
import re, sys, os, requests, json, base64, time
from urllib.parse import urlparse, urljoin, quote, unquote
from base.spider import Spider

# Fallback jika BeautifulSoup tidak ada
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except:
    HAS_BS4 = False
    print("Warning: BeautifulSoup not installed, using regex fallback")

class Spider(Spider):
    def init(self, extend=""):
        self.site = 'https://anichin.moe'
        self.site_domain = 'anichin.moe'
        
        self.site_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.site,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        self.cache = {}
        self.session = requests.Session()
        self.session.headers.update(self.site_headers)
        
        print("✅ ANICHIN.MOE Spider for OK影视 initialized")
    
    def getName(self):
        return "🇨🇳 ANICHIN.MOE"
    
    def isVideoFormat(self, url):
        return any(ext in url.lower() for ext in ['.m3u8', '.mp4', '.mkv', '.webm'])
    
    def manualVideoCheck(self):
        return True
    
    def homeContent(self, filter):
        return {
            'class': [
                # All
                {'type_id': 'all', 'type_name': '📋 All Anime'},
                
                # Status
                {'type_id': 'ongoing', 'type_name': '🔥 Ongoing'},
                {'type_id': 'completed', 'type_name': '✅ Completed'},
              
                # Popular
                {'type_id': 'popular', 'type_name': '⭐ Popular'},
                {'type_id': 'trending', 'type_name': '🔥 Trending'},
                {'type_id': 'latest', 'type_name': '🆕 Latest'},
                
                # Genre
                {'type_id': 'action', 'type_name': '⚔️ Action'},
                {'type_id': 'adventure', 'type_name': '🧭 Adventure'},
                {'type_id': 'cultivation', 'type_name': '🌿 Cultivation'},
                {'type_id': 'comedy', 'type_name': '😂 Comedy'},
                {'type_id': 'drama', 'type_name': '🎭 Drama'},
                {'type_id': 'fantasy', 'type_name': '🧚 Fantasy'},
                {'type_id': 'historical', 'type_name': '🏯 Historical'},
                {'type_id': 'isekai', 'type_name': '🚪 Isekai'},
                {'type_id': 'martial-arts', 'type_name': '🥋 Martial Arts'},
                {'type_id': 'mecha', 'type_name': '🤖 Mecha'},
                {'type_id': 'mystery', 'type_name': '🔍 Mystery'},
                {'type_id': 'psychological', 'type_name': '🧠 Psychological'},
                {'type_id': 'romance', 'type_name': '❤️ Romance'},
                {'type_id': 'sci-fi', 'type_name': '🚀 Sci-Fi'},
                {'type_id': 'super-power', 'type_name': '⚡ Super Power'},
                {'type_id': 'supernatural', 'type_name': '👻 Supernatural'},
                {'type_id': 'thriller', 'type_name': '🔪 Thriller'},
                
            ],
            'filters': {}
        }
    
    def homeVideoContent(self):
        try:
            cache_key = 'home_content'
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            print("📥 Fetching home page...")
            url = f"{self.site}/"
            html = self.fetch(url).text
            
            items = []
            seen = set()
            
            if HAS_BS4:
                items = self._parse_with_bs4(html, seen)
            else:
                items = self._parse_with_regex(html, seen)
            
            print(f"✅ Found {len(items)} items for home page")
            
            result = {'list': items}
            self.cache[cache_key] = result
            return result
            
        except Exception as e:
            print(f"❌ Home error: {e}")
            return {'list': []}
    
    def _parse_with_bs4(self, html, seen):
        items = []
        soup = BeautifulSoup(html, 'html.parser')
        
        listupd = soup.find('div', class_='listupd')
        if not listupd:
            listupd = soup
        
        for article in listupd.find_all('article', class_='bs')[:30]:
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
                
                img = ''
                limit_div = article.find('div', class_='limit')
                if limit_div:
                    img_tag = limit_div.find('img')
                    if img_tag:
                        img = img_tag.get('src') or img_tag.get('data-src') or ''
                
                remarks = 'Ongoing'
                epx = article.find('span', class_='epx')
                if epx:
                    remarks = epx.text.strip()
                
                if article.find('div', class_='hotbadge'):
                    remarks = '🔥 ' + remarks
                
                status_div = article.find('div', class_='status')
                if status_div and status_div.text.strip():
                    remarks = status_div.text.strip()
                
                items.append({
                    'vod_id': href,
                    'vod_name': title,
                    'vod_pic': urljoin(self.site, img),
                    'vod_remarks': remarks
                })
                seen.add(href)
                
            except Exception as e:
                continue
        
        return items
    
    def _parse_with_regex(self, html, seen):
        items = []
        article_pattern = r'<article[^>]*class="bs"[^>]*>(.*?)</article>'
        articles = re.findall(article_pattern, html, re.S | re.I)
        
        for article_html in articles[:30]:
            try:
                link_match = re.search(r'<a[^>]*href="([^"]+)"[^>]*>', article_html)
                if not link_match: continue
                href = link_match.group(1)
                if href in seen: continue
                
                title = ''
                tt_match = re.search(r'<div[^>]*class="tt"[^>]*>.*?<h2[^>]*>(.*?)</h2>', article_html, re.S)
                if tt_match:
                    title = tt_match.group(1).strip()
                
                if not title:
                    title_match = re.search(r'title="([^"]+)"', article_html)
                    title = title_match.group(1) if title_match else ''
                
                img = ''
                img_match = re.search(r'<img[^>]*src="([^"]+)"[^>]*>', article_html)
                if img_match:
                    img = img_match.group(1)
                
                remarks = 'Ongoing'
                epx_match = re.search(r'<span[^>]*class="epx"[^>]*>(.*?)</span>', article_html)
                if epx_match:
                    remarks = epx_match.group(1).strip()
                
                if 'hotbadge' in article_html:
                    remarks = '🔥 ' + remarks
                
                items.append({
                    'vod_id': href,
                    'vod_name': title,
                    'vod_pic': urljoin(self.site, img),
                    'vod_remarks': remarks
                })
                seen.add(href)
                
            except:
                continue
        
        return items
    
    def _get_page_url(self, tid, pg):
        """Buat URL untuk kategori berdasarkan type_id - DENGAN PAGINATION QUERY PARAMETER"""
        base_urls = {
            # Status
            'ongoing': '/anime/?status=ongoing',
            'completed': '/anime/?status=completed',
            'upcoming': '/upcoming-donghua/',
            'drop': '/drop/',
            'schedule': '/schedule/',
            
            # Type
            'movie': '/anime/?type=movie',
            'tv': '/anime/?type=tv',
            'ona': '/anime/?type=ona',
            
            # Popular/trending
            'popular': '/anime/?order=popular',
            'trending': '/anime/?order=popular',
            'latest': '/anime/?order=latest',
            
            # Genre - menggunakan format array []
            'action': '/anime/?genre[]=action',
            'adventure': '/anime/?genre[]=adventure',
            'cultivation': '/anime/?genre[]=cultivation',
            'comedy': '/anime/?genre[]=comedy',
            'drama': '/anime/?genre[]=drama',
            'fantasy': '/anime/?genre[]=fantasy',
            'historical': '/anime/?genre[]=historical',
            'isekai': '/anime/?genre[]=isekai',
            'martial-arts': '/anime/?genre[]=martial-arts',
            'mecha': '/anime/?genre[]=mecha',
            'mystery': '/anime/?genre[]=mystery',
            'psychological': '/anime/?genre[]=psychological',
            'romance': '/anime/?genre[]=romance',
            'sci-fi': '/anime/?genre[]=sci-fi',
            'super-power': '/anime/?genre[]=super-power',
            'supernatural': '/anime/?genre[]=supernatural',
            'thriller': '/anime/?genre[]=thriller',
            
            # All anime
            'all': '/anime/',
        }
        
        base_path = base_urls.get(tid, '/anime/')
        
        # Handle pagination - semua menggunakan query parameter ?page=N
        if int(pg) > 1:
            if '?' in base_path:
                # Jika sudah ada query string, tambahkan &page=N
                return f"{self.site}{base_path}&page={pg}"
            else:
                # Jika tidak ada query string, tambahkan ?page=N
                return f"{self.site}{base_path}?page={pg}"
        
        # Halaman 1: tanpa parameter page
        return f"{self.site}{base_path}"
    
    def categoryContent(self, tid, pg, filter, extend):
        try:
            url = self._get_page_url(tid, pg)
            print(f"📥 Fetching category '{tid}' page {pg}: {url}")
            
            html = self.fetch(url).text
            
            items = []
            seen = set()
            
            if HAS_BS4:
                soup = BeautifulSoup(html, 'html.parser')
                listupd = soup.find('div', class_='listupd')
                if not listupd:
                    listupd = soup
                
                for article in listupd.find_all('article', class_='bs')[:40]:
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
                        
                        img = ''
                        limit_div = article.find('div', class_='limit')
                        if limit_div:
                            img_tag = limit_div.find('img')
                            if img_tag:
                                img = img_tag.get('src') or img_tag.get('data-src') or ''
                        
                        remarks = 'Ongoing'
                        epx = article.find('span', class_='epx')
                        if epx:
                            remarks = epx.text.strip()
                        
                        if article.find('div', class_='hotbadge'):
                            remarks = '🔥 ' + remarks
                        
                        items.append({
                            'vod_id': href,
                            'vod_name': title,
                            'vod_pic': urljoin(self.site, img),
                            'vod_remarks': remarks
                        })
                        seen.add(href)
                        
                    except Exception as e:
                        continue
            
            # ===== PAGINATION - DETEKSI TOTAL HALAMAN =====
            total_pages = int(pg)  # Default ke halaman saat ini
            
            if HAS_BS4 and soup:
                hpage = soup.find('div', class_='hpage')
                if hpage:
                    # Cari link "Next" (biasanya class 'r')
                    next_link = hpage.find('a', class_='r')
                    if next_link:
                        # Jika ada next link, berarti masih ada halaman berikutnya
                        # Ambil nomor halaman dari href next link
                        next_href = next_link.get('href', '')
                        # Cari pattern page=N di URL (format: ?page=3 atau &page=3)
                        page_match = re.search(r'[?&]page=(\d+)', next_href)
                        if page_match:
                            next_page = int(page_match.group(1))
                            # Total halaman setidaknya next_page
                            total_pages = max(total_pages, next_page)
                        else:
                            # Jika tidak ada angka, asumsikan halaman berikutnya
                            total_pages = max(total_pages, int(pg) + 1)
            
            # Jika tidak ada informasi pagination, gunakan logika sederhana
            if total_pages == int(pg) and len(items) > 0:
                if int(pg) == 1:
                    total_pages = 10  # Asumsi 10 halaman untuk halaman 1
                else:
                    total_pages = int(pg) + 1  # Asumsi ada halaman berikutnya
            
            print(f"📊 Page {pg} of {total_pages} - Found {len(items)} items")
            
            return {
                'list': items,
                'page': int(pg),
                'pagecount': total_pages,
                'limit': 30,
                'total': len(items) * total_pages if total_pages > 0 else len(items)
            }
            
        except Exception as e:
            print(f"❌ Category error: {e}")
            return {'list': []}
    
    def detailContent(self, ids):
        """
        Detail anime dan episode - FOKUS PADA EPLISTER
        """
        try:
            url = ids[0] if ids[0].startswith('http') else urljoin(self.site, ids[0])
            print(f"📥 Fetching detail: {url}")
            
            html = self.fetch(url).text
            
            # ===== INFO DASAR =====
            title = ''
            title_match = re.search(r'<h1[^>]*class="entry-title"[^>]*>(.*?)</h1>', html, re.S | re.I)
            if title_match:
                title = title_match.group(1).strip()
            
            img = ''
            img_match = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html, re.I)
            if img_match:
                img = img_match.group(1)
            
            desc = ''
            desc_match = re.search(r'<div[^>]*class="entry-content"[^>]*>(.*?)</div>', html, re.S | re.I)
            if desc_match:
                desc = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()[:500]
            
            year = ''
            year_match = re.search(r'20\d{2}', html)
            if year_match:
                year = year_match.group(0)
            
            # ===== EPISODE DARI EPLISTER =====
            episodes = []
            
            # Cari div dengan class eplister
            eplister_pattern = r'<div[^>]*class="eplister"[^>]*>(.*?)</div>'
            eplister_match = re.search(eplister_pattern, html, re.S | re.I)
            
            if eplister_match:
                eplister_html = eplister_match.group(1)
                print("✅ Found eplister")
                
                # Pattern untuk mengambil episode dari eplister
                li_pattern = r'<li[^>]*data-index="\d+"[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>.*?<div[^>]*class="epl-num"[^>]*>(.*?)</div>.*?<div[^>]*class="epl-title"[^>]*>(.*?)</div>.*?</a>.*?</li>'
                li_matches = re.findall(li_pattern, eplister_html, re.S | re.I)
                
                for href, ep_num, title_text in li_matches:
                    ep_num_clean = re.sub(r'[^0-9]', '', ep_num.strip())
                    if ep_num_clean:
                        episode_url = href if href.startswith('http') else urljoin(self.site, href)
                        episodes.append(f"{ep_num_clean}${episode_url}")
                        print(f"  Episode {ep_num_clean}: {episode_url}")
            
            # Fallback pattern
            if not episodes:
                episode_links = re.findall(r'<a[^>]*href="([^"]*?episode[^"]*?)"[^>]*>.*?<div[^>]*class="epl-num"[^>]*>(.*?)</div>', html, re.S | re.I)
                for href, ep_num in episode_links:
                    ep_num_clean = re.sub(r'[^0-9]', '', ep_num.strip())
                    if ep_num_clean:
                        episode_url = href if href.startswith('http') else urljoin(self.site, href)
                        episodes.append(f"{ep_num_clean}${episode_url}")
                        print(f"  Episode {ep_num_clean}: {episode_url}")
            
            if not episodes:
                print("⚠️ No episodes found, using fallback")
                episodes.append(f"1${url}")
            
            episodes.sort(key=lambda x: int(x.split('$')[0]) if x.split('$')[0].isdigit() else 0)
            
            play_url = '#'.join(episodes)
            print(f"✅ Total episodes: {len(episodes)}")
            
            return {
                'list': [{
                    'vod_id': url,
                    'vod_name': title or 'Unknown',
                    'vod_pic': img,
                    'vod_year': year,
                    'vod_content': desc,
                    'vod_remarks': f"{len(episodes)} Episode",
                    'vod_play_from': 'ANICHIN',
                    'vod_play_url': play_url
                }]
            }
            
        except Exception as e:
            print(f"❌ Detail error: {e}")
            return {'list': []}
    
    def searchContent(self, key, quick, pg="1"):
        try:
            url = f"{self.site}/?s={quote(key)}"
            if int(pg) > 1:
                url += f"&page={pg}"
            
            print(f"📥 Searching: {key}")
            html = self.fetch(url).text
            
            items = []
            seen = set()
            
            article_pattern = r'<article[^>]*class="bs"[^>]*>(.*?)</article>'
            articles = re.findall(article_pattern, html, re.S | re.I)
            
            for article_html in articles[:30]:
                try:
                    link_match = re.search(r'<a[^>]*href="([^"]+)"[^>]*>', article_html)
                    if not link_match: continue
                    href = link_match.group(1)
                    if href in seen: continue
                    
                    title = ''
                    tt_match = re.search(r'<div[^>]*class="tt"[^>]*>.*?<h2[^>]*>(.*?)</h2>', article_html, re.S)
                    if tt_match:
                        title = tt_match.group(1).strip()
                    
                    if not title:
                        title_match = re.search(r'title="([^"]+)"', article_html)
                        title = title_match.group(1) if title_match else ''
                    
                    img = ''
                    img_match = re.search(r'<img[^>]*src="([^"]+)"[^>]*>', article_html)
                    if img_match:
                        img = img_match.group(1)
                    
                    remarks = ''
                    epx_match = re.search(r'<span[^>]*class="epx"[^>]*>(.*?)</span>', article_html)
                    if epx_match:
                        remarks = epx_match.group(1).strip()
                    
                    items.append({
                        'vod_id': href,
                        'vod_name': title,
                        'vod_pic': urljoin(self.site, img),
                        'vod_remarks': remarks
                    })
                    seen.add(href)
                    
                except:
                    continue
            
            return {'list': items, 'page': int(pg), 'pagecount': 1}
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            return {'list': []}
    
    # ===== PLAYER DENGAN PENCARIAN SERVER DI MIRROR =====
    def playerContent(self, flag, id, vipFlags):
        """
        Player untuk OK影视 - mencari server video termasuk Dailymotion di mirror options
        """
        try:
            print(f"📥 Player for: {id}")
            
            # Fetch halaman episode
            resp = self.session.get(id, timeout=15)
            html = resp.text
            
            # ===== 1. CARI DI MIRROR OPTIONS (PRIORITAS) =====
            mirror_pattern = r'<select[^>]*class="mirror"[^>]*>(.*?)</select>'
            select_match = re.search(mirror_pattern, html, re.S | re.I)
            
            if select_match:
                select_html = select_match.group(1)
                option_pattern = r'<option[^>]*value="([^"]+)"[^>]*>(.*?)</option>'
                options = re.findall(option_pattern, select_html, re.S | re.I)
                
                # Urutan prioritas server
                priority_servers = ['Dailymotion', 'New Player', 'RPM Share', 'Okru', 'Rumble']
                sorted_options = []
                
                # Urutkan berdasarkan prioritas
                for priority in priority_servers:
                    for value, name in options:
                        if priority.lower() in name.lower():
                            sorted_options.append((value, name))
                
                # Tambahkan sisa server
                for value, name in options:
                    if not any(p.lower() in name.lower() for p in priority_servers):
                        sorted_options.append((value, name))
                
                # Coba setiap mirror
                for value, name in sorted_options:
                    try:
                        print(f"🔄 Trying mirror: {name.strip()}")
                        
                        # Decode base64
                        try:
                            decoded = base64.b64decode(value).decode('utf-8')
                        except:
                            decoded = value
                        
                        # ===== CARI URL DAILYMOTION YANG BISA STREAMING =====
                        cdndirector_patterns = [
                            r'(https?://cdndirector\.dailymotion\.com[^\s"\']+\.m3u8[^\s"\']*)',
                            r'(https?://[^\s"\']*dailymotion[^\s"\']+\.m3u8[^\s"\']*)',
                        ]
                        
                        for pattern in cdndirector_patterns:
                            cdndirector_match = re.search(pattern, decoded, re.I)
                            if cdndirector_match:
                                video_url = cdndirector_match.group(1)
                                print(f"✅ Found CDNdirector m3u8 in {name}")
                                return {
                                    'parse': 1,
                                    'url': video_url,
                                    'header': {
                                        'User-Agent': self.site_headers['User-Agent'],
                                        'Referer': 'https://www.dailymotion.com/',
                                    }
                                }
                        
                        # Cari iframe Dailymotion
                        dm_patterns = [
                            r'dailymotion\.com/embed/video/([a-zA-Z0-9]+)',
                            r'dailymotion\.com/video/([a-zA-Z0-9]+)',
                            r'video[/=]([a-zA-Z0-9]+)',
                        ]
                        
                        for pattern in dm_patterns:
                            dm_match = re.search(pattern, decoded, re.I)
                            if dm_match:
                                video_id = dm_match.group(1)
                                print(f"✅ Found Dailymotion video ID in {name}: {video_id}")
                                
                                # Ambil dari API Dailymotion
                                api_url = f"https://www.dailymotion.com/player/metadata/video/{video_id}"
                                api_headers = {
                                    'User-Agent': self.site_headers['User-Agent'],
                                    'Referer': 'https://www.dailymotion.com/',
                                    'Origin': 'https://www.dailymotion.com',
                                }
                                
                                try:
                                    api_resp = self.session.get(api_url, headers=api_headers, timeout=10)
                                    if api_resp.status_code == 200:
                                        data = api_resp.json()
                                        if 'qualities' in data:
                                            for quality in ['auto', '1080', '720', '480']:
                                                if quality in data['qualities'] and data['qualities'][quality]:
                                                    for stream in data['qualities'][quality]:
                                                        if 'url' in stream:
                                                            print(f"✅ Found m3u8 from Dailymotion API")
                                                            return {
                                                                'parse': 1,
                                                                'url': stream['url'],
                                                                'header': {
                                                                    'User-Agent': self.site_headers['User-Agent'],
                                                                    'Referer': 'https://www.dailymotion.com/',
                                                                }
                                                            }
                                except:
                                    pass
                        
                        # Cari m3u8 langsung
                        m3u8_patterns = [
                            r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
                            r'(https?://dmxleo\.dailymotion\.com[^\s"\']+\.m3u8[^\s"\']*)',
                            r'(https?://vod\d+\.cf\.dmcdn\.net[^\s"\']+\.m3u8[^\s"\']*)',
                        ]
                        
                        for pattern in m3u8_patterns:
                            m3u8_match = re.search(pattern, decoded, re.I)
                            if m3u8_match:
                                video_url = m3u8_match.group(1)
                                print(f"✅ Found m3u8 in {name}")
                                return {
                                    'parse': 1,
                                    'url': video_url,
                                    'header': {
                                        'User-Agent': self.site_headers['User-Agent'],
                                        'Referer': 'https://www.dailymotion.com/' if 'dailymotion' in video_url else id,
                                    }
                                }
                        
                        # Cari iframe umum
                        iframe_match = re.search(r'<iframe.*?src=["\'](.*?)["\']', decoded, re.I | re.S)
                        if iframe_match:
                            iframe_url = iframe_match.group(1)
                            if iframe_url.startswith('//'):
                                iframe_url = 'https:' + iframe_url
                            print(f"✅ Found iframe in {name}")
                            return {
                                'parse': 1,
                                'url': iframe_url,
                                'header': {
                                    'User-Agent': self.site_headers['User-Agent'],
                                    'Referer': id,
                                }
                            }
                    
                    except Exception as e:
                        print(f"⚠️ Error with mirror {name}: {e}")
                        continue
            
            # ===== 2. CARI LANGSUNG DI HTML =====
            cdndirector_patterns = [
                r'(https?://cdndirector\.dailymotion\.com[^\s"\']+\.m3u8[^\s"\']*)',
                r'"(https?://cdndirector\.dailymotion\.com[^"]+\.m3u8[^"]*)"',
                r"(https?://cdndirector\.dailymotion\.com[^']+\.m3u8[^']*)",
            ]
            
            for pattern in cdndirector_patterns:
                matches = re.findall(pattern, html, re.I)
                if matches:
                    video_url = matches[0] if isinstance(matches[0], str) else matches[0][0]
                    print(f"✅ Found CDNdirector m3u8 in HTML")
                    return {
                        'parse': 1,
                        'url': video_url,
                        'header': {
                            'User-Agent': self.site_headers['User-Agent'],
                            'Referer': 'https://www.dailymotion.com/',
                        }
                    }
            
            # Cari Dailymotion video ID
            video_id = None
            id_patterns = [
                r'dailymotion\.com/embed/video/([a-zA-Z0-9]+)',
                r'dailymotion\.com/video/([a-zA-Z0-9]+)',
                r'data-src=["\'].*?dailymotion\.com/.*?video[/=]([a-zA-Z0-9]+)',
                r'video[/=]([a-zA-Z0-9]+)',
            ]
            
            for pattern in id_patterns:
                match = re.search(pattern, html, re.I)
                if match:
                    video_id = match.group(1)
                    print(f"✅ Found Dailymotion video ID in HTML: {video_id}")
                    break
            
            if video_id:
                api_url = f"https://www.dailymotion.com/player/metadata/video/{video_id}"
                api_headers = {
                    'User-Agent': self.site_headers['User-Agent'],
                    'Referer': 'https://www.dailymotion.com/',
                    'Origin': 'https://www.dailymotion.com',
                }
                
                try:
                    api_resp = self.session.get(api_url, headers=api_headers, timeout=10)
                    if api_resp.status_code == 200:
                        data = api_resp.json()
                        if 'qualities' in data:
                            for quality in ['auto', '1080', '720', '480']:
                                if quality in data['qualities'] and data['qualities'][quality]:
                                    for stream in data['qualities'][quality]:
                                        if 'url' in stream:
                                            print(f"✅ Found m3u8 from Dailymotion API")
                                            return {
                                                'parse': 1,
                                                'url': stream['url'],
                                                'header': {
                                                    'User-Agent': self.site_headers['User-Agent'],
                                                    'Referer': 'https://www.dailymotion.com/',
                                                }
                                            }
                except:
                    pass
            
            # Cari m3u8 lainnya
            m3u8_patterns = [
                r'(https?://[^\s"\']+dailymotion[^\s"\']+\.m3u8[^\s"\']*)',
                r'(https?://dmxleo\.dailymotion\.com[^\s"\']+\.m3u8[^\s"\']*)',
                r'(https?://vod\d+\.cf\.dmcdn\.net[^\s"\']+\.m3u8[^\s"\']*)',
                r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
            ]
            
            for pattern in m3u8_patterns:
                matches = re.findall(pattern, html, re.I)
                if matches:
                    video_url = matches[0] if isinstance(matches[0], str) else matches[0][0]
                    print(f"✅ Found m3u8 in HTML")
                    return {
                        'parse': 1,
                        'url': video_url,
                        'header': {
                            'User-Agent': self.site_headers['User-Agent'],
                            'Referer': 'https://www.dailymotion.com/' if 'dailymotion' in video_url else id,
                        }
                    }
            
            # Fallback: iframe
            iframe = re.search(r'<iframe.*?src=["\'](https?://[^"\']+)["\']', html, re.I)
            if iframe:
                iframe_url = iframe.group(1)
                print(f"⚠️ Using iframe fallback")
                return {
                    'parse': 1,
                    'url': iframe_url,
                    'header': self.site_headers
                }
            
            print("⚠️ No video found")
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
        try:
            return self.session.get(url, timeout=15)
        except:
            class Dummy:
                text = ''
            return Dummy()
    
    def destroy(self):
        self.session.close()