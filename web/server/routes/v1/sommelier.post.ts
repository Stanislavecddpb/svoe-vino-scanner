// "Цифровой сомелье": {food, sweetness, body} -> up to 6 catalog wines with a reason.
const FOODS = ['meat', 'poultry', 'fish', 'cheese', 'veggies', 'dessert', 'aperitif']
const SWEETNESS = ['dry', 'medium', 'sweet', 'sparkling']
const BODIES = ['light', 'rich']

let cache: { at: number, wines: CatalogWine[] } | null = null

async function catalog(): Promise<CatalogWine[]> {
  if (cache && Date.now() - cache.at < 5 * 60_000) return cache.wines
  const { rows } = await getPool().query(
    'SELECT slug, name, winery, category, grapes, region, description FROM wines')
  cache = { at: Date.now(), wines: rows }
  return rows
}

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event).catch(() => null) as Partial<SommelierAnswers> | null
    if (!body || !FOODS.includes(body.food!) || !SWEETNESS.includes(body.sweetness!) || !BODIES.includes(body.body!)) {
      throw new ApiError(400, `expected {food: ${FOODS.join('|')}, sweetness: ${SWEETNESS.join('|')}, body: ${BODIES.join('|')}}`)
    }
    let wines: CatalogWine[]
    try {
      wines = await catalog()
    }
    catch (e) {
      throw new ApiError(503, `database error: ${(e as Error).message}`)
    }
    return recommend(wines, body as SommelierAnswers).map(r => ({
      slug: r.wine.slug, name: r.wine.name, winery: r.wine.winery, score: r.score,
      reason: r.reason, image_url: wineImageUrl(r.wine.slug),
    }))
  }
  catch (e) {
    return sendApiError(event, e)
  }
})
