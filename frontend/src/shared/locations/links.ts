export function websiteHref(value: string | null | undefined) {
  const text = value?.trim()
  if (!text || !/^(https?:\/\/|[a-z0-9][a-z0-9.-]*\.[a-z]{2,}(?::\d+)?(?:[/?#]|$))/i.test(text)) return undefined
  try {
    const url = new URL(text.includes('://') ? text : `https://${text}`)
    return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password ? url.href : undefined
  } catch { return undefined }
}
