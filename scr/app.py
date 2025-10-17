import time
from .utils.telegram_api import get_updates
from .bot.handlers.user_handlers import handle_user_message
from .bot.handlers.callback_handlers import handle_callback_query
from .loader import load_bot

def main():
    load_bot()
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
            time.sleep(5)

if __name__ == "__main__":
    main()
