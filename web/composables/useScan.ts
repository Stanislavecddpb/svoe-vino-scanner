import type { SearchResult } from '~/types/api'

/** Last scan (photo + recognition result), shared between the scan page and the wine card. */
export interface ScanState {
  photoUrl: string
  result: SearchResult
}

export const useScan = () => useState<ScanState | null>('scan', () => null)

export async function searchByPhoto(file: File): Promise<SearchResult> {
  const fd = new FormData()
  fd.append('image', file)
  return await $fetch<SearchResult>('/v1/search', { method: 'POST', body: fd })
}
