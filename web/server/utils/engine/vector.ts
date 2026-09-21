/**
 * SigLIP 2 embedding (+ label text) from the ml service, cosine search in pgvector,
 * then re-ranking of the visual Top-K by the text read on the label (ml /rerank).
 */
interface OcrItem { text: string, conf: number, cx?: number, cy?: number, h?: number }
interface Analysis { model: string, embedding: number[], ocr: OcrItem[] }
interface VisualCandidate { slug: string, name: string, winery: string | null, grapes: string | null, category: string | null, visual: number }
interface Reranked extends VisualCandidate { text: number, conflicts: number, final: number }

export class VectorEngine implements RecognitionEngine {
  readonly name = 'vector'
  get model() {
    return appConfig.modelName
  }

  private async callMl<T>(path: string, init: RequestInit): Promise<T> {
    let res: Response
    try {
      res = await fetch(`${appConfig.mlUrl}${path}`, { ...init, signal: AbortSignal.timeout(appConfig.mlTimeoutMs) })
    }
    catch (e) {
      throw new ApiError(503, `ml service unavailable: ${(e as Error).message}`)
    }
    if (res.status === 400) throw new ApiError(400, 'unsupported or corrupted image')
    if (!res.ok) throw new ApiError(503, `ml service error ${res.status} on ${path}`)
    return (await res.json()) as T
  }

  private async analyze(image: UploadedImage, withOcr: boolean): Promise<Analysis> {
    const fd = new FormData()
    fd.append('image', new Blob([image.data], { type: image.type }), image.filename)
    const body = await this.callMl<Analysis>(withOcr ? '/analyze' : '/embed', { method: 'POST', body: fd })
    if (body.model !== this.model) {
      throw new ApiError(503, `ml model "${body.model}" != index model "${this.model}"`)
    }
    return { ...body, ocr: body.ocr ?? [] }
  }

  private async visualTop(embedding: number[], k: number): Promise<VisualCandidate[]> {
    try {
      const { rows } = await getPool().query(
        // a wine's score = (1 - w) * whole-bottle match + w * best label-crop match
        // (whole bottle only if the wine has no label views); same formula as ml/scripts/evaluate.py
        `SELECT w.slug, w.name, w.winery, w.grapes, w.category, v.score
           FROM (SELECT slug,
                        CASE WHEN max(sim) FILTER (WHERE view <> 'full') IS NULL
                             THEN max(sim) FILTER (WHERE view = 'full')
                             ELSE (1 - $4::float8) * max(sim) FILTER (WHERE view = 'full')
                                  + $4::float8 * max(sim) FILTER (WHERE view <> 'full')
                        END AS score
                   FROM (SELECT slug, view, 1 - (embedding <=> $1::vector) AS sim
                           FROM wine_embeddings
                          WHERE model = $2) e
                  GROUP BY slug) v
           JOIN wines w USING (slug)
          WHERE v.score IS NOT NULL
          ORDER BY v.score DESC
          LIMIT $3`,
        [`[${embedding.join(',')}]`, this.model, k, appConfig.labelWeight],
      )
      return rows.map(r => ({ ...r, visual: Number(r.score) }))
    }
    catch (e) {
      throw new ApiError(503, `database error: ${(e as Error).message}`)
    }
  }

  async recognize(image: UploadedImage, k: number): Promise<Candidate[]> {
    const withOcr = appConfig.ocrEnabled
    const { embedding, ocr } = await this.analyze(image, withOcr)
    const visual = await this.visualTop(embedding, withOcr ? Math.max(k, appConfig.rerankK) : k)

    let ranked: (VisualCandidate & Partial<Reranked>)[] = visual
    if (withOcr && ocr.length) {
      const body = await this.callMl<{ candidates: Reranked[] }>('/rerank', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ocr, candidates: visual }),
      })
      ranked = body.candidates
    }
    const r4 = (x: number) => Number(x.toFixed(4))
    return ranked.slice(0, k).map(c => ({
      slug: c.slug,
      name: c.name,
      winery: c.winery,
      score: r4(c.final ?? c.visual),
      visual: r4(c.visual),
      ...(c.text !== undefined ? { text: c.text } : {}),
    }))
  }
}
