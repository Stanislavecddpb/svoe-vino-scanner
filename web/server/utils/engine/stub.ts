import { createHash } from 'node:crypto'

// Real catalog slugs so the frontend can render cards while the ML part is offline.
const STUB_WINES: Omit<Candidate, 'score'>[] = [
  { slug: 'bogovich-wine-vineyard-klaret-pino-nuar-krasnoe-suhoe-119', name: 'Кларет', winery: 'Bogovich Wine & Vineyard' },
  { slug: 'risling-2024', name: 'Рислинг, 2024', winery: 'Винодельня Братьев Мельниковых' },
  { slug: 'vinodelnya-myshako-risling-beloe-suhoe-123', name: 'Рислинг', winery: 'Мысхако' },
  { slug: 'vinodelnya-byurne-lyublyu-beloe-shardone-suhoe-135', name: 'БЮРНЬЕ.ЛЮБЛЮ сухое белое', winery: 'Винодельня Бюрнье' },
  { slug: 'vibes-silvaner-2022', name: 'VIBES, Silvaner 2022', winery: 'Vibes' },
  { slug: 'alma-valley-tba-sovinon-sovinon-blan-beloe-sladkoe-75', name: 'ТБА Совиньон', winery: 'Alma Valley' },
  { slug: 'dva-serdtsa-saperavi-krasnoe-suhoe-135', name: 'Саперави', winery: 'Два Сердца' },
  { slug: 'belbek-zakat-merlo-sira-krasnoe-suhoe-132', name: 'Закат. Мерло Сира', winery: 'Бельбек' },
]

/** Deterministic fake: same image bytes -> same answer. No ML, no DB. */
export class StubEngine implements RecognitionEngine {
  readonly name = 'stub'
  readonly model = null

  async recognize(image: UploadedImage, k: number): Promise<Candidate[]> {
    const h = createHash('sha256').update(image.data).digest()
    const start = h[0] % STUB_WINES.length
    return Array.from({ length: Math.min(k, STUB_WINES.length) }, (_, i) => ({
      ...STUB_WINES[(start + i) % STUB_WINES.length],
      score: Number((0.9 - i * 0.07 - (h[1] / 255) * 0.02).toFixed(4)),
    }))
  }
}
