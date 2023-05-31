-- name: create-schema
CREATE SCHEMA IF NOT EXISTS waterUsage;

-- name: check-area-keys
SELECT key
FROM geodata.shapes
WHERE key = ANY($1);

-- name: get-all-consumer-groups
SELECT external_identifier
FROM water_usage.usage_types;

-- name: check-consumer-groups
SELECT external_identifier
FROM water_usage.usage_types
WHERE external_identifier = ANY($1);