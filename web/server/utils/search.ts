import type { H3Event } from 'h3'

export interface CandidateOut extends Candidate {
  image_url: string
}

export interface SearchResponse {
  top1: CandidateOut | null
  top5: CandidateOut[]
  /** top1.score - top2.score: how clearly the winner stands out */
  margin: number | null
  /** margin >= CONFIDENCE_MARGIN */
  confident: boolean
  /** UI decision: single card / card + alternatives / not in catalog */
  status: RecognitionStatus
  engine: string
  model: string | null
  latency_ms: number
}

export const wineImageUrl = (slug: string) => `/v1/wines/${encodeURIComponent(slug)}/image`

export async function runSearch(event: H3Event): Promise<SearchResponse> {
  const t0 = performance.now()
  const image = await readImage(event)
  const engine = getEngine()
  const top5 = (await engine.recognize(image, 5)).map(c => ({ ...c, image_url: wineImageUrl(c.slug) }))
  const margin = top5.length >= 2 ? Number((top5[0].score - top5[1].score).toFixed(4)) : null
  return {
    top1: top5[0] ?? null,
    top5,
    margin,
    confident: margin !== null && margin >= appConfig.confidenceMargin,
    status: recognitionStatus(top5[0]?.score ?? null, margin, {
      notFoundScore: appConfig.notFoundScore,
      confidenceMargin: appConfig.confidenceMargin,
    }),
    engine: engine.name,
    model: engine.model,
    latency_ms: Math.round(performance.now() - t0),
  }
}
