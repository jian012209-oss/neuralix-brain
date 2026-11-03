CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS brain_memories (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id TEXT NOT NULL,
    memory TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_brain_memories_user
    ON brain_memories(user_id);

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id TEXT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    embedding vector(384)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_user
    ON knowledge_documents(user_id);

CREATE TABLE IF NOT EXISTS brain_feedback (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id TEXT NOT NULL,
    message_id TEXT,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    feedback TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_feedback_user
    ON brain_feedback(user_id);

CREATE TABLE IF NOT EXISTS brain_conversations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_conversations_user
    ON brain_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_id
    ON brain_conversations(conversation_id);

-- Safe to re-run: ensures the expected embedding column exists.
ALTER TABLE knowledge_documents
    ADD COLUMN IF NOT EXISTS embedding vector(384);
