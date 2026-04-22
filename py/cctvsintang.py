# -*- coding: utf-8 -*-
import re
import json
import requests
import time
from urllib.parse import urljoin, quote, unquote
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.site = 'https://web.sintang.go.id'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': f'{self.site}/cctv-show-NTY%3D',
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
        self.session = requests.Session()
        # API endpoint untuk mengambil data CCTV (ditemukan dari JavaScript)
        self.api_endpoint = f'{self.site}/get_cctv.php'
        self.cctv_icon = 'https://cdn-icons-png.flaticon.com/512/684/684908.png'
        
    def getName(self):
        return "SINTANG CCTV"
    
    def isVideoFormat(self, url):
        return bool(url and ('.m3u8' in url.lower() or '.mp4' in url.lower() or 'stream' in url.lower()))
    
    def homeContent(self, filter):
        """Home content dengan kategori CCTV"""
        return {
            'class': [
                {
                    'type_id': 'cctv',
                    'type_name': 'CCTV SINTANG'
                }
            ]
        }
    
    def _fetch_cctv_data(self):
        """
        Mengambil data CCTV dari API /get_cctv.php
        Berdasarkan analisis halaman, API mengembalikan array JSON dengan field:
        - id, nama_cctv, latitude, longitude, sumber_embed (URL stream)
        """
        try:
            # Tambahkan timestamp untuk menghindari cache
            response = self.session.get(
                f'{self.api_endpoint}?ts={int(time.time())}', 
                headers=self.headers, 
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and 'data' in data:
                    return data['data']
        except Exception as e:
            print(f"Error fetching CCTV data: {e}")
        
        # Fallback data dari dropdown pilihan lokasi (berdasarkan HTML)
        return self._get_fallback_data()
    
    def _get_fallback_data(self):
        """Data fallback berdasarkan lokasi CCTV yang terlihat di halaman"""
        fallback_cctvs = [
            {"nama_cctv": "Simpang 5 Lampu Jalan", "sumber_embed": ""},
            {"nama_cctv": "Simpang 5 PJU", "sumber_embed": ""},
            {"nama_cctv": "Simpang 5 Videotron", "sumber_embed": ""},
            {"nama_cctv": "Simpang Pertanian Lampu Lalu Lintas", "sumber_embed": ""},
            {"nama_cctv": "Tugu Bank BI Jam", "sumber_embed": ""},
            {"nama_cctv": "Tugu Jam Baleho", "sumber_embed": ""},
            {"nama_cctv": "Tugu Jam Tiang Lintas", "sumber_embed": ""}
        ]
        return fallback_cctvs
    
    def homeVideoContent(self):
        """Video yang tampil di home"""
        cctv_list = self._fetch_cctv_data()
        videos = []
        
        for idx, cctv in enumerate(cctv_list):
            # Ambil nama CCTV
            name = cctv.get('nama_cctv', cctv.get('name', f'CCTV {idx+1}'))
            
            # Ambil URL stream
            stream_url = cctv.get('sumber_embed', cctv.get('url', cctv.get('stream', '')))
            
            # Jika URL stream kosong, coba buat berdasarkan nama
            if not stream_url:
                # Beberapa kemungkinan pola URL
                name_slug = name.lower().replace(' ', '_').replace('(', '').replace(')', '')
                stream_url = f"{self.site}/storage/streams/{name_slug}.m3u8"
            
            videos.append({
                'vod_id': f"sintang_{idx + 1}",
                'vod_name': name,
                'vod_pic': self.cctv_icon,
                'vod_remarks': '🟢 LIVE',
                'vod_year': '2026',
                'vod_area': 'Sintang',
                'vod_content': f"📍 {name}\n\n🏛️ Pemerintah Kabupaten Sintang\n🌐 Koordinat: {cctv.get('latitude', '-')}, {cctv.get('longitude', '-')}",
                'vod_play_from': 'SINTANG',
                'vod_play_url': f"{name}${stream_url}"
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
            # Ekstrak index dari vod_id: "sintang_1" -> index 1
            if vod_id.startswith('sintang_'):
                idx = int(vod_id.split('_')[1]) - 1
            else:
                idx = int(vod_id) - 1
                
            home_data = self.homeVideoContent()
            videos = home_data.get('list', [])
            
            if 0 <= idx < len(videos):
                return {'list': [videos[idx]]}
        except Exception as e:
            print(f"Error in detailContent: {e}")
        
        return {'list': []}
    
    def playerContent(self, flag, id, vipFlags):
        """
        Konfigurasi player untuk memutar stream CCTV
        """
        # Deteksi tipe konten berdasarkan URL
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': self.site,
            'Origin': self.site
        }
        
        # Tambahkan header khusus untuk HLS
        if '.m3u8' in id.lower():
            headers['Accept'] = 'application/vnd.apple.mpegurl'
        
        return {
            'parse': 0,  # 0 = langsung mainkan URL
            'url': id,
            'header': headers
        }
    
    def searchContent(self, key, quick, pg="1"):
        """Pencarian CCTV berdasarkan nama"""
        cctv_list = self._fetch_cctv_data()
        videos = []
        
        key_lower = key.lower()
        for idx, cctv in enumerate(cctv_list):
            name = cctv.get('nama_cctv', cctv.get('name', ''))
            if key_lower in name.lower():
                stream_url = cctv.get('sumber_embed', cctv.get('url', ''))
                videos.append({
                    'vod_id': f"sintang_{idx + 1}",
                    'vod_name': name,
                    'vod_pic': self.cctv_icon,
                    'vod_remarks': '🟢 LIVE',
                    'vod_year': '2026',
                    'vod_area': 'Sintang',
                    'vod_content': f"📍 {name}\n\n🏛️ Pemerintah Kabupaten Sintang",
                    'vod_play_from': 'SINTANG',
                    'vod_play_url': f"{name}${stream_url}"
                })
        
        return {
            'list': videos,
            'page': 1,
            'pagecount': 1,
            'limit': 100,
            'total': len(videos)
        }
    
    def destroy(self):
        self.session.close()