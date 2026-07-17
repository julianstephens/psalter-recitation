CREATE TEMP TABLE migration_guard (
    value INTEGER NOT NULL CHECK (value = 1)
);

INSERT INTO migration_guard(value)
SELECT CASE
    WHEN EXISTS (
        SELECT 1
        FROM passages first
        JOIN passages second
          ON first.translation_id = second.translation_id
         AND first.psalm_number = second.psalm_number
         AND first.id < second.id
         AND first.start_verse <= second.end_verse
         AND second.start_verse <= first.end_verse
    ) THEN 0
    ELSE 1
END;

DROP TABLE migration_guard;

CREATE TABLE psalms (
    id TEXT PRIMARY KEY,
    translation_id TEXT NOT NULL,
    psalm_number INTEGER NOT NULL CHECK (psalm_number > 0),
    canonical_text TEXT NOT NULL CHECK (length(trim(canonical_text)) > 0),
    verse_count INTEGER NOT NULL CHECK (verse_count > 0),
    completeness TEXT NOT NULL CHECK (completeness IN ('partial', 'complete')),
    UNIQUE(translation_id, psalm_number)
);

CREATE TABLE psalm_verses (
    psalm_id TEXT NOT NULL,
    verse_number INTEGER NOT NULL CHECK (verse_number > 0),
    canonical_text TEXT NOT NULL CHECK (length(trim(canonical_text)) > 0),
    PRIMARY KEY (psalm_id, verse_number),
    FOREIGN KEY (psalm_id) REFERENCES psalms(id) ON DELETE CASCADE
);

INSERT INTO psalms(id, translation_id, psalm_number, canonical_text, verse_count, completeness)
SELECT
    translation_id || '-psalm-' || psalm_number,
    translation_id,
    psalm_number,
    (
        SELECT group_concat(item.canonical_text, char(10))
        FROM (
            SELECT canonical_text
            FROM passages ordered
            WHERE ordered.translation_id = grouped.translation_id
              AND ordered.psalm_number = grouped.psalm_number
            ORDER BY ordered.start_verse ASC, ordered.end_verse ASC, ordered.id ASC
        ) item
    ) AS canonical_text,
    SUM(end_verse - start_verse + 1) AS verse_count,
    CASE
        WHEN COUNT(*) = MAX(end_verse)
         AND MIN(start_verse) = 1
         AND SUM(CASE WHEN start_verse = end_verse THEN 1 ELSE 0 END) = COUNT(*)
        THEN 'complete'
        ELSE 'partial'
    END AS completeness
FROM passages grouped
GROUP BY translation_id, psalm_number;

INSERT INTO psalm_verses(psalm_id, verse_number, canonical_text)
SELECT
    translation_id || '-psalm-' || psalm_number,
    start_verse,
    canonical_text
FROM passages
WHERE start_verse = end_verse
  AND EXISTS (
      SELECT 1
      FROM psalms
      WHERE id = passages.translation_id || '-psalm-' || passages.psalm_number
        AND completeness = 'complete'
  );

CREATE TABLE passages_new (
    id TEXT PRIMARY KEY,
    psalm_id TEXT NOT NULL,
    translation_id TEXT NOT NULL,
    psalm_number INTEGER NOT NULL CHECK (psalm_number > 0),
    start_verse INTEGER NOT NULL CHECK (start_verse > 0),
    end_verse INTEGER NOT NULL CHECK (end_verse > 0 AND end_verse >= start_verse),
    canonical_text TEXT NOT NULL CHECK (length(trim(canonical_text)) > 0),
    sequence_number INTEGER NOT NULL CHECK (sequence_number > 0),
    kind TEXT NOT NULL CHECK (kind IN ('section', 'consolidation')),
    segmentation_policy_version TEXT,
    UNIQUE(psalm_id, sequence_number),
    FOREIGN KEY (psalm_id) REFERENCES psalms(id) ON DELETE CASCADE
);

INSERT INTO passages_new(
    id, psalm_id, translation_id, psalm_number, start_verse, end_verse,
    canonical_text, sequence_number, kind, segmentation_policy_version
)
SELECT
    id,
    translation_id || '-psalm-' || psalm_number,
    translation_id,
    psalm_number,
    start_verse,
    end_verse,
    canonical_text,
    ROW_NUMBER() OVER (
        PARTITION BY translation_id, psalm_number
        ORDER BY start_verse ASC, end_verse ASC, id ASC
    ) AS sequence_number,
    'section',
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM psalms
            WHERE id = passages.translation_id || '-psalm-' || passages.psalm_number
              AND completeness = 'complete'
        ) THEN 'legacy-migration-v1'
        ELSE NULL
    END
FROM passages;

INSERT INTO passages_new(
    id, psalm_id, translation_id, psalm_number, start_verse, end_verse,
    canonical_text, sequence_number, kind, segmentation_policy_version
)
SELECT
    psalms.id || '-consolidation',
    psalms.id,
    psalms.translation_id,
    psalms.psalm_number,
    1,
    psalms.verse_count,
    psalms.canonical_text,
    (
        SELECT COALESCE(MAX(sequence_number), 0) + 1
        FROM passages_new existing
        WHERE existing.psalm_id = psalms.id
    ),
    'consolidation',
    'legacy-migration-v1'
FROM psalms
WHERE completeness = 'complete';

DROP TABLE passages;
ALTER TABLE passages_new RENAME TO passages;
CREATE INDEX idx_passages_psalm_id ON passages(psalm_id);
CREATE INDEX idx_passages_psalm_kind ON passages(psalm_id, kind);

CREATE TABLE psalm_learning_plans (
    psalm_id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('not_started', 'learning_sections', 'consolidating', 'learned')),
    active_passage_id TEXT,
    started_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    version INTEGER NOT NULL DEFAULT 0 CHECK (version >= 0),
    FOREIGN KEY (psalm_id) REFERENCES psalms(id) ON DELETE CASCADE,
    FOREIGN KEY (active_passage_id) REFERENCES passages(id) ON DELETE SET NULL
);

CREATE TABLE review_states_new (
    passage_id TEXT PRIMARY KEY,
    station INTEGER NOT NULL CHECK (station >= 0),
    learned_at TEXT,
    next_review_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('learning', 'active', 'reinforcement', 'mastered')),
    FOREIGN KEY (passage_id) REFERENCES passages(id) ON DELETE CASCADE
);

INSERT INTO review_states_new(passage_id, station, learned_at, next_review_at, status)
SELECT passage_id, station, learned_at, next_review_at, status
FROM review_states;

DROP TABLE review_states;
ALTER TABLE review_states_new RENAME TO review_states;
CREATE INDEX idx_review_states_next_review_at ON review_states(next_review_at);

CREATE INDEX idx_psalms_translation_psalm_number
    ON psalms(translation_id, psalm_number);
