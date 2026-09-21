/** SigLIP 2 embedding from the ml service + cosine search in pgvector. */
export class VectorEngine implements RecognitionEngine {
  readonly name = 'vector'
  get model() {
    return appConfig.modelName
  }

  private async embed(image: UploadedImage): Promise<number[]> {
    const fd = new FormData()
    fd.append('image', new Blob([image.data], { type: image.type }), image.filename)
    let res: Response
    try {
      res = await fetch(`${appConfig.mlUrl}/embed`, {
        method: 'POST',
        body: fd,
        signal: AbortSignal.timeout(appConfig.mlTimeoutMs),
      })
    }
    catch (e) {
      throw new ApiError(503, `ml service unavailable: ${(e as Error).message}`)
    }
    if (res.status === 400) throw new ApiError(400, 'unsupported or corrupted image')
    if (!res.ok) throw new ApiError(503, `ml service error ${res.status}`)
    const body = (await res.json()) as { model: string, embedding: number[] }
    if (body.model !== this.model) {
      throw new ApiError(503, `ml model "${body.model}" != index model "${this.model}"`)
    }
    return body.embedding
  }

  async recognize(image: UploadedImage, k: number): Promise<Candidate[]> {
    const literal = `[${(await this.embed(image)).join(',')}]`
    try {
      const { rows } = await getPool().query(
        // a wine's score = (1 - w) * whole-bottle match + w * best label-crop match
        // (whole bottle only if the wine has no label views); same formula as ml/scripts/evaluate.py
        `SELECT w.slug, w.name, w.winery, v.score
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
        [literal, this.model, k, appConfig.labelWeight],
      )
      return rows.map(r => ({ slug: r.slug, name: r.name, winery: r.winery, score: Number(Number(r.score).toFixed(4)) }))
    }
    catch (e) {
      throw new ApiError(503, `database error: ${(e as Error).message}`)
    }
  }
}
