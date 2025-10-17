import http.client
import json
import urllib.parse
from html.parser import HTMLParser
import time
import sqlite3
import datetime
import re

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
            link TEXT,
            parsed_at TEXT
        )
    ''')
    
    # Таблица избранных новостей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            news_title TEXT,
            news_description TEXT,
            news_link TEXT,
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
        # Нормализуем ссылку перед сохранением
        link = article.get('link', '')
        if link:
            link = normalize_url(link)
            
        cursor.execute('''
            INSERT OR REPLACE INTO news_cache (title, description, source_url, link, parsed_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            article.get('title'),
            article.get('description'),
            'https://itproger.com/news',
            link,
            now
        ))
    
    conn.commit()
    conn.close()

def get_cached_news(limit=10):
    """Получает новости из кеша"""
    conn = sqlite3.connect('news_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT title, description, link FROM news_cache 
        ORDER BY parsed_at DESC 
        LIMIT ?
    ''', (limit,))
    
    articles = []
    for row in cursor.fetchall():
        articles.append({
            'title': row[0],
            'description': row[1],
            'link': row[2]
        })
    
    conn.close()
    return articles

def add_to_favorites(user_id, news_title, news_description="", news_link=""):
    """Добавляет новость в избранное"""
    conn = sqlite3.connect('news_bot.db')
    cursor = conn.cursor()
    
    # Нормализуем ссылку перед сохранением
    if news_link:
        news_link = normalize_url(news_link)
    
    cursor.execute('''
        INSERT OR IGNORE INTO favorites (user_id, news_title, news_description, news_link, saved_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, news_title, news_description, news_link, datetime.datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def remove_from_favorites(user_id, news_title):
    """Удаляет новость из избранного"""
    conn = sqlite3.connect('news_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        DELETE FROM favorites 
        WHERE user_id = ? AND news_title = ?
    ''', (user_id, news_title))
    
    conn.commit()
    conn.close()

def is_in_favorites(user_id, news_title):
    """Проверяет, есть ли новость в избранном"""
    conn = sqlite3.connect('news_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(*) FROM favorites 
        WHERE user_id = ? AND news_title = ?
    ''', (user_id, news_title))
    
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def get_user_favorites(user_id):
    """Получает избранные новости пользователя"""
    conn = sqlite3.connect('news_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT news_title, news_description, news_link, saved_at FROM favorites 
        WHERE user_id = ? 
        ORDER BY saved_at DESC
    ''', (user_id,))
    
    favorites = []
    for row in cursor.fetchall():
        favorites.append({
            'title': row[0],
            'description': row[1],
            'link': row[2],
            'saved_at': row[3]
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

def normalize_url(url):
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

def send_message(chat_id, text, reply_markup=None):
    try:
        if len(text) > 4096:
            text = text[:4090] + "..."
            
        conn = http.client.HTTPSConnection(BASE_URL)
        url = f"/bot{TOKEN}/sendMessage"
        params = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': False  # Разрешаем превью ссылок
        }
        
        if reply_markup:
            params['reply_markup'] = reply_markup
            
        headers = {'Content-type': 'application/json'}
        conn.request("POST", url, json.dumps(params), headers)
        response = conn.getresponse()
        return response.read()
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")
        return None

def edit_message_reply_markup(chat_id, message_id, reply_markup=None):
    try:
        conn = http.client.HTTPSConnection(BASE_URL)
        url = f"/bot{TOKEN}/editMessageReplyMarkup"
        params = {
            'chat_id': chat_id,
            'message_id': message_id
        }
        
        if reply_markup:
            params['reply_markup'] = reply_markup
            
        headers = {'Content-type': 'application/json'}
        conn.request("POST", url, json.dumps(params), headers)
        response = conn.getresponse()
        return response.read()
    except Exception as e:
        print(f"Ошибка редактирования сообщения: {e}")
        return None

def fetch_url(url):
    try:
        # Нормализуем URL перед запросом
        url = normalize_url(url)
        parsed = urllib.parse.urlparse(url)
        conn = http.client.HTTPSConnection(parsed.netloc)
        path = parsed.path
        if parsed.query:
            path += '?' + parsed.query
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
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
    parser = NewsParser()
    parser.feed(html)
    return parser.articles

def format_article_detail(article):
    """Форматирует детальную информацию о статье"""
    title = article.get('title', 'Без заголовка')
    description = article.get('description', 'Без описания')
    link = article.get('link', '')
    
    # Нормализуем ссылку для отображения
    if link:
        link = normalize_url(link)
    
    response = f"<b>{title}</b>\n\n"
    response += f"<i>{description}</i>\n\n"
    
    if link:
        response += f"🔗 <a href='{link}'>Читать полную статью на itProger</a>"
    
    return response

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

def create_news_keyboard(articles, user_id=None):
    """Создает инлайн-клавиатуру для списка новостей"""
    keyboard = []
    
    for i, article in enumerate(articles, 1):
        title = article.get('title', 'Без заголовка')
        # Обрезаем длинные заголовки для кнопок
        button_text = title[:30] + "..." if len(title) > 30 else title
        
        # Создаем кнопку для каждой статьи
        keyboard.append([{
            "text": f"{i}. {button_text}",
            "callback_data": f"article_{i}"
        }])
    
    # Добавляем кнопку обновления
    keyboard.append([
        {"text": "🔄 Обновить", "callback_data": "refresh_news"},
        {"text": "⭐ Избранное", "callback_data": "show_favorites"}
    ])
    
    return {"inline_keyboard": keyboard}

def create_article_detail_keyboard(article_index, articles, user_id):
    """Создает инлайн-клавиатуру для детального просмотра статьи"""
    article = articles[article_index - 1] if article_index <= len(articles) else {}
    title = article.get('title', '')
    
    if not title:
        return {"inline_keyboard": []}
    
    is_fav = is_in_favorites(user_id, title)
    favorite_text = "❌ Удалить из избранного" if is_fav else "⭐ Добавить в избранное"
    favorite_action = "remove_fav" if is_fav else "add_fav"
    
    # Нормализуем ссылку для кнопки
    article_link = article.get('link', '')
    if article_link:
        article_link = normalize_url(article_link)
    else:
        article_link = 'https://itproger.com/news'
    
    keyboard = [
        [{"text": favorite_text, "callback_data": f"{favorite_action}_{article_index}"}],
        [{"text": "🔗 Открыть статью", "url": article_link}],
        [{"text": "⬅️ Назад к списку", "callback_data": "back_to_list"}]
    ]
    
    return {"inline_keyboard": keyboard}

def create_favorites_keyboard(user_id):
    """Создает инлайн-клавиатуру для избранных новостей"""
    favorites = get_user_favorites(user_id)
    keyboard = []
    
    for i, fav in enumerate(favorites, 1):
        title = fav.get('title', 'Без заголовка')
        button_text = title[:30] + "..." if len(title) > 30 else title
        
        keyboard.append([{
            "text": f"{i}. {button_text}",
            "callback_data": f"fav_{i}"
        }])
    
    # Добавляем кнопку возврата
    if favorites:
        keyboard.append([{"text": "🗑️ Очистить избранное", "callback_data": "clear_favorites"}])
    
    keyboard.append([{"text": "⬅️ Назад", "callback_data": "back_to_list"}])
    
    return {"inline_keyboard": keyboard}

def get_itproger_news(use_cache=True):
    """Функция для получения новостей с itproger.com/news"""
    if use_cache:
        cached_news = get_cached_news()
        if cached_news:
            print("Используются кешированные новости")
            return cached_news
    
    # Исправленная ссылка на itproger.com/news
    html = fetch_url("https://itproger.com/news")
    if html:
        articles = parse_news(html)
        if articles:
            save_news_to_cache(articles)
        return articles
    else:
        # Если не удалось загрузить новые, используем кеш
        cached_news = get_cached_news()
        return cached_news

def handle_callback_query(callback_query, current_articles):
    """Обрабатывает callback запросы от инлайн-кнопок"""
    user_id = callback_query["from"]["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    message_id = callback_query["message"]["message_id"]
    data = callback_query["data"]
    
    # Сохраняем пользователя
    save_user(callback_query["from"])
    
    if data == "refresh_news":
        # Обновляем новости
        articles = get_itproger_news(use_cache=False)
        if articles:
            response = "🔄 <b>Новости обновлены!</b>\n\n" + format_articles_response(articles)
            keyboard = create_news_keyboard(articles, user_id)
            send_message(chat_id, response, keyboard)
        else:
            send_message(chat_id, "❌ Не удалось обновить новости")
            
    elif data == "show_favorites":
        # Показываем избранное
        favorites = get_user_favorites(user_id)
        if favorites:
            response = "⭐ <b>Ваши избранные новости:</b>\n\n"
            for i, fav in enumerate(favorites, 1):
                response += f"<b>{i}. {fav['title']}</b>\n"
                response += f"<i>📝 {fav.get('description', 'Без описания')}</i>\n\n"
            
            keyboard = create_favorites_keyboard(user_id)
            send_message(chat_id, response, keyboard)
        else:
            send_message(chat_id, "📝 У вас пока нет избранных новостей.")
            
    elif data == "back_to_list":
        # Возвращаемся к списку новостей
        articles = current_articles or get_cached_news()
        response = format_articles_response(articles)
        keyboard = create_news_keyboard(articles, user_id)
        edit_message_reply_markup(chat_id, message_id, keyboard)
        send_message(chat_id, response, keyboard)
        
    elif data == "clear_favorites":
        # Очищаем избранное
        conn = sqlite3.connect('news_bot.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM favorites WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        
        send_message(chat_id, "✅ Избранное очищено")
        
    elif data.startswith("article_"):
        # Показываем детали статьи
        article_index = int(data.split("_")[1])
        articles = current_articles or get_cached_news()
        
        if 0 < article_index <= len(articles):
            article = articles[article_index - 1]
            response = format_article_detail(article)
            keyboard = create_article_detail_keyboard(article_index, articles, user_id)
            send_message(chat_id, response, keyboard)
            
    elif data.startswith("fav_"):
        # Показываем детали избранной статьи
        fav_index = int(data.split("_")[1])
        favorites = get_user_favorites(user_id)
        
        if 0 < fav_index <= len(favorites):
            fav = favorites[fav_index - 1]
            response = f"<b>{fav['title']}</b>\n\n"
            response += f"<i>{fav.get('description', 'Без описания')}</i>\n\n"
            
            link = fav.get('link', '')
            if link:
                link = normalize_url(link)
                response += f"🔗 <a href='{link}'>Читать полную статью</a>"
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "❌ Удалить из избранного", "callback_data": f"remove_fav_title_{fav_index}"}],
                    [{"text": "⬅️ Назад к избранному", "callback_data": "show_favorites"}]
                ]
            }
            send_message(chat_id, response, keyboard)
            
    elif data.startswith("add_fav_"):
        # Добавляем в избранное
        article_index = int(data.split("_")[2])
        articles = current_articles or get_cached_news()
        
        if 0 < article_index <= len(articles):
            article = articles[article_index - 1]
            add_to_favorites(user_id, article['title'], article.get('description', ''), article.get('link', ''))
            
            # Обновляем клавиатуру
            keyboard = create_article_detail_keyboard(article_index, articles, user_id)
            edit_message_reply_markup(chat_id, message_id, keyboard)
            
    elif data.startswith("remove_fav_"):
        if data.startswith("remove_fav_title_"):
            # Удаляем из избранного по индексу
            fav_index = int(data.split("_")[3])
            favorites = get_user_favorites(user_id)
            
            if 0 < fav_index <= len(favorites):
                fav_title = favorites[fav_index - 1]['title']
                remove_from_favorites(user_id, fav_title)
                send_message(chat_id, f"✅ Новость удалена из избранного: {fav_title}")
        else:
            # Удаляем из избранного
            article_index = int(data.split("_")[2])
            articles = current_articles or get_cached_news()
            
            if 0 < article_index <= len(articles):
                article = articles[article_index - 1]
                remove_from_favorites(user_id, article['title'])
                
                # Обновляем клавиатуру
                keyboard = create_article_detail_keyboard(article_index, articles, user_id)
                edit_message_reply_markup(chat_id, message_id, keyboard)

def main():
    # Инициализация базы данных
    init_database()
    print("Бот запущен! Ожидание сообщений...")
    offset = 0
    current_articles = {}  # Будет хранить статьи для каждого чата
    
    while True:
        try:
            updates = get_updates(offset)
            
            if "result" in updates:
                for update in updates["result"]:
                    offset = update["update_id"] + 1
                    
                    if "callback_query" in update:
                        # Обрабатываем нажатие на инлайн-кнопку
                        chat_id = update["callback_query"]["message"]["chat"]["id"]
                        handle_callback_query(update["callback_query"], current_articles.get(chat_id))
                        
                    elif "message" in update and "text" in update["message"]:
                        message = update["message"]
                        chat_id = message["chat"]["id"]
                        text = message["text"].strip()
                        
                        # Сохраняем пользователя
                        save_user(message["from"])
                        
                        print(f"Получено сообщение от {chat_id}: {text}")
                        
                        # Логируем запрос
                        log_request(message["from"]["id"], text)
                        
                        if text.startswith("http"):
                            # Нормализуем URL перед обработкой
                            text = normalize_url(text)
                            html = fetch_url(text)
                            if html:
                                if "itproger.com/news" in text:
                                    articles = parse_news(html)
                                    if articles:
                                        save_news_to_cache(articles)
                                        current_articles[chat_id] = articles
                                        response = format_articles_response(articles)
                                        keyboard = create_news_keyboard(articles, message["from"]["id"])
                                        send_message(chat_id, response, keyboard)
                                    else:
                                        response = "❌ Не удалось найти статьи на странице"
                                        send_message(chat_id, response)
                                else:
                                    response = "🔗 Я специализируюсь на парсинге itproger.com/news\nОтправьте ссылку на этот сайт или команду /news"
                                    send_message(chat_id, response)
                            else:
                                response = "❌ Ошибка при загрузке страницы. Проверьте URL."
                                send_message(chat_id, response)
                                
                        elif text == "/start":
                            response = """👋 <b>Привет! Я бот для парсинга новостей itProger</b>

📋 <b>Доступные команды:</b>
/news - Получить последние новости
/favorites - Мои избранные новости
/stats - Моя статистика
/help - Показать справку

🔗 <b>Или просто отправьте ссылку:</b>
https://itproger.com/news"""
                            send_message(chat_id, response)
                            
                        elif text == "/news":
                            articles = get_itproger_news()
                            if articles:
                                current_articles[chat_id] = articles
                                response = format_articles_response(articles)
                                keyboard = create_news_keyboard(articles, message["from"]["id"])
                                send_message(chat_id, response, keyboard)
                            else:
                                send_message(chat_id, "❌ Ошибка при загрузке новостей с itproger.com")
                                
                        elif text == "/favorites":
                            favorites = get_user_favorites(message["from"]["id"])
                            if favorites:
                                response = "⭐ <b>Ваши избранные новости:</b>\n\n"
                                for i, fav in enumerate(favorites, 1):
                                    response += f"<b>{i}. {fav['title']}</b>\n"
                                
                                keyboard = create_favorites_keyboard(message["from"]["id"])
                                send_message(chat_id, response, keyboard)
                            else:
                                send_message(chat_id, "📝 У вас пока нет избранных новостей.")
                                
                        elif text == "/stats":
                            stats = get_user_stats(message["from"]["id"])
                            response = f"""📊 <b>Ваша статистика:</b>

📨 Запросов к боту: {stats['request_count']}
⭐ Избранных новостей: {stats['favorites_count']}
🕐 Последняя активность: {stats['last_activity'][:16]}"""
                            send_message(chat_id, response)
                            
                        elif text == "/help":
                            response = """ℹ️ <b>Справка по боту</b>

Этот бот парсит заголовки и описания статей с сайта itproger.com/news

<b>Команды:</b>
/start - Начать работу
/news - Получить свежие новости
/favorites - Избранные новости
/stats - Статистика
/help - Эта справка

<b>Инлайн-кнопки:</b>
• Просмотр деталей статьи
• Добавление/удаление из избранного
• Прямые ссылки на статьи
• Обновление списка новостей

<b>База данных:</b>
• Сохраняет историю запросов
• Кеширует новости
• Хранит избранное
• Ведет статистику"""
                            send_message(chat_id, response)
                                
                        else:
                            response = """❌ Неизвестная команда

📋 <b>Доступные команды:</b>
/start - Начать работу
/news - Получить новости itProger
/favorites - Избранные новости
/stats - Статистика
/help - Справка"""
                            send_message(chat_id, response)
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Ошибка в основном цикле: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()

