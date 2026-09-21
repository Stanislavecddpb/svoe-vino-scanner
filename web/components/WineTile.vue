<script setup lang="ts">
import type { WineShort } from '~/types/api'

// Compact wine tile for "Не то вино?" / "Похожие вина" lists.
defineProps<{ wine: WineShort, showScore?: boolean }>()
</script>

<template>
  <NuxtLink :to="`/wine/${wine.slug}`" class="tile">
    <div class="tile__img">
      <img :src="wine.image_url" :alt="wine.name" loading="lazy">
    </div>
    <div class="tile__name">{{ wine.name }}</div>
    <div class="tile__winery">{{ wine.winery }}</div>
    <div v-if="showScore" class="tile__score">сходство {{ Math.round(wine.score * 100) }}%</div>
  </NuxtLink>
</template>

<style scoped>
.tile { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.tile__img { aspect-ratio: 3 / 4; background: var(--surface); border-radius: var(--radius); padding: 10px; overflow: hidden; }
.tile__img img { width: 100%; height: 100%; object-fit: contain; mix-blend-mode: multiply; }
.tile__name { font-weight: 600; font-size: 14px; line-height: 1.25; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.tile__winery { font-size: 13px; color: var(--text-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tile__score { font-size: 12px; color: var(--text-3); }
</style>
