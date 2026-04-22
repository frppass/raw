# -*- coding: utf-8 -*-
import re, json, requests, time
from urllib.parse import urljoin, quote, unquote
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.site = 'https://cintadilan.sanggau.go.id'
        self.stream_host = 'https://cintadilanhost.sanggau.go.id'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': f'{self.site}/',
            'Accept': '*/*',
            'Connection': 'keep-alive'
        }
        self.cctv_icon = f'{self.site}/tvt/assets/img/cctv_marker.png'
        
        # Data CCTV dengan mapping ke URL stream yang benar
        self.cctv_list = self._get_cctv_data()
        
    def getName(self):
        return "Cinta Dilan CCTV"
    
    def isVideoFormat(self, url):
        return '.m3u8' in url.lower() if url else False
    
    def homeContent(self, filter):
        """Home content dengan kategori berdasarkan lokasi"""
        # Ambil semua lokasi unik dari cctv_list
        locations = []
        for cctv in self.cctv_list:
            location = cctv['location']
            if location not in locations:
                locations.append(location)
        
        # Urutkan lokasi agar lebih rapi
        locations.sort()
        
        categories = [
            {'type_id': 'all', 'type_name': '📹 SEMUA CCTV'}
        ]
        
        for loc in locations:
            # Buat type_id yang unik dan mudah dibaca
            # Gunakan index untuk memastikan unik
            clean_id = loc.replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '').replace('__', '_')
            # Hapus karakter khusus
            clean_id = re.sub(r'[^a-zA-Z0-9_]', '', clean_id)
            categories.append({
                'type_id': clean_id,
                'type_name': loc
            })
        
        return {'class': categories}
    
    def _get_cctv_data(self):
        """Data CCTV dengan URL streaming yang benar"""
        cctv_data = []
        idx = 1
        
        # Mapping nama lokasi ke kode stream
        stream_mapping = {
            "CCTV Simpang SDN 01 Sanggau": {
                "code": "sdn01",
                "cameras": [1, 2, 3, 4],
                "directions": {
                    1: "Arah Sekadau",
                    2: "Arah Ilir Kota/Pasar Senggol", 
                    3: "Arah Bunut/Pontianak",
                    4: "Arah SMP Negeri 2 Sanggau"
                },
                "address": "Jl. Dewi Sartika, Ilir Kota, Kec. Kapuas"
            },
            "CCTV Simpang Tugu Rambai Ilir Kota": {
                "code": "b_rambai",
                "cameras": [1, 2, 3, 4],
                "directions": {
                    1: "Arah Sanggau Permai",
                    2: "Arah Jl. Rambai",
                    3: "Arah Bunut / Pontianak",
                    4: "Arah Sekadau"
                },
                "address": "Jl. Rambai, Kec. Kapuas"
            },
            "CCTV Tugu Dekranasda": {
                "code": "dekra",
                "cameras": [1, 2, 3],
                "directions": {
                    1: "Arah Sekadau",
                    2: "Arah Kodim 1204 Sanggau",
                    3: "Arah Sanggau Kota/Pontianak"
                },
                "address": "Tanjung Sekayam, Sanggau Kota"
            },
            "CCTV Simpang Tiga Kantor Bupati": {
                "code": "taman-gpu",
                "cameras": [1],
                "directions": {1: "Arah Lapangan Tenis/SMP Kristen Torsina"},
                "address": "Ilir Kota, Kec. Kapuas"
            },
            "CCTV Taman Aronk Belopa": {
                "code": "aronk",
                "cameras": [1, 2, 3, 4, 5, 6],
                "directions": {
                    1: "Jl. Jend. Sudirman, Arah Sekadau",
                    2: "Parkir Sebelah Timur",
                    3: "Jl. Jend. Sudirman, Arah Pontianak",
                    4: "Pos Jaga",
                    5: "Parkiran Sebelah Barat",
                    6: "Taman / Patung air pancur"
                },
                "address": "Taman Arongk Belopa Kota Sanggau"
            },
            "CCTV Simpang Sabang Merah": {
                "code": "sp3-samer",
                "cameras": [1],
                "directions": {1: "Arah Pontianak"},
                "address": "Bunut, Kec. Kapuas"
            },
            "CCTV Simpang Pasar Sentral": {
                "code": "sp4-sentral",
                "cameras": [1, 2, 3, 4],
                "directions": {
                    1: "Arah Mungguk Badang",
                    2: "Arah Beringin/Pasar Sentral",
                    3: "Arah Sekadau",
                    4: "Arah Pontianak"
                },
                "address": "Jl. Jenderal Sudirman"
            },
            "CCTV Simpang RSUD M. Th. Djaman Sanggau (Bunut)": {
                "code": "sp3-rsudbunut",
                "cameras": [1],
                "directions": {1: "Simpang Tiga RSUD/Aming Coffee Shop"},
                "address": "Jl. Jend. Sudirman, Bunut"
            },
            "CCTV Bundaran Sanggau Permai": {
                "code": "spermai",
                "cameras": [1, 2, 3],
                "directions": {
                    1: "Arah Pusat Kota Sanggau",
                    2: "Arah Laverna/Sabang Merah",
                    3: "Arah GOR Sanggau Permai"
                },
                "address": "Sanggau Permai"
            },
            "CCTV Simpang RSUD Lama (Jl. Sutan Syahrir)": {
                "code": "rsud_lama",
                "cameras": [1],
                "directions": {1: "Simpang Jl. Sutan Syahrir/Alfamart"},
                "address": "Jl. Jend. Sudirman, Ilir Kota"
            }
        }
        
        # Generate daftar CCTV dengan URL stream yang benar
        for location_name, config in stream_mapping.items():
            for cam_num in config['cameras']:
                # URL stream dengan format yang benar
                stream_url = f"{self.stream_host}/hls/{config['code']}_{cam_num}/stream.m3u8"
                
                direction = config['directions'].get(cam_num, f"CAM {cam_num}")
                
                # Nama video yang lebih bersih
                video_name = f"{location_name} - CAM {cam_num}"
                if direction and direction != f"CAM {cam_num}":
                    video_name += f" ({direction})"
                
                cctv_data.append({
                    'vod_id': str(idx),
                    'vod_name': video_name,
                    'vod_pic': self.cctv_icon,
                    'vod_remarks': '🟢 LIVE',
                    'vod_year': '2026',
                    'vod_area': 'Kabupaten Sanggau',
                    'vod_content': (
                        f"📍 {location_name}\n\n"
                        f"🎥 CAM {cam_num}: {direction}\n\n"
                        f"🏠 Alamat: {config['address']}\n\n"
                        f"🚦 Dinas Komunikasi dan Informatika Kab. Sanggau"
                    ),
                    'vod_play_from': 'Cinta Dilan',
                    'vod_play_url': f"{video_name}${stream_url}",
                    'location': location_name,
                    'cam_num': cam_num,
                    'direction': direction,
                    'stream_url': stream_url
                })
                idx += 1
        
        return cctv_data
    
    def homeVideoContent(self):
        """Menampilkan semua CCTV"""
        return {
            'list': self.cctv_list,
            'page': 1,
            'pagecount': 1,
            'limit': 100,
            'total': len(self.cctv_list)
        }
    
    def categoryContent(self, tid, pg, filter, ext):
        """Filter berdasarkan kategori/lokasi"""
        # Debug: print untuk melihat tid yang diterima
        print(f"CategoryContent called with tid: {tid}")
        
        if tid == 'all' or not tid:
            return self.homeVideoContent()
        
        # Cari semua CCTV dengan lokasi yang cocok
        # Kita perlu mencocokkan tid dengan nama lokasi yang sudah dibersihkan
        filtered = []
        
        for cctv in self.cctv_list:
            # Buat clean version dari location
            clean_location = cctv['location'].replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '').replace('__', '_')
            clean_location = re.sub(r'[^a-zA-Z0-9_]', '', clean_location)
            
            # Debug: print untuk melihat perbandingan
            print(f"Comparing: {tid} vs {clean_location} for {cctv['location']}")
            
            if clean_location == tid:
                filtered.append(cctv)
        
        # Jika tidak ada yang cocok, coba dengan pencarian substring
        if not filtered:
            for cctv in self.cctv_list:
                if tid.lower() in cctv['location'].lower().replace(' ', '_').replace('/', '_'):
                    filtered.append(cctv)
        
        print(f"Found {len(filtered)} videos for category {tid}")
        
        return {
            'list': filtered,
            'page': 1,
            'pagecount': 1,
            'limit': 100,
            'total': len(filtered)
        }
    
    def detailContent(self, ids):
        """Detail CCTV berdasarkan ID"""
        if not ids:
            return {'list': []}
        
        vod_id = ids[0]
        
        for cctv in self.cctv_list:
            if cctv['vod_id'] == vod_id:
                return {'list': [cctv]}
        
        return {'list': []}
    
    def playerContent(self, flag, id, vipFlags):
        """Player untuk streaming"""
        return {
            'parse': 0,
            'url': id,
            'header': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': self.site,
                'Origin': self.site,
                'Accept': '*/*',
                'Connection': 'keep-alive'
            }
        }
    
    def searchContent(self, key, quick, pg="1"):
        """Pencarian CCTV"""
        if not key:
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 100, 'total': 0}
        
        key_lower = key.lower()
        filtered = []
        for cctv in self.cctv_list:
            if key_lower in cctv['vod_name'].lower() or key_lower in cctv['location'].lower():
                filtered.append(cctv)
        
        return {
            'list': filtered,
            'page': 1,
            'pagecount': 1,
            'limit': 100,
            'total': len(filtered)
        }
    
    def destroy(self):
        pass