-- Demo schema. A simplified, synthetic stand-in for a payments database: it has the columns the
-- monitors need and nothing else.
CREATE TABLE IF NOT EXISTS transactions (
    id               BIGSERIAL PRIMARY KEY,
    request_id       UUID        NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    created_at       TIMESTAMPTZ NOT NULL,
    provider         TEXT        NOT NULL,
    direction        TEXT        NOT NULL CHECK (direction IN ('MONEY_IN', 'MONEY_OUT')),
    status           TEXT        NOT NULL CHECK (status IN ('SUCCESS', 'FAILED', 'PENDING')),
    amount           NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    response_code    TEXT        NOT NULL,
    response_message TEXT        NOT NULL
);

CREATE INDEX IF NOT EXISTS transactions_created_at_idx ON transactions (created_at);
CREATE INDEX IF NOT EXISTS transactions_provider_created_at_idx
    ON transactions (provider, created_at);
