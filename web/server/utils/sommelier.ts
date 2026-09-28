/**
 * "Цифровой сомелье" (rule-based): three answers -> a short list of catalog wines with a reason.
 * No LLM: food pairing rules + sweetness/type from the name and slug + body from the tasting note.
 * Sweetness/sparkling rules mirror ml/wine_ml/analogs.py.
 */
export type Food = 'meat' | 'poultry' | 'fish' | 'cheese' | 'veggies' | 'dessert' | 'aperitif'
export type Sweetness = 'dry' | 'medium' | 'sweet' | 'sparkling'
export type Body = 'light' | 'rich'

export interface SommelierAnswers { food: Food, sweetness: Sweetness, body: Body }

export interface CatalogWine {
  slug: string, name: string, winery: string | null, category: string | null,
  grapes: string | null, region: string | null, description: string | null,
}

interface Pairing { label: string, categories: string[], grapes: string[], words: string[] }

export const PAIRINGS: Record<Food, Pairing> = {
  meat: { label: 'к мясу', categories: ['Красное'], grapes: ['каберне совиньон', 'саперави', 'красностоп', 'мерло', 'сира', 'каберне фран', 'цимлянский'], words: ['мяс', 'стейк', 'дичь', 'барбекю', 'гриль'] },
  poultry: { label: 'к птице', categories: ['Белое', 'Розовое', 'Красное'], grapes: ['шардоне', 'пино нуар', 'вионье', 'пино гри', 'пино блан'], words: ['птиц', 'куриц', 'утк', 'индейк'] },
  fish: { label: 'к рыбе и морепродуктам', categories: ['Белое', 'Розовое'], grapes: ['совиньон блан', 'рислинг', 'алиготе', 'ркацители', 'шардоне', 'кокур', 'пино гри'], words: ['рыб', 'морепродукт', 'устриц', 'мидии', 'креветк'] },
  cheese: { label: 'к сырам', categories: ['Красное', 'Белое'], grapes: ['пино нуар', 'шардоне', 'каберне совиньон', 'мерло', 'рислинг'], words: ['сыр'] },
  veggies: { label: 'к овощам и пасте', categories: ['Розовое', 'Белое', 'Красное'], grapes: ['пино нуар', 'совиньон блан', 'мерло', 'шардоне', 'ркацители'], words: ['овощ', 'паст', 'салат', 'пицц'] },
  dessert: { label: 'к десерту', categories: ['Белое', 'Розовое', 'Красное'], grapes: ['мускат', 'рислинг', 'кокур', 'алеатико', 'пино гри'], words: ['десерт', 'фрукт', 'выпечк', 'шоколад'] },
  aperitif: { label: 'на аперитив и праздник', categories: ['Белое', 'Розовое', 'Красное'], grapes: ['шардоне', 'пино нуар', 'рислинг', 'мускат', 'алиготе'], words: ['аперитив', 'праздн'] },
}

const BODY_WORDS: Record<Body, string[]> = {
  light: ['свеж', 'легк', 'цитрус', 'минерал', 'живая кислот', 'яблок', 'лайм', 'лимон'],
  rich: ['насыщен', 'полнотел', 'плотн', 'выдерж', 'дуб', 'танин', 'бархат', 'шоколад', 'черносл'],
}

const SPARKLING = /bryut|брют|brut|igrist|игрист|petnat|pet.?nat|пет.?нат|shampansk|шампанск|frizzante|prosecco|spumante|cremant/
const SUGAR: [string, RegExp][] = [
  ['экстра брют', /ekstra.?bryut|экстра.?брют|extra.?brut|zero.?dosage|зеро.?дозаж/],
  ['брют', /bryut|брют|brut/],
  ['полусладкое', /polusladk|полуслад/],
  ['полусухое', /polusuh|полусух/],
  ['сладкое', /sladk|сладк|desert|десерт|dessert/],
  ['сухое', /suhoe|suhoy|сухое|сухой/],
]

export function styleOf(w: CatalogWine): { sparkling: boolean, sugar: string } {
  const s = `${w.slug} ${w.name}`.toLowerCase()
  const sparkling = SPARKLING.test(s)
  const sugar = SUGAR.find(([, re]) => re.test(s))?.[0] ?? (sparkling ? 'брют' : 'сухое')
  return { sparkling, sugar }
}

function sweetnessOk(want: Sweetness, st: { sparkling: boolean, sugar: string }): boolean {
  if (want === 'sparkling') return st.sparkling
  if (st.sparkling) return false
  if (want === 'dry') return st.sugar === 'сухое'
  if (want === 'medium') return st.sugar === 'полусухое' || st.sugar === 'полусладкое'
  return st.sugar === 'сладкое'
}

export function recommend(wines: CatalogWine[], a: SommelierAnswers, k = 6) {
  const p = PAIRINGS[a.food]
  const scored = []
  for (const w of wines) {
    const st = styleOf(w)
    if (!sweetnessOk(a.sweetness, st)) continue
    if (a.food !== 'aperitif' && a.food !== 'dessert' && !p.categories.includes(w.category ?? '')) continue
    const grapes = (w.grapes ?? '').toLowerCase().replace(/ё/g, 'е')
    const desc = (w.description ?? '').toLowerCase().replace(/ё/g, 'е')
    const grapeHits = p.grapes.filter(g => grapes.includes(g))
    const foodHits = p.words.filter(x => desc.includes(x))
    const bodyHits = BODY_WORDS[a.body].filter(x => desc.includes(x))
    const score = 2 * Math.min(grapeHits.length, 1) + 1.5 * Math.min(foodHits.length, 1) + 0.5 * Math.min(bodyHits.length, 3)
      + (a.food === 'aperitif' && st.sparkling ? 1 : 0)
    if (score <= 0) continue
    const reason = [
      grapeHits.length ? `${capitalize(grapeHits[0])} — классика ${p.label}` : `подходит ${p.label}`,
      `${st.sugar} ${(w.category ?? '').toLowerCase()}`.trim(),
      foodHits.length ? 'в описании прямо советуют' : '',
      bodyHits.length ? (a.body === 'light' ? 'лёгкое и свежее' : 'насыщенное') : '',
    ].filter(Boolean).join(' · ')
    scored.push({ wine: w, score, reason })
  }
  // ties are frequent: order them by a stable hash of (wine, answers) instead of the alphabet,
  // so different answers surface different wineries but the same answers give the same list
  const seed = `${a.food}|${a.sweetness}|${a.body}`
  scored.sort((x, y) => y.score - x.score || hash(x.wine.slug + seed) - hash(y.wine.slug + seed))
  const out = []
  const wineries = new Set<string>()
  for (const s of scored) {  // variety: at most one wine per winery
    const key = s.wine.winery ?? s.wine.slug
    if (wineries.has(key)) continue
    wineries.add(key)
    out.push(s)
    if (out.length === k) break
  }
  return out
}

function hash(s: string): number { // FNV-1a
  let h = 0x811C9DC5
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 0x01000193)
  return h >>> 0
}

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1)
}
