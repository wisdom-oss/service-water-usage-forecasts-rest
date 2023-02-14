-- name: check-municipality-keys
SELECT key FROM geodata.shapes WHERE key = ANY($1);

-- name: check-consumer-groups
SELECT parameter FROM water_usage.consumer_groups WHERE parameter = ANY($1);

-- name: get-consumer-groups
SELECT DISTINCT parameter FROM water_usage.consumer_groups;