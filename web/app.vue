<script setup lang="ts">
// Minimal demo page: photo -> /v1/search -> card of the top-1 wine + top-5 with scores.
// The real card UI (portal styling) is built separately on top of the same API.
interface Candidate { slug: string, name: string, winery: string | null, score: number }
interface SearchResult { top1: Candidate | null, top5: Candidate[], margin: number | null, confident: boolean, latency_ms: number, engine: string }
interface Wine { slug: string, name: string, winery: string | null, region: string | null, category: string | null, color: string | null, grapes: string | null, description: string | null, image_url: string }

const preview = ref<string | null>(null)
const result = ref<SearchResult | null>(null)
const wine = ref<Wine | null>(null)
const error = ref<string | null>(null)
const loading = ref(false)

async function onFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  preview.value = URL.createObjectURL(file)
  result.value = null
  wine.value = null
  error.value = null
  loading.value = true
  try {
    const fd = new FormData()
    fd.append('image', file)
    result.value = await $fetch<SearchResult>('/v1/search', { method: 'POST', body: fd })
    if (result.value.top1) await openWine(result.value.top1.slug)
  }
  catch (err: any) {
    error.value = err?.data?.error || err?.message || 'Ошибка'
  }
  finally {
    loading.value = false
  }
}

async function openWine(slug: string) {
  try {
    wine.value = await $fetch<Wine>(`/v1/wines/${encodeURIComponent(slug)}`)
  }
  catch {
    wine.value = null
  }
}
</script>

<template>
  <main class="page">
    <h1>Сканер вина</h1>
    <label class="upload">
      <input type="file" accept="image/*" capture="environment" @change="onFile">
      <span>{{ loading ? 'Ищем…' : 'Сфотографировать этикетку' }}</span>
    </label>

    <img v-if="preview" :src="preview" class="preview" alt="Ваше фото">
    <p v-if="error" class="error">{{ error }}</p>

    <section v-if="wine" class="card">
      <img :src="wine.image_url" :alt="wine.name">
      <div>
        <h2>{{ wine.name }}</h2>
        <p class="muted">{{ wine.winery }} · {{ wine.region }}</p>
        <p class="muted">{{ [wine.category, wine.color, wine.grapes].filter(Boolean).join(' · ') }}</p>
        <p>{{ wine.description }}</p>
      </div>
    </section>

    <section v-if="result" class="debug">
      <p>
        {{ result.latency_ms }} мс · отрыв {{ result.margin }} ·
        <b :class="result.confident ? 'ok' : 'warn'">{{ result.confident ? 'уверенно' : 'неуверенно' }}</b>
        · {{ result.engine }}
      </p>
      <ol>
        <li v-for="c in result.top5" :key="c.slug">
          <a href="#" @click.prevent="openWine(c.slug)">{{ c.name }}</a>
          <span class="muted"> — {{ c.winery }}</span>
          <code>{{ c.score.toFixed(3) }}</code>
        </li>
      </ol>
    </section>
  </main>
</template>

<style>
:root { --wine: #7b1e3a; --bg: #faf7f5; --text: #1f1a1c; --muted: #6f6468; --card: #fff }
@media (prefers-color-scheme: dark) { :root { --bg: #161214; --text: #f1eaec; --muted: #a99ca1; --card: #221c1f } }
body { margin: 0; background: var(--bg); color: var(--text); font-family: system-ui, sans-serif }
.page { max-width: 560px; margin: 0 auto; padding: 16px }
h1 { color: var(--wine); font-size: 1.5rem }
.upload input { display: none }
.upload span { display: block; padding: 14px; border-radius: 12px; background: var(--wine); color: #fff; text-align: center; font-weight: 600; cursor: pointer }
.preview { width: 100%; max-height: 280px; object-fit: contain; margin-top: 12px; border-radius: 12px }
.card { display: flex; gap: 12px; margin-top: 16px; padding: 12px; background: var(--card); border-radius: 12px }
.card img { width: 96px; height: 240px; object-fit: contain }
.card h2 { margin: 0 0 4px; font-size: 1.2rem }
.muted { color: var(--muted); margin: 2px 0 }
.debug { margin-top: 16px; font-size: .9rem }
.debug li { margin: 4px 0 }
.debug code { float: right }
.ok { color: #2e7d32 } .warn { color: #b26a00 }
.error { color: #c62828 }
a { color: var(--wine) }
</style>
