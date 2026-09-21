import type { H3Event } from 'h3'

export interface SearchResponse {
  top1: Candidate | null
  top5: Candidate[]
  /** top1.score - top2.score: how clearly the winner stands out */
  margin: number | null
  confident: boolean
  engine: string
  model: string | null
  latency_ms: number
}

export async function runSearch(event: H3Event): Promise<SearchResponse> {
  const t0 = performance.now()
  const image = await readImage(event)
  const engine = getEngine()
  const top5 = await engine.recognize(image, 5)
  const margin = top5.length >= 2 ? Number((top5[0].score - top5[1].score).toFixed(4)) : null
  return {
    top1: top5[0] ?? null,
    top5,
    margin,
    confident: margin !== null && margin >= appConfig.confidenceMargin,
    engine: engine.name,
    model: engine.model,
    latency_ms: Math.round(performance.now() - t0),
  }
}
