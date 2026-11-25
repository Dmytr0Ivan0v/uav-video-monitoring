// Who the site is about and where to reach them; a null link is not shown.
// Email, LinkedIn and Telegram are base64 of the reversed string: address scrapers read both this repository
// and the built HTML, so the browser decodes them only when the visitor clicks.
export const PROFILE = {
  name: { en: 'Dmytro Ivanov', uk: 'Дмитро Іванов' },
  source: 'https://github.com/Dmytr0Ivan0v/uav-video-monitoring',
  email: 'bW9jLmxpYW1nQDY4OTEwdm9uYXZpb3J0eW1k' as string | null,
  linkedin: 'ODIyYjdiNjQwLXZvbmF2aS1vcnR5bWQvbmkvbW9jLm5pZGVrbmlsLnd3dy8vOnNwdHRo' as string | null,
  telegram: 'djBuYXZpb3J0eW1kL2VtLnQvLzpzcHR0aA==' as string | null,
  // path under public/ per language, encoded the same way: the PDF has the contacts in plain text
  cv: { en: 'ZmRwLk5FX3JlcG9sZXZlRF9ub2h0eVBfdm9uYXZJX29ydHltRF9WQy92Yw==', uk: 'ZmRwLkFVX3JlcG9sZXZlRF9ub2h0eVBfdm9uYXZJX29ydHltRF9WQy92Yw==' } as Record<'en' | 'uk', string> | null,
};
