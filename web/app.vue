<template>
  <div>
    <header class="header">
      <div class="container header__row">
        <NuxtLink to="/" class="logo serif">Своё вино</NuxtLink>
        <NuxtLink to="/" class="header__scan" aria-label="Сканировать">Сканер</NuxtLink>
      </div>
    </header>
    <NuxtPage />
  </div>
</template>

<style scoped>
.header { position: sticky; top: 0; z-index: 10; background: rgba(253, 249, 237, .92); backdrop-filter: blur(8px); border-bottom: 1px solid var(--sand); }
.header__row { display: flex; align-items: center; justify-content: space-between; height: 56px; }
.logo { font-size: 22px; color: var(--wine); }
.header__scan { font-size: 14px; color: var(--wine); padding: 6px 14px; border: 1px solid var(--wine); border-radius: 999px; }
</style>
