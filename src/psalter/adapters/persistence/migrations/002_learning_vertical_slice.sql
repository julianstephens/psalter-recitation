CREATE TEMP TABLE migration_guard (
    value INTEGER NOT NULL CHECK (value = 1)
);

INSERT INTO migration_guard(value)
SELECT CASE
    WHEN EXISTS (
        SELECT 1
        FROM recitation_attempts ra
        WHERE NOT EXISTS (
            SELECT 1
            FROM learning_sessions ls
            WHERE ls.passage_id = ra.passage_id
        )
    ) THEN 0
    ELSE 1
END;

DROP TABLE migration_guard;

CREATE TABLE learning_sessions_new (
    id TEXT PRIMARY KEY,
    passage_id TEXT NOT NULL UNIQUE,
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
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY (passage_id) REFERENCES passages(id) ON DELETE CASCADE
);

INSERT INTO learning_sessions_new(
    id, passage_id, phase, practice_level, successful_blank_recitations, started_at, updated_at, completed_at
)
SELECT
    ls.id,
    ls.passage_id,
    ls.phase,
    ls.practice_level,
    ls.successful_blank_recitations,
    ls.started_at,
    COALESCE(ls.completed_at, ls.started_at),
    ls.completed_at
FROM learning_sessions ls
WHERE ls.id = (
    SELECT id
    FROM learning_sessions
    WHERE passage_id = ls.passage_id
    ORDER BY started_at DESC
    LIMIT 1
);

DROP TABLE learning_sessions;
ALTER TABLE learning_sessions_new RENAME TO learning_sessions;
CREATE INDEX IF NOT EXISTS idx_learning_sessions_passage_id
    ON learning_sessions(passage_id);

CREATE TABLE recitation_attempts_new (
    id TEXT PRIMARY KEY,
    passage_id TEXT NOT NULL,
    learning_session_id TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('typed', 'speech_transcript')),
    submitted_text TEXT NOT NULL,
    normalized_text TEXT NOT NULL,
    attempted_at TEXT NOT NULL,
    result TEXT NOT NULL CHECK (result IN ('pass', 'retry', 'manual_review')),
    weighted_accuracy REAL NOT NULL CHECK (weighted_accuracy >= 0.0 AND weighted_accuracy <= 1.0),
    assessment_policy_version TEXT NOT NULL,
    omission_count INTEGER NOT NULL CHECK (omission_count >= 0),
    substitution_count INTEGER NOT NULL CHECK (substitution_count >= 0),
    insertion_count INTEGER NOT NULL CHECK (insertion_count >= 0),
    longest_omitted_span INTEGER NOT NULL CHECK (longest_omitted_span >= 0),
    alignment_diagnostics TEXT NOT NULL CHECK (json_valid(alignment_diagnostics)),
    FOREIGN KEY (passage_id) REFERENCES passages(id) ON DELETE CASCADE,
    FOREIGN KEY (learning_session_id) REFERENCES learning_sessions(id) ON DELETE CASCADE
);

INSERT INTO recitation_attempts_new(
    id, passage_id, learning_session_id, source, submitted_text, normalized_text, attempted_at, result,
    weighted_accuracy, assessment_policy_version, omission_count, substitution_count, insertion_count,
    longest_omitted_span, alignment_diagnostics
)
SELECT
    ra.id,
    ra.passage_id,
    (
        SELECT ls.id
        FROM learning_sessions ls
        WHERE ls.passage_id = ra.passage_id
        LIMIT 1
    ) AS learning_session_id,
    'speech_transcript',
    ra.transcript,
    ra.normalized_transcript,
    ra.attempted_at,
    ra.result,
    ra.accuracy,
    'legacy-v0',
    0,
    0,
    0,
    0,
    '[]'
FROM recitation_attempts ra;

DROP TABLE recitation_attempts;
ALTER TABLE recitation_attempts_new RENAME TO recitation_attempts;
CREATE INDEX IF NOT EXISTS idx_recitation_attempts_passage_id
    ON recitation_attempts(passage_id);
CREATE INDEX IF NOT EXISTS idx_recitation_attempts_learning_session_id
    ON recitation_attempts(learning_session_id);
