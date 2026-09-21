"""Postgres/pgvector access for the offline scripts."""
from __future__ import annotations

import numpy as np
import psycopg
from pgvector.psycopg import register_vector

from wine_ml.config import DATABASE_URL

WINE_COLUMNS = ("slug", "name", "category", "color", "region", "grapes",
                "description", "winery", "image_file")


def connect(url: str = DATABASE_URL) -> psycopg.Connection:
    conn = psycopg.connect(url)
    register_vector(conn)
    return conn


def upsert_wines(conn: psycopg.Connection, wines: list[dict]) -> None:
    cols = ", ".join(WINE_COLUMNS)
    params = ", ".join(f"%({c})s" for c in WINE_COLUMNS)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in WINE_COLUMNS[1:])
    with conn.cursor() as cur:
        cur.executemany(
            f"INSERT INTO wines ({cols}) VALUES ({params}) "
            f"ON CONFLICT (slug) DO UPDATE SET {updates}",
            [{c: w.get(c) for c in WINE_COLUMNS} for w in wines],
        )
    conn.commit()


def delete_wines_not_in(conn: psycopg.Connection, slugs: list[str]) -> int:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM wines WHERE NOT (slug = ANY(%s))", (slugs,))
        n = cur.rowcount
    conn.commit()
    return n


def indexed_slugs(conn: psycopg.Connection, model: str) -> set[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT slug FROM wine_embeddings WHERE model = %s", (model,))
        return {r[0] for r in cur.fetchall()}


def upsert_embeddings(conn: psycopg.Connection, model: str, slugs: list[str],
                      vectors: np.ndarray) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO wine_embeddings (slug, model, embedding) VALUES (%s, %s, %s) "
            "ON CONFLICT (slug, model) DO UPDATE SET embedding = EXCLUDED.embedding",
            [(s, model, v) for s, v in zip(slugs, vectors)],
        )
    conn.commit()


def fetch_embeddings(conn: psycopg.Connection, model: str) -> tuple[list[str], np.ndarray]:
    with conn.cursor() as cur:
        cur.execute("SELECT slug, embedding FROM wine_embeddings WHERE model = %s ORDER BY slug",
                    (model,))
        rows = cur.fetchall()
    if not rows:
        return [], np.zeros((0, 0), np.float32)
    return [r[0] for r in rows], np.stack([np.asarray(r[1], np.float32) for r in rows])
