from ...utils.telegram_api import send_message, fetch_url
from ...bot.parser.itproger_parser import parse_news
from ...bot.keyboards.inline import create_news_keyboard, create_favorites_keyboard
from ...database.db_operations import save_user, log_request, save_news_to_cache, get_cached_news, get_user_favorites, get_user_stats

def format_article_detail(article):
    title = article.get('title', 'Без заголовка')
    description = article.get('description', 'Без описания')
    
    response = f"<b>{title}</b>\n\n"
    response += f"<i>{description}</i>\n\n"
    response += f"🔗 <a href='https://itproger.com/news'>Читать полную статью на itProger</a>"
    
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

def get_itproger_news(use_cache=True):
    if use_cache:
        cached_news = get_cached_news()
        if cached_news:
            return cached_news
    
    html = fetch_url("https://itproger.com/news")
    if html:
        articles = parse_news(html)
        if articles:
            save_news_to_cache(articles)
        return articles
    else:
        return get_cached_news()

def handle_user_message(message, current_articles):
    chat_id = message["chat"]["id"]
    text = message["text"].strip()
    user_id = message["from"]["id"]
    
    save_user(message["from"])
    log_request(user_id, text)
    
    if text.startswith("http"):
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
        articles = get_itproger_news()
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
            
            keyboard = create_favorites_keyboard(user_id)
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
/help - Эта справка"""
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
