-- "Аналоги из других виноделен": precomputed by ml/scripts/build_analogs.py. Idempotent.
CREATE TABLE IF NOT EXISTS wine_analogs (
  slug        text NOT NULL REFERENCES wines(slug) ON DELETE CASCADE,
  rank        int  NOT NULL,
  analog_slug text NOT NULL REFERENCES wines(slug) ON DELETE CASCADE,
  score       real NOT NULL,
  reason      text NOT NULL,
  PRIMARY KEY (slug, rank)
);
