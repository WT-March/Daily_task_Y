-- Database Schema for Pilotage de Survie
-- PostgreSQL

-- Categories enum
CREATE TYPE task_category AS ENUM ('Recovery', 'Core', 'Dynamic', 'Denial');
CREATE TYPE task_impact AS ENUM ('Personal', 'Family', 'Social');

-- Tasks table
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    category task_category NOT NULL,
    title VARCHAR(255) NOT NULL,
    justification TEXT DEFAULT '',
    impact task_impact,
    completed BOOLEAN DEFAULT FALSE,
    task_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Daily notes table
CREATE TABLE daily_notes (
    id SERIAL PRIMARY KEY,
    note_date DATE UNIQUE NOT NULL DEFAULT CURRENT_DATE,
    note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Configuration table
CREATE TABLE config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Default config values
INSERT INTO config (key, value) VALUES
    ('auto_start', 'false'),
    ('daily_note_enabled', 'true'),
    ('program_started', 'false'),
    ('program_start_date', 'null'),
    ('default_recovery_tasks', '["Sport", "Anime/Manga", "Sommeil (8h)"]'),
    ('default_core_tasks', '["Apprentissage Rust", "Prospection Cyber"]'),
    ('telegram_chat_id', 'null'),
    ('reminder_time', '"21:00"');

-- Index for faster date queries
CREATE INDEX idx_tasks_date ON tasks(task_date);
CREATE INDEX idx_tasks_completed ON tasks(completed);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for daily_notes
CREATE TRIGGER daily_notes_updated_at
    BEFORE UPDATE ON daily_notes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- View for today's tasks
CREATE VIEW today_tasks AS
SELECT * FROM tasks WHERE task_date = CURRENT_DATE ORDER BY category, id;

-- View for incomplete tasks today
CREATE VIEW today_incomplete AS
SELECT * FROM tasks WHERE task_date = CURRENT_DATE AND completed = FALSE;
