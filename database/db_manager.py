"""
Менеджер базы данных для работы с PostgreSQL
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
            logger.info("Подключение к базе данных установлено")
            return self.connection
        except Exception as e:
            logger.error(f"Ошибка подключения к базе данных: {e}")
            raise
    
    def disconnect(self):
        """Закрытие соединения с базой данных"""
        if self.connection:
            self.connection.close()
            logger.info("Соединение с базой данных закрыто")
    
    def init_database(self):
        """Инициализация базы данных: создание таблиц и заполнение начальными данными"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # Создание таблиц
            logger.info("Создание таблиц...")
            cursor.execute(CREATE_TABLES_SQL)
            
            # Заполнение времени пар
            logger.info("Заполнение времени пар...")
            cursor.execute(INSERT_LESSON_TIMES_SQL)
            
            # Заполнение тестовыми данными
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
        """
        Выполнение SQL-запроса
        
        :param query: SQL-запрос
        :param params: Параметры запроса
        :param fetch: Нужно ли получить результат
        :return: Результат запроса или None
        """
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
        query = """
            INSERT INTO users (telegram_id, username, fio, role, group_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        result = self.execute_query(query, (telegram_id, username, fio, role, group_id), fetch=True)
        
        # Создание настроек для пользователя
        if result:
            user_id = result[0]['id']
            settings_query = "INSERT INTO user_settings (user_id) VALUES (%s)"
            self.execute_query(settings_query, (user_id,))
            
        return result[0] if result else None
    
    def log_user_action(self, user_id, action_type, action_details=None):
        """Логирование действий пользователя"""
        query = """
            INSERT INTO user_actions_log (user_id, action_type, action_details)
            VALUES (%s, %s, %s)
        """
        self.execute_query(query, (user_id, action_type, action_details))
    
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
        """Получение списка всех преподавателей"""
        query = """
            SELECT id, fio, department, position
            FROM teachers
            ORDER BY fio
        """
        return self.execute_query(query, fetch=True)
    
    def get_user_settings(self, user_id):
        """Получение настроек пользователя"""
        query = "SELECT * FROM user_settings WHERE user_id = %s"
        result = self.execute_query(query, (user_id,), fetch=True)
        return result[0] if result else None
    
    def update_user_settings(self, user_id, **settings):
        """Обновление настроек пользователя"""
        fields = ', '.join([f"{key} = %s" for key in settings.keys()])
        query = f"UPDATE user_settings SET {fields}, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s"
        values = list(settings.values()) + [user_id]
        self.execute_query(query, values)
