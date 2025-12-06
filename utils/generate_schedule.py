"""
Скрипт для генерации расписания
- Генерация семестра (произвольное количество недель)
- Генерация полного учебного года:
    осень: 1 сентября – 31 декабря
    весна: 10 февраля – 29 мая
"""

import psycopg2
from datetime import datetime, timedelta
import random

# Настройки подключения к БД
DB_CONFIG = {
    'host': 'localhost',
    'database': 'schedule_bot_db',
    'user': 'postgres',
    'password': 'postgres'
}

# Типы занятий
LESSON_TYPES = ['lecture', 'practice', 'lab']

# Дни недели для занятий (0 = понедельник, 5 = суббота)
WEEKDAYS = [0, 1, 2, 3, 4, 5]


def generate_semester_schedule(semester_start_date: datetime,
                               weeks_count: int = 18,
                               clear_old: bool = True):
    """
    Генерация расписания на семестр

    :param semester_start_date: Дата начала семестра (datetime)
    :param weeks_count: Количество недель
    :param clear_old: Если True — удаляем старое расписание начиная с semester_start_date
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        # Получаем все группы
        cursor.execute("SELECT id, group_number FROM student_groups")
        groups = cursor.fetchall()

        # Получаем все предметы
        cursor.execute("SELECT id, name FROM subjects")
        subjects = cursor.fetchall()

        # Получаем всех преподавателей
        cursor.execute("SELECT id, fio FROM teachers")
        teachers = cursor.fetchall()

        # Получаем все аудитории
        cursor.execute("SELECT id, room_number FROM rooms")
        rooms = cursor.fetchall()

        # Получаем время пар
        cursor.execute("SELECT id, lesson_number FROM lesson_times ORDER BY lesson_number")
        lesson_times = cursor.fetchall()

        print(f"Генерация расписания на {weeks_count} недель...")
        print(f"Групп: {len(groups)}, Предметов: {len(subjects)}")

        # Очищаем старое расписание (опционально)
        if clear_old:
            cursor.execute("DELETE FROM schedule WHERE lesson_date >= %s", (semester_start_date,))
            print(f"Удалено старых записей: {cursor.rowcount}")
        else:
            print("Очистка старого расписания отключена (clear_old=False)")

        total_lessons = 0

        # Для каждой недели
        for week in range(weeks_count):
            # ИСПРАВЛЕНИЕ: правильный расчет начала недели
            # Находим понедельник первой недели
            if week == 0:
                # Для первой недели: находим ближайший понедельник
                days_since_monday = semester_start_date.weekday()
                week_start = semester_start_date - timedelta(days=days_since_monday)
            else:
                # Для остальных недель: просто добавляем 7 дней
                week_start = semester_start_date - timedelta(days=semester_start_date.weekday()) + timedelta(weeks=week)

            print(f"Неделя {week + 1}: {week_start.strftime('%d.%m.%Y')}")

            # Для каждой группы
            for group_id, group_number in groups:
                # Выбираем 3-4 случайных предмета для группы на неделю
                group_subjects = random.sample(subjects, min(4, len(subjects)))

                # Для каждого дня недели ПН–СБ
                for day_offset in range(6):
                    lesson_date = week_start + timedelta(days=day_offset)

                    # Генерируем 2-4 пары в день
                    lessons_per_day = random.randint(2, 4)

                    # Выбираем случайные пары из доступных
                    day_lessons = random.sample(
                        lesson_times,
                        min(lessons_per_day, len(lesson_times))
                    )

                    for lesson_time_id, lesson_number in day_lessons:
                        # Случайный предмет
                        subject_id, subject_name = random.choice(group_subjects)

                        # Случайный преподаватель
                        teacher_id, teacher_name = random.choice(teachers)

                        # Случайная аудитория
                        room_id, room_number = random.choice(rooms)

                        # Заметки (иногда)
                        notes = None
                        if random.random() < 0.1:  # 10% вероятность
                            notes = random.choice([
                                "Дистанционно",
                                "Перенесено из ауд. 101",
                                "Консультация",
                                None
                            ])

                        # Вставляем запись в расписание
                        insert_query = """
                            INSERT INTO schedule 
                            (group_id, subject_id, teacher_id, room_id, lesson_time_id, lesson_date, notes)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """
                        cursor.execute(insert_query, (
                            group_id, subject_id, teacher_id, room_id,
                            lesson_time_id, lesson_date, notes
                        ))
                        total_lessons += 1

        conn.commit()
        print(f"\n✅ Успешно создано {total_lessons} занятий")

        # Статистика
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT group_id) as groups,
                COUNT(DISTINCT teacher_id) as teachers,
                COUNT(DISTINCT room_id) as rooms
            FROM schedule
            WHERE lesson_date >= %s
        """, (semester_start_date,))
        stats = cursor.fetchone()
        print(f"\nСтатистика:")
        print(f"  Всего занятий: {stats[0]}")
        print(f"  Задействовано групп: {stats[1]}")
        print(f"  Задействовано преподавателей: {stats[2]}")
        print(f"  Задействовано аудиторий: {stats[3]}")

    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def update_subject_types():
    """Обновление типов занятий для предметов"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, name FROM subjects")
        subjects = cursor.fetchall()

        for subject_id, subject_name in subjects:
            name_lower = subject_name.lower()
            if any(word in name_lower for word in ['лабораторная', 'лаб.', 'lab']):
                lesson_type = 'lab'
            elif any(word in name_lower for word in ['практика', 'практ.', 'practice']):
                lesson_type = 'practice'
            else:
                lesson_type = 'lecture'

            cursor.execute(
                "UPDATE subjects SET lesson_type = %s WHERE id = %s",
                (lesson_type, subject_id)
            )

        conn.commit()
        print(f"✅ Обновлены типы для {len(subjects)} предметов")

    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


# ---------- НОВОЕ: генерация полного учебного года ----------

def schedule_exists_anywhere() -> bool:
    """Проверяем, есть ли вообще хоть одно занятие в таблице schedule."""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM schedule LIMIT 1")
        return cursor.fetchone() is not None
    finally:
        cursor.close()
        conn.close()


def weeks_between(start: datetime, end: datetime) -> int:
    """
    Считает количество ПОЛНЫХ НЕДЕЛЬ между датами start и end.
    """
    days = (end - start).days
    return days // 7  # количество полных недель


def generate_full_academic_year(start_year: int, clear_old: bool = True):
    """
    Генерация полного учебного года:
    - осенний семестр: с 1 сентября start_year по 31 декабря start_year
    - весенний семестр: с 10 февраля (start_year+1) по 29 мая (start_year+1)
    """
    # ОСЕННИЙ СЕМЕСТР
    autumn_start = datetime(start_year, 9, 1)
    autumn_end = datetime(start_year, 12, 31)  # 31 декабря включительно
    
    # Рассчитываем количество недель для осеннего семестра
    # Обычно это около 17 недель (сентябрь-декабрь)
    autumn_weeks = weeks_between(autumn_start, autumn_end + timedelta(days=1))

    print(f"\n{'='*60}")
    print(f"ОСЕННИЙ СЕМЕСТР {start_year}")
    print(f"{'='*60}")
    print(f"Период: {autumn_start.strftime('%d.%m.%Y')} — {autumn_end.strftime('%d.%m.%Y')}")
    print(f"Недель: {autumn_weeks}")

    generate_semester_schedule(
        semester_start_date=autumn_start,
        weeks_count=autumn_weeks,
        clear_old=clear_old,  # чистим только один раз, перед всем годом
    )

    # ВЕСЕННИЙ СЕМЕСТР
    spring_start = datetime(start_year + 1, 2, 10)
    spring_end = datetime(start_year + 1, 5, 29)  # 29 мая включительно
    
    # Рассчитываем количество недель для весеннего семестра
    # Обычно это около 15 недель (февраль-май)
    spring_weeks = weeks_between(spring_start, spring_end + timedelta(days=1))

    print(f"\n{'='*60}")
    print(f"ВЕСЕННИЙ СЕМЕСТР {start_year + 1}")
    print(f"{'='*60}")
    print(f"Период: {spring_start.strftime('%d.%m.%Y')} — {spring_end.strftime('%d.%m.%Y')}")
    print(f"Недель: {spring_weeks}")

    # Важно: clear_old=False, чтобы не снести осенний семестр
    generate_semester_schedule(
        semester_start_date=spring_start,
        weeks_count=spring_weeks,
        clear_old=False,
    )

    print(f"\n{'='*60}")
    print(f"✅ УЧЕБНЫЙ ГОД {start_year}-{start_year + 1} СГЕНЕРИРОВАН")
    print(f"{'='*60}")


def ensure_schedule_for_academic_year():
    """
    Вызывается при старте бота.
    Если в schedule уже есть записи — ничего не делаем.
    Если пусто — генерируем полный учебный год:
        1.09.Y — 31.12.Y (осень)
        10.02.(Y+1) — 29.05.(Y+1) (весна)
    """
    if schedule_exists_anywhere():
        print("✅ В таблице schedule уже есть данные — генерация при старте не требуется.")
        return

    today = datetime.now()
    # Учебный год начинается осенью:
    # если сейчас сентябрь–декабрь -> учебный год этого же года
    # если январь–август -> учебный год начался прошлой осенью
    if today.month >= 9:
        start_year = today.year
    else:
        start_year = today.year - 1

    print(f"\n⚠️ Расписания нет. Генерируем учебный год {start_year}-{start_year + 1}...")
    # Перед полным годом чистим всё расписание целиком
    generate_full_academic_year(start_year=start_year, clear_old=True)
    print(f"\n✅ Генерация учебного года {start_year}-{start_year + 1} завершена.")


# ---------- Ручной запуск как отдельного скрипта ----------

if __name__ == "__main__":
    print("=" * 60)
    print("ГЕНЕРАЦИЯ РАСПИСАНИЯ")
    print("=" * 60)

    # Определяем учебный год относительно сегодняшней даты
    today = datetime.now()
    if today.month >= 9:
        start_year = today.year
    else:
        start_year = today.year - 1

    print(f"Учебный год: {start_year}-{start_year + 1}")

    print("\n1. Обновление типов занятий...")
    update_subject_types()

    print("\n2. Генерация полного учебного года...")
    generate_full_academic_year(start_year=start_year, clear_old=True)

    print("\n" + "=" * 60)
    print("ГОТОВО!")
    print("=" * 60)