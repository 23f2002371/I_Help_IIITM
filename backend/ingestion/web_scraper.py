import requests
from bs4 import BeautifulSoup
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; CourseGenieBot/1.0; +https://example.com/bot)'}
STRIP_TAGS = ['script', 'style', 'nav', 'footer', 'header', 'noscript', 'iframe', 'svg']

def fetch_and_clean(url: str, timeout: int=20) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    for tag_name in STRIP_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()
    main = soup.find('main') or soup.find('article') or soup.body or soup
    text = main.get_text(separator='\n')
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return '\n'.join(lines)