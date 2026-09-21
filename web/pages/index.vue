<script setup lang="ts">
// Scan screen: photo -> /v1/search -> wine card (or "not in catalog" with similar wines).
const scan = useScan()
const loading = ref(false)
const error = ref<string | null>(null)
const camera = ref<HTMLInputElement>()
const gallery = ref<HTMLInputElement>()

const notFound = computed(() => scan.value?.result.status === 'not_found' ? scan.value : null)

onMounted(() => {
  // a finished "not found" scan stays on screen; anything else starts fresh
  if (scan.value && scan.value.result.status !== 'not_found') scan.value = null
})

async function onFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  error.value = null
  loading.value = true
  const photoUrl = URL.createObjectURL(file)
  scan.value = null
  try {
    const result = await searchByPhoto(file)
    scan.value = { photoUrl, result }
    if (result.status !== 'not_found' && result.top1) await navigateTo(`/wine/${result.top1.slug}`)
  }
  catch (err: any) {
    error.value = err?.data?.error || 'Не удалось распознать фото. Попробуйте ещё раз.'
  }
  finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="container scan">
    <section class="hero">
      <p class="crumbs muted">Главная · Сканер</p>
      <h1 class="serif">Узнайте вино по этикетке</h1>
      <p class="muted">Сфотографируйте этикетку — найдём вино в каталоге «Своё вино» и покажем его карточку.</p>
    </section>

    <div class="actions">
      <input ref="camera" type="file" accept="image/*" capture="environment" hidden @change="onFile">
      <input ref="gallery" type="file" accept="image/*" hidden @change="onFile">
      <button class="btn" :disabled="loading" @click="camera?.click()">
        {{ loading ? 'Ищем вино…' : 'Сфотографировать этикетку' }}
      </button>
      <button class="btn btn--ghost" :disabled="loading" @click="gallery?.click()">
        Выбрать из галереи
      </button>
    </div>

    <div v-if="loading" class="loader" aria-live="polite">
      <span /><span /><span />
    </div>
    <p v-if="error" class="notice error">{{ error }}</p>

    <section v-if="notFound" class="not-found">
      <div class="notice">
        <img :src="notFound.photoUrl" class="photo" alt="Ваше фото">
        <span><b>Точного совпадения нет в каталоге.</b> Возможно, этого вина ещё нет на платформе — вот самые похожие.</span>
      </div>
      <h2 class="section-title">Похожие вина</h2>
      <WineGrid :wines="notFound.result.top5" />
    </section>

    <ul v-else-if="!loading" class="tips muted">
      <li>Этикетка целиком в кадре</li>
      <li>Без сильных бликов</li>
      <li>Можно под углом и у полки</li>
    </ul>
  </main>
</template>

<style scoped>
.scan { padding-top: 16px; padding-bottom: 48px; }
.crumbs { font-size: 13px; margin: 8px 0 16px; }
.hero h1 { font-size: 34px; line-height: 1.15; margin: 0 0 12px; }
.hero p { margin: 0; line-height: 1.5; }
.actions { display: grid; gap: 10px; margin: 28px 0 16px; }
@media (min-width: 640px) { .actions { grid-template-columns: 1fr 1fr; } }
.tips { list-style: none; padding: 0; margin: 20px 0 0; display: grid; gap: 8px; font-size: 14px; }
.tips li::before { content: '·'; color: var(--wine); font-weight: 700; margin-right: 8px; }
.not-found { margin-top: 8px; }
.photo { width: 64px; height: 84px; flex: none; object-fit: cover; border-radius: 8px; }
.error { color: var(--wine); }
.loader { display: flex; justify-content: center; gap: 8px; margin: 24px 0; }
.loader span { width: 10px; height: 10px; border-radius: 50%; background: var(--wine); animation: pulse 1s infinite ease-in-out; }
.loader span:nth-child(2) { animation-delay: .15s; }
.loader span:nth-child(3) { animation-delay: .3s; }
@keyframes pulse { 0%, 100% { opacity: .25; transform: scale(.8); } 50% { opacity: 1; transform: scale(1); } }
</style>
