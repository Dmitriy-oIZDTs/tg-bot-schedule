# -*- coding: utf-8 -*-

CREATE_TABLES_SQL = """
-- =========================
-- ТАБЛИЦА КОРПУСОВ
-- =========================
CREATE TABLE IF NOT EXISTS buildings (
    id SERIAL PRIMARY KEY,
    building_name VARCHAR(255) NOT NULL,
    address VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- ТАБЛИЦА АУДИТОРИЙ
-- =========================
CREATE TABLE IF NOT EXISTS rooms (
    id SERIAL PRIMARY KEY,
    building_id INTEGER REFERENCES buildings(id) ON DELETE SET NULL,
    room_number VARCHAR(50) NOT NULL,
    capacity INTEGER,
    room_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (building_id, room_number)
);

-- =========================
-- ТАБЛИЦА ГРУПП
-- =========================
CREATE TABLE IF NOT EXISTS groups (
    id SERIAL PRIMARY KEY,
    group_number VARCHAR(50) NOT NULL UNIQUE,
    faculty_name VARCHAR(255),
    course INTEGER,
    students_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- ТАБЛИЦА ПРЕПОДАВАТЕЛЕЙ
-- =========================
CREATE TABLE IF NOT EXISTS teachers (
    id SERIAL PRIMARY KEY,
    fio VARCHAR(255) NOT NULL,
    department VARCHAR(255),
    position VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- ТАБЛИЦА ПРЕДМЕТОВ (опционально, если нужно отдельно хранить)
-- =========================
CREATE TABLE IF NOT EXISTS subjects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    short_name VARCHAR(100),
    subject_type VARCHAR(50), -- лекция, практика, лабораторная
    hours_total INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- ТАБЛИЦА ВРЕМЕНИ ПАР
-- =========================
CREATE TABLE IF NOT EXISTS lessons_time (
    id SERIAL PRIMARY KEY,
    lesson_number INTEGER NOT NULL UNIQUE,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- ТАБЛИЦА РАСПИСАНИЯ
-- =========================
CREATE TABLE IF NOT EXISTS schedule (
    id SERIAL PRIMARY KEY,

    -- Дата и номер пары
    lesson_date   DATE NOT NULL,
    lesson_number INTEGER NOT NULL,

    -- Название предмета и тип (лекция/пр/лаб)
    subject_name  VARCHAR(255) NOT NULL,
    subject_type  VARCHAR(50),
    notes         TEXT,

    -- Связи
    group_id      INTEGER REFERENCES groups(id) ON DELETE CASCADE,
    teacher_id    INTEGER REFERENCES teachers(id) ON DELETE SET NULL,
    room_id       INTEGER REFERENCES rooms(id) ON DELETE SET NULL,

    -- Денормализованные поля (для быстрого вывода без JOIN)
    group_number  VARCHAR(50),
    teacher_fio   VARCHAR(255),
    building_name VARCHAR(255),
    room_number   VARCHAR(50),

    -- Время пары (дублируем из lessons_time)
    start_time    TIME,
    end_time      TIME,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_schedule_group_date
    ON schedule (group_number, lesson_date);

CREATE INDEX IF NOT EXISTS idx_schedule_teacher_date
    ON schedule (teacher_id, lesson_date);

CREATE INDEX IF NOT EXISTS idx_schedule_room_date
    ON schedule (room_id, lesson_date);

-- =========================
-- ТАБЛИЦА ПОЛЬЗОВАТЕЛЕЙ БОТА
-- =========================
CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    username    VARCHAR(255),
    full_name   VARCHAR(255),
    role        VARCHAR(50) NOT NULL DEFAULT 'user', -- user, admin, developer
    group_id    INTEGER REFERENCES groups(id) ON DELETE SET NULL,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_telegram_id
    ON users (telegram_id);

-- =========================
-- ТАБЛИЦА НАСТРОЕК ПОЛЬЗОВАТЕЛЕЙ
-- (СООТВЕТСТВУЕТ handlers.py: time_format, notifications, default_view, theme)
-- =========================
CREATE TABLE IF NOT EXISTS user_settings (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    time_format   VARCHAR(10) NOT NULL DEFAULT '24',      -- '24' или '12'
    notifications BOOLEAN NOT NULL DEFAULT TRUE,          -- включены/выключены
    default_view  VARCHAR(10) NOT NULL DEFAULT 'day',     -- 'day' или 'week'
    theme         VARCHAR(10) NOT NULL DEFAULT 'light',   -- 'light' или 'dark' (пока заглушка)
    updated_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =========================
-- ТАБЛИЦА ЛОГОВ ДЕЙСТВИЙ ПОЛЬЗОВАТЕЛЕЙ
-- (СООТВЕТСТВУЕТ db.log_user_action / handlers.log_user_action)
-- =========================
CREATE TABLE IF NOT EXISTS user_actions (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    telegram_id BIGINT NOT NULL,
    action      VARCHAR(255) NOT NULL,
    details     TEXT,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_actions_user_id
    ON user_actions (user_id);

CREATE INDEX IF NOT EXISTS idx_user_actions_created_at
    ON user_actions (created_at);
"""

# =========================
# НАЧАЛЬНОЕ ЗАПОЛНЕНИЕ ВРЕМЕНИ ПАР
# =========================
INSERT_LESSON_TIMES_SQL = """
INSERT INTO lessons_time (lesson_number, start_time, end_time) VALUES
(1, '09:00', '10:30'),
(2, '10:40', '12:10'),
(3, '12:40', '14:10'),
(4, '14:20', '15:50'),
(5, '16:20', '17:50'),
(6, '18:00', '19:30'),
(7, '19:40', '21:10')
ON CONFLICT (lesson_number) DO NOTHING;
"""

# =========================
# ТЕСТОВЫЕ ДАННЫЕ
# =========================
INSERT_TEST_DATA_SQL = """
-- Корпуса
INSERT INTO buildings (building_name, address) VALUES
('Главный корпус', 'ул. Ленина, д. 1'),
('Второй корпус', 'ул. Пушкина, д. 10'),
('Третий корпус', 'пр. Победы, д. 25')
ON CONFLICT DO NOTHING;

-- Аудитории
INSERT INTO rooms (building_id, room_number, capacity, room_type) VALUES
(1, '101', 30, 'лекционная'),
(1, '102', 25, 'практическая'),
(1, '201', 50, 'лекционная'),
(2, '301', 20, 'лабораторная'),
(2, '302', 30, 'практическая'),
(3, '401', 40, 'лекционная')
ON CONFLICT DO NOTHING;

-- Группы
INSERT INTO groups (group_number, faculty_name, course, students_count) VALUES
('ИВТ-21', 'Факультет информационных технологий', 4, 25),
('ИВТ-22', 'Факультет информационных технологий', 4, 28),
('ЭК-31', 'Экономический факультет', 2, 30)
ON CONFLICT (group_number) DO NOTHING;

-- Преподаватели
INSERT INTO teachers (fio, department, position, email) VALUES
('Смирнов Алексей Петрович', 'Кафедра информатики', 'Доцент', 'smirnov@university.ru'),
('Козлова Мария Ивановна', 'Кафедра программирования', 'Профессор', 'kozlova@university.ru'),
('Новиков Дмитрий Сергеевич', 'Кафедра экономики', 'Старший преподаватель', 'novikov@university.ru')
ON CONFLICT DO NOTHING;

-- Предметы (опционально)
INSERT INTO subjects (name, short_name, subject_type, hours_total) VALUES
('Базы данных', 'БД', 'лекция', 72),
('Базы данных (практика)', 'БД (пр)', 'практика', 36),
('Программирование на Python', 'Python', 'лекция', 72),
('Веб-разработка', 'Web', 'лабораторная', 54)
ON CONFLICT DO NOTHING;
"""
