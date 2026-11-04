import { ArrowRight, ImageOff, Plus, Search, X } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';

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

async function fetchJson(url, method = 'GET', body) {
  const r = await fetch(url, {
    method,
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

  const isUrl = URL_RE.test(query.trim());

  const loadDishes = useCallback(async () => {
    const q = query.trim();
    const path =
      isUrl && tab === TAB_DEFAULT
        ? `/api/cookbook?category=${encodeURIComponent(tab)}`
        : q && !isUrl
          ? `/api/cookbook?category=${encodeURIComponent(tab)}&q=${encodeURIComponent(q)}`
          : `/api/cookbook?category=${encodeURIComponent(tab)}`;
    const d = await fetchJson(path);
    setCategories(d.categories || []);
    setDishes(d.dishes || []);
  }, [tab, query, isUrl]);

  useEffect(() => {
    loadDishes().catch(() => {});
  }, [loadDishes]);

  const runImport = useCallback(async () => {
    const url = query.trim();
    if (!URL_RE.test(url)) return;
    setImportBusy(true);
    setImportError('');
    try {
      const meal = await fetchJson('/api/cookbook/import-url', 'POST', { url });
      setPreview(meal);
      lastAutoImport.current = url;
    } catch (err) {
      setImportError(err?.message || 'Import failed.');
      setPreview(null);
    } finally {
      setImportBusy(false);
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
    if (!preview) return;
    await fetchJson('/api/cookbook/saved', 'POST', preview);
    await loadDishes();
    if (andApply) {
      onApplyMeal(preview);
      setPreview(null);
      setQuery('');
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
      onApplyMeal(d.payload);
      return;
    }
    onApplyMeal({ dish_name: d.display_name, parseName: d.display_name });
  }

  return (
    <section className="favorite-strip cookbook-bar cookbook-compact">
      <div className="cookbook-head">
        <strong>Vietnamese cookbook</strong>
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
            aria-selected={tab === c.id}
            className={tab === c.id ? 'tab-on' : ''}
            onClick={() => {
              setTab(c.id);
              setPreview(null);
            }}
          >
            {c.label}
          </button>
        ))}
      </div>
      <div className="cookbook-unified">
        <Search size={17} aria-hidden />
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            if (!URL_RE.test(e.target.value.trim())) {
              setPreview(null);
              setImportError('');
              lastAutoImport.current = '';
            }
          }}
          placeholder="Search dishes or paste a recipe URL…"
          aria-label="Search dishes or paste recipe URL"
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
          <span className="cookbook-hint">40+ weeknight dishes</span>
        )}
      </div>
      {importError && (
        <p className="cookbook-import-error" role="alert">
          {importError}
        </p>
      )}
      {preview && (
        <article className="import-preview">
          <header className="preview-head">
            <DishThumb src={preview.image_url} alt={preview.dish_name} size="preview" />
            <h3>{preview.dish_name}</h3>
            <button
              type="button"
              className="icon preview-close"
              aria-label="Dismiss preview"
              onClick={() => {
                setPreview(null);
                lastAutoImport.current = '';
              }}
            >
              <X size={16} />
            </button>
          </header>
          <p>{preview.parser_note}</p>
          <ul>
            {preview.ingredients.slice(0, 8).map((ing) => (
              <li key={`${ing.name}-${ing.quantity}`}>
                {ing.name} · {ing.quantity} {ing.unit}
              </li>
            ))}
            {preview.ingredients.length > 8 && (
              <li>+{preview.ingredients.length - 8} more…</li>
            )}
          </ul>
          <div className="preview-actions">
            <button
              type="button"
              disabled={busy}
              onClick={() => persistPreview(false)}
            >
              Save to favorites
            </button>
            <button
              type="button"
              className="primary compact"
              disabled={busy}
              onClick={() => persistPreview(true)}
            >
              Save & add to {days[target]} <ArrowRight size={14} />
            </button>
          </div>
        </article>
      )}
      <div className="favorite-chips cookbook-chips">
        {dishes.map((d) => (
          <span className="chip-wrap" key={d.id}>
            <button type="button" disabled={busy} onClick={() => pickDish(d)} title={d.name_en}>
              <DishThumb src={dishImage(d)} alt={d.display_name} />
              <Plus size={13} />
              {d.display_name}
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
