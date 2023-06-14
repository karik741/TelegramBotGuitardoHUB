# Выберите базовый образ с Python
FROM python:3.10

# Установите рабочую директорию в контейнере
WORKDIR /app

# Копируйте требования для вашего проекта в контейнер
COPY ./requirements.txt ./

# Установите все зависимости
RUN pip install --no-cache-dir -r requirements.txt --root-user-action=ignore

# Копируйте ваш скрипт в контейнер
COPY ./ ./

# Запускайте ваш скрипт при запуске контейнера
 CMD ["python", "main.py"]