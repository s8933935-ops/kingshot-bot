import urllib.request
import os

url = 'https://kingshotdata.com/icons/yeonwoo-avatar.png'
dest = r'web_tierlist\icons\yeonwoo.png'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = resp.read()
        with open(dest, 'wb') as f:
            f.write(data)
        print(f"Downloaded Yeonwoo avatar: {len(data)} bytes")
except Exception as e:
    print("Error:", e)
