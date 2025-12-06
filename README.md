# ИНСТРУКЦИЯ ПО УСТАНОВКЕ И НАСТРОЙКЕ БОТА РАСПИСАНИЯ

## Содержание
1. [Требования](#требования)
2. [Установка](#установка)
3. [Миграция базы данных](#миграция-базы-данных)
4. [Генерация расписания](#генерация-расписания)
5. [Интеграция новых файлов](#интеграция-новых-файлов)
6. [Учетные данные пользователей](#учетные-данные-пользователей)
7. [Функционал бота](#функционал-бота)

---

## Требования

- Python 3.12+
- PostgreSQL 13+
- Библиотеки: aiogram, psycopg2

---

## Установка

### 1. Применить миграцию к базе данных

```bash
cd /tg-bot-schedule
psql -U postgres -d schedule_bot_db -f /home/claude/migration_add_features.sql
```

### 2. Скопировать новые файлы

```bash
# Конфигурация ролей
cp /home/config_roles.py config/roles.py

# Обработчики команд
cp /home/bot_commands.py bot/commands.py

# Обработчики настроек
cp /home/bot_settings_handlers.py bot/settings_handlers.py

# Админ-панель
cp /home/bot_admin_handlers.py bot/admin_handlers.py

# Скрипт генерации расписания
cp /home/generate_schedule.py scripts/generate_schedule.py
chmod +x scripts/generate_schedule.py
```

---

## Миграция базы данных

Миграция добавляет:
- Поле `lesson_type` в таблицу `subjects` (lecture, practice, lab)
- Таблицу `user_preferences` для настроек пользователей
- Таблицу `user_activity_log` для логирования действий
- Индексы для оптимизации запросов

**Выполнение:**
```bash
psql -U postgres -d schedule_bot_db -f migration_add_features.sql
```

---

## Генерация расписания

Скрипт `generate_schedule.py` генерирует расписание на семестр (18 недель).

**Параметры:**
- Автоматически определяет семестр (осенний с 1 сентября, весенний с 1 февраля)
- Генерирует 2-4 пары в день для каждой группы
- Случайно распределяет предметы, преподавателей и аудитории
- Обновляет типы занятий (лекция/практика/лабораторная)

**Запуск:**
```bash
python scripts/generate_schedule.py
```

**Вывод:**
```
==============================================================
ГЕНЕРАЦИЯ РАСПИСАНИЯ НА СЕМЕСТР
==============================================================

Дата начала семестра: 01.09.2024

1. Обновление типов занятий...
✅ Обновлены типы для 10 предметов

2. Генерация расписания на 18 недель...
Генерация расписания на 18 недель...
Групп: 3, Предметов: 10

Неделя 1: 02.09.2024
...

✅ Успешно создано 1234 занятий

Статистика:
  Всего занятий: 1234
  Задействовано групп: 3
  Задействовано преподавателей: 5
  Задействовано аудиторий: 8

==============================================================
ГОТОВО!
==============================================================
```

---

## Интеграция новых файлов

### 1. Обновить `config/settings.py`

Добавить импорт ролей:
```python
from config.roles import ROLES, TEST_USERS, check_permission
```

### 2. Обновить `bot/handlers.py`

Добавить импорты в начало файла:
```python
from bot.commands import (
    cmd_schedule_with_params,
    cmd_week_with_params,
    cmd_teacher_with_params,
    cmd_room_with_params,
    cmd_find_with_params
)
from bot.settings_handlers import (
    cmd_settings,
    settings_notifications,
    settings_notification_time,
    settings_teacher_contacts,
    settings_compact_view,
    settings_week_start,
    settings_theme,
    process_notification_time,
    SettingsStates
)
from bot.admin_handlers import (
    cmd_admin,
    cmd_stats,
    cmd_export,
    admin_stats,
    admin_users,
    admin_export_schedule,
    admin_logs,
    admin_report,
    log_user_action
)
```

Зарегистрировать команды:
```python
# После существующих команд добавить:

# Команды с параметрами
@dp.message(Command("schedule"))
async def schedule_command(message: types.Message):
    await cmd_schedule_with_params(message)

@dp.message(Command("week"))
async def week_command(message: types.Message):
    await cmd_week_with_params(message)

@dp.message(Command("find"))
async def find_command(message: types.Message):
    await cmd_find_with_params(message)

# Настройки
@dp.message(Command("settings"))
async def settings_command(message: types.Message):
    await cmd_settings(message)

@dp.callback_query(F.data == "settings_notifications")
async def settings_notif_callback(callback: types.CallbackQuery):
    await settings_notifications(callback)

@dp.callback_query(F.data == "settings_notification_time")
async def settings_time_callback(callback: types.CallbackQuery, state: FSMContext):
    await settings_notification_time(callback, state)

@dp.callback_query(F.data == "settings_teacher_contacts")
async def settings_contacts_callback(callback: types.CallbackQuery):
    await settings_teacher_contacts(callback)

@dp.callback_query(F.data == "settings_compact_view")
async def settings_compact_callback(callback: types.CallbackQuery):
    await settings_compact_view(callback)

@dp.callback_query(F.data == "settings_week_start")
async def settings_week_callback(callback: types.CallbackQuery):
    await settings_week_start(callback)

@dp.message(SettingsStates.waiting_for_notification_time)
async def process_time(message: types.Message, state: FSMContext):
    await process_notification_time(message, state)

# Админ-панель
@dp.message(Command("admin"))
async def admin_command(message: types.Message):
    await cmd_admin(message)

@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    await cmd_stats(message)

@dp.message(Command("export"))
async def export_command(message: types.Message):
    await cmd_export(message)

@dp.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: types.CallbackQuery):
    await admin_stats(callback)

@dp.callback_query(F.data == "admin_users")
async def admin_users_callback(callback: types.CallbackQuery):
    await admin_users(callback)

@dp.callback_query(F.data == "admin_export_schedule")
async def admin_export_callback(callback: types.CallbackQuery):
    await admin_export_schedule(callback)

@dp.callback_query(F.data == "admin_logs")
async def admin_logs_callback(callback: types.CallbackQuery):
    await admin_logs(callback)

@dp.callback_query(F.data == "admin_report")
async def admin_report_callback(callback: types.CallbackQuery):
    await admin_report(callback)
```

### 3. Добавить логирование действий

В каждый обработчик добавить логирование:
```python
from bot.admin_handlers import log_user_action

# В начале каждого обработчика:
user = db.get_user_by_telegram_id(message.from_user.id)
if user:
    log_user_action(user['id'], 'view_schedule', f'Группа: {user["group_number"]}')
```

---

## Учетные данные пользователей

Для демонстрации работы системы с разными уровнями доступа созданы тестовые пользователи:

### 1. Разработчик (Developer)
- **Telegram ID**: 123456789 (замените на ваш)
- **ФИО**: Иванов Иван Иванович
- **Username**: developer_user
- **Группа**: ИВТ-21
- **Права**: Полный доступ ко всем функциям

### 2. Администратор (Admin)
- **Telegram ID**: 987654321
- **ФИО**: Петров Петр Петрович
- **Username**: admin_user
- **Группа**: ИВТ-22
- **Права**: 
  - Управление расписанием
  - Управление пользователями
  - Просмотр статистики
  - Экспорт данных

### 3. Пользователь (User)
- **Telegram ID**: 111222333
- **ФИО**: Сидоров Сидор Сидорович
- **Username**: regular_user
- **Группа**: ИВТ-21
- **Права**:
  - Просмотр расписания
  - Поиск по расписанию

### Добавление пользователей в БД

```sql
-- Разработчик
INSERT INTO users (telegram_id, username, fio, role, group_id) 
VALUES (123456789, 'developer_user', 'Иванов Иван Иванович', 'developer',
        (SELECT id FROM student_groups WHERE group_number = 'ИВТ-21'));

-- Администратор
INSERT INTO users (telegram_id, username, fio, role, group_id) 
VALUES (987654321, 'admin_user', 'Петров Петр Петрович', 'admin',
        (SELECT id FROM student_groups WHERE group_number = 'ИВТ-22'));

-- Пользователь
INSERT INTO users (telegram_id, username, fio, role, group_id) 
VALUES (111222333, 'regular_user', 'Сидоров Сидор Сидорович', 'user',
        (SELECT id FROM student_groups WHERE group_number = 'ИВТ-21'));
```

---

## Функционал бота

### Команды без параметров (5 команд)
1. `/start` - Начало работы, выбор группы
2. `/help` - Справка по боту
3. `/settings` - Настройки пользователя
4. `/admin` - Панель администратора (для админов)
5. `/stats` - Статистика (для админов)

### Команды с параметрами (5+ команд)
1. `/schedule [группа] [дата]` - Расписание группы на дату
2. `/week [номер]` - Расписание на неделю по номеру
3. `/teacher [ФИО]` - Расписание преподавателя
4. `/room [номер]` - Занятость аудитории
5. `/find [тип] [запрос]` - Универсальный поиск
6. `/export` - Экспорт данных (для админов)

### Настройки пользователя (6 пунктов)
1. 🔔 Уведомления (вкл/выкл)
2. ⏰ Время уведомлений
3. 📞 Показывать контакты преподавателей
4. 📋 Компактный вид
5. 📅 Начало недели (ПН/ВС)
6. 🎨 Тема оформления (заглушка)

### Варианты ответов с маркапами (5+ типов)
1. **InlineKeyboard**: Выбор дня недели
2. **InlineKeyboard**: Выбор номера недели
3. **InlineKeyboard**: Настройки пользователя
4. **InlineKeyboard**: Админ-панель
5. **ReplyKeyboard**: Главное меню
6. **Document**: Экспорт расписания в CSV
7. **Document**: Экспорт отчетов в JSON

### Сценарии получения данных (3+ сценария)
1. Выбор группы при регистрации (FSM)
2. Ввод времени уведомлений (FSM)
3. Поиск по группе (FSM)
4. Поиск по преподавателю (FSM)
5. Поиск по аудитории (FSM)

### Работа с файловой системой
- Экспорт расписания в CSV файл
- Экспорт отчетов в JSON файл
- Временное хранение файлов в `/tmp`
- Автоматическое удаление после отправки

### Логирование и отчеты
- Все действия пользователей логируются в `user_activity_log`
- Админ может просмотреть логи через `/admin`
- Экспорт отчетов за период
- Статистика активности

### Уровни доступа (3 уровня)
1. **Developer**: Полный доступ
2. **Admin**: Управление + статистика
3. **User**: Только просмотр

---

## Проверка работы

### 1. Запуск бота
```bash
python main.py
```

### 2. Тестирование команд

**Пользователь**:
- `/start` - выбор группы
- `/schedule ИВТ-21` - расписание группы
- `/week 1` - расписание 1-й недели
- `/settings` - настройки

**Администратор**:
- `/admin` - админ-панель
- `/stats` - статистика
- `/export` - экспорт данных

### 3. Проверка логов
```sql
SELECT * FROM user_activity_log ORDER BY created_at DESC LIMIT 20;
```

---

## Автор

**ФИО**: Романов Дмитрий Владимирович 
**Группа**: o.ИЗДтс 23.2/Б1-22 

---

## Дата создания

Декабрь 2024
