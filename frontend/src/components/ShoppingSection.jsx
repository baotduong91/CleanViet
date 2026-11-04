import { ArrowRight, Search, ShoppingBag } from 'lucide-react';

const money = (n) =>
  n == null
    ? 'Unpriced'
    : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n);

function dealForItem(item, liveDeals) {
  if (!item?.id || !liveDeals) return null;
  const key = item.id.split('|')[0];
  return liveDeals[key]?.label || liveDeals[key]?.merchant ? liveDeals[key] : null;
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
}) {
  return (
    <section className={`shopping ${storeMode ? 'shopping-store-mode' : ''}`}>
      <div className="section-heading">
        <div className="eyebrow">A SMARTER RUN, A LIGHTER BASKET</div>
        <h2>Where to shop this week</h2>
        <p>
          Specialty picks for Little Saigon, bulk staples closer to home, and a cupboard check
          first.
        </p>
        {shopping && (
          <button type="button" className="sync-flyers" disabled={busy} onClick={onSyncFlyers}>
            🔄 Sync Live OC Flyer Prices
          </button>
        )}
      </div>
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
          placeholder="Check Item / Supermarket Intel — try Mực trứng or Nấm đùi gà"
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
                <span>
                  {r.store.name} · {r.store.specialty}
                </span>
                <small>
                  Estimated {money(r.ingredient.local_price)} / {r.ingredient.unit} vs. Weee!{' '}
                  {money(r.ingredient.weee_price)}. {r.basis}
                </small>
                {liveIntel?.deals?.length > 0 && (
                  <p className="live-deal-badge">
                    {liveIntel.deals[0].baseline_fallback
                      ? `Baseline ${money(liveIntel.deals[0].price)} (offline cache)`
                      : `🔥 Live Flyer: ${money(liveIntel.deals[0].price)} @ ${liveIntel.deals[0].merchant}`}
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
              <span>ESTIMATED REMAINING INGREDIENTS</span>
              <strong>{money(shopping.estimated_cost)}</strong>
            </div>
            <div>
              <span>COMPARABLE WEEE! QUANTITIES</span>
              <strong>{money(shopping.estimated_weee)}</strong>
            </div>
            <div>
              <span>ESTIMATED DIFFERENCE</span>
              <strong>{money(shopping.estimated_savings)}</strong>
            </div>
          </div>
          <p className="basis">
            {shopping.basis}{' '}
            {shopping.unpriced_items > 0 &&
              `${shopping.unpriced_items} custom item(s) are unpriced and excluded from totals.`}{' '}
            {dirty && 'The list reflects your last confirmed dishes.'}
          </p>
          <div className="routes">
            {shopping.routes.map((route, i) => (
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
                              Check recent reviews <ArrowRight size={12} />
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
                                🍲 Make broth from chicken poaching / shrimp shells
                                {shopping.homemade_broth_savings &&
                                  ` (-$${shopping.homemade_broth_savings})`}
                              </label>
                            )}
                            <button
                              type="button"
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
          <h3>Your next grocery run starts here.</h3>
          <p>Confirm your four dishes to combine ingredients and find the right specialty stops.</p>
        </div>
      )}
    </section>
  );
}
