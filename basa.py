2. Модуль базы данных (database.py)
python
import sqlite3
import datetime

def init_database():
    """
    Инициализирует базу данных SQLite
    Создает все необходимые таблицы
    """
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
    from news_parser import normalize_url  # Импортируем здесь чтобы избежать циклических импортов
    
    conn = sqlite3.connect('news_bot.db')
    cursor = conn.cursor()
    
    now = datetime.datetime.now().isoformat()
    
    for article in articles:
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
    from news_parser import normalize_url
    
    conn = sqlite3.connect('news_bot.db')
    cursor = conn.cursor()
    
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
    
    cursor.execute('SELECT COUNT(*) FROM requests WHERE user_id = ?', (user_id,))
    request_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM favorites WHERE user_id = ?', (user_id,))
    favorites_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT last_activity FROM users WHERE user_id = ?', (user_id,))
    last_activity = cursor.fetchone()
    last_activity = last_activity[0] if last_activity else "Неизвестно"
    
    conn.close()
    
    return {
        'request_count': request_count,
        'favorites_count': favorites_count,
        'last_activity': last_activity
    }
