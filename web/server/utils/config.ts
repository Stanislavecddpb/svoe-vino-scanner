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
  get mlTimeoutMs() {
    return Number(process.env.ML_TIMEOUT_MS ?? 8000)
  },
  get catalogImagesDir() {
    return process.env.CATALOG_IMAGES_DIR || '../data/catalog/images'
  },
  maxUploadBytes: 15 * 1024 * 1024,
}
