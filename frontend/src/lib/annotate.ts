import type { EditableResponse } from "@/components/annotate/SortableResponseCard";

export function buildRankingGroups(items: EditableResponse[]): number[][] {
  const groups = new Map<number, number[]>();
  items.forEach((item, index) => {
    const key = item.group ?? index;
    const bucket = groups.get(key) || [];
    bucket.push(item.id);
    groups.set(key, bucket);
  });
  return Array.from(groups.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([, ids]) => ids);
}
