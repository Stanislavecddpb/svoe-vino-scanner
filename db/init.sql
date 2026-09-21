CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS wines (
  slug        text PRIMARY KEY,
  name        text NOT NULL,
  category    text,
  color       text,
  region      text,
  grapes      text,
  description text,
  winery      text,
  image_file  text NOT NULL
);

-- Dimension is not fixed so the model can be swapped without a migration.
-- ~2k rows: exact scan is fast enough, no ANN index needed.
CREATE TABLE IF NOT EXISTS wine_embeddings (
  slug      text NOT NULL REFERENCES wines(slug) ON DELETE CASCADE,
  model     text NOT NULL,
  embedding vector NOT NULL,
  PRIMARY KEY (slug, model)
);
