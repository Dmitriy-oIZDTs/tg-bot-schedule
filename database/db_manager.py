"""
Менеджер базы данных для работы с PostgreSQL
ИСПРАВЛЕНО: убран параметр commit, убрано дублирование методов
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from config.settings import DB_CONFIG
from database.schema import CREATE_TABLES_SQL, INSERT_LESSON_TIMES_SQL, INSERT_TEST_DATA_SQL

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Класс для управления подключением и операциями с базой данных"""
    
    def __init__(self):
        self.connection = None
    
    def connect(self):
        """Установка соединения с базой данных"""
        try:
            self.connection = psycopg2.connect(**DB_CONFIG)
            return self.connection
        except Exception as e:
            logger.error(f"Ошибка подключения к базе данных: {e}")
            raise
    
    def disconnect(self):
        """Закрытие соединения с базой данных"""
        if self.connection:
            self.connection.close()
    
    def init_database(self):
        """Инициализация базы данных"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            logger.info("Создание таблиц...")
            cursor.execute(CREATE_TABLES_SQL)
            
            logger.info("Заполнение времени пар...")
            cursor.execute(INSERT_LESSON_TIMES_SQL)
            
            logger.info("Заполнение тестовыми данными...")
            cursor.execute(INSERT_TEST_DATA_SQL)
            
            conn.commit()
            logger.info("База данных успешно инициализирована")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка инициализации базы данных: {e}")
            raise
        finally:
            cursor.close()
            self.disconnect()
    
    def execute_query(self, query, params=None, fetch=False):
        """Выполнение SQL-запроса"""
        conn = self.connect()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute(query, params)
            
            if fetch:
                result = cursor.fetchall()
                return result
            else:
                conn.commit()
                return cursor.rowcount
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка выполнения запроса: {e}")
            raise
        finally:
            cursor.close()
            self.disconnect()
    
    def get_user_by_telegram_id(self, telegram_id):
        """Получение пользователя по Telegram ID"""
        query = """
            SELECT u.*, sg.group_number, f.name as faculty_name
            FROM users u
            LEFT JOIN student_groups sg ON u.group_id = sg.id
            LEFT JOIN faculties f ON sg.faculty_id = f.id
            WHERE u.telegram_id = %s
        """
        result = self.execute_query(query, (telegram_id,), fetch=True)
        return result[0] if result else None
    
    def create_user(self, telegram_id, username, fio, role='user', group_id=None):
        """Создание нового пользователя"""
        conn = self.connect()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Создаем пользователя
            query = """
                INSERT INTO users (telegram_id, username, fio, role, group_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """
            cursor.execute(query, (telegram_id, username, fio, role, group_id))
            result = cursor.fetchone()
            user_id = result['id']
            
            # Создаем настройки
            settings_query = "INSERT INTO user_settings (user_id) VALUES (%s)"
            cursor.execute(settings_query, (user_id,))
            
            conn.commit()
            
            # Получаем полного пользователя
            cursor.execute("""
                SELECT u.*, sg.group_number, f.name as faculty_name
                FROM users u
                LEFT JOIN student_groups sg ON u.group_id = sg.id
                LEFT JOIN faculties f ON sg.faculty_id = f.id
                WHERE u.id = %s
            """, (user_id,))
            
            return cursor.fetchone()
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка создания пользователя: {e}")
            raise
        finally:
            cursor.close()
            self.disconnect()
    
    def update_user_group(self, user_id, group_id):
        """Обновление группы пользователя"""
        query = """
            UPDATE users 
            SET group_id = %s, last_active = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        self.execute_query(query, (group_id, user_id))
    
    def get_schedule_by_group(self, group_number, date):
        """Получение расписания группы на определенную дату"""
        query = """
            SELECT 
                s.lesson_date,
                lt.lesson_number,
                lt.start_time,
                lt.end_time,
                sub.name as subject_name,
                sub.subject_type,
                t.fio as teacher_fio,
                t.phone as teacher_phone,
                b.name as building_name,
                r.room_number,
                s.notes
            FROM schedule s
            JOIN student_groups sg ON s.group_id = sg.id
            JOIN lesson_times lt ON s.lesson_time_id = lt.id
            JOIN subjects sub ON s.subject_id = sub.id
            LEFT JOIN teachers t ON s.teacher_id = t.id
            LEFT JOIN rooms r ON s.room_id = r.id
            LEFT JOIN buildings b ON r.building_id = b.id
            WHERE sg.group_number = %s AND s.lesson_date = %s
            ORDER BY lt.lesson_number
        """
        return self.execute_query(query, (group_number, date), fetch=True)
    
    def get_schedule_by_group_range(self, group_number, date_from, date_to):
        """Получение расписания группы за период"""
        query = """
            SELECT 
                s.lesson_date,
                lt.lesson_number,
                lt.start_time,
                lt.end_time,
                sub.name as subject_name,
                sub.subject_type,
                t.fio as teacher_fio,
                b.name as building_name,
                r.room_number
            FROM schedule s
            JOIN student_groups sg ON s.group_id = sg.id
            JOIN lesson_times lt ON s.lesson_time_id = lt.id
            JOIN subjects sub ON s.subject_id = sub.id
            LEFT JOIN teachers t ON s.teacher_id = t.id
            LEFT JOIN rooms r ON s.room_id = r.id
            LEFT JOIN buildings b ON r.building_id = b.id
            WHERE sg.group_number = %s 
            AND s.lesson_date BETWEEN %s AND %s
            ORDER BY s.lesson_date, lt.lesson_number
        """
        return self.execute_query(query, (group_number, date_from, date_to), fetch=True)

    def get_schedule_by_faculty(self, faculty_id, date):
        """Получение расписания всего факультета на дату"""
        query = """
            SELECT 
                sg.group_number,
                s.lesson_date,
                lt.lesson_number,
                lt.start_time,
                lt.end_time,
                sub.name as subject_name,
                t.fio as teacher_fio,
                r.room_number,
                b.name as building_name
            FROM schedule s
            JOIN student_groups sg ON s.group_id = sg.id
            JOIN faculties f ON sg.faculty_id = f.id
            JOIN lesson_times lt ON s.lesson_time_id = lt.id
            JOIN subjects sub ON s.subject_id = sub.id
            LEFT JOIN teachers t ON s.teacher_id = t.id
            LEFT JOIN rooms r ON s.room_id = r.id
            LEFT JOIN buildings b ON r.building_id = b.id
            WHERE f.id = %s AND s.lesson_date = %s
            ORDER BY sg.group_number, lt.lesson_number
        """
        return self.execute_query(query, (faculty_id, date), fetch=True)
    
    def get_teacher_schedule(self, teacher_id, date):
        """Получение расписания преподавателя на дату"""
        query = """
            SELECT 
                s.lesson_date,
                lt.lesson_number,
                lt.start_time,
                lt.end_time,
                sg.group_number,
                sub.name as subject_name,
                b.name as building_name,
                r.room_number
            FROM schedule s
            JOIN lesson_times lt ON s.lesson_time_id = lt.id
            JOIN student_groups sg ON s.group_id = sg.id
            JOIN subjects sub ON s.subject_id = sub.id
            LEFT JOIN rooms r ON s.room_id = r.id
            LEFT JOIN buildings b ON r.building_id = b.id
            WHERE s.teacher_id = %s AND s.lesson_date = %s
            ORDER BY lt.lesson_number
        """
        return self.execute_query(query, (teacher_id, date), fetch=True)
    
    def get_room_schedule(self, room_id, date):
        """Получение расписания кабинета на дату"""
        query = """
            SELECT 
                s.lesson_date,
                lt.lesson_number,
                lt.start_time,
                lt.end_time,
                sg.group_number,
                sub.name as subject_name,
                t.fio as teacher_fio
            FROM schedule s
            JOIN lesson_times lt ON s.lesson_time_id = lt.id
            JOIN student_groups sg ON s.group_id = sg.id
            JOIN subjects sub ON s.subject_id = sub.id
            LEFT JOIN teachers t ON s.teacher_id = t.id
            WHERE s.room_id = %s AND s.lesson_date = %s
            ORDER BY lt.lesson_number
        """
        return self.execute_query(query, (room_id, date), fetch=True)
    
    def get_all_groups(self):
        """Получение списка всех групп"""
        query = """
            SELECT sg.id, sg.group_number, sg.course, f.name as faculty_name
            FROM student_groups sg
            JOIN faculties f ON sg.faculty_id = f.id
            ORDER BY f.name, sg.group_number
        """
        return self.execute_query(query, fetch=True)
    
    def get_all_teachers(self):
        """Получение списка всех преподавателей (без дублей)"""
        query = """
            SELECT DISTINCT ON (fio) id, fio, department, position
            FROM teachers
            ORDER BY fio, id
        """
        return self.execute_query(query, fetch=True)
    
    def get_all_users(self):
        """Получение всех пользователей"""
        query = "SELECT id, telegram_id, username, role FROM users"
        return self.execute_query(query, fetch=True)

    # ===== РОЛИ ПОЛЬЗОВАТЕЛЕЙ =====

    def update_user_role(self, user_id: int, role: str):
        """Обновление роли пользователя"""
        query = "UPDATE users SET role = %s WHERE id = %s"
        self.execute_query(query, (role, user_id))

    # ===== НАСТРОЙКИ ПОЛЬЗОВАТЕЛЯ =====

    def get_user_settings(self, user_id: int):
        """Получение настроек пользователя"""
        query = """
            SELECT time_format, notifications, default_view, theme
            FROM user_settings
            WHERE user_id = %s
        """
        rows = self.execute_query(query, (user_id,), fetch=True)
        return rows[0] if rows else None

    def update_user_settings(self, user_id: int, settings: dict):
        """
        Обновление настроек пользователя
        settings: {'time_format': '24', 'notifications': True, ...}
        """
        # Проверяем, есть ли запись
        existing = self.get_user_settings(user_id)
        if existing is None:
            # Создаём запись по умолчанию
            insert_query = "INSERT INTO user_settings (user_id) VALUES (%s)"
            self.execute_query(insert_query, (user_id,))

        # Формируем динамический UPDATE
        fields = []
        values = []
        for key, value in settings.items():
            fields.append(f"{key} = %s")
            values.append(value)
        values.append(user_id)

        update_query = f"""
            UPDATE user_settings
            SET {", ".join(fields)}, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """
        self.execute_query(update_query, tuple(values))

    # ===== ЛОГИ ДЕЙСТВИЙ ПОЛЬЗОВАТЕЛЕЙ =====

    def log_user_action(self, telegram_id: int, action: str, details: str = ""):
        """
        Записываем действие в таблицу user_actions
        """
        user = self.get_user_by_telegram_id(telegram_id)
        user_id = user["id"] if user else None
        username = user["username"] if user else None

        query = """
            INSERT INTO user_actions (user_id, telegram_id, username, action, details)
            VALUES (%s, %s, %s, %s, %s)
        """
        self.execute_query(query, (user_id, telegram_id, username, action, details))

    def get_user_actions(self, last_days: int = 1):
        """
        Возвращает последние действия пользователей за N дней
        """
        query = """
            SELECT user_id, telegram_id, username, action, details, created_at
            FROM user_actions
            WHERE created_at >= NOW() - INTERVAL %s
            ORDER BY created_at DESC
        """
        param = f"{last_days} days"
        return self.execute_query(query, (param,), fetch=True)