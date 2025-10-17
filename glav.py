#4. Главный модуль бота (main_bot.py)

import time
from news_parser import get_itproger_news, parse_news, fetch_url, normalize_url
from database import (
    init_database, save_user, log_request, save_news_to_cache, 
    get_cached_news, add_to_favorites, remove_from_favorites, 
    is_in_favorites, get_user_favorites, get_user_stats
)
from bot_interface import (
    send_message, edit_message_reply_markup, get_updates,
    format_article_detail, format_articles_response,
    create_news_keyboard, create_article_detail_keyboard, create_favorites_keyboard
)

def handle_callback_query(callback_query, current_articles):
    """Обрабатывает callback запросы от инлайн-кнопок"""
    user_id = callback_query["from"]["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    message_id = callback_query["message"]["message_id"]
    data = callback_query["data"]
    
    save_user(callback_query["from"])
    
    if data == "refresh_news":
        articles = get_itproger_news(use_cache=False, get_cached_news_func=get_cached_news)
        if articles:
            save_news_to_cache(articles)
            response = "🔄 <b>Новости обновлены!</b>\n\n" + format_articles_response(articles)
            keyboard = create_news_keyboard(articles, user_id)
            send_message(chat_id, response, keyboard)
        else:
            send_message(chat_id, "❌ Не удалось обновить новости")
            
    elif data == "show_favorites":
        favorites = get_user_favorites(user_id)
        if favorites:
            response = "⭐ <b>Ваши избранные новости:</b>\n\n"
            for i, fav in enumerate(favorites, 1):
                response += f"<b>{i}. {fav['title']}</b>\n"
                response += f"<i>📝 {fav.get('description', 'Без описания')}</i>\n\n"
            
            keyboard = create_favorites_keyboard(user_id, get_user_favorites)
            send_message(chat_id, response, keyboard)
        else:
            send_message(chat_id, "📝 У вас пока нет избранных новостей.")
            
    elif data == "back_to_list":
        articles = current_articles or get_cached_news()
        response = format_articles_response(articles)
        keyboard = create_news_keyboard(articles, user_id)
        edit_message_reply_markup(chat_id, message_id, keyboard)
        send_message(chat_id, response, keyboard)
        
    elif data == "clear_favorites":
        from database import sqlite3
        conn = sqlite3.connect('news_bot.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM favorites WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        send_message(chat_id, "✅ Избранное очищено")
        
    elif data.startswith("article_"):
        article_index = int(data.split("_")[1])
        articles = current_articles or get_cached_news()
        
        if 0 < article_index <= len(articles):
            article = articles[article_index - 1]
            response = format_article_detail(article)
            keyboard = create_article_detail_keyboard(article_index, articles, user_id, is_in_favorites)
            send_message(chat_id, response, keyboard)
            
    elif data.startswith("fav_"):
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
        article_index = int(data.split("_")[2])
        articles = current_articles or get_cached_news()
        
        if 0 < article_index <= len(articles):
            article = articles[article_index - 1]
            add_to_favorites(user_id, article['title'], article.get('description', ''), article.get('link', ''))
            keyboard = create_article_detail_keyboard(article_index, articles, user_id, is_in_favorites)
            edit_message_reply_markup(chat_id, message_id, keyboard)
            
    elif data.startswith("remove_fav_"):
        if data.startswith("remove_fav_title_"):
            fav_index = int(data.split("_")[3])
            favorites = get_user_favorites(user_id)
            
            if 0 < fav_index <= len(favorites):
                fav_title = favorites[fav_index - 1]['title']
                remove_from_favorites(user_id, fav_title)
                send_message(chat_id, f"✅ Новость удалена из избранного: {fav_title}")
        else:
            article_index = int(data.split("_")[2])
            articles = current_articles or get_cached_news()
            
            if 0 < article_index <= len(articles):
                article = articles[article_index - 1]
                remove_from_favorites(user_id, article['title'])
                keyboard = create_article_detail_keyboard(article_index, articles, user_id, is_in_favorites)
                edit_message_reply_markup(chat_id, message_id, keyboard)

def handle_user_message(message, current_articles):
    """Обрабатывает текстовые сообщения от пользователя"""
    chat_id = message["chat"]["id"]
    text = message["text"].strip()
    user_id = message["from"]["id"]
    
    save_user(message["from"])
    log_request(user_id, text)
    
    if text.startswith("http"):
        text = normalize_url(text)
        html = fetch_url(text)
        if html:
            if "itproger.com/news" in text:
                articles = parse_news(html)
                if articles:
                    save_news_to_cache(articles)
                    current_articles[chat_id] = articles
                    response = format_articles_response(articles)
                    keyboard = create_news_keyboard(articles, user_id)
                    send_message(chat_id, response, keyboard)
                else:
                    send_message(chat_id, "❌ Не удалось найти статьи на странице")
            else:
                send_message(chat_id, "🔗 Я специализируюсь на парсинге itproger.com/news\nОтправьте ссылку на этот сайт или команду /news")
        else:
            send_message(chat_id, "❌ Ошибка при загрузке страницы. Проверьте URL.")
            
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
        articles = get_itproger_news(get_cached_news_func=get_cached_news)
        if articles:
            current_articles[chat_id] = articles
            response = format_articles_response(articles)
            keyboard = create_news_keyboard(articles, user_id)
            send_message(chat_id, response, keyboard)
        else:
            send_message(chat_id, "❌ Ошибка при загрузке новостей с itproger.com")
            
    elif text == "/favorites":
        favorites = get_user_favorites(user_id)
        if favorites:
            response = "⭐ <b>Ваши избранные новости:</b>\n\n"
            for i, fav in enumerate(favorites, 1):
                response += f"<b>{i}. {fav['title']}</b>\n"
            
            keyboard = create_favorites_keyboard(user_id, get_user_favorites)
            send_message(chat_id, response, keyboard)
        else:
            send_message(chat_id, "📝 У вас пока нет избранных новостей.")
            
    elif text == "/stats":
        stats = get_user_stats(user_id)
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
• Обновление списка новостей"""
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

def main():
    """Главная функция бота"""
    init_database()
    print("Бот запущен! Ожидание сообщений...")
    offset = 0
    current_articles = {}
    
    while True:
        try:
            updates = get_updates(offset)
            
            if "result" in updates:
                for update in updates["result"]:
                    offset = update["update_id"] + 1
                    
                    if "callback_query" in update:
                        chat_id = update["callback_query"]["message"]["chat"]["id"]
                        handle_callback_query(update["callback_query"], current_articles.get(chat_id))
                        
                    elif "message" in update and "text" in update["message"]:
                        handle_user_message(update["message"], current_articles)
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Ошибка в основном цикле: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()