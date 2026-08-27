-- Personal Budget Tracker — Database Schema
-- Matches Budget_App_Project_Spec.docx Section 5 exactly.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT UNIQUE NOT NULL,
    soft_limit  REAL NOT NULL,
    hard_limit  REAL NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    date               TEXT NOT NULL,
    amount             REAL NOT NULL,
    type               TEXT NOT NULL
                           CHECK(type IN ('expense', 'income')),
    category_id        INTEGER REFERENCES categories(id),
    description        TEXT,
    funding_source     TEXT NOT NULL DEFAULT 'regular'
                           CHECK(funding_source IN ('regular', 'savings', 'emergency_fund')),
    recurring_id       INTEGER REFERENCES recurring_transactions(id),
    status             TEXT NOT NULL DEFAULT 'confirmed'
                           CHECK(status IN ('confirmed', 'pending_approval'))
);

CREATE TABLE IF NOT EXISTS savings (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    month                  TEXT UNIQUE NOT NULL,   -- 'YYYY-MM'
    rollover_amount        REAL NOT NULL,
    emergency_fund_delta   REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    key    TEXT UNIQUE NOT NULL,
    value  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS emergency_fund (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    balance       REAL NOT NULL DEFAULT 0,
    last_updated  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS emergency_fund_log (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    date    TEXT NOT NULL,
    amount  REAL NOT NULL,               -- positive = deposit, negative = withdrawal
    source  TEXT NOT NULL
                CHECK(source IN ('monthly_rollover', 'manual')),
    note    TEXT
);

CREATE TABLE IF NOT EXISTS recurring_transactions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id         INTEGER REFERENCES categories(id),
    amount              REAL NOT NULL,
    description         TEXT,
    type                TEXT NOT NULL
                            CHECK(type IN ('expense', 'income')),
    frequency           TEXT NOT NULL
                            CHECK(frequency IN ('daily', 'monthly', 'yearly', 'custom')),
    interval_days       INTEGER,          -- only used when frequency = 'custom'
    next_due_date       TEXT NOT NULL,
    active              INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
