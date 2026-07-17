CREATE TABLE installation_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    scripture_provider TEXT NOT NULL CHECK (length(trim(scripture_provider)) > 0),
    default_translation_id TEXT,
    default_translation_name TEXT,
    catalog_status TEXT NOT NULL CHECK (catalog_status IN ('not_started', 'installing', 'ready', 'failed')),
    catalog_version TEXT,
    initialized_at TEXT,
    updated_at TEXT NOT NULL,
    last_error TEXT,
    CHECK (
        catalog_status != 'ready'
        OR (
            default_translation_id IS NOT NULL
            AND default_translation_name IS NOT NULL
            AND initialized_at IS NOT NULL
        )
    )
);

CREATE TABLE catalog_import_progress (
    installation_id INTEGER NOT NULL,
    psalm_number INTEGER NOT NULL CHECK (psalm_number BETWEEN 1 AND 150),
    status TEXT NOT NULL CHECK (status IN ('pending', 'imported', 'failed')),
    imported_at TEXT,
    error TEXT,
    PRIMARY KEY (installation_id, psalm_number),
    FOREIGN KEY (installation_id) REFERENCES installation_settings(id) ON DELETE CASCADE
);

INSERT INTO installation_settings(
    id,
    scripture_provider,
    default_translation_id,
    default_translation_name,
    catalog_status,
    catalog_version,
    initialized_at,
    updated_at,
    last_error
)
WITH translation_stats AS (
    SELECT
        translation_id,
        COUNT(*) AS psalm_total,
        COUNT(DISTINCT psalm_number) AS distinct_psalm_numbers,
        MIN(psalm_number) AS min_psalm_number,
        MAX(psalm_number) AS max_psalm_number
    FROM psalms
    GROUP BY translation_id
),
structurally_valid_translations AS (
    SELECT ts.translation_id
    FROM translation_stats ts
    WHERE
        ts.psalm_total = 150
        AND ts.distinct_psalm_numbers = 150
        AND ts.min_psalm_number = 1
        AND ts.max_psalm_number = 150
        AND NOT EXISTS (
            SELECT 1
            FROM psalms p
            WHERE p.translation_id = ts.translation_id
              AND (
                  p.completeness != 'complete'
                  OR (SELECT COUNT(*) FROM psalm_verses pv WHERE pv.psalm_id = p.id) != p.verse_count
                  OR (SELECT MIN(verse_number) FROM psalm_verses pv WHERE pv.psalm_id = p.id) != 1
                  OR (SELECT MAX(verse_number) FROM psalm_verses pv WHERE pv.psalm_id = p.id) != p.verse_count
                  OR (
                      SELECT COUNT(*)
                      FROM passages c
                      WHERE c.psalm_id = p.id
                        AND c.kind = 'consolidation'
                  ) != 1
                  OR (
                      SELECT COUNT(*)
                      FROM passages s
                      WHERE s.psalm_id = p.id
                        AND s.kind = 'section'
                  ) < 1
                  OR EXISTS (
                      SELECT 1
                      FROM passages c
                      WHERE c.psalm_id = p.id
                        AND c.kind = 'consolidation'
                        AND (
                            c.start_verse != 1
                            OR c.end_verse != p.verse_count
                            OR c.segmentation_policy_version IS NULL
                        )
                  )
                  OR (
                      SELECT MIN(s.start_verse)
                      FROM passages s
                      WHERE s.psalm_id = p.id
                        AND s.kind = 'section'
                  ) != 1
                  OR (
                      SELECT MAX(s.end_verse)
                      FROM passages s
                      WHERE s.psalm_id = p.id
                        AND s.kind = 'section'
                  ) != p.verse_count
                  OR (
                      SELECT SUM(s.end_verse - s.start_verse + 1)
                      FROM passages s
                      WHERE s.psalm_id = p.id
                        AND s.kind = 'section'
                  ) != p.verse_count
                  OR EXISTS (
                      SELECT 1
                      FROM passages s
                      WHERE s.psalm_id = p.id
                        AND s.kind = 'section'
                        AND s.segmentation_policy_version IS NULL
                  )
                  OR EXISTS (
                      SELECT 1
                      FROM passages s1
                      JOIN passages s2
                        ON s1.psalm_id = s2.psalm_id
                       AND s1.id < s2.id
                       AND s1.kind = 'section'
                       AND s2.kind = 'section'
                       AND s1.start_verse <= s2.end_verse
                       AND s2.start_verse <= s1.end_verse
                      WHERE s1.psalm_id = p.id
                  )
              )
        )
),
inferred AS (
    SELECT
        (SELECT COUNT(DISTINCT translation_id) FROM psalms) AS translation_total,
        (SELECT COUNT(*) FROM structurally_valid_translations) AS valid_translation_total,
        (SELECT translation_id FROM structurally_valid_translations LIMIT 1) AS ready_translation_id
)
SELECT
    1,
    'helloao',
    CASE
        WHEN inferred.valid_translation_total = 1 THEN inferred.ready_translation_id
        ELSE NULL
    END,
    CASE
        WHEN inferred.valid_translation_total = 1 THEN inferred.ready_translation_id
        ELSE NULL
    END,
    CASE
        WHEN inferred.translation_total = 0 THEN 'not_started'
        WHEN inferred.valid_translation_total = 1 THEN 'ready'
        ELSE 'failed'
    END,
    CASE
        WHEN inferred.valid_translation_total = 1 THEN 'legacy-migration-v1'
        ELSE NULL
    END,
    CASE
        WHEN inferred.valid_translation_total = 1 THEN datetime('now')
        ELSE NULL
    END,
    datetime('now'),
    CASE
        WHEN inferred.translation_total > 1 THEN 'Multiple existing translations require init selection.'
        WHEN inferred.translation_total = 1 AND inferred.valid_translation_total = 0 THEN 'Existing Psalm catalog is incomplete or invalid.'
        ELSE NULL
    END
FROM inferred;
