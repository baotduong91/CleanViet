BEGIN;
SELECT pg_advisory_xact_lock(20261103);
CREATE TABLE IF NOT EXISTS meal_canvases (week_start date PRIMARY KEY CHECK(extract(isodow FROM week_start)=1),revision integer NOT NULL DEFAULT 1,payload jsonb NOT NULL CHECK(jsonb_typeof(payload)='object'),updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS meal_history (dish_key text PRIMARY KEY,dish_name text NOT NULL,payload jsonb NOT NULL CHECK(jsonb_typeof(payload)='object'),updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS cookbook_saved (dish_key text PRIMARY KEY,dish_name text NOT NULL,payload jsonb NOT NULL CHECK(jsonb_typeof(payload)='object'),source text NOT NULL DEFAULT 'import',updated_at timestamptz NOT NULL DEFAULT now());
COMMIT;
