<script setup lang="ts">
import type { WineShort } from '~/types/api'

// "Цифровой сомелье": three questions -> wines from the catalog with a reason.
type Pick = WineShort & { reason: string }

const steps = [
  {
    key: 'food', title: 'К чему выбираем вино?',
    options: [['meat', 'Мясо, стейк'], ['poultry', 'Птица'], ['fish', 'Рыба, морепродукты'], ['cheese', 'Сыры'],
      ['veggies', 'Овощи, паста'], ['dessert', 'Десерт, фрукты'], ['aperitif', 'Аперитив, праздник']],
  },
  {
    key: 'sweetness', title: 'Какой вкус любите?',
    options: [['dry', 'Сухое'], ['medium', 'Полусухое / полусладкое'], ['sweet', 'Сладкое'], ['sparkling', 'Игристое']],
  },
  {
    key: 'body', title: 'Какой характер?',
    options: [['light', 'Лёгкое и свежее'], ['rich', 'Насыщенное, выразительное']],
  },
] as const

const answers = reactive<Record<string, string>>({})
const step = ref(0)
const picks = ref<Pick[] | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

async function choose(key: string, value: string) {
  answers[key] = value
  if (step.value < steps.length - 1) {
    step.value++
    return
  }
  loading.value = true
  error.value = null
  try {
    picks.value = await $fetch<Pick[]>('/v1/sommelier', { method: 'POST', body: answers })
  }
  catch (e: any) {
    error.value = e?.data?.error || 'Не получилось подобрать вино'
  }
  finally {
    loading.value = false
  }
}

function restart() {
  step.value = 0
  picks.value = null
  for (const k of Object.keys(answers)) delete answers[k]
}

useHead({ title: 'Цифровой сомелье — Своё вино' })
</script>

<template>
  <main class="container som">
    <p class="crumbs muted"><NuxtLink to="/">Сканер</NuxtLink> · Цифровой сомелье</p>
    <h1 class="serif">Цифровой сомелье</h1>
    <p class="muted lead">Три вопроса — и подборка российских вин из каталога «Своё вино».</p>

    <section v-if="!picks" class="q">
      <p class="q__n muted">Вопрос {{ step + 1 }} из {{ steps.length }}</p>
      <h2 class="serif q__title">{{ steps[step].title }}</h2>
      <div class="q__opts">
        <button v-for="[v, label] in steps[step].options" :key="v" class="opt" :disabled="loading"
                :class="{ sel: answers[steps[step].key] === v }" @click="choose(steps[step].key, v)">
          {{ label }}
        </button>
      </div>
      <button v-if="step > 0" class="back muted" @click="step--">← Назад</button>
      <p v-if="loading" class="muted">Подбираем…</p>
      <p v-if="error" class="notice">{{ error }}</p>
    </section>

    <section v-else>
      <h2 class="section-title">Сомелье советует</h2>
      <p v-if="!picks.length" class="notice">Под такое сочетание в каталоге ничего не нашлось — попробуйте другой вкус.</p>
      <WineGrid :wines="picks" />
      <button class="btn btn--ghost again" @click="restart">Подобрать ещё</button>
    </section>
  </main>
</template>

<style scoped>
.som { padding-top: 16px; padding-bottom: 48px; }
.crumbs { font-size: 13px; margin: 8px 0 16px; }
.crumbs a { color: var(--wine); }
h1 { font-size: 34px; margin: 0 0 8px; }
.lead { margin: 0 0 24px; }
.q__n { font-size: 13px; margin: 0; }
.q__title { font-size: 24px; margin: 6px 0 16px; }
.q__opts { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.opt { padding: 14px 12px; border-radius: var(--radius-s); border: 1px solid var(--sand); background: var(--surface);
  color: var(--text); font-weight: 600; cursor: pointer; text-align: left; }
.opt:hover, .opt.sel { border-color: var(--wine); color: var(--wine); }
.back { margin-top: 16px; background: none; border: 0; cursor: pointer; }
.again { margin-top: 24px; }
</style>
