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
            # Попытка вставить пользователя, если уже есть - получить id
            insert_query = """
                INSERT INTO users (telegram_id, username, fio, role, group_id)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (telegram_id) DO NOTHING
                RETURNING id
            """
            cursor.execute(insert_query, (telegram_id, username, fio, role, group_id))
            result = cursor.fetchone()
            if result and result.get('id'):
                user_id = result['id']
            else:
                # Если запись уже существует или RETURNING не вернул id, получить по telegram_id
                cursor.execute("SELECT id FROM users WHERE telegram_id = %s", (telegram_id,))
                res = cursor.fetchone()
                if not res:
                    raise Exception("Не удалось создать или найти пользователя в таблице users")
                user_id = res['id']

            # Создаем настройки если их нет
            settings_query = "INSERT INTO user_settings (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING"
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
    
    def get_all_schedule_range(self, date_from, date_to, group_number=None):
        """Получение расписания за период для всех групп или конкретной группы"""
        if group_number:
            # Расписание для конкретной группы
            query = """
                SELECT 
                    sg.group_number,
                    s.lesson_date,
                    lt.lesson_number,
                    lt.start_time,
                    lt.end_time,
                    sub.name as subject_name,
                    sub.subject_type,
                    t.fio as teacher_fio,
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
                WHERE sg.group_number = %s 
                AND s.lesson_date BETWEEN %s AND %s
                ORDER BY s.lesson_date, lt.lesson_number
            """
            return self.execute_query(query, (group_number, date_from, date_to), fetch=True)
        else:
            # Расписание для всех групп
            query = """
                SELECT 
                    sg.group_number,
                    s.lesson_date,
                    lt.lesson_number,
                    lt.start_time,
                    lt.end_time,
                    sub.name as subject_name,
                    sub.subject_type,
                    t.fio as teacher_fio,
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
                WHERE s.lesson_date BETWEEN %s AND %s
                ORDER BY sg.group_number, s.lesson_date, lt.lesson_number
            """
            return self.execute_query(query, (date_from, date_to), fetch=True)
    
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

    # ===== ИМПОРТ РАСПИСАНИЯ =====

    def get_or_create_subject(self, subject_name: str, subject_type: str = "lecture"):
        """Получить или создать предмет"""
        try:
            # Ищем существующий предмет
            query = "SELECT id FROM subjects WHERE name = %s LIMIT 1"
            result = self.execute_query(query, (subject_name,), fetch=True)
            
            if result:
                return result[0]['id']
            
            # Создаём новый предмет
            insert_query = """
                INSERT INTO subjects (name, subject_type)
                VALUES (%s, %s)
                RETURNING id
            """
            conn = self.connect()
            cursor = conn.cursor()
            try:
                cursor.execute(insert_query, (subject_name, subject_type))
                new_id = cursor.fetchone()[0]
                conn.commit()
                return new_id
            finally:
                cursor.close()
                self.disconnect()
        except Exception as e:
            logger.error(f"Ошибка при создании предмета '{subject_name}': {e}")
            raise

    def get_or_create_teacher(self, teacher_fio: str):
        """Получить или создать преподавателя"""
        if not teacher_fio:
            return None
            
        try:
            # Ищем существующего преподавателя
            query = "SELECT id FROM teachers WHERE fio = %s LIMIT 1"
            result = self.execute_query(query, (teacher_fio,), fetch=True)
            
            if result:
                return result[0]['id']
            
            # Создаём нового преподавателя
            insert_query = "INSERT INTO teachers (fio) VALUES (%s) RETURNING id"
            conn = self.connect()
            cursor = conn.cursor()
            try:
                cursor.execute(insert_query, (teacher_fio,))
                new_id = cursor.fetchone()[0]
                conn.commit()
                return new_id
            finally:
                cursor.close()
                self.disconnect()
        except Exception as e:
            logger.error(f"Ошибка при создании преподавателя '{teacher_fio}': {e}")
            raise

    def get_or_create_room(self, room_number: str):
        """Получить или создать аудиторию"""
        if not room_number:
            return None
            
        try:
            # Ищем существующую аудиторию
            query = "SELECT id FROM rooms WHERE room_number = %s LIMIT 1"
            result = self.execute_query(query, (room_number,), fetch=True)
            
            if result:
                return result[0]['id']
            
            # Создаём новую аудиторию (по умолчанию здание 1)
            insert_query = """
                INSERT INTO rooms (room_number, building_id)
                VALUES (%s, (SELECT id FROM buildings LIMIT 1))
                RETURNING id
            """
            conn = self.connect()
            cursor = conn.cursor()
            try:
                cursor.execute(insert_query, (room_number,))
                result = cursor.fetchone()
                if result:
                    new_id = result[0]
                    conn.commit()
                    return new_id
                else:
                    # Если зданий нет, создаём здание
                    cursor.execute("INSERT INTO buildings (name) VALUES ('Главный корпус') RETURNING id")
                    building_id = cursor.fetchone()[0]
                    cursor.execute(
                        "INSERT INTO rooms (room_number, building_id) VALUES (%s, %s) RETURNING id",
                        (room_number, building_id)
                    )
                    new_id = cursor.fetchone()[0]
                    conn.commit()
                    return new_id
            finally:
                cursor.close()
                self.disconnect()
        except Exception as e:
            logger.error(f"Ошибка при создании аудитории '{room_number}': {e}")
            raise

    def add_schedule_from_import(self, group_number: str, lesson_date: str, lesson_number: int,
                                start_time: str, end_time: str, subject_name: str,
                                subject_type: str = "lecture", teacher_fio: str = None,
                                room_number: str = None):
        """
        Добавить расписание из импорта.
        Автоматически создаст недостающие сущности (преподавателя, аудиторию, предмет).
        """
        try:
            # Получаем/создаём группу
            groups = self.execute_query(
                "SELECT id FROM student_groups WHERE group_number = %s",
                (group_number,), fetch=True
            )
            
            if not groups:
                raise ValueError(f"Группа '{group_number}' не найдена")
            
            group_id = groups[0]['id']
            
            # Получаем/создаём предмет
            subject_id = self.get_or_create_subject(subject_name, subject_type)
            
            # Получаем/создаём преподавателя
            teacher_id = None
            if teacher_fio:
                teacher_id = self.get_or_create_teacher(teacher_fio)
            
            # Получаем/создаём аудиторию
            room_id = None
            if room_number:
                room_id = self.get_or_create_room(room_number)
            
            # Получаем время пары
            lesson_times = self.execute_query(
                "SELECT id FROM lesson_times WHERE lesson_number = %s",
                (lesson_number,), fetch=True
            )
            
            if not lesson_times:
                raise ValueError(f"Пара номер {lesson_number} не найдена")
            
            lesson_time_id = lesson_times[0]['id']
            
            # Проверяем, нет ли уже такой записи
            existing = self.execute_query("""
                SELECT id FROM schedule 
                WHERE group_id = %s AND lesson_date = %s 
                AND lesson_time_id = %s
            """, (group_id, lesson_date, lesson_time_id), fetch=True)
            
            if existing:
                # Обновляем существующую запись
                update_query = """
                    UPDATE schedule
                    SET subject_id = %s, teacher_id = %s, room_id = %s
                    WHERE id = %s
                """
                self.execute_query(
                    update_query,
                    (subject_id, teacher_id, room_id, existing[0]['id'])
                )
            else:
                # Создаём новую запись
                insert_query = """
                    INSERT INTO schedule (group_id, lesson_date, lesson_time_id, subject_id, teacher_id, room_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                self.execute_query(
                    insert_query,
                    (group_id, lesson_date, lesson_time_id, subject_id, teacher_id, room_id)
                )
            
            logger.info(f"Добавлено расписание: {group_number} {lesson_date} пара {lesson_number}")
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении расписания: {e}")
            raise

    def delete_schedule_for_group(self, group_number: str, date_from: str = None, date_to: str = None):
        """Удалить расписание группы за период (или всё)"""
        try:
            groups = self.execute_query(
                "SELECT id FROM student_groups WHERE group_number = %s",
                (group_number,), fetch=True
            )
            
            if not groups:
                raise ValueError(f"Группа '{group_number}' не найдена")
            
            group_id = groups[0]['id']
            
            if date_from and date_to:
                query = """
                    DELETE FROM schedule
                    WHERE group_id = %s AND lesson_date BETWEEN %s AND %s
                """
                self.execute_query(query, (group_id, date_from, date_to))
            else:
                query = "DELETE FROM schedule WHERE group_id = %s"
                self.execute_query(query, (group_id,))
            
            logger.info(f"Удалено расписание для группы {group_number}")
        except Exception as e:
            logger.error(f"Ошибка при удалении расписания: {e}")
            raise

    def get_teacher_schedule_range(self, teacher_id, date_from, date_to):
        """Получение расписания преподавателя за период (оптимизировано для недели)"""
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
            WHERE s.teacher_id = %s AND s.lesson_date BETWEEN %s AND %s
            ORDER BY s.lesson_date, lt.lesson_number
        """
        return self.execute_query(query, (teacher_id, date_from, date_to), fetch=True)
    
    def get_room_schedule_range(self, room_id, date_from, date_to):
        """Получение расписания кабинета за период (оптимизировано для недели)"""
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
            WHERE s.room_id = %s AND s.lesson_date BETWEEN %s AND %s
            ORDER BY s.lesson_date, lt.lesson_number
        """
        return self.execute_query(query, (room_id, date_from, date_to), fetch=True)

    def get_schedule_stats(self):
        """Получить статистику по расписанию в БД"""
        stats = {}
        try:
            # Количество записей по датам
            query = """
                SELECT 
                    COUNT(*) as total_records,
                    MIN(lesson_date) as earliest_date,
                    MAX(lesson_date) as latest_date,
                    COUNT(DISTINCT lesson_date) as unique_dates,
                    COUNT(DISTINCT group_id) as unique_groups
                FROM schedule
            """
            result = self.execute_query(query, fetch=True)
            if result:
                stats.update(result[0])
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики расписания: {e}")
        
        return stats