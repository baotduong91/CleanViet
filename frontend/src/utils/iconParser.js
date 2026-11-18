export const ICON_RULES = [
  [['muc', 'bach tuoc', 'squid', 'octopus'], '🦑', 'Seafood'],
  [['tom', 'cua', 'ghe', 'ngheu', 'hen', 'shrimp', 'crab', 'shellfish'], '🦐', 'Seafood'],
  [['ca', 'cha ca', 'salmon', 'tilapia', 'catfish', 'fish'], '🐟', 'Clean Fish'],
  [['bun', 'pho', 'hu tieu', 'mien', 'banh canh'], '🍜', 'Noodle Bowl'],
  [['sup', 'nui', 'chao', 'canh'], '🥣', 'Clear Soup / Canh'],
  [['ga', 'vit', 'chicken', 'duck'], '🍗', 'Poultry'],
  [['bo', 'thit', 'suon', 'beef', 'pork'], '🥩', 'Savory Meat'],
  [['dau hu', 'nam', 'rau', 'bau', 'bi', 'cai', 'tofu'], '🥬', 'Greens & Umami'],
  [['pasta', 'bolognese', 'spaghetti', 'macaroni'], '🍝', 'Pasta'],
];

export function normalizeDiacritics(value = '') {
  return value.toLowerCase().replace(/đ/g, 'd').normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9 ]/g, ' ')
    .replace(/\s+/g, ' ').trim();
}

export function resolveDishIcon(title) {
  const text = ` ${normalizeDiacritics(title)} `;
  for (const [tokens, icon, category_label] of ICON_RULES) {
    if (tokens.some((token) => text.includes(` ${token} `))) return { icon, category_label };
  }
  return { icon: '🍲', category_label: 'Home Dish' };
}
