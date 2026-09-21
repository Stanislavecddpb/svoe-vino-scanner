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
        `SELECT w.slug, w.name, w.winery, 1 - (e.embedding <=> $1::vector) AS score
           FROM wine_embeddings e JOIN wines w USING (slug)
          WHERE e.model = $2
          ORDER BY e.embedding <=> $1::vector
          LIMIT $3`,
        [literal, this.model, k],
      )
      return rows.map(r => ({ slug: r.slug, name: r.name, winery: r.winery, score: Number(Number(r.score).toFixed(4)) }))
    }
    catch (e) {
      throw new ApiError(503, `database error: ${(e as Error).message}`)
    }
  }
}
