import http.client
import json
import urllib.parse
from html.parser import HTMLParser

class NewsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.articles = []
        self.current_article = {}
        self.in_article = False
        self.in_title_span = False
        self.in_description = False
        self.current_tag = ""
        self.title_collected = False
        self.description_collected = False
        
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        attrs_dict = dict(attrs)
        
        if tag == 'div' and attrs_dict.get('class') == 'article':
            self.in_article = True
            self.current_article = {}
            self.title_collected = False
            self.description_collected = False
            
        elif tag == 'span' and self.in_article and not self.title_collected:
            # Это заголовок статьи
            self.in_title_span = True
            
        elif tag == 'span' and self.in_article and self.title_collected and not self.description_collected:
            # Это описание статьи (второй span после заголовка)
            self.in_description = True

    def handle_endtag(self, tag):
        if tag == 'div' and self.in_article:
            if self.current_article:
                self.articles.append(self.current_article.copy())
            self.in_article = False
        elif tag == 'span':
            self.in_title_span = False
            self.in_description = False

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

TOKEN = "8399667774:AAEYrsNonQW0t8wKZhhvAoLzr1BUbtH3WL4"
BASE_URL = "api.telegram.org"

def get_updates(offset=None):
    try:
        conn = http.client.HTTPSConnection(BASE_URL)
        url = f"/bot{TOKEN}/getUpdates?timeout=100"
        if offset:
            url += f"&offset={offset}"
        conn.request("GET", url)
        response = conn.getresponse()
        data = response.read().decode()
        return json.loads(data)
    except Exception as e:
        print(f"Error getting updates: {e}")
        return {"result": []}

def send_message(chat_id, text):
    try:
        conn = http.client.HTTPSConnection(BASE_URL)
        url = f"/bot{TOKEN}/sendMessage"
        params = {
            'chat_id': chat_id,
            'text': text
        }
        headers = {'Content-type': 'application/json'}
        conn.request("POST", url, json.dumps(params), headers)
        response = conn.getresponse()
        return response.read()
    except Exception as e:
        print(f"Error sending message: {e}")
        return None

def fetch_url(url):
    try:
        parsed = urllib.parse.urlparse(url)
        conn = http.client.HTTPSConnection(parsed.netloc)
        path = parsed.path
        if parsed.query:
            path += '?' + parsed.query
        conn.request("GET", path)
        response = conn.getresponse()
        return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error fetching URL: {e}")
        return None

def parse_news(html):
    parser = NewsParser()
    parser.feed(html)
    return parser.articles

def format_articles_response(articles):
    if not articles:
        return "Не удалось найти статьи"
    
    response = "📰 Последние новости с itProger:\n\n"
    for i, article in enumerate(articles, 1):
        title = article.get('title', 'Без заголовка')
        description = article.get('description', 'Без описания')
        response += f"{i}. {title}\n"
        response += f"   📝 {description}\n\n"
    
    # Ограничиваем длину сообщения для Telegram
    if len(response) > 4096:
        response = response[:4090] + "..."
    
    return response

class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.article_title = ""
        self.article_text = ""
        self.in_title = False
        self.in_body = False
        self.tag_stack = []
        self.text_length = 0
        self.max_text_length = 500

    def handle_starttag(self, tag, attrs):
        self.tag_stack.append(tag)
        if tag == 'title':
            self.in_title = True
        if tag == 'body':
            self.in_body = True

    def handle_endtag(self, tag):
        while self.tag_stack and self.tag_stack[-1] != tag:
            self.tag_stack.pop()
        if self.tag_stack and self.tag_stack[-1] == tag:
            self.tag_stack.pop()
        if tag == 'title':
            self.in_title = False
        if tag == 'body':
            self.in_body = False

    def handle_data(self, data):
        if self.in_title and not self.article_title:
            self.article_title = data.strip()
        if self.in_body and self.text_length < self.max_text_length:
            stripped_data = data.strip()
            if stripped_data and len(stripped_data) > 10:
                if self.text_length + len(stripped_data) < self.max_text_length:
                    self.article_text += stripped_data + ' '
                    self.text_length = len(self.article_text)
                else:
                    remaining = self.max_text_length - self.text_length
                    self.article_text += stripped_data[:remaining] + '...'
                    self.text_length = self.max_text_length

def main():
    offset = 0
    while True:
        updates = get_updates(offset)
        if "result" in updates:
            for update in updates["result"]:
                offset = update["update_id"] + 1
                if "message" in update and "text" in update["message"]:
                    message = update["message"]
                    chat_id = message["chat"]["id"]
                    text = message["text"]

                    if text.startswith("http"):
                        html = fetch_url(text)
                        if html:
                            if "itproger.com/news" in text:
                                articles = parse_news(html)
                                response = format_articles_response(articles)
                            else:
                                parser = ArticleParser()
                                parser.feed(html)
                                response_text = parser.article_text[:1000] + "..." if len(parser.article_text) > 1000 else parser.article_text
                                response = f"Заголовок: {parser.article_title}\n\nТекст: {response_text}"
                        else:
                            response = "Ошибка при загрузке страницы"
                    elif text == "/news":
                        html = fetch_url("https://itproger.com/news")
                        if html:
                            articles = parse_news(html)
                            response = format_articles_response(articles)
                        else:
                            response = "Ошибка при загрузке новостей"
                    else:
                        response = "Отправьте URL страницы для парсинга или команду /news для получения новостей itProger"

                    send_message(chat_id, response)

if __name__ == "__main__":
    main()
