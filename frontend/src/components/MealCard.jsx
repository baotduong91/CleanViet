import { Home, LoaderCircle, Plus, TrainFront, X } from 'lucide-react';
import { estimateMacros } from '../utils/workflow.js';

export function MealCard({
  meal,
  index,
  busy,
  leanMode,
  packLunch,
  onUpdate,
  onParse,
  onPackLunchChange,
}) {
  const macros = estimateMacros(meal.ingredients, {
    leanMode,
    packLunch: !!packLunch?.[index],
  });
  return (
    <article className="meal">
      <div className="day-title">
        <span className="day-number">0{index + 1}</span>
        <h2>{meal.day}</h2>
      </div>
      <p className="macro-pill">
        ~{macros.kcal} kcal · {macros.protein}g P · {macros.tier}
      </p>
      {leanMode && (
        <p className="lean-badge">
          Lean tweak: -25% carbs, +30% volume mushrooms/greens (-140 kcal)
        </p>
      )}
      <span className={`day-badge ${index === 2 ? 'wfh' : ''}`}>
        {index === 2 ? <Home size={12} /> : <TrainFront size={12} />}{' '}
        {index === 2 ? 'WFH · Flexible Prep' : 'Commute Day · Fast Prep / <20 mins'}
      </span>
      <label className="pack-lunch">
        <input
          type="checkbox"
          checked={!!packLunch?.[index]}
          onChange={(e) => onPackLunchChange(index, e.target.checked)}
        />
        🍱 Pack Tomorrow&apos;s Office Lunch
      </label>
      <label className="dish-label" htmlFor={`dish-${index}`}>
        What sounds good?
      </label>
      <textarea
        id={`dish-${index}`}
        value={meal.dish_name}
        maxLength={200}
        placeholder="Type any dish…"
        onChange={(e) => onUpdate({ dish_name: e.target.value })}
      />
      <input
        className="history-input"
        aria-label={`Past meal for ${meal.day}`}
        list="past-meals"
        placeholder="Or search past meals"
        onChange={(e) => {
          if (e.target.value) onUpdate({ dish_name: e.target.value });
        }}
      />
      <button
        className="parse-button"
        type="button"
        disabled={busy || !meal.dish_name.trim()}
        onClick={() => onParse()}
      >
        {busy ? <LoaderCircle size={14} className="spin" /> : <Plus size={14} />}{' '}
        Suggest ingredients
      </button>
      <div className="ingredients-title">
        GROCERY TAGS <span>{meal.ingredients.length}</span>
      </div>
      <div className="ingredient-list">
        {meal.ingredients.map((item, j) => (
          <div className="ingredient-row" key={j}>
            <input
              aria-label={`${meal.day} ingredient ${j + 1}`}
              value={item.name}
              maxLength={120}
              onChange={(e) =>
                onUpdate({
                  ingredients: meal.ingredients.map((x, k) =>
                    j === k
                      ? { ...x, name: e.target.value, ingredient_id: null }
                      : x,
                  ),
                })
              }
            />
            <input
              type="number"
              min="0.001"
              max="1000"
              step="0.001"
              aria-label={`${meal.day} quantity ${j + 1}`}
              value={item.quantity}
              onChange={(e) =>
                onUpdate({
                  ingredients: meal.ingredients.map((x, k) =>
                    j === k ? { ...x, quantity: e.target.value } : x,
                  ),
                })
              }
            />
            <select
              aria-label={`${meal.day} unit ${j + 1}`}
              value={item.unit}
              onChange={(e) =>
                onUpdate({
                  ingredients: meal.ingredients.map((x, k) =>
                    j === k ? { ...x, unit: e.target.value } : x,
                  ),
                })
              }
            >
              {['lb', 'L', 'each'].map((u) => (
                <option key={u}>{u}</option>
              ))}
            </select>
            <button
              type="button"
              className="icon"
              aria-label={`Remove ${item.name}`}
              onClick={() =>
                onUpdate({
                  ingredients: meal.ingredients.filter((_, k) => k !== j),
                })
              }
            >
              <X size={12} />
            </button>
          </div>
        ))}
      </div>
      <button
        type="button"
        className="add-item"
        onClick={() =>
          onUpdate({
            ingredients: [
              ...meal.ingredients,
              { name: '', quantity: 1, unit: 'lb', ingredient_id: null },
            ],
          })
        }
      >
        <Plus size={13} /> Add ingredient manually
      </button>
      <p className="parser-note">
        {meal.parser_note || 'Any cuisine is welcome. Suggestions are editable.'}
      </p>
      <div className="toddler">
        <label htmlFor={`tip-${index}`}>LITTLE BOWL, SAME DINNER</label>
        <textarea
          id={`tip-${index}`}
          value={meal.toddler_tip}
          maxLength={1000}
          placeholder="Your toddler tweak…"
          onChange={(e) => onUpdate({ toddler_tip: e.target.value })}
        />
      </div>
    </article>
  );
}
