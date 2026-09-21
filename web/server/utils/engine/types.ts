export interface Candidate {
  slug: string
  name: string
  winery: string | null
  /** cosine similarity in [-1, 1]; higher is better */
  score: number
}

export interface RecognitionEngine {
  readonly name: string
  readonly model: string | null
  /** Top candidates sorted by score desc (at most `k`). */
  recognize(image: UploadedImage, k: number): Promise<Candidate[]>
}
