import { en, type Dict } from './en';
import { uk } from './uk';

export type Lang = 'en' | 'uk';

export const DICTS: Record<Lang, Dict> = { en, uk };

export function dictFor(locale: string | undefined): Dict {
  return locale === 'uk' ? uk : en;
}
