// "Похожие вина": nearest catalog wines by the reference-image embedding (excluding the wine itself).
export default defineEventHandler(async (event) => {
  const slug = getRouterParam(event, 'slug') || ''
  const limit = Math.min(Math.max(Number(getQuery(event).limit) || 8, 1), 24)
  try {
    const { rows } = await getPool().query(
      `WITH me AS (SELECT embedding FROM wine_embeddings WHERE slug = $1 AND model = $2)
       SELECT w.slug, w.name, w.winery, 1 - (e.embedding <=> me.embedding) AS score
         FROM wine_embeddings e JOIN wines w USING (slug), me
        WHERE e.model = $2 AND e.slug <> $1
        ORDER BY e.embedding <=> me.embedding
        LIMIT $3`,
      [slug, appConfig.modelName, limit],
    )
    return rows.map(r => ({
      slug: r.slug, name: r.name, winery: r.winery,
      score: Number(Number(r.score).toFixed(4)), image_url: wineImageUrl(r.slug),
    }))
  }
  catch (e) {
    return sendApiError(event, new ApiError(503, `database error: ${(e as Error).message}`))
  }
})
