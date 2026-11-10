
-- NEURALIX BRAIN KNOWLEDGE TRAINING V1

ALTER TABLE knowledge_documents
    ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT 'general',
    ADD COLUMN IF NOT EXISTS source TEXT,
    ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    document_id BIGINT NOT NULL
        REFERENCES knowledge_documents(id) ON DELETE CASCADE,

    user_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content TEXT NOT NULL,
    embedding VECTOR(384),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_user
    ON knowledge_chunks(user_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_document
    ON knowledge_chunks(document_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_category
    ON knowledge_documents(category);
