import http.client
import json
import urllib.parse
from html.parser import HTMLParser
import time

class NewsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.articles = []
        self.current_article = {}
        self.in_article = False
        self.in_title_span = False
        self.in_description = False
        self.title_collected = False
        self.description_collected = False
        
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

    def handle_endtag(self, tag):
        if tag == 'div' and self.in_article:
            if self.current_article and ('title' in self.current_article or 'description' in self.current_article):
                self.articles.append(self.current_article.copy())
            self.in_article = False
            self.current_article = {}
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

# Настройки бота
TOKEN = "8399667774:AAEYrsNonQW0t8wKZhhvAoLzr1BUbtH3WL4"
BASE_URL = "api.telegram.org"

def get_updates(offset=None):
    try:
        conn = http.client.HTTPSConnection(BASE_URL)
        url = f"/bot{TOKEN}/getUpdates?timeout=60"
        if offset:
            url += f"&offset={offset}"
        conn.request("GET", url)
        response = conn.getresponse()
        data = response.read().decode()
        return json.loads(data)
    except Exception as e:
        print(f"Ошибка получения обновлений: {e}")
        return {"result": []}

def send_message(chat_id, text):
    try:
        # Ограничение длины сообщения для Telegram
        if len(text) > 4096:
            text = text[:4090] + "..."
            
        conn = http.client.HTTPSConnection(BASE_URL)
        url = f"/bot{TOKEN}/sendMessage"
        params = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        headers = {'Content-type': 'application/json'}
        conn.request("POST", url, json.dumps(params), headers)
        response = conn.getresponse()
        return response.read()
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")
        return None

def fetch_url(url):
    try:
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
            print(f"HTTP ошибка: {response.status}")
            return None
    except Exception as e:
        print(f"Ошибка загрузки URL: {e}")
        return None

def parse_news(html):
    parser = NewsParser()
    parser.feed(html)
    return parser.articles

def format_articles_response(articles):
    if not articles:
        return "❌ Не удалось найти статьи на странице"
    
    response = "📰 <b>Последние новости с itProger:</b>\n\n"
    
    for i, article in enumerate(articles, 1):
        title = article.get('title', 'Без заголовка')
        description = article.get('description', 'Без описания')
        
        response += f"<b>{i}. {title}</b>\n"
        response += f"<i>📝 {description}</i>\n\n"
        
        # Если сообщение становится слишком длинным, отправляем текущее и начинаем новое
        if len(response) > 3500:
            response += "... и другие статьи"
            break
    
    return response

def get_itproger_news():
    """Функция для получения новостей с itproger.com/news"""
    html = fetch_url("https://itproger.com/news")
    if html:
        articles = parse_news(html)
        return format_articles_response(articles)
    else:
        return "❌ Ошибка при загрузке новостей с itproger.com"

def main():
    print("Бот запущен! Ожидание сообщений...")
    offset = 0
    
    while True:
        try:
            updates = get_updates(offset)
            
            if "result" in updates:
                for update in updates["result"]:
                    offset = update["update_id"] + 1
                    
                    if "message" in update and "text" in update["message"]:
                        message = update["message"]
                        chat_id = message["chat"]["id"]
                        text = message["text"].strip()
                        
                        print(f"Получено сообщение от {chat_id}: {text}")
                        
                        if text.startswith("http"):
                            # Парсинг по ссылке
                            html = fetch_url(text)
                            if html:
                                if "itproger.com/news" in text:
                                    articles = parse_news(html)
                                    response = format_articles_response(articles)
                                else:
                                    response = "🔗 Я специализируюсь на парсинге itproger.com/news\nОтправьте ссылку на этот сайт или команду /news"
                            else:
                                response = "❌ Ошибка при загрузке страницы. Проверьте URL."
                                
                        elif text == "/start":
                            response = """👋 <b>Привет! Я бот для парсинга новостей itProger</b>

📋 <b>Доступные команды:</b>
/news - Получить последние новости с itproger.com
/help - Показать справку

🔗 <b>Или просто отправьте ссылку:</b>
https://itproger.com/news"""
                            
                        elif text == "/news":
                            response = get_itproger_news()
                            
                        elif text == "/help":
                            response = """ℹ️ <b>Справка по боту</b>

Этот бот парсит заголовки и описания статей с сайта itproger.com/news

<b>Команды:</b>
/start - Начать работу
/news - Получить свежие новости
/help - Эта справка

<b>Также можно отправить прямую ссылку:</b>
https://itproger.com/news"""
                            
                        else:
                            response = """❌ Неизвестная команда

📋 <b>Доступные команды:</b>
/start - Начать работу
/news - Получить новости itProger
/help - Справка

🔗 <b>Или отправьте ссылку:</b>
https://itproger.com/news"""
                        
                        send_message(chat_id, response)
                        print(f"Отправлен ответ пользователю {chat_id}")
            
            # Пауза между проверками обновлений
            time.sleep(1)
            
        except Exception as e:
            print(f"Ошибка в основном цикле: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()