CREATE TABLE IF NOT EXISTS passages (
    id TEXT PRIMARY KEY,
    translation_id TEXT NOT NULL,
    psalm_number INTEGER NOT NULL CHECK (psalm_number > 0),
    start_verse INTEGER NOT NULL CHECK (start_verse > 0),
    end_verse INTEGER NOT NULL CHECK (end_verse > 0 AND end_verse >= start_verse),
    canonical_text TEXT NOT NULL CHECK (length(trim(canonical_text)) > 0)
);

CREATE TABLE IF NOT EXISTS learning_sessions (
    id TEXT PRIMARY KEY,
    passage_id TEXT NOT NULL,
    phase TEXT NOT NULL CHECK (phase IN (
        'unseen',
        'exposure',
        'practice',
        'ready_for_recitation',
        'learned',
        'needs_reinforcement'
    )),
    practice_level INTEGER NOT NULL CHECK (practice_level >= 0),
    successful_blank_recitations INTEGER NOT NULL CHECK (successful_blank_recitations >= 0),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY (passage_id) REFERENCES passages(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_learning_sessions_passage_id
    ON learning_sessions(passage_id);

CREATE TABLE IF NOT EXISTS recitation_attempts (
    id TEXT PRIMARY KEY,
    passage_id TEXT NOT NULL,
    attempted_at TEXT NOT NULL,
    transcript TEXT NOT NULL,
    normalized_transcript TEXT NOT NULL,
    result TEXT NOT NULL CHECK (result IN ('pass', 'retry', 'manual_review')),
    accuracy REAL NOT NULL CHECK (accuracy >= 0.0 AND accuracy <= 1.0),
    FOREIGN KEY (passage_id) REFERENCES passages(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_recitation_attempts_passage_id
    ON recitation_attempts(passage_id);

CREATE TABLE IF NOT EXISTS review_states (
    passage_id TEXT PRIMARY KEY,
    station INTEGER NOT NULL CHECK (station >= 0),
    learned_at TEXT,
    next_review_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('learning', 'active', 'reinforcement', 'mastered')),
    FOREIGN KEY (passage_id) REFERENCES passages(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_review_states_next_review_at
    ON review_states(next_review_at);
