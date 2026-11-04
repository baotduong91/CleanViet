const PROTEIN_KCAL_PER_LB = 620;
const PROTEIN_G_PER_LB = 92;
const CARB_KCAL_PER_LB = 820;
const CARB_G_PER_LB = 180;
const VEG_KCAL_PER_LB = 120;
const VEG_G_PER_LB = 8;
const DEFAULT_KCAL = 420;
const DEFAULT_PROTEIN = 28;

const PROTEIN_IDS = new Set([
  'chicken',
  'tilapia',
  'salmon',
  'shrimp',
  'pork',
  'fish_paste',
  'squid',
  'beef',
  'whole_fish',
]);
const CARB_IDS = new Set(['rice', 'nui', 'pasta', 'bun']);
const LEAN_CARB_IDS = new Set(['rice', 'nui', 'pasta', 'bun']);
const LEAN_VOLUME_IDS = new Set(['king_oyster', 'broccoli', 'greens']);

export function normalizeDish(name) {
  return (name || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

export function isKitchenHandoffWindow(now = new Date()) {
  const day = now.getDay();
  if (day < 1 || day > 4) return false;
  const minutes = now.getHours() * 60 + now.getMinutes();
  return minutes >= 16 * 60 && minutes <= 19 * 60 + 30;
}

export function tonightMealIndex(now = new Date()) {
  const day = now.getDay();
  if (day >= 1 && day <= 4) return day - 1;
  return null;
}

export function prepChecklist(dishName) {
  const n = normalizeDish(dishName);
  if (n.includes('salmon') || n.includes('tilapia') || n.includes('fish')) {
    return [
      '1. Start rice / water boil',
      '2. Air fry or poach protein (12 mins)',
      '3. Steam/cut toddler veggies',
    ];
  }
  if (n.includes('pasta') || n.includes('bolognese')) {
    return [
      '1. Boil pasta water and soften carrots',
      '2. Brown beef while sauce simmers (15 mins)',
      '3. Set aside plain toddler noodles + mild scoop',
    ];
  }
  if (n.includes('bun quay')) {
    return [
      '1. Simmer broth and soak noodles',
      '2. Poach fish/shrimp paste balls (8 mins)',
      '3. Keep muối ớt tắc off the toddler bowl',
    ];
  }
  return [
    '1. Start rice / water boil',
    '2. Air fry or poach protein (12 mins)',
    '3. Steam/cut toddler veggies',
  ];
}

export function estimateMacros(ingredients, { leanMode, packLunch } = {}) {
  const divisor = packLunch ? 3.5 : 2.5;
  let kcal = 0;
  let protein = 0;
  for (const item of ingredients || []) {
    let qty = Number(item.quantity) || 0;
    const id = item.ingredient_id;
    if (leanMode && LEAN_CARB_IDS.has(id)) qty *= 0.75;
    if (leanMode && LEAN_VOLUME_IDS.has(id)) qty *= 1.3;
    if (PROTEIN_IDS.has(id)) {
      kcal += qty * PROTEIN_KCAL_PER_LB;
      protein += qty * PROTEIN_G_PER_LB;
    } else if (CARB_IDS.has(id)) {
      kcal += qty * CARB_KCAL_PER_LB;
      protein += qty * 12;
    } else if (LEAN_VOLUME_IDS.has(id)) {
      kcal += qty * VEG_KCAL_PER_LB;
      protein += qty * VEG_G_PER_LB;
    }
  }
  if (!ingredients?.length) {
    kcal = DEFAULT_KCAL * divisor;
    protein = DEFAULT_PROTEIN * divisor;
  }
  kcal = Math.round(kcal / divisor);
  protein = Math.round(protein / divisor);
  const tier = kcal > 750 ? 'Hearty' : kcal >= 550 ? 'Balanced' : 'Lean';
  return { kcal, protein, tier };
}

export function officeLunchSavings(packLunch) {
  const count = (packLunch || []).filter(Boolean).length;
  return { count, saved: count * 16 };
}
