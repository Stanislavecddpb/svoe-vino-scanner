// Plain env vars (read at request time) so the same build runs in any environment.
export type EngineName = 'vector' | 'stub'

export const appConfig = {
  get engine(): EngineName {
    return process.env.ENGINE === 'stub' ? 'stub' : 'vector'
  },
  get mlUrl() {
    return (process.env.ML_URL || 'http://127.0.0.1:8001').replace(/\/$/, '')
  },
  get databaseUrl() {
    return process.env.DATABASE_URL || 'postgresql://wine:wine@127.0.0.1:5432/wine'
  },
  get modelName() {
    return process.env.MODEL_NAME || 'google/siglip2-so400m-patch14-384'
  },
  get confidenceMargin() {
    return Number(process.env.CONFIDENCE_MARGIN ?? 0.03)
  },
  /** search score = (1 - w) * whole bottle + w * best label crop */
  get labelWeight() {
    return Number(process.env.LABEL_WEIGHT ?? 0.5)
  },
  /** re-rank the visual Top-K by label text (ml /analyze + /rerank) */
  get ocrEnabled() {
    return !['0', 'false', 'no'].includes((process.env.OCR_ENABLED ?? '1').toLowerCase())
  },
  get rerankK() {
    return Number(process.env.RERANK_K ?? 10)
  },
  get notFoundScore() {
    return Number(process.env.NOT_FOUND_SCORE ?? 0.75)
  },
  get mlTimeoutMs() {
    return Number(process.env.ML_TIMEOUT_MS ?? 8000)
  },
  get catalogImagesDir() {
    return process.env.CATALOG_IMAGES_DIR || '../data/catalog/images'
  },
  maxUploadBytes: 15 * 1024 * 1024,
}
