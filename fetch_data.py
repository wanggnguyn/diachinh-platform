import duckdb
import json
import os
import pandas as pd
from datetime import datetime

# Path to the existing data.json
data_file = 'data.json'

print("Loading existing data.json...")
with open(data_file, 'r', encoding='utf-8') as f:
    local_data = json.load(f)

# The Parquet URLs from huggingface datasets server
print("Querying HuggingFace Parquet via DuckDB...")
meta_url = "https://huggingface.co/datasets/th1nhng0/vietnamese-legal-documents/resolve/refs%2Fconvert%2Fparquet/metadata/data/0000.parquet"
content_url = "https://huggingface.co/datasets/th1nhng0/vietnamese-legal-documents/resolve/refs%2Fconvert%2Fparquet/content/data/0000.parquet"

# Use duckdb to query. It will only download the necessary chunks!
query = f"""
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
FROM read_parquet('{meta_url}') m
JOIN read_parquet('{content_url}') c ON m.id::VARCHAR = c.id::VARCHAR
WHERE 
    lower(m.title) LIKE '%đất đai%' OR
    lower(m.title) LIKE '%nông nghiệp%' OR
    lower(m.title) LIKE '%địa chính%' OR
    lower(m.title) LIKE '%quy hoạch%' OR
    lower(m.title) LIKE '%bồi thường%' OR
    lower(m.title) LIKE '%thu hồi đất%' OR
    lower(m.nganh) LIKE '%đất đai%' OR
    lower(m.nganh) LIKE '%nông nghiệp%'
"""

con = duckdb.connect()
df = con.execute(query).df()

print(f"Found {len(df)} documents matching the criteria.")

# We don't want to bloat the JSON file to gigabytes. Let's take the latest 500 documents.
def parse_date(date_str):
    try:
        if not date_str or date_str == '—': return datetime(1900,1,1)
        # Format DD/MM/YYYY
        parts = date_str.split('/')
        if len(parts) == 3:
            return datetime(int(parts[2]), int(parts[1]), int(parts[0]))
    except:
        pass
    return datetime(1900,1,1)

# Sort by date
df['parsed_date'] = df['ngayBanHanh'].apply(parse_date)
df = df.sort_values(by='parsed_date', ascending=False)

# Take top 1000
df_top = df.head(1000).copy()

# Fill NaNs with empty string
df_top = df_top.fillna('')

# Format as list of dicts
new_docs = []
for _, row in df_top.iterrows():
    doc = {
        "id": str(row['id']),
        "url": "#",
        "tieuDe": str(row['tieuDe']).strip(),
        "soHieu": str(row['soHieu']).strip() or '—',
        "ngayBanHanh": str(row['ngayBanHanh']).strip() or '—',
        "ngayHieuLuc": str(row['ngayHieuLuc']).strip() or '—',
        "loaiVanBan": str(row['loaiVanBan']).strip() or '—',
        "coQuanBanHanh": str(row['coQuanBanHanh']).split('/')[0].strip(),
        "tinhTrang": str(row['tinhTrang']).strip() or '—',
        "nganh": str(row['nganh']).strip(),
        "linhVuc": str(row['linhVuc']).strip(),
        "noiDung": str(row['noiDung']).strip()
    }
    new_docs.append(doc)

local_data['vanban'] = new_docs

# Update stats
tong = len(new_docs)
dat_dai = sum(1 for d in new_docs if 'đất' in d['tieuDe'].lower() or 'đất' in d['nganh'].lower())
nong_nghiep = sum(1 for d in new_docs if 'nông' in d['tieuDe'].lower() or 'nông' in d['nganh'].lower())
dia_chinh = sum(1 for d in new_docs if 'địa chính' in d['tieuDe'].lower() or 'địa chính' in d['nganh'].lower())
con_hl = sum(1 for d in new_docs if 'còn hiệu lực' in d['tinhTrang'].lower())
het_hl = sum(1 for d in new_docs if 'hết hiệu lực' in d['tinhTrang'].lower())

local_data['thongKe'] = {
    "tongVanBan": tong,
    "vanBanDatDai": dat_dai,
    "vanBanNongNghiep": nong_nghiep,
    "vanBanDiaChinh": dia_chinh,
    "vanBanConHieuLuc": con_hl,
    "vanBanHetHieuLuc": het_hl
}

print("Saving to data.json...")
with open(data_file, 'w', encoding='utf-8') as f:
    json.dump(local_data, f, ensure_ascii=False, indent=2)

print("Done! Check data.json.")
