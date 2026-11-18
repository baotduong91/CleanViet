import test from 'node:test';
import assert from 'node:assert/strict';
import { searchAllowed, localSuggestions, cacheSuggestions, cachedSuggestions, initialSuggestions } from './recipeSearch.js';

test('strict word gate and instant accented local search', () => {
  assert.equal(searchAllowed('canh'), false);
  assert.equal(searchAllowed('canh c'), false);
  assert.equal(searchAllowed('  canh   chua '), true);
  assert.ok(localSuggestions('canh').length);
  assert.deepEqual(localSuggestions('gà hấp'), localSuggestions('ga hap'));
});

test('cache normalizes accents and never makes one-word lookup live', () => {
  const rows = [{ title_clean: 'Gà hấp', source_url: 'https://hungryhuy.com/ga/' }];
  cacheSuggestions('gà hấp', rows);
  assert.equal(cachedSuggestions(' GA   HAP '), rows);
  assert.equal(initialSuggestions('ga hap'), rows);
  cacheSuggestions('canh', rows);
  assert.notEqual(initialSuggestions('canh'), rows);
});

test('LRU bounds memory and keeps recently used entries', () => {
  for (let i = 0; i < 128; i++) cacheSuggestions('recipe ' + i, []);
  cachedSuggestions('recipe 0');
  cacheSuggestions('recipe newest', []);
  assert.equal(cachedSuggestions('recipe 1'), null);
  assert.deepEqual(cachedSuggestions('recipe 0'), []);
});
