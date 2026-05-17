import json
import os
import sys
import re
import time
import urllib.request
import urllib.parse

# Ensure standard UTF-8 console output
sys.stdout.reconfigure(encoding='utf-8')

metadata_file = 'data/metadata.json'
articles_dir = 'articles'
progress_file = 'supplement_progress.json'

def remove_vietnamese_accents(s):
    s = s.lower()
    s = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', s)
    s = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', s)
    s = re.sub(r'[ìíịỉĩ]', 'i', s)
    s = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', s)
    s = re.sub(r'[ùúụủũưừứựửữ]', 'u', s)
    s = re.sub(r'[ỳýỵỷỹ]', 'y', s)
    s = re.sub(r'[đ]', 'd', s)
    return s

def extract_province_slug(tieu_de):
    """
    Extract key province/city name from title and return lowercase slug
    e.g. "tỉnh Gia Lai" -> "gia-lai"
    """
    tieu_de_lower = tieu_de.lower()
    provinces = [
        "an giang", "ba ria vung tau", "bac giang", "bac kan", "bac lieu", "bac ninh",
        "ben tre", "binh dinh", "binh duong", "binh phuoc", "binh thuan", "ca mau",
        "can tho", "cao bang", "da nang", "dak lak", "dak nong", "dien bien",
        "dong nai", "dong thap", "gia lai", "ha giang", "ha nam", "ha noi",
        "ha tinh", "hai duong", "hai phong", "hau giang", "hoa binh", "hung yen",
        "khanh hoa", "kien giang", "kon tum", "lai chau", "lam dong", "lang son",
        "lao cai", "long an", "nam dinh", "nghe an", "ninh binh", "ninh thuan",
        "phu tho", "phu yen", "quang binh", "quang nam", "quang ngai", "quang ninh",
        "quang tri", "soc trang", "son la", "tay ninh", "thai binh", "thai nguyen",
        "thanh hoa", "thua thien hue", "tien giang", "toan quoc", "tra vinh",
        "tuyen quang", "vinh long", "vinh phuc", "yen bai"
    ]
    
    # Remove accents for search
    normalized_title = remove_vietnamese_accents(tieu_de_lower)
    for p in provinces:
        if p in normalized_title:
            return p.replace(' ', '-')
    return None

def load_metadata():
    if not os.path.exists(metadata_file):
        print(f"Error: {metadata_file} not found! Please run split_database.py first.")
        sys.exit(1)
    with open(metadata_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_article(doc_id):
    path = os.path.join(articles_dir, f"{doc_id}.json")
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_article(doc_id, doc_data):
    path = os.path.join(articles_dir, f"{doc_id}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(doc_data, f, ensure_ascii=False, indent=2)

def load_progress():
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"completed": [], "skipped": []}

def save_progress(progress):
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

def search_yahoo(query):
    """
    Search Yahoo Search which is extremely permissive and rate-limit free
    """
    encoded_query = urllib.parse.quote(query)
    search_url = f"https://search.yahoo.com/search?p={encoded_query}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    req = urllib.request.Request(search_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            html = response.read().decode('utf-8')
            
            # Find outbound redirect URLs or direct URLs
            urls = []
            # Extract RU= components
            ru_matches = re.findall(r'RU=([^/]+)', html)
            for match in ru_matches:
                decoded = urllib.parse.unquote(match)
                if 'thuvienphapluat.vn/van-ban/' in decoded:
                    urls.append(decoded)
            
            # Extract direct links
            direct_matches = re.findall(r'href="(https?://(?:m\.)?thuvienphapluat\.vn/van-ban/[^"]+?\.aspx)"', html)
            for match in direct_matches:
                urls.append(match)
                
            return list(set(urls))
    except Exception as e:
        print(f"  [Yahoo Search Error] {e}")
        return []

def search_ddg_clean(query):
    """
    Search DuckDuckGo with ultra-cleaned queries to avoid 403 blocks
    """
    # Clean query of special chars
    query_clean = re.sub(r'[^\w\s\.\/\-\:]', '', query)
    encoded_query = urllib.parse.quote(query_clean)
    search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    req = urllib.request.Request(search_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            
            # Find outbound redirect URLs
            urls = re.findall(r'uddg=([^&"\']+)', html)
            found_urls = []
            for url in urls:
                decoded = urllib.parse.unquote(url)
                if 'thuvienphapluat.vn/van-ban/' in decoded:
                    found_urls.append(decoded)
            return found_urls
    except Exception as e:
        print(f"  [DDG Search Error] {e}")
        return []

def resolve_best_url(urls, so_hieu, tieu_de):
    """
    Intelligently select and score the best URL from candidates
    """
    if not urls:
        return None
        
    province_slug = extract_province_slug(tieu_de)
    
    # Try to extract year from title or so_hieu
    year_match = re.search(r'\b(2019|2020|2021|2022|2023|2024|2025|2026)\b', tieu_de + " " + so_hieu)
    doc_year = year_match.group(1) if year_match else None
    
    # Try to extract number from so_hieu (e.g. "31/2026/QĐ-UBND" -> "31")
    num_match = re.search(r'\b(\d+)\b', so_hieu)
    doc_num = num_match.group(1) if num_match else None
    
    best_url = None
    best_score = -9999
    
    for url in urls:
        # Standardize url for mobile/desktop
        std_url = url.replace('m.thuvienphapluat.vn', 'thuvienphapluat.vn')
        
        # Skip translation pages
        if '/tieng-anh.aspx' in std_url:
            continue
            
        score = 0
        url_lower = std_url.lower()
        
        # 1. Match province slug
        if province_slug:
            # Normalized search for province slug in URL
            clean_prov = province_slug.replace('-', '')
            clean_url = url_lower.replace('-', '').replace('_', '')
            if province_slug in url_lower:
                score += 50
            elif clean_prov in clean_url:
                score += 30
            else:
                score -= 500 # Strict penalty for mismatching province!
                
        # 2. Match number (e.g. "31-2026" or "31")
        if doc_num:
            if f"-{doc_num}-" in url_lower or f"_{doc_num}_" in url_lower or f"/{doc_num}/" in url_lower or url_lower.endswith(f"-{doc_num}.aspx"):
                score += 30
            elif doc_num in url_lower:
                score += 15
                
        # 3. Match year
        if doc_year:
            if doc_year in url_lower:
                score += 20
                
        if score > best_score:
            best_score = score
            best_url = std_url
            
    print(f"  -> Evaluated {len(urls)} candidates. Best match score: {best_score}")
    # Threshold to prevent completely wrong matches
    if best_score < 0 and province_slug is not None:
        print("  -> Best score too low (unmatched province). Rejecting candidates.")
        return None
    return best_url

def fetch_and_extract_content(url):
    """
    Fetch thuvienphapluat.vn page and extract HTML inside <div class="content1">...</div>
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8')
            
            # Match <div class="content1"> using a quick stack-based tracker
            start_idx = html.find('class="content1"')
            if start_idx == -1:
                start_idx = html.find("class='content1'")
                
            if start_idx != -1:
                div_start = html.rfind('<div', 0, start_idx)
                if div_start != -1:
                    open_divs = 1
                    curr_pos = div_start + 4
                    while open_divs > 0 and curr_pos < len(html):
                        next_open = html.find('<div', curr_pos)
                        next_close = html.find('</div>', curr_pos)
                        
                        if next_close == -1:
                            break
                            
                        if next_open != -1 and next_open < next_close:
                            open_divs += 1
                            curr_pos = next_open + 4
                        else:
                            open_divs -= 1
                            curr_pos = next_close + 6
                            
                    extracted = html[div_start:curr_pos]
                    return extracted
            return None
    except Exception as e:
        print(f"  [Fetch Error] {e}")
        return None

def main():
    print("=================================================================")
    print("      DECENTRALIZED CRAWLER & DATA SUPPLEMENTER (OPTIMIZED)      ")
    print("=================================================================")
    
    # Load metadata index
    metadata = load_metadata()
    progress = load_progress()
    
    docs = metadata.get('vanban', [])
    completed_ids = set(progress.get("completed", []))
    skipped_ids = set()
    progress["skipped"] = []
    
    # Identify placeholder documents (< 1500 characters) by looking inside /articles/<id>.json
    targets = []
    print("Scanning /articles/ to identify placeholder documents...")
    for doc in docs:
        doc_id = str(doc.get('id'))
        if doc_id in completed_ids:
            continue
            
        article = load_article(doc_id)
        if not article:
            continue
            
        content_len = len(article.get('noiDung', ''))
        
        # Target if short
        if content_len < 1500:
            targets.append(article)
            
    total_targets = len(targets)
    print(f"Total documents in metadata index: {len(docs)}")
    print(f"Total placeholder/short articles identified: {total_targets}")
    print(f"Already completed in progress: {len(completed_ids)}")
    print("-----------------------------------------------------------------")
    
    if not targets:
        print("All placeholder documents have already been successfully updated!")
        return
        
    print(f"Starting auto-supplementing of {total_targets} documents...")
    print("Press Ctrl+C at any time to safely pause the script.")
    print("-----------------------------------------------------------------")
    
    success_count = 0
    try:
        for idx, doc in enumerate(targets):
            doc_id = str(doc.get('id'))
            so_hieu = doc.get('soHieu', '')
            tieu_de = doc.get('tieuDe', '')
            province_slug = extract_province_slug(tieu_de) or "Unknown"
            
            print(f"[{idx+1}/{total_targets}] Processing ID: {doc_id} | Province: {province_slug} | SoHieu: {so_hieu} | {tieu_de[:50]}...")
            
            # Step 1: Resolve outbound URLs from Yahoo Search
            query_str = f"site:thuvienphapluat.vn {so_hieu}" if so_hieu and so_hieu != '—' else f"site:thuvienphapluat.vn {tieu_de[:80]}"
            print(f"  -> Yahoo Searching: {query_str}")
            urls = search_yahoo(query_str)
            
            # Fallback to DDG if Yahoo yields nothing
            if not urls:
                print("  -> Yahoo yielded nothing. Falling back to clean DuckDuckGo...")
                urls = search_ddg_clean(query_str)
                
            # Step 2: Resolve the single best URL
            best_url = resolve_best_url(urls, so_hieu, tieu_de)
            
            if not best_url:
                print("  -> Could not resolve correct thuvienphapluat.vn URL. Skipping.")
                progress["skipped"].append(doc_id)
                save_progress(progress)
                time.sleep(1)
                continue
                
            # Step 3: Fetch and extract from resolved URL
            print(f"  -> Fetching and Parsing: {best_url}")
            extracted_html = fetch_and_extract_content(best_url)
            
            if extracted_html:
                # Update individual article file directly
                doc['noiDung'] = extracted_html
                save_article(doc_id, doc)
                print(f"  -> Successfully extracted & saved {len(extracted_html)} chars to articles/{doc_id}.json!")
                
                # Mark as completed
                progress["completed"].append(doc_id)
                success_count += 1
                
                # Save progress
                save_progress(progress)
                print("  -> Progress updated successfully!")
            else:
                print("  -> Failed to extract HTML structure from page. Skipping.")
                progress["skipped"].append(doc_id)
                save_progress(progress)
                
            # Respectful delay between requests
            time.sleep(3)
            
    except KeyboardInterrupt:
        print("\n[Paused] Script paused safely by user request. All processed data remains fully saved on disk.")
    
    print("\n-----------------------------------------------------------------")
    print(f"Run summary: Successfully supplemented {success_count} documents in this run!")
    print("=================================================================")

if __name__ == '__main__':
    main()
