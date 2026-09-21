import { createReadStream, existsSync } from 'node:fs'
import { basename, extname, resolve } from 'node:path'

const TYPES: Record<string, string> = {
  '.webp': 'image/webp', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
  '.gif': 'image/gif', '.bmp': 'image/bmp', '.tif': 'image/tiff', '.tiff': 'image/tiff',
}

// Catalog reference photos (data/catalog/images) for the wine card UI.
export default defineEventHandler((event) => {
  const file = basename(getRouterParam(event, 'file') || '')
  const path = resolve(appConfig.catalogImagesDir, file)
  const type = TYPES[extname(file).toLowerCase()]
  if (!type || !existsSync(path)) return sendApiError(event, new ApiError(404, 'image not found'))
  setResponseHeaders(event, { 'Content-Type': type, 'Cache-Control': 'public, max-age=86400' })
  return sendStream(event, createReadStream(path))
})
