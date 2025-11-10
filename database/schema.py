"""
SQL-скрипт для создания базы данных расписания
"""

CREATE_TABLES_SQL = """
-- Таблица корпусов университета
CREATE TABLE IF NOT EXISTS buildings (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    address VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица кабинетов
CREATE TABLE IF NOT EXISTS rooms (
    id SERIAL PRIMARY KEY,
    building_id INTEGER REFERENCES buildings(id) ON DELETE CASCADE,
    room_number VARCHAR(20) NOT NULL,
    capacity INTEGER,
    room_type VARCHAR(50), -- лекционная, практическая, лабораторная
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(building_id, room_number)
);

-- Таблица факультетов
CREATE TABLE IF NOT EXISTS faculties (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    short_name VARCHAR(50),
    dean_fio VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица групп
CREATE TABLE IF NOT EXISTS student_groups (
    id SERIAL PRIMARY KEY,
    faculty_id INTEGER REFERENCES faculties(id) ON DELETE CASCADE,
    group_number VARCHAR(50) NOT NULL UNIQUE,
    course INTEGER,
    students_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица преподавателей
CREATE TABLE IF NOT EXISTS teachers (
    id SERIAL PRIMARY KEY,
    fio VARCHAR(255) NOT NULL,
    department VARCHAR(255),
    position VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица предметов
CREATE TABLE IF NOT EXISTS subjects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    short_name VARCHAR(100),
    subject_type VARCHAR(50), -- лекция, практика, лабораторная
    hours_total INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица времени пар
CREATE TABLE IF NOT EXISTS lesson_times (
    id SERIAL PRIMARY KEY,
    lesson_number INTEGER NOT NULL UNIQUE,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица расписания
CREATE TABLE IF NOT EXISTS schedule (
    id SERIAL PRIMARY KEY,
    group_id INTEGER REFERENCES student_groups(id) ON DELETE CASCADE,
    subject_id INTEGER REFERENCES subjects(id) ON DELETE CASCADE,
    teacher_id INTEGER REFERENCES teachers(id) ON DELETE SET NULL,
    room_id INTEGER REFERENCES rooms(id) ON DELETE SET NULL,
    lesson_time_id INTEGER REFERENCES lesson_times(id) ON DELETE CASCADE,
    lesson_date DATE NOT NULL,
    day_of_week INTEGER, -- 1-7 (понедельник-воскресенье)
    week_number INTEGER, -- номер недели в семестре
    is_numerator BOOLEAN DEFAULT TRUE, -- числитель/знаменатель
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица пользователей бота
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(100),
    fio VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user', -- developer, admin, user
    group_id INTEGER REFERENCES student_groups(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица логов действий пользователей
CREATE TABLE IF NOT EXISTS user_actions_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    action_type VARCHAR(100) NOT NULL,
    action_details TEXT,
    ip_address VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица настроек бота для пользователей
CREATE TABLE IF NOT EXISTS user_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    notifications_enabled BOOLEAN DEFAULT TRUE,
    notification_time TIME DEFAULT '08:00',
    show_week_schedule BOOLEAN DEFAULT FALSE,
    show_teacher_info BOOLEAN DEFAULT TRUE,
    show_room_info BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_schedule_group_date ON schedule(group_id, lesson_date);
CREATE INDEX IF NOT EXISTS idx_schedule_teacher ON schedule(teacher_id, lesson_date);
CREATE INDEX IF NOT EXISTS idx_schedule_room ON schedule(room_id, lesson_date);
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_user_actions_log_user_id ON user_actions_log(user_id);
"""

# SQL для начального заполнения таблицы времени пар
INSERT_LESSON_TIMES_SQL = """
INSERT INTO lesson_times (lesson_number, start_time, end_time) VALUES
(1, '09:00', '10:30'),
(2, '10:40', '12:10'),
(3, '12:40', '14:10'),
(4, '14:20', '15:50'),
(5, '16:20', '17:50'),
(6, '18:00', '19:30'),
(7, '19:40', '21:10')
ON CONFLICT (lesson_number) DO NOTHING;
"""

# SQL для добавления тестовых данных
INSERT_TEST_DATA_SQL = """
-- Добавление корпусов
INSERT INTO buildings (name, address) VALUES
('Главный корпус', 'ул. Ленина, д. 1'),
('Второй корпус', 'ул. Пушкина, д. 10'),
('Третий корпус', 'пр. Победы, д. 25')
ON CONFLICT DO NOTHING;

-- Добавление кабинетов
INSERT INTO rooms (building_id, room_number, capacity, room_type) VALUES
(1, '101', 30, 'лекционная'),
(1, '102', 25, 'практическая'),
(1, '201', 50, 'лекционная'),
(2, '301', 20, 'лабораторная'),
(2, '302', 30, 'практическая'),
(3, '401', 40, 'лекционная')
ON CONFLICT DO NOTHING;

-- Добавление факультетов
INSERT INTO faculties (name, short_name, dean_fio) VALUES
('Факультет информационных технологий', 'ФИТ', 'Иванов И.И.'),
('Экономический факультет', 'ЭФ', 'Петрова П.П.')
ON CONFLICT DO NOTHING;

-- Добавление групп
INSERT INTO student_groups (faculty_id, group_number, course, students_count) VALUES
(1, 'ИВТ-21', 4, 25),
(1, 'ИВТ-22', 4, 28),
(2, 'ЭК-31', 2, 30)
ON CONFLICT DO NOTHING;

-- Добавление преподавателей
INSERT INTO teachers (fio, department, position, email) VALUES
('Смирнов Алексей Петрович', 'Кафедра информатики', 'Доцент', 'smirnov@university.ru'),
('Козлова Мария Ивановна', 'Кафедра программирования', 'Профессор', 'kozlova@university.ru'),
('Новиков Дмитрий Сергеевич', 'Кафедра экономики', 'Старший преподаватель', 'novikov@university.ru')
ON CONFLICT DO NOTHING;

-- Добавление предметов
INSERT INTO subjects (name, short_name, subject_type, hours_total) VALUES
('Базы данных', 'БД', 'лекция', 72),
('Базы данных (практика)', 'БД (пр)', 'практика', 36),
('Программирование на Python', 'Python', 'лекция', 72),
('Веб-разработка', 'Web', 'лабораторная', 54)
ON CONFLICT DO NOTHING;
"""
