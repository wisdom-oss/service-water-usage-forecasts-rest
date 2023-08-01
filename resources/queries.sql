-- name: create-schema
CREATE SCHEMA IF NOT EXISTS water_usage;

-- name: count-keys
SELECT count(key)
FROM geodata.shapes
WHERE key = ANY($1);

-- name: count-consumer-groups
SELECT COUNT(external_identifier)
FROM water_usage.usage_types
WHERE external_identifier = ANY($1);