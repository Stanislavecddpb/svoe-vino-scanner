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
-- view: 'full' (whole bottle) or a label-band crop ('label_mid', 'label_low');
-- a wine's search score is the max over its views.
-- ~6k rows: exact scan is fast enough, no ANN index needed.
CREATE TABLE IF NOT EXISTS wine_embeddings (
  slug      text NOT NULL REFERENCES wines(slug) ON DELETE CASCADE,
  model     text NOT NULL,
  view      text NOT NULL DEFAULT 'full',
  embedding vector NOT NULL,
  PRIMARY KEY (slug, model, view)
);
