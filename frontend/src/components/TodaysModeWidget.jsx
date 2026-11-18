import { ChevronDown } from 'lucide-react';
import { useState } from 'react';
import {
  isKitchenHandoffWindow,
  prepChecklist,
  tonightMealIndex,
} from '../utils/workflow.js';

export function TodaysModeWidget({ meals, preferences, onPreferencesChange }) {
  const [open, setOpen] = useState(true);
  const handoff = isKitchenHandoffWindow();
  const index = tonightMealIndex();
  const meal = index != null ? meals[index] : null;
  const lunch = officeLunchBadge(preferences?.pack_lunch);

  return (
    <section className={`today-widget ${handoff ? 'today-widget-handoff' : ''}`}>
      <button
        type="button"
        className="today-widget-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <div>
          <span className="eyebrow">Options</span>
          <strong>{handoff ? 'Tonight' : 'Meal options'}</strong>
          {lunch.count > 0 && (
            <span className="today-badge">
              Office lunches prepped: {lunch.count} (+${lunch.saved.toFixed(2)} saved vs
              takeout)
            </span>
          )}
        </div>
        <ChevronDown size={18} className={open ? 'chev-open' : ''} />
      </button>
      {open && (
        <div className="today-widget-body">
          <div className="today-actions">
            <button
              type="button"
              className={preferences?.store_mode ? 'toggle-on' : ''}
              onClick={() =>
                onPreferencesChange({ store_mode: !preferences?.store_mode })
              }
            >
              Store mode
            </button>
            <button
              type="button"
              className={preferences?.lean_mode ? 'toggle-on' : ''}
              onClick={() => onPreferencesChange({ lean_mode: !preferences?.lean_mode })}
            >
              Lean portions
            </button>
          </div>
          {handoff && meal?.dish_name?.trim() && (
            <article className="handoff-card">
              <h3>Tonight: {meal.day}</h3>
              <p className="handoff-dish">{meal.dish_name}</p>
              <ol>
                {prepChecklist(meal.dish_name).map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
              {meal.toddler_tip && (
                <div className="handoff-toddler">
                  <span>Toddler notes</span>
                  <p>{meal.toddler_tip}</p>
                </div>
              )}
            </article>
          )}
        </div>
      )}
    </section>
  );
}

function officeLunchBadge(packLunch) {
  const count = (packLunch || []).filter(Boolean).length;
  return { count, saved: count * 16 };
}
