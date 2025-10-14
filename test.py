import http.client
import json
import urllib.parse
from html.parser import HTMLParser

class ArticleParser(HTMLParser):
    def init(self):
        super().init()
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
        while self.tag_stack and self.tag_stack.pop() != tag:
            pass
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
                self.article_text += stripped_data + ' '
                self.text_length = len(self.article_text)

TOKEN = "8399667774:AAEYrsNonQW0t8wKZhhvAoLzr1BUbtH3WL4"
BASE_URL = "api.telegram.org"

def get_updates(offset=None):
    conn = http.client.HTTPSConnection(BASE_URL)
    url = f"/bot{TOKEN}/getUpdates?timeout=100"
    if offset:
        url += f"&offset={offset}"
    conn.request("GET", url)
    response = conn.getresponse()
    return json.loads(response.read().decode())

def send_message(chat_id, text):
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

def fetch_url(url):
    try:
        parsed = urllib.parse.urlparse(url)
        conn = http.client.HTTPSConnection(parsed.netloc)
        conn.request("GET", parsed.path)
        response = conn.getresponse()
        return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return None

def parse_article(html):
    parser = ArticleParser()
    parser.feed(html)
    return parser.article_title, parser.article_text.strip()

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
                            title, content = parse_article(html)
                            response = f"Заголовок: {title}\n\nТекст: {content[:1000]}..."
                        else:
                            response = "Ошибка при загрузке страницы"
                    else:
                        response = "Отправьте URL страницы для парсинга"

                    send_message(chat_id, response)

if name == "main":
    main()
