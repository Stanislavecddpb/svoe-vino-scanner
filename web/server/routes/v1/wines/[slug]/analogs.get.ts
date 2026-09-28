// "Аналоги из других виноделен": same style from other producers, with a short reason (ml/scripts/build_analogs.py).
export default defineEventHandler(async (event) => {
  const slug = getRouterParam(event, 'slug') || ''
  const limit = Math.min(Math.max(Number(getQuery(event).limit) || 6, 1), 12)
  try {
    const { rows } = await getPool().query(
      `SELECT w.slug, w.name, w.winery, w.category, a.score, a.reason
         FROM wine_analogs a JOIN wines w ON w.slug = a.analog_slug
        WHERE a.slug = $1
        ORDER BY a.rank
        LIMIT $2`,
      [slug, limit],
    )
    return rows.map(r => ({
      slug: r.slug, name: r.name, winery: r.winery, category: r.category,
      score: Number(Number(r.score).toFixed(4)), reason: r.reason, image_url: wineImageUrl(r.slug),
    }))
  }
  catch (e) {
    return sendApiError(event, new ApiError(503, `database error: ${(e as Error).message}`))
  }
})
