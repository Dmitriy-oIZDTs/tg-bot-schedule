# Диагностика и решение проблем

## Проблема 1: При экспорте выводится только один день

### Возможные причины:

1. **В БД расписание только на один день**
   - Проверьте статистику: `/schedule_stats`
   - Посмотрите поле `unique_dates` - если 1, значит в БД только один день

2. **Неправильный расчет дат**
   - Система вычисляет дата_от как `сегодня - N дней`
   - Если расписание находится в будущем, а вы экспортируете в прошлое, закажется в будущем

### Решение:

#### Вариант 1: Добавить больше расписания (импорт)
```bash
1. /get_template           # Получить шаблон
2. Заполнить на разные даты
3. /import_schedule        # Загрузить
4. /schedule_stats         # Проверить добавилось ли
```

#### Вариант 2: Проверить диапазон дат
```bash
/schedule_stats
# Посмотрите "earliest_date" и "latest_date"
```

Если прибавше дать, которые нужны, заполнить их можно через импорт.

#### Вариант 3: Увеличить диапазон в экспорте
```
/export_schedule БПИ-24 365  # Экспортировать на весь год
```

---

## Диагностические команды

### `/schedule_stats` 
Показывает:
- **total_records** - всего записей расписания
- **unique_dates** - количество уникальных дат (дней)
- **unique_groups** - количество групп
- **earliest_date** - первая дата расписания
- **latest_date** - последняя дата расписания

**Интерпретация:**
```
Если unique_dates = 1  → только один день в БД
Если earliest_date = 2026-02-01 и latest_date = 2026-02-03
    то расписание есть только с 1 по 3 февраля
```

---

## Как правильно импортировать расписание

### 1. Подготовка данных

Использовать файл `example_schedule.csv` как образец:

```csv
Группа,Дата,Пара,Начало,Конец,Предмет,Тип,Преподаватель,Аудитория
БПИ-24,2026-02-10,1,09:00,10:30,Программирование,lecture,Иванов И.И.,101
БПИ-24,2026-02-10,2,10:45,12:15,Алгоритмы,practice,Петров П.П.,102
```

**Важные детали:**
- Дата: `YYYY-MM-DD` (2026-02-10)
- Время: `HH:MM` (09:00)
- Пара: число (1-6)
- Тип: только `lecture`, `practice`, `lab`

### 2. Преобразовать CSV в XLSX

```bash
# В Excel:
1. Открыть CSV можно напрямую (File > Open)
2. Сохранить как XLSX (File > Save As > Excel)

# Или скриптом:
pip install openpyxl pandas
python -c "
import pandas as pd
df = pd.read_csv('schedule.csv')
df.to_excel('schedule.xlsx', index=False)
"
```

### 3. Загрузить
```
/import_schedule
# Отправить файл
```

### 4. Проверить результат
```
/schedule_stats      # Статистика
/export_schedule БПИ-24 30  # Экспортировать и открыть
```

---

## SQL запросы для диагностики

### Посмотреть все расписание
```sql
SELECT 
    sg.group_number,
    s.lesson_date,
    lt.lesson_number,
    lt.start_time,
    sub.name,
    t.fio,
    r.room_number
FROM schedule s
JOIN student_groups sg ON s.group_id = sg.id
JOIN lesson_times lt ON s.lesson_time_id = lt.id
JOIN subjects sub ON s.subject_id = sub.id
LEFT JOIN teachers t ON s.teacher_id = t.id
LEFT JOIN rooms r ON s.room_id = r.id
ORDER BY sg.group_number, s.lesson_date, lt.lesson_number
LIMIT 50;
```

### Посчитать записи по датам
```sql
SELECT 
    lesson_date,
    COUNT(*) as count
FROM schedule
GROUP BY lesson_date
ORDER BY lesson_date DESC;
```

### Посчитать записи по группам
```sql
SELECT 
    sg.group_number,
    COUNT(*) as count
FROM schedule s
JOIN student_groups sg ON s.group_id = sg.id
GROUP BY sg.group_number
ORDER BY sg.group_number;
```

### Проверить диапазон дат
```sql
SELECT 
    MIN(lesson_date) as earliest,
    MAX(lesson_date) as latest,
    MAX(lesson_date) - MIN(lesson_date) as days_span
FROM schedule;
```

---

## Частые ошибки при импорте и решения

### Ошибка: "Группа БПИ-24 не найдена"
**Причина:** Группа не существует в БД
**Решение:** 
```bash
# Проверить какие группы есть
SELECT group_number FROM student_groups ORDER BY group_number;

# Использовать существующую группу или создать новую в админ-панели
```

### Ошибка: "Неизвестный тип пары 'лекция'"
**Причина:** Используется русский текст вместо английского
**Решение:** Использовать: `lecture`, `practice`, `lab`

### Ошибка: "Дата в неправильном формате"
**Причина:** Дата вместо YYYY-MM-DD
**Решение:** 
- ❌ 10-02-2026 или 10.02.2026
- ✅ 2026-02-10

### Ошибка: "Время в неправильном формате"  
**Причина:** Время вместо HH:MM
**Решение:**
- ❌ 9:00 или 09-00
- ✅ 09:00

### Ошибка: "Пара должна быть числом"
**Причина:** Текст вместо номера
**Решение:**
- ❌ Первая пара или "1"
- ✅ 1

---

## Целостность данных

### При импорте автоматически создаются:
- ✅ Преподаватели (если указаны в поле)
- ✅ Аудитории (если указаны в поле)
- ✅ Предметы (всегда создаются)

### Не создаются автоматически:
- ❌ Группы - должны существовать в БД

### Что происходит при дублях:
- Если такое расписание уже есть → обновляется
- Если нового → добавляется

---

## Экспорт для проверки

После импорта сразу же нужно проверить:

```bash
# 1. Статистика
/schedule_stats

# 2. Экспортировать то, что добавили
/export_schedule БПИ-24 30

# 3. Открыть и визуально проверить в Excel
```

Если экспорт пустой → что-то не добавилось, проверить логи:
```bash
tail -50 bot.log | grep -i "import\|schedule"
```

---

## Быстрая диагностика

1. Запущен ли бот?
   ```bash
   ps aux | grep python | grep main.py
   ```

2. БД доступна?
   ```bash
   psql -U postgres -d schedule_bot_db -c "SELECT COUNT(*) FROM schedule;"
   ```

3. Есть ли группы?
   ```bash
   psql -U postgres -d schedule_bot_db -c "SELECT group_number FROM student_groups LIMIT 5;"
   ```

4. Какое расписание в БД?
   ```bash
   psql -U postgres -d schedule_bot_db -c "SELECT MIN(lesson_date), MAX(lesson_date), COUNT(*) FROM schedule;"
   ```

---

## Контакт для вопросов

При проблемах отправьте:
1. Результат `/schedule_stats`
2. Первые 10 строк лога: `tail -100 bot.log | head -50`
3. Ваш файл с расписанием для проверки
