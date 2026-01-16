-- ================================
-- USERS TABLE
-- Stores user-declared identity
-- ================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    profession TEXT,
    public_email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================
-- CONSENT TABLE
-- Legal consent record
-- ================================
CREATE TABLE IF NOT EXISTS consent (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    consent_given BOOLEAN NOT NULL,
    scope TEXT DEFAULT 'public_web_only',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ================================
-- SOURCES TABLE
-- Tracks public URLs used
-- ================================
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    source_url TEXT NOT NULL,
    source_type TEXT, -- website, directory, article
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ================================
-- PROFILE FIELDS TABLE
-- Extracted public info
-- ================================
CREATE TABLE IF NOT EXISTS profile_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    field_name TEXT NOT NULL,
    field_value TEXT NOT NULL,
    source_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ================================
-- ABOUT PROFILE TABLE
-- Final generated profile snapshot
-- ================================
CREATE TABLE IF NOT EXISTS about_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    about_json TEXT NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ================================
-- AUDIT LOG TABLE
-- Compliance & debugging
-- ================================
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    detail TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
