import duckdb
import json
import os
import sys
import urllib.request
import pandas as pd
from datetime import datetime

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

data_file = 'data.json'
meta_url = "https://huggingface.co/datasets/th1nhng0/vietnamese-legal-documents/resolve/main/data/metadata.parquet"
content_url = "https://huggingface.co/datasets/th1nhng0/vietnamese-legal-documents/resolve/main/data/content.parquet"

# Path to the local content.parquet in scratch directory
local_content_file = "C:/Users/wangg/.gemini/antigravity/brain/0cc7eb56-d0a3-47ca-a887-744c52a82f76/scratch/content.parquet"

print("Connecting to DuckDB...")
con = duckdb.connect()

print("Loading metadata...")
df = con.execute(f"SELECT * FROM read_parquet('{meta_url}')").df()
print(f"Total metadata records: {len(df)}")

# Extract year
def get_year(date_str):
    try:
        if not date_str or date_str == '—': return 0
        parts = date_str.split('/')
        if len(parts) == 3:
            return int(parts[2].strip())
    except:
        pass
    return 0

df['year'] = df['ngay_ban_hanh'].apply(get_year)

# Filter 2019 to current
df_recent = df[df['year'] >= 2019].copy()
print(f"Documents from 2019 to now: {len(df_recent)}")

# Keywords from context.md
LAND_KEYWORDS = [
    "đất đai", "quyền sử dụng đất", "giao đất", "thu hồi đất", "bồi thường", "tái định cư",
    "sổ đỏ", "quy hoạch sử dụng đất", "địa giới hành chính đất đai"
]

GEO_KEYWORDS = [
    "địa chính", "bản đồ địa chính", "đo đạc", "cadastral", "hồ sơ địa chính", 
    "đăng ký đất đai", "thông tin đất đai", "cơ sở dữ liệu đất đai", "trắc địa"
]

AGRI_KEYWORDS = [
    "nông nghiệp", "nông thôn", "trồng trọt", "chăn nuôi", "thủy sản", "lâm nghiệp",
    "cây trồng", "vật nuôi", "khuyến nông", "bảo vệ thực vật", "thú y", 
    "hợp tác xã nông nghiệp", "phát triển nông thôn"
]

ALL_KEYWORDS = LAND_KEYWORDS + GEO_KEYWORDS + AGRI_KEYWORDS

def score_metadata(row):
    title = str(row['title']).lower()
    nganh = str(row['nganh']).lower()
    linh_vuc = str(row['linh_vuc']).lower()
    
    score = 0
    matched_kws = []
    
    for kw in ALL_KEYWORDS:
        if kw in linh_vuc:
            score += 5
            matched_kws.append(f"linh_vuc:{kw}")
        if kw in nganh:
            score += 5
            matched_kws.append(f"nganh:{kw}")
        if kw in title:
            score += 4
            matched_kws.append(f"title:{kw}")
            
    return score, matched_kws

print("Calculating domain matches based on metadata...")
res = df_recent.apply(score_metadata, axis=1)
df_recent['score'] = [r[0] for r in res]
df_recent['matches'] = [r[1] for r in res]

df_matched = df_recent[df_recent['score'] >= 5].copy()
print(f"Matched candidate documents with score >= 5: {len(df_matched)}")

# Download content.parquet locally if it does not exist
if not os.path.exists(local_content_file):
    print("Local content.parquet not found. Downloading...")
    os.makedirs(os.path.dirname(local_content_file), exist_ok=True)
    def report_progress(block_num, block_size, total_size):
        downloaded = block_num * block_size
        percent = (downloaded / total_size) * 100 if total_size > 0 else 0
        if block_num % 500 == 0:
            print(f"Downloaded: {downloaded/(1024*1024):.2f} MB / {total_size/(1024*1024):.2f} MB ({percent:.1f}%)")
    urllib.request.urlretrieve(content_url, local_content_file, reporthook=report_progress)
    print("Download completed successfully!")

# Register df_matched as virtual table in DuckDB
con.register("matched_meta", df_matched)

# Fetch contents for matched IDs locally
print("Querying full text content for matches via local DuckDB...")
content_query = f"""
SELECT 
    m.id,
    m.title as tieuDe,
    m.so_ky_hieu as soHieu,
    m.ngay_ban_hanh as ngayBanHanh,
    m.loai_van_ban as loaiVanBan,
    m.ngay_co_hieu_luc as ngayHieuLuc,
    m.co_quan_ban_hanh as coQuanBanHanh,
    m.tinh_trang_hieu_luc as tinhTrang,
    m.nganh,
    m.linh_vuc as linhVuc,
    c.content_html as noiDung
FROM matched_meta m
JOIN read_parquet('{local_content_file}') c ON m.id::VARCHAR = c.id::VARCHAR
"""
df_final = con.execute(content_query).df()
print(f"Successfully loaded full content locally for {len(df_final)} documents.")

# Fill NaNs
df_final = df_final.fillna('')

# Convert and save
new_docs = []
for _, row in df_final.iterrows():
    co_quan = str(row['coQuanBanHanh']).split('/')[0].strip() if row['coQuanBanHanh'] else '—'
    doc = {
        "id": str(row['id']),
        "url": f"http://127.0.0.1:5500/detail.html?src=api&id={row['id']}",
        "tieuDe": str(row['tieuDe']).strip(),
        "soHieu": str(row['soHieu']).strip() or '—',
        "ngayBanHanh": str(row['ngayBanHanh']).strip() or '—',
        "ngayHieuLuc": str(row['ngayHieuLuc']).strip() or '—',
        "loaiVanBan": str(row['loaiVanBan']).strip() or '—',
        "coQuanBanHanh": co_quan,
        "tinhTrang": str(row['tinhTrang']).strip() or '—',
        "nganh": str(row['nganh']).strip(),
        "linhVuc": str(row['linhVuc']).strip(),
        "noiDung": str(row['noiDung']).strip()
    }
    new_docs.append(doc)

# Sort descending
def parse_date(date_str):
    try:
        if not date_str or date_str == '—': return datetime(1900,1,1)
        parts = date_str.split('/')
        if len(parts) == 3:
            return datetime(int(parts[2]), int(parts[1]), int(parts[0]))
    except:
        pass
    return datetime(1900,1,1)

new_docs.sort(key=lambda d: parse_date(d['ngayBanHanh']), reverse=True)

# Statistics
tong = len(new_docs)
dat_dai = 0
nong_nghiep = 0
dia_chinh = 0

for d in new_docs:
    td = d['tieuDe'].lower()
    ng = d['nganh'].lower()
    lv = d['linhVuc'].lower()
    
    is_dat_dai = False
    is_nong_nghiep = False
    is_dia_chinh = False
    
    for kw in LAND_KEYWORDS:
        if kw in td or kw in ng or kw in lv:
            is_dat_dai = True
            break
            
    for kw in AGRI_KEYWORDS:
        if kw in td or kw in ng or kw in lv:
            is_nong_nghiep = True
            break
            
    for kw in GEO_KEYWORDS:
        if kw in td or kw in ng or kw in lv:
            is_dia_chinh = True
            break
            
    if is_dat_dai: dat_dai += 1
    if is_nong_nghiep: nong_nghiep += 1
    if is_dia_chinh: dia_chinh += 1

con_hl = sum(1 for d in new_docs if 'còn hiệu lực' in d['tinhTrang'].lower())
het_hl = sum(1 for d in new_docs if 'hết hiệu lực' in d['tinhTrang'].lower())

if os.path.exists(data_file):
    with open(data_file, 'r', encoding='utf-8') as f:
        existing_data = json.load(f)
else:
    existing_data = {}

local_data = {
    "vanban": new_docs,
    "thongKe": {
        "tongVanBan": tong,
        "vanBanDatDai": dat_dai,
        "vanBanNongNghiep": nong_nghiep,
        "vanBanDiaChinh": dia_chinh,
        "vanBanConHieuLuc": con_hl,
        "vanBanHetHieuLuc": het_hl
    },
    "linhVuc": existing_data.get("linhVuc", []),
    "khuVuc": existing_data.get("khuVuc", [])
}

with open(data_file, 'w', encoding='utf-8') as f:
    json.dump(local_data, f, ensure_ascii=False, indent=2)

print(f"Successfully finished! Processed and saved {tong} documents to data.json.")
