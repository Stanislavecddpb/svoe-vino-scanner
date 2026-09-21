<script setup lang="ts">
import type { Wine, WineShort } from '~/types/api'

// Wine card in the vino-svoe.ru style + recognition alternatives + similar wines.
const route = useRoute()
const slug = computed(() => String(route.params.slug))
const scan = useScan()

const { data: wine, error } = await useFetch<Wine>(() => `/v1/wines/${encodeURIComponent(slug.value)}`)
const { data: similar } = await useFetch<WineShort[]>(() => `/v1/wines/${encodeURIComponent(slug.value)}/similar?limit=8`, { default: () => [] })

useHead(() => ({ title: wine.value ? `${wine.value.name} — Своё вино` : 'Вино — Своё вино' }))

// Recognition context: only when this card was opened from a scan that contains it.
const fromScan = computed(() => {
  const s = scan.value
  return s && s.result.top5.some(c => c.slug === slug.value) ? s : null
})
const isTop1 = computed(() => fromScan.value?.result.top1?.slug === slug.value)
const uncertain = computed(() => isTop1.value && fromScan.value?.result.status === 'uncertain')
const alternatives = computed(() => fromScan.value?.result.top5.filter(c => c.slug !== slug.value) ?? [])
const showAlternatives = ref(false)
watchEffect(() => { showAlternatives.value = uncertain.value || (!!fromScan.value && !isTop1.value) })

const specs = computed(() => {
  const w = wine.value
  if (!w) return []
  return [
    ['Регион', w.region],
    ['Сорт винограда', w.grapes],
    ['Категория', w.category],
    ['Цвет', w.color],
  ].filter(([, v]) => v) as [string, string][]
})
</script>

<template>
  <main class="container card-page">
    <p class="crumbs muted">
      <NuxtLink to="/">Сканер</NuxtLink> · Свои вина · {{ wine?.name ?? '…' }}
    </p>

    <div v-if="error" class="notice">
      <span><b>Вино не найдено.</b> <NuxtLink to="/" class="link">Сканировать другое</NuxtLink></span>
    </div>

    <template v-else-if="wine">
      <div v-if="uncertain" class="notice top-notice">
        <span>🔍</span>
        <span><b>Возможно, это</b> — на фото похожие этикетки. Проверьте варианты ниже.</span>
      </div>

      <article class="card">
        <div class="card__media">
          <img :src="wine.image_url" :alt="wine.name">
        </div>
        <div class="card__body">
          <h1 class="serif card__title">{{ wine.name }}</h1>
          <p class="card__winery">{{ wine.winery }}</p>

          <dl class="specs">
            <div v-for="[k, v] in specs" :key="k" class="spec">
              <dt>{{ k }}</dt>
              <dd>{{ v }}</dd>
            </div>
          </dl>

          <p v-if="wine.description" class="card__desc">{{ wine.description }}</p>
        </div>
      </article>

      <section v-if="alternatives.length" class="alts">
        <button class="alts__toggle" :aria-expanded="showAlternatives" @click="showAlternatives = !showAlternatives">
          <span class="serif">Не то вино?</span>
          <span class="muted">{{ showAlternatives ? 'Скрыть' : `Ещё ${alternatives.length} варианта` }}</span>
        </button>
        <div v-if="showAlternatives" class="alts__body">
          <img v-if="fromScan" :src="fromScan.photoUrl" class="alts__photo" alt="Ваше фото">
          <WineGrid :wines="alternatives" show-score />
        </div>
      </section>

      <section v-if="similar?.length">
        <h2 class="section-title">Похожие вина</h2>
        <WineGrid :wines="similar" />
      </section>

      <NuxtLink to="/" class="btn btn--ghost again">Сканировать другое вино</NuxtLink>
    </template>
  </main>
</template>

<style scoped>
.card-page { padding-top: 8px; padding-bottom: 48px; }
.crumbs { font-size: 13px; margin: 8px 0 16px; }
.crumbs a { color: var(--wine); }
.top-notice { margin-bottom: 16px; }
.link { color: var(--wine); text-decoration: underline; }

.card { display: grid; gap: 20px; }
.card__media { background: var(--surface); border-radius: var(--radius); display: flex; justify-content: center; padding: 20px; }
.card__media img { height: 320px; object-fit: contain; mix-blend-mode: multiply; }
.card__title { font-size: 32px; line-height: 1.15; margin: 0; }
.card__winery { color: var(--wine); font-weight: 600; margin: 6px 0 20px; }
.specs { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 0; }
.spec { background: var(--sand-soft); border: 1px solid var(--sand); border-radius: var(--radius-s); padding: 10px 12px; }
.spec dt { font-size: 12px; color: var(--text-2); margin-bottom: 4px; }
.spec dd { margin: 0; font-weight: 600; font-size: 15px; }
.card__desc { line-height: 1.6; margin: 20px 0 0; }

@media (min-width: 720px) {
  .card { grid-template-columns: 260px 1fr; align-items: start; }
  .card__media img { height: 420px; }
}

.alts { margin-top: 24px; border-top: 1px solid var(--sand); border-bottom: 1px solid var(--sand); }
.alts__toggle { width: 100%; display: flex; justify-content: space-between; align-items: center; padding: 16px 0; background: none; border: 0; cursor: pointer; color: var(--text); }
.alts__toggle .serif { font-size: 20px; }
.alts__body { padding-bottom: 16px; }
.alts__photo { width: 96px; height: 128px; object-fit: cover; border-radius: var(--radius-s); margin-bottom: 12px; }
.again { margin-top: 32px; }
</style>
