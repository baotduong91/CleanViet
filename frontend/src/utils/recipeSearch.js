import catalog from '../data/cookbookCatalog.json' with { type: 'json' };
import { normalizeDiacritics, resolveDishIcon } from './iconParser.js';

const clientCache = new Map();
const MAX_CACHE = 128;

export function searchAllowed(query) {
  const words = query.trim().split(/\s+/).filter(Boolean);
  return words.length >= 2 && words[1].length >= 2;
}

export function cachedSuggestions(query) {
  const key = normalizeDiacritics(query);
  if (!clientCache.has(key)) return null;
  const rows = clientCache.get(key);
  clientCache.delete(key);
  clientCache.set(key, rows);
  return rows;
}

export function cacheSuggestions(query, rows) {
  const key = normalizeDiacritics(query);
  clientCache.delete(key);
  clientCache.set(key, rows);
  if (clientCache.size > MAX_CACHE) clientCache.delete(clientCache.keys().next().value);
}

function trigrams(text) {
  return new Set(Array.from({ length: Math.max(0, text.length - 2) }, (_, i) => text.slice(i, i + 3)));
}

export function localSuggestions(query) {
  const q = normalizeDiacritics(query);
  if (!q) return [];
  const grams = trigrams(q);
  return catalog.map((row) => {
    let score = 0;
    if (normalizeDiacritics(row.title_clean).startsWith(q)) score = 100;
    else if (row.search_text.includes(q) || q.split(' ').every((word) => row.search_text.split(' ').includes(word))) score = 80;
    else if (q.includes(' ') && grams.size) {
      const candidate = trigrams(row.search_text);
      const overlap = [...grams].filter((gram) => candidate.has(gram)).length / grams.size;
      if (overlap >= 0.65) score = overlap * 50;
    }
    return { row, score };
  }).filter(({ score }) => score > 0)
    .sort((a, b) => b.score - a.score || a.row.catalog_id.localeCompare(b.row.catalog_id))
    .slice(0, 8).map(({ row }) => ({ ...row, ...resolveDishIcon(row.title_clean) }));
}

export function initialSuggestions(query) {
  if (/^https?:\/\//i.test(query.trim())) return [];
  return (searchAllowed(query) && cachedSuggestions(query)) || localSuggestions(query);
}
