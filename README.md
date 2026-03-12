# SQL Trainer

MVP веб-приложение для практики SQL-запросов: задания, SQL-редактор, автопроверка по результату, прогресс и базовая авторизация.

## Что реализовано

- Регистрация и вход (JWT-токен).
- Список заданий с уровнем сложности и темой.
- SQL-редактор в браузере.
- Выполнение только `SELECT`-запросов.
- Проверка решения по сравнению результата запроса с эталоном.
- Просмотр структуры учебной БД.
- Страница прогресса пользователя (решённые задачи, попытки, успешность).

## Технологии

- **Backend:** FastAPI, SQLAlchemy, SQLite
- **Frontend:** HTML + JavaScript (без фреймворка)
- **Auth:** JWT + bcrypt
- **Запуск:** Docker / Docker Compose

## Структура проекта

```text
.
├── backend/
│   ├── app/
│   │   ├── auth.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models.py
│   │   └── seed.py
│   └── requirements.txt
├── frontend/
│   └── index.html
├── Dockerfile
└── docker-compose.yml
```

## Запуск через Docker Compose

```bash
docker compose up --build
```

После запуска откройте:

- http://localhost:8000

## Быстрый сценарий использования

1. Зарегистрируйтесь (логин + пароль).
2. Выберите задачу из списка.
3. Напишите `SELECT`-запрос в редакторе.
4. Нажмите **Выполнить** для просмотра результата.
5. Нажмите **Проверить** для проверки решения.
6. Откройте **Мой прогресс** для статистики.

## Ограничения безопасности SQL

Разрешены только запросы, начинающиеся с `SELECT`.
Запрещены команды изменения данных/схемы: `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `CREATE`, `ATTACH`, `PRAGMA`.

## Учебная схема БД

- `groups(id, name, course_number)`
- `students(id, full_name, age, group_id)`
- `teachers(id, full_name, subject)`
- `courses(id, title, teacher_id)`
- `grades(id, student_id, course_id, grade)`
