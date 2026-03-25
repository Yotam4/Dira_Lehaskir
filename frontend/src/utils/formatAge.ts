export function formatAge(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return 'היום'
  if (diffDays === 1) return 'אתמול'
  if (diffDays < 7) return `לפני ${diffDays} ימים`
  const diffWeeks = Math.floor(diffDays / 7)
  if (diffWeeks === 1) return 'שבוע+'
  if (diffDays < 30) return `לפני ${diffWeeks} שבועות`
  const diffMonths = Math.floor(diffDays / 30)
  return `לפני ${diffMonths} חודשים`
}

export function formatLastScrape(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return 'זה עתה'
  if (diffMin < 60) return `לפני ${diffMin} דק׳`
  const diffHours = Math.floor(diffMin / 60)
  if (diffHours < 24) return `לפני ${diffHours} ש׳`
  return formatAge(iso)
}
