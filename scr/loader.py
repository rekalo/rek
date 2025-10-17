from .database.db_operations import init_database

def load_bot():
    init_database()
    print("Бот инициализирован и готов к работе!")
