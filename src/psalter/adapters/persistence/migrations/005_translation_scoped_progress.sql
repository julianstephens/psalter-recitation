CREATE TABLE catalog_import_progress_new (
    installation_id INTEGER NOT NULL,
    translation_id TEXT NOT NULL CHECK (length(trim(translation_id)) > 0),
    psalm_number INTEGER NOT NULL CHECK (psalm_number BETWEEN 1 AND 150),
    status TEXT NOT NULL CHECK (status IN ('pending', 'imported', 'failed')),
    imported_at TEXT,
    error TEXT,
    PRIMARY KEY (installation_id, translation_id, psalm_number),
    FOREIGN KEY (installation_id) REFERENCES installation_settings(id) ON DELETE CASCADE
);

INSERT INTO catalog_import_progress_new(
    installation_id,
    translation_id,
    psalm_number,
    status,
    imported_at,
    error
)
SELECT
    cip.installation_id,
    COALESCE(
        (
            SELECT default_translation_id
            FROM installation_settings settings
            WHERE settings.id = cip.installation_id
        ),
        'unknown'
    ),
    cip.psalm_number,
    cip.status,
    cip.imported_at,
    cip.error
FROM catalog_import_progress cip;

DROP TABLE catalog_import_progress;
ALTER TABLE catalog_import_progress_new RENAME TO catalog_import_progress;

CREATE INDEX idx_catalog_import_progress_translation
    ON catalog_import_progress(installation_id, translation_id, status);
