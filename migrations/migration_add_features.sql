-- Миграция: добавление типов занятий и расширение функционала

-- 1. Добавляем типы занятий в subjects (если колонка уже есть, этот запрос выдаст ошибку - это нормально)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='subjects' AND column_name='lesson_type') THEN
        ALTER TABLE subjects ADD COLUMN lesson_type VARCHAR(20) DEFAULT 'lecture';
    END IF;
END $$;

-- 2. Обновляем существующие записи (если subject_type был 'Лекция', 'Практика' и т.д.)
UPDATE subjects SET lesson_type = 
    CASE 
        WHEN subject_type ILIKE '%лекц%' THEN 'lecture'
        WHEN subject_type ILIKE '%практ%' THEN 'practice'
        WHEN subject_type ILIKE '%лаб%' THEN 'lab'
        ELSE 'lecture'
    END
WHERE lesson_type IS NULL OR lesson_type = 'lecture';

-- 3. Добавляем constraint для lesson_type
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'subjects_lesson_type_check') THEN
        ALTER TABLE subjects ADD CONSTRAINT subjects_lesson_type_check 
        CHECK (lesson_type IN ('lecture', 'practice', 'lab'));
    END IF;
END $$;

-- 4. Создаем таблицу настроек пользователей (расширенная версия)
CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    notifications_enabled BOOLEAN DEFAULT true,
    notification_time TIME DEFAULT '18:00:00',
    show_teacher_contacts BOOLEAN DEFAULT true,
    compact_view BOOLEAN DEFAULT false,
    week_start_day VARCHAR(10) DEFAULT 'monday',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- 5. Создаем таблицу для статистики и логов
CREATE TABLE IF NOT EXISTS user_activity_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    action_type VARCHAR(50) NOT NULL,
    action_details TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_schedule_date ON schedule(lesson_date);
CREATE INDEX IF NOT EXISTS idx_schedule_group ON schedule(group_id);
CREATE INDEX IF NOT EXISTS idx_schedule_teacher ON schedule(teacher_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_log_user ON user_activity_log(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_log_date ON user_activity_log(created_at);

-- 7. Комментарии к таблицам
COMMENT ON TABLE subjects IS 'Учебные дисциплины с типами занятий';
COMMENT ON COLUMN subjects.lesson_type IS 'Тип занятия: lecture, practice, lab';
COMMENT ON TABLE user_preferences IS 'Персональные настройки пользователей';
COMMENT ON TABLE user_activity_log IS 'Лог действий пользователей для отчетности';