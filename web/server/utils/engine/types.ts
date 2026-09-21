export interface Candidate {
  slug: string
  name: string
  winery: string | null
  /** final ranking score; higher is better (= visual when there is no text re-ranking) */
  score: number
  /** visual similarity to the catalog reference (blend of bottle and label-crop cosines) */
  visual?: number
  /** share of the wine's name/winery confirmed by the label text (0..1), when OCR re-ranking ran */
  text?: number
}

export interface RecognitionEngine {
  readonly name: string
  readonly model: string | null
  /** Top candidates sorted by score desc (at most `k`). */
  recognize(image: UploadedImage, k: number): Promise<Candidate[]>
}
