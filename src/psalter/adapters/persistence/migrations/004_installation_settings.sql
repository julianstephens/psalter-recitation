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
SELECT
    1,
    'helloao',
    inferred.translation_id,
    inferred.translation_id,
    CASE
        WHEN inferred.translation_id IS NOT NULL AND inferred.psalm_total = 150 THEN 'ready'
        WHEN inferred.translation_total = 0 THEN 'not_started'
        ELSE 'failed'
    END,
    CASE
        WHEN inferred.translation_id IS NOT NULL AND inferred.psalm_total = 150 THEN 'legacy-migration-v1'
        ELSE NULL
    END,
    CASE
        WHEN inferred.translation_id IS NOT NULL AND inferred.psalm_total = 150 THEN datetime('now')
        ELSE NULL
    END,
    datetime('now'),
    CASE
        WHEN inferred.translation_total > 1 THEN 'Multiple existing translations require init selection.'
        WHEN inferred.translation_total = 1 AND inferred.psalm_total < 150 THEN 'Existing Psalm catalog is incomplete.'
        ELSE NULL
    END
FROM (
    SELECT
        (
            SELECT translation_id
            FROM psalms
            GROUP BY translation_id
            HAVING COUNT(*) = 150
            LIMIT 1
        ) AS translation_id,
        (
            SELECT COUNT(*)
            FROM psalms p
            WHERE p.translation_id = (
                SELECT translation_id
                FROM psalms
                GROUP BY translation_id
                HAVING COUNT(*) = 150
                LIMIT 1
            )
        ) AS psalm_total,
        (
            SELECT COUNT(DISTINCT translation_id)
            FROM psalms
        ) AS translation_total
) inferred;
