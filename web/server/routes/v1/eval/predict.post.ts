// Organizer contract: multipart "image" -> {"slug": "..."}
export default defineEventHandler(async (event) => {
  try {
    const result = await runSearch(event)
    if (!result.top1) throw new ApiError(503, 'index is empty')
    return { slug: result.top1.slug }
  }
  catch (e) {
    return sendApiError(event, e)
  }
})
