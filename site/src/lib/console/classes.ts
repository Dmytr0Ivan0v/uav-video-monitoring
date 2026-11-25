// Legend groups over the model classes in clip.classes; boxes and labels share these colours.
export const GROUPS = [
  { key: 'people', color: '--c-person', classes: [0] },
  { key: 'cars', color: '--c-car', classes: [2] },
  { key: 'heavy', color: '--c-heavy', classes: [5, 7] },
  { key: 'twoWheelers', color: '--c-two', classes: [1, 3] },
] as const;

export type GroupKey = (typeof GROUPS)[number]['key'];

export function groupIndex(cls: number): number {
  const i = GROUPS.findIndex((g) => (g.classes as readonly number[]).includes(cls));
  if (i < 0) throw new Error(`class ${cls} has no legend group`);
  return i;
}
