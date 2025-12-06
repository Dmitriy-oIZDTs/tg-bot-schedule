#!/usr/bin/env python3
"""
Скрипт для проверки расписания в базе данных
Показывает статистику по неделям и месяцам
"""

import psycopg2
from datetime import datetime, timedelta

DB_CONFIG = {
    'host': 'localhost',
    'database': 'schedule_bot_db',
    'user': 'postgres',
    'password': 'postgres'
}


def check_schedule_stats():
    """Проверка статистики по расписанию"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        # Общая статистика
        cursor.execute("""
            SELECT 
                MIN(lesson_date) as first_date,
                MAX(lesson_date) as last_date,
                COUNT(*) as total_lessons,
                COUNT(DISTINCT lesson_date) as unique_dates
            FROM schedule
        """)
        stats = cursor.fetchone()

        if not stats[0]:
            print("❌ В таблице schedule нет данных!")
            return

        print("=" * 60)
        print("СТАТИСТИКА РАСПИСАНИЯ")
        print("=" * 60)
        print(f"Период: {stats[0]} — {stats[1]}")
        print(f"Всего занятий: {stats[2]}")
        print(f"Уникальных дней: {stats[3]}")
        print()

        # Статистика по месяцам
        cursor.execute("""
            SELECT 
                TO_CHAR(lesson_date, 'YYYY-MM') as month,
                TO_CHAR(lesson_date, 'Month YYYY') as month_name,
                COUNT(*) as lessons_count,
                COUNT(DISTINCT lesson_date) as days_count
            FROM schedule
            GROUP BY TO_CHAR(lesson_date, 'YYYY-MM'), TO_CHAR(lesson_date, 'Month YYYY')
            ORDER BY month
        """)
        months = cursor.fetchall()

        print("РАСПРЕДЕЛЕНИЕ ПО МЕСЯЦАМ:")
        print("-" * 60)
        for month_code, month_name, lessons, days in months:
            print(f"{month_name:20} | Занятий: {lessons:5} | Дней: {days:3}")

        # Статистика по неделям
        print("\n" + "=" * 60)
        print("ПЕРВЫЕ 10 НЕДЕЛЬ:")
        print("-" * 60)

        first_date = stats[0]
        for week in range(10):
            week_start = first_date + timedelta(weeks=week)
            week_end = week_start + timedelta(days=6)

            cursor.execute("""
                SELECT COUNT(*) 
                FROM schedule 
                WHERE lesson_date BETWEEN %s AND %s
            """, (week_start, week_end))

            count = cursor.fetchone()[0]
            print(f"Неделя {week+1:2d} ({week_start} — {week_end}): {count:4d} занятий")

        # Проверка пустых дней в первом месяце
        print("\n" + "=" * 60)
        print("ПРОВЕРКА ПЕРВОГО МЕСЯЦА (по дням):")
        print("-" * 60)

        first_month_end = datetime(first_date.year, first_date.month + 1 if first_date.month < 12 else 1, 1) - timedelta(days=1)

        current_date = first_date
        while current_date <= first_month_end:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM schedule 
                WHERE lesson_date = %s
            """, (current_date,))

            count = cursor.fetchone()[0]
            day_name = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС'][current_date.weekday()]

            if count == 0:
                print(f"{current_date} ({day_name}): ❌ НЕТ ЗАНЯТИЙ")
            else:
                print(f"{current_date} ({day_name}): ✅ {count:3d} занятий")

            current_date += timedelta(days=1)

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    check_schedule_stats()