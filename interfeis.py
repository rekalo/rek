#3. Модуль интерфейса бота (bot_interface.py)
import json
import http.client
from news_parser import normalize_url

# Настройки бота
TOKEN = "8399667774:AAEYrsNonQW0t8wKZhhvAoLzr1BUbtH3WL4"
BASE_URL = "api.telegram.org"

def format_article_detail(article):
    """Форматирует детальную информацию о статье"""
    title = article.get('title', 'Без заголовка')
    description = article.get('description', 'Без описания')
    link = article.get('link', '')
    
    if link:
        link = normalize_url(link)
    
    response = f"<b>{title}</b>\n\n"
    response += f"<i>{description}</i>\n\n"
    
    if link:
        response += f"🔗 <a href='{link}'>Читать полную статью на itProger</a>"
    
    return response

def format_articles_response(articles, show_numbers=True):
    """Форматирует список статей для отправки в Telegram"""
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
        button_text = title[:30] + "..." if len(title) > 30 else title
        
        keyboard.append([{
            "text": f"{i}. {button_text}",
            "callback_data": f"article_{i}"
        }])
    
    keyboard.append([
        {"text": "🔄 Обновить", "callback_data": "refresh_news"},
        {"text": "⭐ Избранное", "callback_data": "show_favorites"}
    ])
    
    return {"inline_keyboard": keyboard}

def create_article_detail_keyboard(article_index, articles, user_id, is_in_favorites_func):
    """Создает инлайн-клавиатуру для детального просмотра статьи"""
    article = articles[article_index - 1] if article_index <= len(articles) else {}
    title = article.get('title', '')
    
    if not title:
        return {"inline_keyboard": []}
    
    is_fav = is_in_favorites_func(user_id, title)
    favorite_text = "❌ Удалить из избранного" if is_fav else "⭐ Добавить в избранное"
    favorite_action = "remove_fav" if is_fav else "add_fav"
    
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

def create_favorites_keyboard(user_id, get_user_favorites_func):
    """Создает инлайн-клавиатуру для избранных новостей"""
    favorites = get_user_favorites_func(user_id)
    keyboard = []
    
    for i, fav in enumerate(favorites, 1):
        title = fav.get('title', 'Без заголовка')
        button_text = title[:30] + "..." if len(title) > 30 else title
        
        keyboard.append([{
            "text": f"{i}. {button_text}",
            "callback_data": f"fav_{i}"
        }])
    
    if favorites:
        keyboard.append([{"text": "🗑️ Очистить избранное", "callback_data": "clear_favorites"}])
    
    keyboard.append([{"text": "⬅️ Назад", "callback_data": "back_to_list"}])
    
    return {"inline_keyboard": keyboard}

def send_message(chat_id, text, reply_markup=None):
    """Отправляет сообщение в Telegram"""
    try:
        if len(text) > 4096:
            text = text[:4090] + "..."
            
        conn = http.client.HTTPSConnection(BASE_URL)
        url = f"/bot{TOKEN}/sendMessage"
        params = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': False
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
    """Редактирует инлайн-клавиатуру сообщения"""
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

def get_updates(offset=None):
    """Получает обновления от Telegram API"""
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