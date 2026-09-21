// Liveness + dependency status. Always 200; status "ok" if the active engine can serve requests.
export default defineEventHandler(async () => {
  const engine = getEngine()

  let db: { ok: boolean, wines?: number, indexed?: number, error?: string }
  try {
    const { rows } = await getPool().query(
      `SELECT (SELECT count(*) FROM wines)::int AS wines,
              (SELECT count(*) FROM wine_embeddings WHERE model = $1)::int AS indexed`,
      [appConfig.modelName],
    )
    db = { ok: true, ...rows[0] }
  }
  catch (e) {
    db = { ok: false, error: (e as Error).message }
  }

  let ml: { ok: boolean, [k: string]: unknown }
  try {
    const res = await fetch(`${appConfig.mlUrl}/health`, { signal: AbortSignal.timeout(2000) })
    ml = { ok: res.ok, ...(res.ok ? await res.json() : {}) }
  }
  catch (e) {
    ml = { ok: false, error: (e as Error).message }
  }

  const ready = engine.name === 'stub' || (db.ok && (db.indexed ?? 0) > 0 && ml.ok)
  return { status: ready ? 'ok' : 'degraded', engine: engine.name, model: engine.model, db, ml }
})
