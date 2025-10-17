import sqlite3
import datetime
from ..data.config import DATABASE_PATH

def init_database():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            command TEXT,
            timestamp TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
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

def save_user(user_data):
    conn = sqlite3.connect(DATABASE_PATH)
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
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO requests (user_id, command, timestamp)
        VALUES (?, ?, ?)
    ''', (user_id, command, datetime.datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def save_news_to_cache(articles):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    now = datetime.datetime.now().isoformat()
    
    for article in articles:
        cursor.execute('''
            INSERT OR REPLACE INTO news_cache (title, description, source_url, link, parsed_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            article.get('title'),
            article.get('description', ''),
            'https://itproger.com/news',
            "https://itproger.com/news",
            now
        ))
    
    conn.commit()
    conn.close()

def get_cached_news(limit=10):
    conn = sqlite3.connect(DATABASE_PATH)
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
            'link': "https://itproger.com/news"
        })
    
    conn.close()
    return articles

def add_to_favorites(user_id, news_title, news_description="", news_link=""):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR IGNORE INTO favorites (user_id, news_title, news_description, news_link, saved_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, news_title, news_description, "https://itproger.com/news", datetime.datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def remove_from_favorites(user_id, news_title):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        DELETE FROM favorites 
        WHERE user_id = ? AND news_title = ?
    ''', (user_id, news_title))
    
    conn.commit()
    conn.close()

def is_in_favorites(user_id, news_title):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(*) FROM favorites 
        WHERE user_id = ? AND news_title = ?
    ''', (user_id, news_title))
    
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def get_user_favorites(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
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
            'link': "https://itproger.com/news",
            'saved_at': row[3]
        })
    
    conn.close()
    return favorites

def get_user_stats(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
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
