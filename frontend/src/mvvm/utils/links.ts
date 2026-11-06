import type { MouseEvent } from 'react'

export type OpenLink = (url: string) => void

// websiteHref accepts only plain http(s) addresses, adding the scheme that
// sources often omit, so published text never becomes a script or login URL.
export function websiteHref(value: string | null | undefined) {
  const text = value?.trim()
  if (!text || !/^(https?:\/\/|[a-z0-9][a-z0-9.-]*\.[a-z]{2,}(?::\d+)?(?:[/?#]|$))/i.test(text)) return undefined
  try {
    const url = new URL(text.includes('://') ? text : `https://${text}`)
    return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password ? url.href : undefined
  } catch { return undefined }
}

// hostLink routes a link click through the host when it provides openLink:
// sandboxed MCP hosts block plain navigation. Without it the browser follows
// the link as usual.
export function hostLink(openLink?: OpenLink) {
  return (event: MouseEvent<HTMLAnchorElement>) => {
    if (!openLink) return
    event.preventDefault()
    openLink(event.currentTarget.href)
  }
}
