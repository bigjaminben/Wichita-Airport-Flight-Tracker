"""Download brand logo into static/logo.png.

Usage: python download_logo.py
"""
import os
import requests

URL = "https://www.pngmart.com/files/23/Deloitte-Logo-PNG-Pic.png"
ROOT = os.path.dirname(__file__)
STATIC = os.path.join(ROOT, 'static')
OUT = os.path.join(STATIC, 'logo.png')

os.makedirs(STATIC, exist_ok=True)

try:
    r = requests.get(URL, timeout=20)
    r.raise_for_status()
    with open(OUT, 'wb') as f:
        f.write(r.content)
    print(f"Downloaded logo to {OUT}")
except Exception as e:
    print(f"Could not download logo: {e}")
    # If there's a failure, leave things as-is; server can run without the logo.
