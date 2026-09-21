import { createReadStream, existsSync } from 'node:fs'
import { resolve } from 'node:path'

// Catalog reference photo. build_catalog.py stores it as <slug><ext>, so no DB lookup is needed.
const TYPES: [string, string][] = [
  ['.webp', 'image/webp'], ['.jpg', 'image/jpeg'], ['.jpeg', 'image/jpeg'], ['.png', 'image/png'],
  ['.gif', 'image/gif'], ['.bmp', 'image/bmp'], ['.tif', 'image/tiff'], ['.tiff', 'image/tiff'],
]

export default defineEventHandler((event) => {
  const slug = getRouterParam(event, 'slug') || ''
  if (!/^[\w-]+$/.test(slug)) return sendApiError(event, new ApiError(400, 'bad slug'))
  for (const [ext, type] of TYPES) {
    const path = resolve(appConfig.catalogImagesDir, slug + ext)
    if (existsSync(path)) {
      setResponseHeaders(event, { 'Content-Type': type, 'Cache-Control': 'public, max-age=86400' })
      return sendStream(event, createReadStream(path))
    }
  }
  return sendApiError(event, new ApiError(404, 'image not found'))
})
