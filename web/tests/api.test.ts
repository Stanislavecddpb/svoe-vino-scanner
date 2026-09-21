import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { $fetch, fetch, setup } from '@nuxt/test-utils/e2e'

// 1x1 PNG
const PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
  'base64',
)

function form(data: Buffer | null, field = 'image') {
  const fd = new FormData()
  if (data) fd.append(field, new Blob([data], { type: 'image/png' }), 'x.png')
  return fd
}

describe('api (stub engine)', async () => {
  await setup({
    rootDir: fileURLToPath(new URL('..', import.meta.url)),
    server: true,
    browser: false,
    env: { ENGINE: 'stub', DATABASE_URL: 'postgresql://invalid:invalid@127.0.0.1:1/none' },
  })

  it('predict returns flat {slug}', async () => {
    const res = await fetch('/v1/eval/predict', { method: 'POST', body: form(PNG) })
    expect(res.status).toBe(200)
    const body = await res.json()
    expect(Object.keys(body)).toEqual(['slug'])
    expect(typeof body.slug).toBe('string')
    expect(body.slug.length).toBeGreaterThan(0)
  })

  it('predict is deterministic for the same image', async () => {
    const a = await $fetch('/v1/eval/predict', { method: 'POST', body: form(PNG) })
    const b = await $fetch('/v1/eval/predict', { method: 'POST', body: form(PNG) })
    expect(a).toEqual(b)
  })

  it('predict without image -> 400 {error}', async () => {
    const res = await fetch('/v1/eval/predict', { method: 'POST', body: form(null) })
    expect(res.status).toBe(400)
    expect(typeof (await res.json()).error).toBe('string')
  })

  it('predict with non-image bytes -> 400', async () => {
    const res = await fetch('/v1/eval/predict', { method: 'POST', body: form(Buffer.from('hello')) })
    expect(res.status).toBe(400)
  })

  it('search returns top5 sorted with margin', async () => {
    const body: any = await $fetch('/v1/search', { method: 'POST', body: form(PNG) })
    expect(body.top5).toHaveLength(5)
    const scores = body.top5.map((c: any) => c.score)
    expect([...scores].sort((a, b) => b - a)).toEqual(scores)
    expect(body.top1.slug).toBe(body.top5[0].slug)
    expect(body.margin).toBeCloseTo(scores[0] - scores[1], 6)
    expect(typeof body.confident).toBe('boolean')
    expect(body.engine).toBe('stub')
    expect(typeof body.latency_ms).toBe('number')
  })

  it('health reports engine', async () => {
    const body: any = await $fetch('/health')
    expect(body.engine).toBe('stub')
    expect(body.status).toBe('ok')
  })
})
