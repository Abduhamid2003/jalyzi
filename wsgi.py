# wsgi.py - для PythonAnywhere
import sys
import os

# Добавляем путь к вашему проекту
path = '/home/korolevskiezhalyuzi/KRK_BLINDS'
if path not in sys.path:
    sys.path.append(path)

# Устанавливаем переменную окружения для FastAPI
os.environ['FASTAPI_APP'] = 'main:app'

# Импортируем ваше приложение
from main import app

# Это то, что ожидает PythonAnywhere
application = app