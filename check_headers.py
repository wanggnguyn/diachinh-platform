import urllib.request
import urllib.error
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

try:
    # Use a real user agent to prevent basic blocks
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    req = urllib.request.Request("https://quyhoach.hanoi.gov.vn/quyhoach", method='HEAD', headers=headers)
    with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
        headers = response.info()
        print("HEADERS:")
        print(headers)
except urllib.error.URLError as e:
    print(f"Error: {e}")
