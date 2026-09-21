import { describe, expect, it } from 'vitest'
import { recognitionStatus } from '../server/utils/status'

const T = { notFoundScore: 0.72, confidenceMargin: 0.03 }

describe('recognitionStatus', () => {
  it('not_found when top1 score is below the floor', () => {
    expect(recognitionStatus(0.69, 0.2, T)).toBe('not_found')
  })
  it('confident when score is high and margin is large', () => {
    expect(recognitionStatus(0.85, 0.05, T)).toBe('confident')
  })
  it('uncertain when margin is small', () => {
    expect(recognitionStatus(0.84, 0.002, T)).toBe('uncertain')
  })
  it('confident when there is only one candidate', () => {
    expect(recognitionStatus(0.8, null, T)).toBe('confident')
  })
  it('not_found when there are no candidates', () => {
    expect(recognitionStatus(null, null, T)).toBe('not_found')
  })
})
