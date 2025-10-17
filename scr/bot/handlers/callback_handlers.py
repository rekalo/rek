from ...utils.telegram_api import send_message, edit_message_reply_markup
from ...bot.handlers.user_handlers import format_articles_response, format_article_detail, get_itproger_news
from ...bot.keyboards.inline import create_news_keyboard, create_article_detail_keyboard, create_favorites_keyboard
from ...database.db_operations import save_user, save_news_to_cache, get_cached_news, get_user_favorites, add_to_favorites, remove_from_favorites
import sqlite3
from ...data.config import DATABASE_PATH

def handle_callback_query(callback_query, current_articles):
    user_id = callback_query["from"]["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    message_id = callback_query["message"]["message_id"]
    data = callback_query["data"]
    
    save_user(callback_query["from"])
    
    if data == "refresh_news":
        articles = get_itproger_news(use_cache=False)
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
            
            keyboard = create_favorites_keyboard(user_id)
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
        conn = sqlite3.connect(DATABASE_PATH)
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
            keyboard = create_article_detail_keyboard(article_index, articles, user_id)
            send_message(chat_id, response, keyboard)
            
    elif data.startswith("fav_"):
        fav_index = int(data.split("_")[1])
        favorites = get_user_favorites(user_id)
        
        if 0 < fav_index <= len(favorites):
            fav = favorites[fav_index - 1]
            response = f"<b>{fav['title']}</b>\n\n"
            response += f"<i>{fav.get('description', 'Без описания')}</i>\n\n"
            response += f"🔗 <a href='https://itproger.com/news'>Читать полную статью</a>"
            
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
            add_to_favorites(user_id, article['title'], article.get('description', ''), "https://itproger.com/news")
            keyboard = create_article_detail_keyboard(article_index, articles, user_id)
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
                keyboard = create_article_detail_keyboard(article_index, articles, user_id)
                edit_message_reply_markup(chat_id, message_id, keyboard)
