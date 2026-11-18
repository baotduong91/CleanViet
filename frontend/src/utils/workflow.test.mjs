import { test } from 'node:test';
import assert from 'node:assert/strict';
import { estimateMacros } from './workflow.js';

test('packed lunch scales protein and carbs before dividing servings', () => {
  assert.deepEqual(estimateMacros([{ ingredient_id: 'salmon', quantity: 1 }], { packLunch: true }),
    { kcal: 266, protein: 39, tier: 'Lean' });
});

test('tiers use unrounded serving calories at both boundaries', () => {
  for (const [kcal, tier] of [[549.6, 'Lean'], [550, 'Balanced'], [750, 'Balanced'], [750.4, 'Hearty']]) {
    assert.equal(estimateMacros([{ ingredient_id: 'rice', quantity: kcal * 2.5 / 820 }]).tier, tier);
  }
});

test('lean and lunch preferences compose without mutating ingredients', () => {
  const ingredients = [
    { ingredient_id: 'bun', quantity: 1 },
    { ingredient_id: 'carrot', quantity: 1 },
  ];
  const result = estimateMacros(ingredients, { leanMode: true, packLunch: true });
  assert.equal(result.kcal, Math.round((820 * 1.5 * 0.75 + 120 * 1.3) / 3.5));
  assert.equal(ingredients[0].quantity, 1);
});
