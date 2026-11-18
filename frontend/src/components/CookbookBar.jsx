import { ArrowRight, ImageOff, Plus, Search, X } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';

import { RecipeSearchAutocomplete } from './RecipeSearchAutocomplete.jsx';
import { resolveDishIcon } from '../utils/iconParser.js';

const TAB_DEFAULT = 'favorites';
const URL_RE = /^https?:\/\//i;

function dishImage(d) {
  return d?.image_url || d?.payload?.image_url || null;
}

function DishThumb({ src, alt, size = 'chip' }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    setFailed(false);
  }, [src]);
  if (!src) return null;
  if (failed) {
    return (
      <span className={`dish-thumb dish-thumb-fallback dish-thumb-${size}`} aria-hidden>
        <ImageOff size={size === 'preview' ? 22 : 14} />
      </span>
    );
  }
  return (
    <img
      className={`dish-thumb dish-thumb-${size}`}
      src={src}
      alt={alt || ''}
      loading="lazy"
      decoding="async"
      onError={() => setFailed(true)}
    />
  );
}

async function fetchJson(url, method = 'GET', body, signal) {
  const r = await fetch(url, {
    method,
    signal,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  let d;
  try {
    d = await r.json();
  } catch {
    throw new Error(
      r.ok
        ? 'Invalid response from server.'
        : 'API unreachable. Start the backend (docker compose up app on port 8017).',
    );
  }
  if (!r.ok) {
    throw new Error(typeof d.detail === 'string' ? d.detail : 'Request failed.');
  }
  return d;
}

export function CookbookBar({ target, days, busy, onApplyMeal }) {
  const [tab, setTab] = useState(TAB_DEFAULT);
  const [categories, setCategories] = useState([]);
  const [dishes, setDishes] = useState([]);
  const [query, setQuery] = useState('');
  const [preview, setPreview] = useState(null);
  const [importBusy, setImportBusy] = useState(false);
  const [importError, setImportError] = useState('');
  const lastAutoImport = useRef('');
  const previewRequest = useRef(null);
  const previewPanel = useRef(null);
  const previewVersion = useRef(0);
  const [searchResults, setSearchResults] = useState([]);
  const [savingPreview, setSavingPreview] = useState(false);
  useEffect(() => () => previewRequest.current?.abort(), []);

  const isUrl = URL_RE.test(query.trim());
  const searching = !!query.trim() && !isUrl;
  const visibleDishes = searching
    ? searchResults.map((row) => ({
        ...row, id: row.source_url || row.catalog_id || row.title_clean,
        display_name: row.title_clean, name_en: row.title_clean,
      }))
    : dishes;
  useEffect(() => {
    previewPanel.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [preview?.dish_name, importBusy]);

  const validPreview = preview?.ingredients.length > 0 &&
    preview.ingredients.every((item) => item.name.trim() && Number(item.quantity) > 0);

  const loadDishes = useCallback(async () => {
    const path = `/api/cookbook?category=${encodeURIComponent(tab)}`;
    const d = await fetchJson(path);
    setCategories(d.categories || []);
    setDishes(d.dishes || []);
  }, [tab]);

  useEffect(() => {
    loadDishes().catch(() => {});
  }, [loadDishes]);

  function clearPreview() {
    previewVersion.current += 1;
    previewRequest.current?.abort();
    setPreview(null);
    setImportBusy(false);
    setImportError('');
  }

  async function preparePreview(row) {
    clearPreview();
    const version = previewVersion.current;
    const controller = new AbortController();
    previewRequest.current = controller;
    const title = `${row.icon || resolveDishIcon(row.title_clean).icon} ${row.title_clean}`.slice(0, 200);
    setPreview({ dish_name: title, ingredients: [], toddler_tip: '', parser_note: 'Loading ingredients…' });
    setImportBusy(true);
    try {
      const meal = await fetchJson('/api/cookbook/select-suggestion', 'POST', {
        title_clean: row.title_clean, source_url: row.source_url || null,
        catalog_id: row.catalog_id || null,
      }, controller.signal);
      if (previewVersion.current === version) setPreview(meal);
    } catch (error) {
      if (!controller.signal.aborted && previewVersion.current === version) {
        setImportError(error.message || 'Could not load ingredients. Select the recipe to retry.');
      }
    } finally {
      if (previewVersion.current === version) setImportBusy(false);
    }
  }

  const runImport = useCallback(async () => {
    const url = query.trim();
    if (!URL_RE.test(url)) return;
    previewVersion.current += 1;
    const version = previewVersion.current;
    previewRequest.current?.abort();
    const controller = new AbortController();
    previewRequest.current = controller;
    setImportBusy(true);
    setImportError('');
    try {
      const meal = await fetchJson('/api/cookbook/import-url', 'POST', { url }, controller.signal);
      if (version !== previewVersion.current) return;
      setPreview(meal);
      lastAutoImport.current = url;
    } catch (err) {
      if (!controller.signal.aborted && version === previewVersion.current) {
        setImportError(err?.message || 'Import failed.');
      }
    } finally {
      if (version === previewVersion.current) setImportBusy(false);
    }
  }, [query]);

  useEffect(() => {
    const url = query.trim();
    if (!URL_RE.test(url)) {
      setImportError('');
      return;
    }
    if (url === lastAutoImport.current) return;
    const timer = window.setTimeout(() => {
      runImport();
    }, 450);
    return () => window.clearTimeout(timer);
  }, [query, runImport]);

  async function persistPreview(andApply) {
    if (!preview || !validPreview || importBusy || savingPreview) return;
    setSavingPreview(true);
    setImportError('');
    try {
      if (andApply) {
        await onApplyMeal(preview);
        clearPreview();
        setQuery('');
      } else {
        await fetchJson('/api/cookbook/saved', 'POST', preview);
        await loadDishes();
      }
    } catch (error) {
      setImportError(error.message || 'Could not save dish. Try again.');
    } finally {
      setSavingPreview(false);
    }
  }

  async function removeSaved(dish) {
    if (!dish.deletable || !dish.saved_key) return;
    const ok = window.confirm(`Remove “${dish.display_name}” from your saved dishes?`);
    if (!ok) return;
    await fetchJson(`/api/cookbook/saved/${encodeURIComponent(dish.saved_key)}`, 'DELETE');
    await loadDishes();
    if (preview && preview.dish_name === dish.display_name) setPreview(null);
  }

  function pickDish(d) {
    if (d.payload) {
      clearPreview();
      setPreview(d.payload);
      return;
    }
    preparePreview({
      title_clean: d.display_name, icon: d.icon,
      source_url: d.source_url, catalog_id: d.source_url ? null : (d.catalog_id || d.id),
    });
  }

  function updateIngredient(index, patch) {
    setPreview((meal) => ({
      ...meal,
      ingredients: meal.ingredients.map((item, i) => i === index ? { ...item, ...patch } : item),
    }));
  }

  return (
    <section className="favorite-strip cookbook-bar cookbook-compact">
      <div className="cookbook-head">
        <strong>Recipes</strong>
        <span>Add to {days[target]}</span>
      </div>
      <div className="cookbook-tabs" role="tablist">
        {(categories.length
          ? categories
          : [
              { id: 'favorites', label: '⭐ Favorites' },
              { id: 'canh_soups', label: '🥣 Canh / Soups' },
              { id: 'noodle_bowls', label: '🍜 Bún / Nui' },
              { id: 'steamed_airfry', label: '🐟 Steamed & Air-Fry' },
              { id: 'stir_fry_savory', label: '🍚 Stir-Fry & Clean Savory' },
            ]
        ).map((c) => (
          <button
            key={c.id}
            type="button"
            role="tab"
            aria-selected={!searching && tab === c.id}
            className={!searching && tab === c.id ? 'tab-on' : ''}
            onClick={() => {
              setTab(c.id);
              setQuery('');
              clearPreview();
            }}
          >
            {c.label.replace(/^[^\p{L}]+/u, '')}
          </button>
        ))}
      </div>
      <div className="cookbook-unified">
        <Search size={17} aria-hidden />
        <RecipeSearchAutocomplete
          value={query}
          onChange={(text) => {
            setQuery(text);
            clearPreview();
            lastAutoImport.current = '';
          }}
          onSelect={preparePreview}
          onResultsChange={setSearchResults}
          disabled={busy}
        />
        {isUrl ? (
          <button
            type="button"
            className="import-cta"
            disabled={busy || importBusy}
            onClick={runImport}
          >
            {importBusy ? 'Importing…' : 'Import'}
          </button>
        ) : (
          <span className="cookbook-hint"></span>
        )}
      </div>
      {searching && <p className="search-scope">Search results · All recipes</p>}
      {importError && (
        <p className="cookbook-import-error" role="alert">
          {importError}
        </p>
      )}
      {preview && (
        <article ref={previewPanel} className="import-preview" aria-label="Ingredient preview" aria-busy={importBusy}>
          <header className="preview-head">
            <DishThumb src={preview.image_url} alt={preview.dish_name} size="preview" />
            <h3>{preview.dish_name}</h3>
            <button
              type="button"
              className="icon preview-close"
              aria-label="Dismiss preview"
              onClick={() => {
                clearPreview();
                lastAutoImport.current = '';
              }}
            >
              <X size={16} />
            </button>
          </header>
          <p>{preview.parser_note}</p>
          {importBusy && <p role="status">Preparing ingredient list…</p>}
          <div className="preview-ingredients">
            {preview.ingredients.map((ing, index) => (
              <div className="preview-ingredient" key={index}>
                <span>{ing.name}</span>
                <input type="number" min="0.001" max="1000" step="0.001"
                  aria-label={`Preview quantity for ${ing.name}`}
                  value={ing.quantity} disabled={importBusy || savingPreview}
                  onChange={(e) => updateIngredient(index, { quantity: e.target.value })} />
                <select aria-label={`Preview unit for ${ing.name}`} value={ing.unit}
                  disabled={importBusy || savingPreview}
                  onChange={(e) => updateIngredient(index, { unit: e.target.value })}>
                  {['lb', 'L', 'each'].map((unit) => <option key={unit}>{unit}</option>)}
                </select>
              </div>
            ))}
          </div>
          {preview.toddler_tip && <p><strong>Toddler notes</strong> · {preview.toddler_tip}</p>}
          <div className="preview-actions">
            <button
              type="button"
              disabled={busy || importBusy || savingPreview || !validPreview}
              onClick={() => persistPreview(false)}
            >
              Save to favorites
            </button>
            <button
              type="button"
              className="primary compact"
              disabled={busy || importBusy || savingPreview || !validPreview}
              onClick={() => persistPreview(true)}
            >
              Add to {days[target]} <ArrowRight size={14} />
            </button>
          </div>
        </article>
      )}
      <div className="favorite-chips cookbook-chips">
        {visibleDishes.map((d) => (
          <span className="chip-wrap" key={d.id}>
            <button type="button" disabled={busy} onMouseDown={(e) => e.preventDefault()} onClick={() => pickDish(d)} title={d.name_en}>
              <DishThumb src={dishImage(d)} alt={d.display_name} />
              <Plus size={13} />
              <span className={`dish-chip-name ${d.display_name.length > 85 ? 'dish-chip-name-long' : ''}`}>{d.display_name}</span>
            </button>
            {d.deletable && (
              <button
                type="button"
                className="chip-remove"
                disabled={busy}
                aria-label={`Remove ${d.display_name}`}
                onClick={() => removeSaved(d)}
              >
                <X size={14} />
              </button>
            )}
          </span>
        ))}
      </div>
    </section>
  );
}
