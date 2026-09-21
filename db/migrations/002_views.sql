-- Adds per-view embeddings (whole bottle + label crops) to databases created before 2026-09-21.
-- Idempotent. Run: docker compose exec -T db psql -U wine < db/migrations/002_views.sql
ALTER TABLE wine_embeddings ADD COLUMN IF NOT EXISTS view text NOT NULL DEFAULT 'full';
ALTER TABLE wine_embeddings DROP CONSTRAINT IF EXISTS wine_embeddings_pkey;
ALTER TABLE wine_embeddings ADD PRIMARY KEY (slug, model, view);
