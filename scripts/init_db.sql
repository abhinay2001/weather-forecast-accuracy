-- runs automatically when the warehouse-db container first starts

CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.forecast_daily (
    id                              BIGSERIAL PRIMARY KEY,
    city                            TEXT NOT NULL,
    state                           TEXT NOT NULL,
    latitude                        DOUBLE PRECISION NOT NULL,
    longitude                       DOUBLE PRECISION NOT NULL,
    forecast_made_on                DATE NOT NULL,
    target_date                     DATE NOT NULL,
    temperature_2m_max              DOUBLE PRECISION,
    temperature_2m_min              DOUBLE PRECISION,
    precipitation_sum               DOUBLE PRECISION,
    precipitation_probability_max   DOUBLE PRECISION,
    weather_code                    INTEGER,
    inserted_at                     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (city, forecast_made_on, target_date)
);

CREATE TABLE IF NOT EXISTS raw.actuals_daily (
    id                   BIGSERIAL PRIMARY KEY,
    city                 TEXT NOT NULL,
    state                TEXT NOT NULL,
    latitude             DOUBLE PRECISION NOT NULL,
    longitude            DOUBLE PRECISION NOT NULL,
    target_date          DATE NOT NULL,
    temperature_2m_max   DOUBLE PRECISION,
    temperature_2m_min   DOUBLE PRECISION,
    precipitation_sum    DOUBLE PRECISION,
    weather_code         INTEGER,
    inserted_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (city, target_date)
);

CREATE INDEX IF NOT EXISTS idx_forecast_target_date ON raw.forecast_daily (target_date);
CREATE INDEX IF NOT EXISTS idx_actuals_target_date ON raw.actuals_daily (target_date);
