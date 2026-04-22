# -*- coding: utf-8 -*-
import re, json, requests, time
from urllib.parse import urljoin, quote, unquote
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.site = 'https://cctv.mempawahkab.go.id'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': f'{self.site}/frontend/'
        }
        self.session = requests.Session()
        
        # Deteksi icon dari website
        self.cctv_icon = self._detect_cctv_icon()
        
        # Data CCTV dengan ID yang sesuai
        self.cctv_data = [
            # Anjongan (3 CCTV)
            {'id': '1', 'name': 'CCTV Anjongan 1', 'kecamatan': 'Anjongan'},
            {'id': '2', 'name': 'CCTV Anjongan 2', 'kecamatan': 'Anjongan'},
            {'id': '3', 'name': 'CCTV Anjongan 3', 'kecamatan': 'Anjongan'},
            
            # Jongkat (4 CCTV)
            {'id': '4', 'name': 'CCTV Jongkat 1', 'kecamatan': 'Jongkat'},
            {'id': '5', 'name': 'CCTV Jongkat 2', 'kecamatan': 'Jongkat'},
            {'id': '6', 'name': 'CCTV Jongkat 3', 'kecamatan': 'Jongkat'},
            {'id': '7', 'name': 'CCTV Jongkat 4', 'kecamatan': 'Jongkat'},
            
            # Mempawah Hilir (4 CCTV)
            {'id': '8', 'name': 'CCTV Mempawah Hilir 1', 'kecamatan': 'Mempawah Hilir'},
            {'id': '9', 'name': 'CCTV Mempawah Hilir 2', 'kecamatan': 'Mempawah Hilir'},
            {'id': '10', 'name': 'CCTV Mempawah Hilir 3', 'kecamatan': 'Mempawah Hilir'},
            {'id': '11', 'name': 'CCTV Mempawah Hilir 4', 'kecamatan': 'Mempawah Hilir'},
            
            # Segedong (3 CCTV)
            {'id': '12', 'name': 'CCTV Segedong 1', 'kecamatan': 'Segedong'},
            {'id': '13', 'name': 'CCTV Segedong 2', 'kecamatan': 'Segedong'},
            {'id': '14', 'name': 'CCTV Segedong 3', 'kecamatan': 'Segedong'},
            
            # Sungai Pinyuh (3 CCTV)
            {'id': '15', 'name': 'CCTV Sungai Pinyuh 1', 'kecamatan': 'Sungai Pinyuh'},
            {'id': '16', 'name': 'CCTV Sungai Pinyuh 2', 'kecamatan': 'Sungai Pinyuh'},
            {'id': '17', 'name': 'CCTV Sungai Pinyuh 3', 'kecamatan': 'Sungai Pinyuh'},
        ]
        
        # Generate stream URL
        for cctv in self.cctv_data:
            cctv['stream_url'] = f'{self.site}/stream/{cctv["id"]}/playlist.m3u8'
    
    def _detect_cctv_icon(self):
        """Deteksi icon CCTV dari website"""
        # Coba ambil dari file map.js
        try:
            response = self.session.get(f'{self.site}/frontend/js/map.js', timeout=5)
            if response.status_code == 200:
                js_content = response.text
                
                # Cari pola icon dalam JS
                # Biasanya: icon: L.icon({ iconUrl: '...' })
                icon_pattern = r"iconUrl\s*:\s*['\"]([^'\"]+\.(?:png|jpg|jpeg|gif|svg))['\"]"
                matches = re.findall(icon_pattern, js_content, re.IGNORECASE)
                
                for icon_path in matches:
                    if 'cctv' in icon_path.lower() or 'marker' in icon_path.lower():
                        if icon_path.startswith('http'):
                            return icon_path
                        else:
                            return urljoin(self.site, icon_path)
        except:
            pass
        
        # Coba cek lokasi icon yang umum
        icon_candidates = [
            f'{self.site}/assets/img/cctv-icon.png',
            f'{self.site}/assets/img/cctv.png',
            f'{self.site}/assets/img/marker-icon.png',
            f'{self.site}/frontend/assets/img/cctv.png',
            f'{self.site}/img/cctv.png',
            'https://cdn-icons-png.flaticon.com/512/3075/3075970.png'  # fallback
        ]
        
        for icon_url in icon_candidates:
            try:
                resp = self.session.head(icon_url, timeout=2)
                if resp.status_code == 200:
                    return icon_url
            except:
                continue
        
        return icon_candidates[-1]  # return fallback icon
    
    def getName(self):
        return "CCTV Mempawah"
    
    def isVideoFormat(self, url):
        return '.m3u8' in url.lower() if url else False
    
    def homeContent(self, filter):
        classes = [
            {'type_id': 'all', 'type_name': 'SEMUA CCTV'},
            {'type_id': 'Anjongan', 'type_name': 'ANJONGAN'},
            {'type_id': 'Jongkat', 'type_name': 'JONGKAT'},
            {'type_id': 'Mempawah Hilir', 'type_name': 'MEMPAWAH HILIR'},
            {'type_id': 'Segedong', 'type_name': 'SEGEDONG'},
            {'type_id': 'Sungai Pinyuh', 'type_name': 'SUNGAI PINYUH'}
        ]
        return {'class': classes}
    
    def homeVideoContent(self):
        return self._build_video_list(self.cctv_data)
    
    def _build_video_list(self, cctv_list, kecamatan_filter=None):
        videos = []
        
        for cctv in cctv_list:
            if kecamatan_filter and kecamatan_filter != 'all':
                if cctv.get('kecamatan', '') != kecamatan_filter:
                    continue
            
            videos.append({
                'vod_id': cctv['id'],
                'vod_name': f'[{cctv["kecamatan"]}] {cctv["name"]}',
                'vod_pic': self.cctv_icon,
                'vod_remarks': '🟢 LIVE',
                'vod_year': '2026',
                'vod_area': 'Mempawah',
                'vod_content': f'📍 {cctv["kecamatan"]}\n📹 {cctv["name"]}\n\n🏢 Pemerintah Kabupaten Mempawah\n\n🔗 Stream: /stream/{cctv["id"]}/playlist.m3u8',
                'vod_play_from': 'CCTV Mempawah',
                'vod_play_url': f'{cctv["name"]}${cctv["stream_url"]}'
            })
        
        return {
            'list': videos,
            'page': 1,
            'pagecount': 1,
            'limit': 100,
            'total': len(videos)
        }
    
    def categoryContent(self, tid, pg, filter, ext):
        if tid and tid != 'all':
            return self._build_video_list(self.cctv_data, kecamatan_filter=tid)
        return self._build_video_list(self.cctv_data)
    
    def detailContent(self, ids):
        vod_id = ids[0]
        
        for cctv in self.cctv_data:
            if cctv['id'] == vod_id:
                video = {
                    'vod_id': vod_id,
                    'vod_name': f'[{cctv["kecamatan"]}] {cctv["name"]}',
                    'vod_pic': self.cctv_icon,
                    'vod_remarks': '🟢 LIVE',
                    'vod_year': '2026',
                    'vod_area': 'Mempawah',
                    'vod_content': f'📍 {cctv["kecamatan"]}\n📹 {cctv["name"]}\n\n🏢 Pemerintah Kabupaten Mempawah\n\n🔗 Stream: /stream/{cctv["id"]}/playlist.m3u8',
                    'vod_play_from': 'CCTV Mempawah',
                    'vod_play_url': f'{cctv["name"]}${cctv["stream_url"]}'
                }
                return {'list': [video]}
        
        return {'list': []}
    
    def playerContent(self, flag, id, vipFlags):
        return {
            'parse': 0,
            'url': id,
            'header': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': f'{self.site}/frontend/',
                'Origin': self.site
            }
        }
    
    def searchContent(self, key, quick, pg="1"):
        filtered = []
        key_lower = key.lower()
        
        for cctv in self.cctv_data:
            if key_lower in cctv['name'].lower() or key_lower in cctv['kecamatan'].lower():
                filtered.append(cctv)
        
        return self._build_video_list(filtered)
    
    def destroy(self):
        self.session.close()