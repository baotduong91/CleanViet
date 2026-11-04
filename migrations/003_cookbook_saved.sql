CREATE TABLE IF NOT EXISTS cookbook_saved (
  dish_key text PRIMARY KEY,
  dish_name text NOT NULL,
  payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
  source text NOT NULL DEFAULT 'import',
  updated_at timestamptz NOT NULL DEFAULT now()
);
