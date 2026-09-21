// Shapes of the public API responses (see README "API").
export type RecognitionStatus = 'confident' | 'uncertain' | 'not_found'

export interface WineShort {
  slug: string
  name: string
  winery: string | null
  score: number
  image_url: string
}

export interface SearchResult {
  top1: WineShort | null
  top5: WineShort[]
  margin: number | null
  confident: boolean
  status: RecognitionStatus
  engine: string
  model: string | null
  latency_ms: number
}

export interface Wine {
  slug: string
  name: string
  category: string | null
  color: string | null
  region: string | null
  grapes: string | null
  description: string | null
  winery: string | null
  image_url: string
}
