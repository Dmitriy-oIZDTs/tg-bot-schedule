import psycopg2
from datetime import datetime, timedelta
import random
from config.settings import DB_CONFIG


def generate_test_schedule():
    """Генерация тестового расписания"""
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        print("Начало генерации тестового расписания...")
        
        # Получаем все группы
        cursor.execute("SELECT id, group_number FROM student_groups")
        groups = cursor.fetchall()
        
        # Получаем все предметы
        cursor.execute("SELECT id FROM subjects")
        subjects = cursor.fetchall()
        
        # Получаем всех преподавателей
        cursor.execute("SELECT id FROM teachers")
        teachers = cursor.fetchall()
        
        # Получаем все аудитории
        cursor.execute("SELECT id FROM rooms")
        rooms = cursor.fetchall()
        
        # Получаем время пар
        cursor.execute("SELECT id FROM lesson_times ORDER BY lesson_number")
        lesson_times = cursor.fetchall()
        
        if not all([groups, subjects, teachers, rooms, lesson_times]):
            print("Ошибка: недостаточно данных в базе для генерации расписания")
            return
        
        # Генерируем расписание на 2 недели вперед (рабочие дни)
        start_date = datetime.now()
        
        schedule_entries = []
        
        for group_id, group_number in groups:
            print(f"Генерация расписания для группы {group_number}...")
            
            for day_offset in range(14):
                current_date = start_date + timedelta(days=day_offset)
                day_of_week = current_date.weekday() + 1  # 1-7 (понедельник-воскресенье)
                
                # Пропускаем выходные
                if day_of_week in [6, 7]:
                    continue
                
                # Определяем количество пар в день (3-5 пар)
                num_lessons = random.randint(3, 5)
                
                # Выбираем случайные пары для этого дня
                selected_lesson_times = random.sample(lesson_times[:5], num_lessons)
                
                for lesson_time_id, in selected_lesson_times:
                    subject_id, = random.choice(subjects)
                    teacher_id, = random.choice(teachers)
                    room_id, = random.choice(rooms)
                    
                    # Определяем числитель/знаменатель
                    week_number = (day_offset // 7) + 1
                    is_numerator = week_number % 2 == 1
                    
                    schedule_entries.append((
                        group_id,
                        subject_id,
                        teacher_id,
                        room_id,
                        lesson_time_id,
                        current_date.date(),
                        day_of_week,
                        week_number,
                        is_numerator
                    ))
        
        # Массовая вставка данных
        print("Вставка данных в базу...")
        insert_query = """
            INSERT INTO schedule 
            (group_id, subject_id, teacher_id, room_id, lesson_time_id, 
             lesson_date, day_of_week, week_number, is_numerator)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.executemany(insert_query, schedule_entries)
        conn.commit()
        
        print(f"✅ Успешно создано {len(schedule_entries)} записей расписания!")
        print(f"📅 Расписание создано на период с {start_date.strftime('%d.%m.%Y')} "
              f"по {(start_date + timedelta(days=13)).strftime('%d.%m.%Y')}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка при генерации расписания: {e}")
        raise
    finally:
        cursor.close()
        conn.close()
