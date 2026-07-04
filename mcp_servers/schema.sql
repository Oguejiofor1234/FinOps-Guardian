-- Schema definition for FinOps Guardian ERP Ledger
CREATE TABLE IF NOT EXISTS expenses (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    category VARCHAR(50) NOT NULL,
    expense_date DATE NOT NULL,
    has_receipt BOOLEAN DEFAULT FALSE,
    has_itinerary BOOLEAN DEFAULT FALSE,
    risk_level VARCHAR(20),
    tax_code VARCHAR(20),
    gl_code VARCHAR(20),
    cost_center VARCHAR(20),
    saving_insight TEXT,
    tax_deductibility TEXT,
    manager_decision VARCHAR(50),
    approval_status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for searching and duplicate checks
CREATE INDEX IF NOT EXISTS idx_expenses_duplicate_check ON expenses (title, amount, category, expense_date);
