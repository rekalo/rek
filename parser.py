1. Модуль парсера новостей (news_parser.py)
python
import re
import urllib.parse
import http.client
from html.parser import HTMLParser

class NewsParser(HTMLParser):
    """
    Парсер HTML для извлечения новостей с itproger.com
    Находит заголовки, описания и ссылки на статьи
    """
    def __init__(self):
        super().__init__()
        self.articles = []
        self.current_article = {}
        self.in_article = False
        self.in_title_span = False
        self.in_description = False
        self.title_collected = False
        self.description_collected = False
        self.in_link = False
        self.current_link = ""
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        if tag == 'div' and attrs_dict.get('class') == 'article':
            self.in_article = True
            self.current_article = {}
            self.title_collected = False
            self.description_collected = False
            
        elif tag == 'span' and self.in_article and not self.title_collected:
            self.in_title_span = True
            
        elif tag == 'span' and self.in_article and self.title_collected and not self.description_collected:
            self.in_description = True
            
        elif tag == 'a' and self.in_article:
            self.in_link = True
            href = attrs_dict.get('href', '')
            if href:
                # Исправляем ссылки - добавляем базовый URL если нужно
                if href.startswith('//'):
                    href = 'https:' + href
                elif href.startswith('/'):
                    href = 'https://itproger.com' + href
                elif not href.startswith('http'):
                    href = 'https://itproger.com/' + href.lstrip('/')
                
                # Нормализуем URL (исправляем двойные слэши и т.д.)
                href = self.normalize_url(href)
            self.current_link = href

    def normalize_url(self, url):
        """Нормализует URL, исправляя проблемы со слэшами"""
        if not url:
            return url
            
        # Заменяем двойные слэши (кроме протокола)
        parts = url.split('://', 1)
        if len(parts) == 2:
            protocol, path = parts
            path = re.sub(r'/+', '/', path)  # Заменяем множественные слэши на один
            url = protocol + '://' + path
        
        # Убеждаемся, что в пути нет двойных слэшей
        url = re.sub(r'(?<!:)/{2,}', '/', url)
        
        return url

    def handle_endtag(self, tag):
        if tag == 'div' and self.in_article:
            if self.current_article and ('title' in self.current_article or 'description' in self.current_article):
                if 'link' not in self.current_article and self.current_link:
                    self.current_article['link'] = self.current_link
                self.articles.append(self.current_article.copy())
            self.in_article = False
            self.current_article = {}
        elif tag == 'span':
            self.in_title_span = False
            self.in_description = False
        elif tag == 'a':
            self.in_link = False

    def handle_data(self, data):
        data = data.strip()
        if not data:
            return
            
        if self.in_title_span and self.in_article and not self.title_collected:
            self.current_article['title'] = data
            self.title_collected = True
                
        elif self.in_description and self.in_article and not self.description_collected:
            self.current_article['description'] = data
            self.description_collected = True

def normalize_url(url):
    """Нормализует URL, исправляя проблемы со слэшами"""
    if not url:
        return url
        
    # Заменяем двойные слэши (кроме протокола)
    parts = url.split('://', 1)
    if len(parts) == 2:
        protocol, path = parts
        path = re.sub(r'/+', '/', path)
        url = protocol + '://' + path
    
    url = re.sub(r'(?<!:)/{2,}', '/', url)
    
    return url

def fetch_url(url):
    """
    Загружает HTML содержимое по URL
    Возвращает текст страницы или None при ошибке
    """
    try:
        url = normalize_url(url)
        parsed = urllib.parse.urlparse(url)
        conn = http.client.HTTPSConnection(parsed.netloc)
        path = parsed.path
        if parsed.query:
            path += '?' + parsed.query
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        conn.request("GET", path, headers=headers)
        response = conn.getresponse()
        
        if response.status == 200:
            return response.read().decode('utf-8', errors='ignore')
        else:
            print(f"HTTP ошибка: {response.status} для URL: {url}")
            return None
    except Exception as e:
        print(f"Ошибка загрузки URL {url}: {e}")
        return None

def parse_news(html):
    """
    Основная функция парсинга новостей
    Принимает HTML, возвращает список статей
    """
    parser = NewsParser()
    parser.feed(html)
    return parser.articles

def get_itproger_news(use_cache=True, get_cached_news_func=None):
    """
    Получает новости с itproger.com/news
    Может использовать кеш или загружать свежие данные
    """
    if use_cache and get_cached_news_func:
        cached_news = get_cached_news_func()
        if cached_news:
            print("Используются кешированные новости")
            return cached_news
    
    html = fetch_url("https://itproger.com/news")
    if html:
        articles = parse_news(html)
        return articles
    else:
        return get_cached_news_func() if get_cached_news_func else []
