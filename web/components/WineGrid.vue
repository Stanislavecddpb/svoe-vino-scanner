<script setup lang="ts">
import type { WineShort } from '~/types/api'

// Horizontal scroller on phones, grid on wider screens.
defineProps<{ wines: WineShort[], showScore?: boolean }>()
</script>

<template>
  <div class="grid">
    <WineTile v-for="w in wines" :key="w.slug" :wine="w" :show-score="showScore" />
  </div>
</template>

<style scoped>
.grid { display: grid; grid-auto-flow: column; grid-auto-columns: 42%; gap: 12px; overflow-x: auto; scroll-snap-type: x mandatory; scroll-padding: 0 16px; scrollbar-width: none; padding: 0 16px 8px; margin: 0 -16px; }
.grid::-webkit-scrollbar { display: none; }
.grid > * { scroll-snap-align: start; }
@media (min-width: 640px) {
  .grid { grid-auto-flow: row; grid-template-columns: repeat(4, 1fr); overflow: visible; margin: 0; padding: 0; }
}
</style>
