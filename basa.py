import http.client
import json
import urllib.parse
from html.parser import HTMLParser
import time
import sqlite3
import datetime

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

# Инициализация базы данных
def init_database():
    conn = sqlite3.connect('news_bot.db')
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TEXT,
            last_activity TEXT
        )
    ''')
    
    # Таблица запросов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            command TEXT,
            timestamp TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Таблица новостей (кеширование)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE,
            description TEXT,
            source_url TEXT,
            parsed_at TEXT
        )
    ''')
    
    # Таблица избранных новостей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            news_title TEXT,
            saved_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("База данных инициализирована")

def save_user(user_data):
    """Сохраняет или обновляет данные пользователя"""
    conn = sqlite3.connect('news_bot.db')
    cursor = conn.cursor()
    
    now = datetime.datetime.now().isoformat()
    
    cursor.execute('''
        INSERT OR REPLACE INTO users 
        (user_id, username, first_name, last_name, created_at, last_activity) 
        VALUES (?, ?, ?, ?, COALESCE((SELECT created_at FROM users WHERE user_id = ?), ?), ?)
    ''', (
        user_data['id'],
        user_data.get('username'),
        user_data.get('first_name'),
        user_data.get('last_name'),
        user_data['id'],
        now,
        now
    ))
    
    conn.commit()
    conn.close()

def log_request(user_id, command):
    """Логирует запрос пользователя"""
    conn = sqlite3.connect('news_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO requests (user_id, command, timestamp)
        VALUES (?, ?, ?)
    ''', (user_id, command, datetime.datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def save_news_to_cache(articles):
    """Сохраняет новости в кеш"""
    conn = sqlite3.connect('news_bot.db')
    cursor = conn.cursor()
    
    now = datetime.datetime.now().isoformat()
    
    for article in articles:
        cursor.execute('''
            INSERT OR REPLACE INTO news_cache (title, description, source_url, parsed_at)
            VALUES (?, ?, ?, ?)
        ''', (
            article.get('title'),
            article.get('description'),
            'https://itproger.com/news',
            now
        ))
    
    conn.commit()
    conn.close()

def get_cached_news(limit=10):
    """Получает новости из кеша"""
    conn = sqlite3.connect('news_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT title, description FROM news_cache 
        ORDER BY parsed_at DESC 
        LIMIT ?
    ''', (limit,))
    
    articles = []
    for row in cursor.fetchall():
        articles.append({
            'title': row[0],
            'description': row[1]
        })
    
    conn.close()
    return articles

def add_to_favorites(user_id, news_title):
    """Добавляет новость в избранное"""
    conn = sqlite3.connect('news_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR IGNORE INTO favorites (user_id, news_title, saved_at)
        VALUES (?, ?, ?)
    ''', (user_id, news_title, datetime.datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def get_user_favorites(user_id):
    """Получает избранные новости пользователя"""
    conn = sqlite3.connect('news_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT news_title, saved_at FROM favorites 
        WHERE user_id = ? 
        ORDER BY saved_at DESC
    ''', (user_id,))
    
    favorites = []
    for row in cursor.fetchall():
        favorites.append({
            'title': row[0],
            'saved_at': row[1]
        })
    
    conn.close()
    return favorites

def get_user_stats(user_id):
    """Получает статистику пользователя"""
    conn = sqlite3.connect('news_bot.db')
    cursor = conn.cursor()
    
    # Количество запросов
    cursor.execute('SELECT COUNT(*) FROM requests WHERE user_id = ?', (user_id,))
    request_count = cursor.fetchone()[0]
    
    # Количество избранных
    cursor.execute('SELECT COUNT(*) FROM favorites WHERE user_id = ?', (user_id,))
    favorites_count = cursor.fetchone()[0]
    
    # Последняя активность
    cursor.execute('SELECT last_activity FROM users WHERE user_id = ?', (user_id,))
    last_activity = cursor.fetchone()
    last_activity = last_activity[0] if last_activity else "Неизвестно"
    
    conn.close()
    
    return {
        'request_count': request_count,
        'favorites_count': favorites_count,
        'last_activity': last_activity
    }

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

def format_articles_response(articles, show_numbers=True):
    if not articles:
        return "❌ Не удалось найти статьи на странице"
    
    response = "📰 <b>Последние новости с itProger:</b>\n\n"
    
    for i, article in enumerate(articles, 1):
        title = article.get('title', 'Без заголовка')
        description = article.get('description', 'Без описания')
        
        if show_numbers:
            response += f"<b>{i}. {title}</b>\n"
        else:
            response += f"<b>{title}</b>\n"
            
        response += f"<i>📝 {description}</i>\n\n"
        
        if len(response) > 3500:
            response += "... и другие статьи"
            break
    
    return response

def get_itproger_news(use_cache=True):
    """Функция для получения новостей с itproger.com/news"""
    if use_cache:
        cached_news = get_cached_news()
        if cached_news:
            print("Используются кешированные новости")
            return format_articles_response(cached_news)
    
    html = fetch_url("https://itproger.com/news")
    if html:
        articles = parse_news(html)
        if articles:
            save_news_to_cache(articles)
        return format_articles_response(articles)
    else:
        # Если не удалось загрузить новые, используем кеш
        cached_news = get_cached_news()
        if cached_news:
            return "⚠️ <b>Используются кешированные данные</b>\n\n" + format_articles_response(cached_news)
        else:
            return "❌ Ошибка при загрузке новостей с itproger.com"

def main():
    # Инициализация базы данных
    init_database()
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
                        
                        # Сохраняем пользователя
                        save_user(message["from"])
                        
                        print(f"Получено сообщение от {chat_id}: {text}")
                        
                        # Логируем запрос
                        log_request(message["from"]["id"], text)
                        
                        if text.startswith("http"):
                            html = fetch_url(text)
                            if html:
                                if "itproger.com/news" in text:
                                    articles = parse_news(html)
                                    response = format_articles_response(articles)
                                    if articles:
                                        save_news_to_cache(articles)
                                else:
                                    response = "🔗 Я специализируюсь на парсинге itproger.com/news\nОтправьте ссылку на этот сайт или команду /news"
                            else:
                                response = "❌ Ошибка при загрузке страницы. Проверьте URL."
                                
                        elif text == "/start":
                            response = """👋 <b>Привет! Я бот для парсинга новостей itProger</b>

📋 <b>Доступные команды:</b>
/news - Получить последние новости
/favorites - Мои избранные новости
/stats - Моя статистика
/help - Показать справку

🔗 <b>Или просто отправьте ссылку:</b>
https://itproger.com/news"""
                            
                        elif text == "/news":
                            response = get_itproger_news()
                            
                        elif text == "/favorites":
                            favorites = get_user_favorites(message["from"]["id"])
                            if favorites:
                                response = "⭐ <b>Ваши избранные новости:</b>\n\n"
                                for fav in favorites:
                                    response += f"• {fav['title']}\n"
                            else:
                                response = "📝 У вас пока нет избранных новостей.\nИспользуйте команду /news чтобы добавить."
                                
                        elif text == "/stats":
                            stats = get_user_stats(message["from"]["id"])
                            response = f"""📊 <b>Ваша статистика:</b>

📨 Запросов к боту: {stats['request_count']}
⭐ Избранных новостей: {stats['favorites_count']}
🕐 Последняя активность: {stats['last_activity'][:16]}"""
                            
                        elif text == "/help":
                            response = """ℹ️ <b>Справка по боту</b>

Этот бот парсит заголовки и описания статей с сайта itproger.com/news

<b>Команды:</b>
/start - Начать работу
/news - Получить свежие новости
/favorites - Избранные новости
/stats - Статистика
/help - Эта справка

<b>База данных:</b>
• Сохраняет историю запросов
• Кеширует новости
• Хранит избранное
• Ведет статистику"""
                            
                        elif text.startswith("/add_fav"):
                            # Простая реализация добавления в избранное
                            news_title = text.replace("/add_fav", "").strip()
                            if news_title:
                                add_to_favorites(message["from"]["id"], news_title)
                                response = f"✅ Новость добавлена в избранное: {news_title}"
                            else:
                                response = "❌ Укажите название новости"
                                
                        else:
                            response = """❌ Неизвестная команда

📋 <b>Доступные команды:</b>
/start - Начать работу
/news - Получить новости itProger
/favorites - Избранные новости
/stats - Статистика
/help - Справка"""
                        
                        send_message(chat_id, response)
                        print(f"Отправлен ответ пользователю {chat_id}")
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Ошибка в основном цикле: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()