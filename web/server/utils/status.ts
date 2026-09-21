export type RecognitionStatus = 'confident' | 'uncertain' | 'not_found'

export interface StatusThresholds {
  /** top1 score below this: the wine is most likely not in the catalog */
  notFoundScore: number
  /** top1 - top2 at or above this: show the single card without alternatives */
  confidenceMargin: number
}

export function recognitionStatus(score1: number | null, margin: number | null, t: StatusThresholds): RecognitionStatus {
  if (score1 === null || score1 < t.notFoundScore) return 'not_found'
  if (margin === null || margin >= t.confidenceMargin) return 'confident'
  return 'uncertain'
}
