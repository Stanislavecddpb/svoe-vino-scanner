// Extended result for frontend / debugging: top1, top5 with scores, margin.
export default defineEventHandler(async (event) => {
  try {
    return await runSearch(event)
  }
  catch (e) {
    return sendApiError(event, e)
  }
})
