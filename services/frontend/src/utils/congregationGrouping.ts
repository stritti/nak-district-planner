import type { CongregationGroupResponse, CongregationResponse } from '@/api/districts'

export interface CongregationSection {
  key: string
  title: string | null
  items: CongregationResponse[]
}

export function buildCongregationSections(
  congregations: CongregationResponse[],
  groups: CongregationGroupResponse[],
): CongregationSection[] {
  const grouped: Record<string, CongregationResponse[]> = {}
  const ungrouped: CongregationResponse[] = []

  for (const congregation of congregations) {
    if (!congregation.group_id) {
      ungrouped.push(congregation)
      continue
    }
    if (!grouped[congregation.group_id]) {
      grouped[congregation.group_id] = []
    }
    grouped[congregation.group_id].push(congregation)
  }

  const sections: CongregationSection[] = []
  for (const group of groups) {
    const items = (grouped[group.id] ?? []).slice().sort((a, b) => a.name.localeCompare(b.name))
    if (items.length > 0) {
      sections.push({ key: `group-${group.id}`, title: group.name, items })
    }
  }

  for (const [groupId, items] of Object.entries(grouped)) {
    if (groups.some((group) => group.id === groupId) || items.length === 0) continue
    sections.push({
      key: `group-${groupId}`,
      title: items[0].group_name ?? 'Gruppe',
      items: items.slice().sort((a, b) => a.name.localeCompare(b.name)),
    })
  }

  if (ungrouped.length > 0) {
    sections.push({
      key: 'ungrouped',
      title: sections.length > 0 ? 'Ohne Gruppe' : null,
      items: ungrouped.slice().sort((a, b) => a.name.localeCompare(b.name)),
    })
  }

  return sections
}
