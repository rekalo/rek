from ...database.db_operations import is_in_favorites, get_user_favorites

def create_news_keyboard(articles, user_id=None):
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

def create_article_detail_keyboard(article_index, articles, user_id):
    article = articles[article_index - 1] if article_index <= len(articles) else {}
    title = article.get('title', '')
    
    if not title:
        return {"inline_keyboard": []}
    
    is_fav = is_in_favorites(user_id, title)
    favorite_text = "❌ Удалить из избранного" if is_fav else "⭐ Добавить в избранное"
    favorite_action = "remove_fav" if is_fav else "add_fav"
    
    keyboard = [
        [{"text": favorite_text, "callback_data": f"{favorite_action}_{article_index}"}],
        [{"text": "🔗 Открыть статью", "url": "https://itproger.com/news"}],
        [{"text": "⬅️ Назад к списку", "callback_data": "back_to_list"}]
    ]
    
    return {"inline_keyboard": keyboard}

def create_favorites_keyboard(user_id):
    favorites = get_user_favorites(user_id)
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
