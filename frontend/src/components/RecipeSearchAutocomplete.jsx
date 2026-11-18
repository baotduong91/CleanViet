import { useEffect, useId, useRef, useState } from 'react';
import { normalizeDiacritics } from '../utils/iconParser.js';
import { initialSuggestions, searchAllowed, cachedSuggestions, cacheSuggestions } from '../utils/recipeSearch.js';

function Highlight({ title, query }) {
  const words = normalizeDiacritics(query).split(' ').filter(Boolean);
  const segments = [...new Intl.Segmenter('vi', { granularity: 'grapheme' }).segment(title)];
  let normalized = '';
  const positions = [];
  for (let i = 0; i < segments.length; i += 1) {
    const part = normalizeDiacritics(segments[i].segment) || ' ';
    normalized += part;
    positions.push(...Array(part.length).fill(i));
  }
  const matched = new Set();
  for (const word of words) {
    let from = 0;
    while (from < normalized.length) {
      const index = normalized.indexOf(word, from);
      if (index < 0) break;
      for (let j = index; j < index + word.length; j += 1) matched.add(positions[j]);
      from = index + word.length;
    }
  }
  return segments.map(({ segment }, i) => matched.has(i) ? <strong key={i}>{segment}</strong> : segment);
}

export function RecipeSearchAutocomplete({
  value, onChange, onSelect, id, label = 'Search dishes or paste recipe URL',
  placeholder = 'Search dishes or paste a recipe URL…', multiline = false, disabled = false, onResultsChange,
}) {
  const listId = useId();
  const [rows, setRows] = useState(() => initialSuggestions(value));
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [loading, setLoading] = useState(false);
  const request = useRef(null);
  const generation = useRef(0);
  const timer = useRef(null);
  const composing = useRef(false);
  const [composition, setComposition] = useState(false);
  const optionRefs = useRef([]);
  const keyboardNavigation = useRef(false);

  function cancel() {
    generation.current += 1;
    request.current?.abort();
    clearTimeout(timer.current);
  }

  useEffect(() => {
    cancel();
    setLoading(false);
    if (!open) return cancel;
    const rows = initialSuggestions(value);
    setRows(rows);
    setActive(-1);
    setLoading(false);
    if (!open || composition || !searchAllowed(value) || /^https?:\/\//i.test(value.trim()) || cachedSuggestions(value)) return cancel;
    const version = generation.current;
    timer.current = setTimeout(async () => {
      const controller = new AbortController();
      request.current = controller;
      setLoading(true);
      try {
        const response = await fetch(`/api/cookbook/autocomplete?q=${encodeURIComponent(value.trim())}`, { signal: controller.signal });
        if (!response.ok) throw new Error('Search unavailable');
        const result = await response.json();
        if (generation.current !== version || controller.signal.aborted) return;
        cacheSuggestions(value, result.suggestions || []);
        setRows(result.suggestions || []);
      } catch (error) {
        // The already-visible local results remain usable if a provider is offline.
      } finally {
        if (generation.current === version) setLoading(false);
      }
    }, 180);
    return cancel;
  }, [value, composition, open]);

  useEffect(() => {
    if (keyboardNavigation.current && active >= 0) optionRefs.current[active]?.scrollIntoView({ block: 'nearest' });
  }, [active]);

  useEffect(() => {
    onResultsChange?.(rows);
  }, [rows, onResultsChange]);

  function choose(row) {
    cancel();
    setOpen(false);
    setActive(-1);
    onSelect(row);
  }

  const Input = multiline ? 'textarea' : 'input';
  return (
    <div className={`recipe-autocomplete ${multiline ? 'recipe-autocomplete-card' : ''}`}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}>
      <Input
        id={id}
        role="combobox"
        aria-label={label}
        aria-autocomplete="list"
        aria-expanded={open && rows.length > 0}
        aria-controls={listId}
        aria-activedescendant={open && active >= 0 ? `${listId}-${active}` : undefined}
        autoComplete="off"
        value={value}
        maxLength={200}
        disabled={disabled}
        placeholder={placeholder}
        onFocus={() => setOpen(true)}
        onCompositionStart={() => { composing.current = true; cancel(); setComposition(true); }}
        onCompositionEnd={() => { composing.current = false; setComposition(false); }}
        onChange={(e) => {
          cancel();
          setRows(initialSuggestions(e.target.value));
          setLoading(false);
          setOpen(true);
          setActive(-1);
          onChange(e.target.value);
        }}
        onKeyDown={(e) => {
          if (composing.current || e.nativeEvent.isComposing) return;
          if (e.key === 'Escape') { cancel(); setLoading(false); setOpen(false); setActive(-1); }
          if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
            keyboardNavigation.current = true;
            if (!rows.length) return;
            e.preventDefault();
            setOpen(true);
            setActive((i) => e.key === 'ArrowDown' ? (i + 1) % rows.length : (i <= 0 ? rows.length - 1 : i - 1));
          }
          if (e.key === 'Enter' && open && active >= 0 && rows[active]) {
            e.preventDefault();
            choose(rows[active]);
          }
        }}
      />
      {open && (rows.length > 0 || loading) && (
        <div className="recipe-suggestions" role="listbox" id={listId} aria-label="Recipe suggestions">
          {rows.map((row, i) => (
            <button
              type="button"
              role="option"
              aria-selected={active === i}
              id={`${listId}-${i}`}
              className={active === i ? 'suggestion-active' : ''}
              key={row.source_url || row.catalog_id || row.title_clean}
              ref={(node) => { optionRefs.current[i] = node; }}
              tabIndex={-1}
              onMouseDown={(e) => {
                if (e.button !== 0) return;
                e.preventDefault();
              }}
              onPointerDown={() => { cancel(); setLoading(false); }}
              onMouseEnter={() => { keyboardNavigation.current = false; setActive(i); }}
              onClick={() => choose(row)}
            >
              <span aria-hidden="true">{row.icon}</span>
              <span className="suggestion-title"><Highlight title={row.title_clean} query={value} /><small>{row.category_label}</small></span>
              <span className="suggestion-source">{row.source_domain === 'CleanViet Catalog' ? 'Local' : row.source_domain}</span>
            </button>
          ))}
          {loading && <div className="suggestion-loading" role="status">Searching recipe sites…</div>}
        </div>
      )}
    </div>
  );
}
