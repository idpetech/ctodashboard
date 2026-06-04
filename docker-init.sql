-- Initialize ctodashboard schema in local PostgreSQL
-- This matches the Railway production setup exactly

CREATE SCHEMA IF NOT EXISTS ctodashboard;
COMMENT ON SCHEMA ctodashboard IS 'CTO Dashboard application data - local development';

-- Grant permissions
GRANT USAGE ON SCHEMA ctodashboard TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA ctodashboard TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA ctodashboard TO postgres;