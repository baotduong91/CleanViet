export const defaultPreferences = () => ({
  lean_mode: false,
  pack_lunch: [false, false, false, false],
  homemade_broth: false,
  store_mode: false,
});

export function storageKey(week) {
  return `cleanviet_state_${week}`;
}

export function loadWeekState(week) {
  try {
    const raw = localStorage.getItem(storageKey(week));
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function persistWeekState(week, slice) {
  const prev = loadWeekState(week) || {};
  localStorage.setItem(
    storageKey(week),
    JSON.stringify({ ...prev, ...slice, updatedAt: Date.now() }),
  );
}
