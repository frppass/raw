# -*- coding: utf-8 -*-
import re, json, requests, time
from urllib.parse import urljoin, quote, unquote
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.site = 'https://pantau.singkawangkota.go.id'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': f'{self.site}/'
        }
        self.session = requests.Session()
        self.api_endpoint = f'{self.site}/source'
        self.cctv_icon = f'{self.site}/cctv.png'
        
    def getName(self):
        return "MATA INDAH CCTV"
    
    def isVideoFormat(self, url):
        return '.m3u8' in url.lower() if url else False
    
    def homeContent(self, filter):
        """Home content dengan kategori BERANDA"""
        return {
            'class': [
                {
                    'type_id': '1',
                    'type_name': 'BERANDA'
                }
            ]
        }
    
    def _fetch_cctv_data(self):
        """Ambil data CCTV dari API /source"""
        try:
            response = self.session.get(self.api_endpoint, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return []
    
    def homeVideoContent(self):
        """Video yang tampil di home"""
        cctv_list = self._fetch_cctv_data()
        videos = []
        
        # Data dari screenshot (kalau API kosong)
        nama_cctv = [
            "Pasir Panjang 1",
            "Simpang Mah",
            "Simpang Kual", 
            "Simpang Pone",
            "Simpang PU",
            "Simpang Her",
            "SIMPANG VIT",
            "Simpang PLN",
            "Simpang PLN 2"
        ]
        
        # Kalau API kosong, pakai data dari screenshot
        if not cctv_list:
            for idx, name in enumerate(nama_cctv):
                videos.append({
                    'vod_id': str(idx + 1),
                    'vod_name': name,
                    'vod_pic': self.cctv_icon,
                    'vod_remarks': '🟢 LIVE',
                    'vod_year': '2026',
                    'vod_area': 'Singkawang',
                    'vod_content': f'📍 {name}\n\n🚦 Dishub Singkawang',
                    'vod_play_from': 'MATA INDAH',
                    'vod_play_url': f'{name}$https://pantau.singkawangkota.go.id/storage/streams/{name.lower().replace(" ", "_")}.m3u8'
                })
        else:
            # Pakai data dari API
            for idx, cctv in enumerate(cctv_list):
                name = cctv.get('name', f'CCTV {idx+1}')
                path = cctv.get('path', '')
                
                if path:
                    if not path.startswith('http'):
                        hls_url = urljoin(self.site, path)
                    else:
                        hls_url = path
                    
                    videos.append({
                        'vod_id': str(idx + 1),
                        'vod_name': str(name),
                        'vod_pic': self.cctv_icon,
                        'vod_remarks': '🟢 LIVE',
                        'vod_year': '2026',
                        'vod_area': 'Singkawang',
                        'vod_content': f'📍 {name}\n\n🚦 Dishub Singkawang',
                        'vod_play_from': 'MATA INDAH',
                        'vod_play_url': f'{name}${hls_url}'
                    })
        
        return {
            'list': videos,
            'page': 1,
            'pagecount': 1,
            'limit': 100,
            'total': len(videos)
        }
    
    def categoryContent(self, tid, pg, filter, ext):
        """Category content - panggil homeVideoContent"""
        return self.homeVideoContent()
    
    def detailContent(self, ids):
        vod_id = ids[0]
        
        try:
            idx = int(vod_id) - 1
            home_data = self.homeVideoContent()
            videos = home_data.get('list', [])
            
            if 0 <= idx < len(videos):
                return {'list': [videos[idx]]}
        except:
            pass
        
        return {'list': []}
    
    def playerContent(self, flag, id, vipFlags):
        return {
            'parse': 0,
            'url': id,
            'header': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': self.site,
            }
        }
    
    def searchContent(self, key, quick, pg="1"):
        return self.homeVideoContent()
    
    def destroy(self):
        self.session.close()