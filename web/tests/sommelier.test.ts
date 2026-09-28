import { describe, expect, it } from 'vitest'
import { recommend, styleOf, type CatalogWine } from '../server/utils/sommelier'

const w = (slug: string, category: string, grapes: string, description = '', winery = slug, name = slug): CatalogWine =>
  ({ slug, name, winery, category, grapes, region: 'Крым', description })

const wines = [
  w('cab-krasnoe-suhoe', 'Красное', 'Каберне Совиньон', 'Насыщенное, танины, отлично к мясу'),
  w('cab2-krasnoe-suhoe', 'Красное', 'Саперави', 'Плотное, выдержка в дубе', 'cab-krasnoe-suhoe'),  // same winery
  w('sb-beloe-suhoe', 'Белое', 'Совиньон Блан', 'Свежее, цитрус, к рыбе и морепродуктам'),
  w('musk-beloe-sladkoe', 'Белое', 'Мускат', 'К десерту и фруктам'),
  w('brut-igristoe', 'Белое', 'Шардоне', 'Свежее, для праздника', 'x', 'Кюве брют'),
  w('pn-rozovoe-polusladkoe', 'Розовое', 'Пино Нуар', 'Ягоды'),
]

describe('sommelier', () => {
  it('derives sweetness and sparkling from slug and name', () => {
    expect(styleOf(wines[3])).toEqual({ sparkling: false, sugar: 'сладкое' })
    expect(styleOf(wines[4])).toEqual({ sparkling: true, sugar: 'брют' })
  })

  it('meat + dry + rich -> dry red with a matching grape, one per winery', () => {
    const r = recommend(wines, { food: 'meat', sweetness: 'dry', body: 'rich' })
    expect(r.map(x => x.wine.slug)).toEqual(['cab-krasnoe-suhoe'])
    expect(r[0].reason).toContain('Каберне совиньон — классика к мясу')
  })

  it('fish + dry -> white, never red', () => {
    const r = recommend(wines, { food: 'fish', sweetness: 'dry', body: 'light' })
    expect(r[0].wine.slug).toBe('sb-beloe-suhoe')
    expect(r.every(x => x.wine.category !== 'Красное')).toBe(true)
  })

  it('dessert + sweet -> muscat; aperitif + sparkling -> brut', () => {
    expect(recommend(wines, { food: 'dessert', sweetness: 'sweet', body: 'light' })[0].wine.slug).toBe('musk-beloe-sladkoe')
    expect(recommend(wines, { food: 'aperitif', sweetness: 'sparkling', body: 'light' })[0].wine.slug).toBe('brut-igristoe')
  })
})
