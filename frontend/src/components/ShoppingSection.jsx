import { useState } from 'react';
import { ArrowRight, Search, ShoppingBag, X, ExternalLink } from 'lucide-react';

const money = (n) =>
  n == null
    ? 'Unpriced'
    : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n);

function dealForItem(item, liveDeals) {
  if (!item?.id || !liveDeals) return null;
  const key = item.id.split('|')[0];
  return liveDeals[key]?.label || liveDeals[key]?.merchant ? liveDeals[key] : null;
}

function itemUrl(item, deals) {
  const url = item.url || dealForItem(item, deals)?.url;
  return typeof url === 'string' && /^https?:\/\//i.test(url) ? url : null;
}

export function ShoppingSection({
  shopping,
  dirty,
  busy,
  query,
  setQuery,
  results,
  liveIntel,
  onSearch,
  onSyncFlyers,
  intel,
  onReview,
  onToggleItem,
  preferences,
  onHomemadeBroth,
  storeMode,
  liveDeals,
  flyerStatus,
  syncingFlyers,
}) {
  const [dismissedSync, setDismissedSync] = useState(null);
  const statusKey = flyerStatus?.synced_at || (flyerStatus?.unavailable ? 'unavailable' : 'never');
  return (
    <section className={`shopping ${storeMode ? 'shopping-store-mode' : ''}`}>
      <div className="section-heading">
        <h2>Shopping list</h2>
      </div>
      <div className="flyer-tools">
        <button type="button" disabled={busy} onClick={onSyncFlyers}>{syncingFlyers ? 'Syncing flyers…' : 'Sync OC flyers'}</button>
        {dismissedSync === statusKey && (
          <button type="button" onClick={() => setDismissedSync(null)}>Show sync status</button>
        )}
      </div>
      {dismissedSync !== statusKey && (
        <div className="flyer-status" role="status">
          <div>
            <strong>OC flyer status</strong>
            <p>{flyerStatus?.synced_at
              ? `Last check ${new Date(flyerStatus.synced_at).toLocaleString()} · ${flyerStatus.flyer_count || 0} flyer matches · ${flyerStatus.baseline_count || 0} baseline estimates. Flyer results may be cached up to 12 hours.`
              : flyerStatus?.unavailable ? 'Sync status unavailable. Try syncing again.' : 'No completed flyer sync recorded.'}</p>
          </div>
          <button type="button" className="icon" aria-label="Dismiss flyer status temporarily" onClick={() => setDismissedSync(statusKey)}><X size={16} /></button>
        </div>
      )}
      <form
        className="intel-search"
        onSubmit={(e) => {
          e.preventDefault();
          onSearch();
        }}
      >
        <Search size={19} />
        <input
          aria-label="Check Item / Supermarket Intel"
          value={query}
          maxLength={120}
          required
          placeholder="Ingredient in Vietnamese or English, e.g. thịt bò phi lê"
          onChange={(e) => setQuery(e.target.value)}
        />
        <button disabled={busy} type="submit">
          Check item <ArrowRight size={14} />
        </button>
      </form>
      {results && (
        <div className="search-results">
          {results.length ? (
            results.map((r) => (
              <div key={r.ingredient.id}>
                <strong>{r.ingredient.name}</strong>
                {r.ingredient.name_vi && <span>{r.ingredient.name_vi}</span>}
                <span>
                  {r.store.name} · {r.store.specialty}
                </span>
                <small>
                  {r.ingredient.local_price == null
                    ? 'Price unavailable. '
                    : `Estimate ${money(r.ingredient.local_price)} / ${r.ingredient.unit} vs. Weee! ${money(r.ingredient.weee_price)}. `}
                  {r.basis}
                </small>
                {liveIntel?.ingredient_id === r.ingredient.id && liveIntel?.deals?.length > 0 && (
                  <p className="live-deal-badge">
                    {liveIntel.deals[0].baseline_fallback
                      ? `Baseline ${money(liveIntel.deals[0].price)} (offline cache)`
                      : `Flyer: ${money(liveIntel.deals[0].price)} @ ${liveIntel.deals[0].merchant}`}
                  </p>
                )}
              </div>
            ))
          ) : (
            <p>
              No reliable specialty match. Compare your usual supermarket; add this item manually
              to any meal.
            </p>
          )}
        </div>
      )}
      {shopping ? (
        <>
          <div className="budget">
            <div>
              <span>Remaining</span>
              <strong>{money(shopping.estimated_cost)}</strong>
            </div>
            <div>
              <span>Weee! estimate</span>
              <strong>{money(shopping.estimated_weee)}</strong>
            </div>
            <div>
              <span>Difference</span>
              <strong>{money(shopping.estimated_savings)}</strong>
            </div>
          </div>
          <details className="basis"><summary>Estimate details{dirty ? ' · Save dishes to refresh' : ''}</summary><p>
            {shopping.basis}{' '}
            {shopping.unpriced_items > 0 &&
              `${shopping.unpriced_items} custom item(s) are unpriced and excluded from totals.`}{' '}
            {dirty && 'The list reflects your last confirmed dishes.'}
          </p></details>
          <div className="routes">
            {shopping.routes.filter((r) => r.stores.length).map((route, i) => (
              <section className="route" key={route.id}>
                <div className="route-header">
                  <span>0{i + 1}</span>
                  <div>
                    <h3>{route.name}</h3>
                    <p>{route.note}</p>
                  </div>
                </div>
                {route.stores.length ? (
                  route.stores.map((store) => (
                    <article className="store" key={store.id}>
                      <h4>{store.name}</h4>
                      {store.cooler_reminder && (
                        <p className="cooler-tag">{store.cooler_reminder}</p>
                      )}
                      <p>{store.specialty}</p>
                      {store.query && (
                        <a className="store-review-link" href={intel[store.id]?.url || `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(store.query)}`} target="_blank" rel="noreferrer">View store reviews <ExternalLink size={12} /></a>
                      )}
                      {!storeMode && (
                        <div className="intel-badge">
                          <span className="intel-label">
                            COMMUNITY INTEL ·{' '}
                            {intel[store.id]?.status === 'live'
                              ? 'GOOGLE MAPS REVIEW SAMPLE'
                              : 'SPECIALTY HEURISTIC'}
                          </span>
                          <p>
                            {intel[store.id]?.summary ||
                              'Household specialty recommendation. Current quality, best price and stock are unverified.'}
                          </p>
                          {store.query && (
                            <button type="button" disabled={busy} onClick={() => onReview(store.id)}>
                              Load review summary <ArrowRight size={12} />
                            </button>
                          )}
                          {intel[store.id]?.place_name && (
                            <p>
                              {intel[store.id].place_name} · {intel[store.id].address}{' '}
                              <a href={intel[store.id].url} target="_blank" rel="noreferrer">
                                Google Maps ↗
                              </a>
                            </p>
                          )}
                          {intel[store.id]?.reviews?.map((r, j) => (
                            <div className="review" key={j}>
                              <a href={r.author_url || r.url} target="_blank" rel="noreferrer">
                                {r.author}
                              </a>{' '}
                              · {r.published_at.slice(0, 10)}
                              <p>“{r.excerpt}”</p>
                              <a href={r.url} target="_blank" rel="noreferrer">
                                Read review ↗
                              </a>
                            </div>
                          ))}
                        </div>
                      )}
                      <div className="shop-items">
                        {store.items.map((item) => (
                          <div key={item.id}>
                            {item.broth_arbitrage_eligible && (
                              <label className="broth-toggle">
                                <input
                                  type="checkbox"
                                  checked={!!preferences?.homemade_broth}
                                  onChange={(e) => onHomemadeBroth(e.target.checked)}
                                />
                                Use homemade broth
                                {shopping.homemade_broth_savings &&
                                  ` (-$${shopping.homemade_broth_savings})`}
                              </label>
                            )}
                            <div className="shop-item-actions">
                            <button
                              type="button"
                              aria-pressed={item.checked}
                              className={`shop-item ${item.checked ? 'covered' : ''}`}
                              disabled={busy || dirty}
                              onClick={() => onToggleItem(item.id)}
                            >
                              <span className={`shop-check ${item.checked ? 'shop-check-on' : ''}`} />
                              <span>
                                {item.name}
                                <small>
                                  {Number(item.quantity)} {item.unit}
                                </small>
                              </span>
                              <strong>{money(item.estimated_cost)}</strong>
                            </button>
                            {itemUrl(item, liveDeals) && (
                              <a className="item-source" href={itemUrl(item, liveDeals)} target="_blank" rel="noreferrer" aria-label={`View source for ${item.name}`} title="View item or flyer">
                                <ExternalLink size={15} />
                              </a>
                            )}
                            </div>
                            {dealForItem(item, liveDeals)?.label && (
                              <p className="live-deal-badge">{dealForItem(item, liveDeals).label}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </article>
                  ))
                ) : (
                  <p className="empty-route">No items needed for this run.</p>
                )}
              </section>
            ))}
          </div>
        </>
      ) : (
        <div className="empty-shopping">
          <ShoppingBag size={30} />
          <h3>No shopping list yet.</h3>
          <p>Save dishes to generate a shopping list.</p>
        </div>
      )}
    </section>
  );
}
