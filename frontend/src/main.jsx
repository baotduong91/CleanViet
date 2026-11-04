import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Sprout,
  X,
  ShoppingBag,
  Sun,
  Moon,
  Check,
  ArrowRight,
  LoaderCircle,
} from 'lucide-react';
import './styles.css';
import { MealCard } from './components/MealCard.jsx';
import { ShoppingSection } from './components/ShoppingSection.jsx';
import { TodaysModeWidget } from './components/TodaysModeWidget.jsx';
import { CookbookBar } from './components/CookbookBar.jsx';
import {
  defaultPreferences,
  loadWeekState,
  persistWeekState,
} from './utils/persistence.js';

const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday'];
const empty = () =>
  days.map((day) => ({
    day,
    dish_name: '',
    ingredients: [],
    toddler_tip: '',
    parser_note: '',
  }));

function monday() {
  const d = new Date();
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

async function api(url, method = 'GET', body) {
  const r = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const d = await r.json();
  if (!r.ok) {
    throw new Error(
      typeof d.detail === 'string'
        ? d.detail
        : Array.isArray(d.detail)
          ? d.detail.map((e) => e.msg).join('; ')
          : 'Request failed.',
    );
  }
  return d;
}

function mergePreferences(serverPrefs, week) {
  const local = loadWeekState(week)?.preferences;
  return { ...defaultPreferences(), ...serverPrefs, ...local };
}

function App() {
  const [week, setWeek] = useState(monday());
  const [meals, setMeals] = useState(empty);
  const [revision, setRevision] = useState(0);
  const [loadedWeek, setLoadedWeek] = useState(monday());
  const [checked, setChecked] = useState([]);
  const [shopping, setShopping] = useState(null);
  const [preferences, setPreferences] = useState(defaultPreferences());
  const [history, setHistory] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [dirty, setDirty] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [intel, setIntel] = useState({});
  const [liveIntel, setLiveIntel] = useState(null);
  const [liveDeals, setLiveDeals] = useState({});
  const [target, setTarget] = useState(0);
  const [dark, setDark] = useState(() => localStorage.getItem('cv-theme') === 'dark');

  useEffect(() => {
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    localStorage.setItem('cv-theme', dark ? 'dark' : 'light');
  }, [dark]);

  useEffect(() => {
    api('/api/meals/history')
      .then((d) => {
        setHistory(d.past_meals);
      })
      .catch((e) => setError(e.message));
  }, []);

  async function work(fn) {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      await fn();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function load(value = week) {
    await work(async () => {
      const d = await api(`/api/canvas?week_start=${value}`);
      setWeek(value);
      setLoadedWeek(value);
      setMeals(
        d.meals.length
          ? days.map((day) => d.meals.find((m) => m.day === day) || { day, dish_name: '', ingredients: [], toddler_tip: '', parser_note: '' })
          : empty(),
      );
      setRevision(d.revision);
      setChecked(d.checked || []);
      setShopping(d.shopping);
      setPreferences(mergePreferences(d.preferences, value));
      setDirty(false);
      setIntel({});
    });
  }

  useEffect(() => {
    load();
  }, []);

  function update(i, patch) {
    setMeals((ms) => ms.map((m, j) => (i === j ? { ...m, ...patch } : m)));
    setDirty(true);
    persistWeekState(week, { mealsDraft: true });
  }

  async function save(nextChecked = checked, nextPreferences = preferences) {
    await work(async () => {
      if (week !== loadedWeek) {
        throw new Error('Load the selected week before saving or changing shopping checks.');
      }
      const d = await api('/api/canvas', 'PUT', {
        week_start: week,
        revision,
        meals,
        checked: nextChecked,
        preferences: nextPreferences,
      });
      setRevision(d.revision);
      setShopping(d.shopping);
      setChecked(d.checked);
      setPreferences(mergePreferences(d.preferences, week));
      persistWeekState(week, { preferences: d.preferences, checked: d.checked });
      setDirty(false);
      setMessage('Four dinners confirmed. Your shopping list is saved.');
      const h = await api('/api/meals/history');
      setHistory(h.past_meals);
    });
  }

  async function toggle(id) {
    const next = checked.includes(id) ? checked.filter((k) => k !== id) : [...checked, id];
    setChecked(next);
    persistWeekState(week, { checked: next });
    await save(next);
  }

  function mealSlotEmpty(meal) {
    return !meal.dish_name?.trim();
  }

  function nextEmptyDayIndex(list, afterIndex) {
    for (let step = 1; step <= list.length; step += 1) {
      const idx = (afterIndex + step) % list.length;
      if (mealSlotEmpty(list[idx])) return idx;
    }
    return null;
  }

  async function parse(i, name = meals[i].dish_name, { advanceDay } = {}) {
    await work(async () => {
      const d = await api('/api/meals/parse-ingredients', 'POST', { dish_name: name });
      let nextMeals;
      setMeals((ms) => {
        nextMeals = ms.map((m, j) => (i === j ? { ...d, day: m.day } : m));
        return nextMeals;
      });
      if (advanceDay && nextMeals) {
        const slot = nextEmptyDayIndex(nextMeals, i);
        if (slot != null) setTarget(slot);
      }
      setDirty(true);
      persistWeekState(week, { mealsDraft: true });
      setMessage('Suggestions added. Edit ingredients, amounts and toddler notes to fit your meal.');
    });
  }

  async function patchPreferences(patch) {
    const next = { ...preferences, ...patch };
    if (patch.pack_lunch) next.pack_lunch = patch.pack_lunch;
    setPreferences(next);
    persistWeekState(week, { preferences: next });
    const mealsReady =
      week === loadedWeek &&
      !dirty &&
      meals.every((m) => m.dish_name.trim() && m.ingredients.every((x) => x.name.trim() && Number(x.quantity) > 0));
    if (mealsReady) {
      await save(checked, next);
    }
  }

  function onPackLunchChange(index, value) {
    const pack_lunch = [...(preferences.pack_lunch || defaultPreferences().pack_lunch)];
    pack_lunch[index] = value;
    patchPreferences({ pack_lunch });
  }

  const storeMode = !!preferences.store_mode;
  const canvasHidden = storeMode;

  return (
    <div className="page">
      <header>
        <a href="/" className="brand">
          <span>
            <Sprout size={25} />
          </span>
          cleanviet
          <small>the family meal canvas</small>
        </a>
        <div className="header-actions">
          <span className="local">● Your local kitchen</span>
          <button
            type="button"
            className="icon"
            onClick={() => setDark(!dark)}
            aria-label={dark ? 'Use light mode' : 'Use dark mode'}
          >
            {dark ? <Sun size={19} /> : <Moon size={19} />}
          </button>
        </div>
      </header>
      <main>
        <section className="intro">
          <div className="eyebrow">LESS PLANNING. MORE LIVING.</div>
          <h1>Four nights. Anything you’re craving.</h1>
          <p>
            A Vietnamese soup, a favorite pasta, a quick salmon dinner. Make this week yours.
          </p>
          <div className="week-controls">
            <label>
              Week of{' '}
              <input type="date" value={week} onChange={(e) => setWeek(e.target.value)} />
            </label>
            <button type="button" onClick={() => load()} disabled={busy}>
              Load week
            </button>
            <span>Friday gathering · Weekends out</span>
          </div>
        </section>

        <TodaysModeWidget
          meals={meals}
          preferences={preferences}
          onPreferencesChange={patchPreferences}
        />

        {error && (
          <div className="alert error" role="alert">
            {error}
            <button type="button" className="icon" aria-label="Dismiss error" onClick={() => setError('')}>
              <X size={17} />
            </button>
          </div>
        )}
        {message && (
          <div className="alert" role="status">
            <Check size={17} />
            {message}
          </div>
        )}

        <div className="favorite-tools inline-target">
          <label>
            Add to{' '}
            <select value={target} onChange={(e) => setTarget(Number(e.target.value))}>
              {days.map((day, i) => (
                <option key={day} value={i}>
                  {day}
                </option>
              ))}
            </select>
          </label>
        </div>
        <CookbookBar
          target={target}
          days={days}
          busy={busy}
          onApplyMeal={(payload) =>
            work(async () => {
              let meal = payload;
              if (payload.parseName) {
                meal = await api('/api/meals/parse-ingredients', 'POST', {
                  dish_name: payload.parseName,
                });
              }
              let nextMeals;
              setMeals((ms) => {
                nextMeals = ms.map((m, j) =>
                  target === j ? { ...meal, day: m.day } : m,
                );
                return nextMeals;
              });
              const slot = nextMeals ? nextEmptyDayIndex(nextMeals, target) : null;
              if (slot != null) setTarget(slot);
              setDirty(true);
              persistWeekState(week, { mealsDraft: true });
              setMessage('Dish added. Review ingredients before confirming.');
            })
          }
        />

        {!canvasHidden && (
          <>
            <div className="canvas-heading">
              <h2>Your dinner canvas</h2>
              <span>Family dinner · 2 adults + a little explorer</span>
            </div>
            <section className="canvas">
              {meals.map((meal, i) => (
                <MealCard
                  key={meal.day}
                  meal={meal}
                  index={i}
                  busy={busy}
                  leanMode={preferences.lean_mode}
                  packLunch={preferences.pack_lunch}
                  onUpdate={(patch) => update(i, patch)}
                  onParse={() => parse(i)}
                  onPackLunchChange={onPackLunchChange}
                />
              ))}
            </section>
            <datalist id="past-meals">
              {history.map((h) => (
                <option key={h} value={h} />
              ))}
            </datalist>
            <div className="confirm-bar">
              <p>
                {week !== loadedWeek
                  ? 'Load the selected week before editing or confirming it.'
                  : dirty
                    ? 'You have unsaved changes. Confirm to update the shopping list.'
                    : 'Choose four dinners, review the suggestions, then confirm.'}
                <small>
                  Commute badges are helpful reminders. No meal is blocked by cuisine, timing or
                  repetition.
                </small>
              </p>
              <button
                type="button"
                className="primary"
                disabled={
                  busy ||
                  week !== loadedWeek ||
                  meals.some(
                    (m) =>
                      !m.dish_name.trim() ||
                      m.ingredients.some((x) => !x.name.trim() || !(Number(x.quantity) > 0)),
                  )
                }
                onClick={() => save()}
              >
                {busy ? <LoaderCircle size={17} className="spin" /> : <ShoppingBag size={17} />}{' '}
                Confirm 4 dishes <ArrowRight size={16} />
              </button>
            </div>
          </>
        )}

        <ShoppingSection
          shopping={shopping}
          dirty={dirty}
          busy={busy}
          query={query}
          setQuery={setQuery}
          results={results}
          liveIntel={liveIntel}
          liveDeals={liveDeals}
          onSyncFlyers={() =>
            work(async () => {
              const d = await api('/api/prices/sync-flyers', 'POST');
              setLiveDeals(d.deals || {});
              setMessage('OC flyer prices synced (12h cache).');
            })
          }
          onSearch={() =>
            work(async () => {
              const d = await api(`/api/stores/intel?q=${encodeURIComponent(query)}`);
              setResults(d.matches);
              setLiveIntel(d.live || null);
            })
          }
          intel={intel}
          onReview={(id) =>
            work(async () => {
              const d = await api(`/api/stores/${id}/community`);
              setIntel((s) => ({ ...s, [id]: d }));
            })
          }
          onToggleItem={toggle}
          preferences={preferences}
          onHomemadeBroth={(value) => patchPreferences({ homemade_broth: value })}
          storeMode={storeMode}
        />

        <footer>
          <Sprout size={16} /> A little structure. Plenty of freedom.
          <span>CleanViet · Your family, your food.</span>
        </footer>
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);

const localSplitUi =
  import.meta.env.DEV || location.port === '4173' || location.port === '5173';

if ('serviceWorker' in navigator) {
  if (localSplitUi) {
    navigator.serviceWorker.getRegistrations().then((regs) => {
      regs.forEach((r) => r.unregister());
    });
  } else if (import.meta.env.PROD) {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  }
}
