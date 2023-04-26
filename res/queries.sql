-- name: create-schema
CREATE SCHEMA IF NOT EXISTS waterUsage;

-- name: create-consumer-group-table
CREATE TABLE IF NOT EXISTS waterUsage.consumerGroups (
  id SERIAL PRIMARY KEY,
  name varchar(255) NOT NULL,
  description text NOT NULL,
  parameter varchar(25) NOT NULL UNIQUE
);

-- name: create-usage-table
CREATE TABLE IF NOT EXISTS waterUsage.usage (
  id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  consumerGroup smallint,
  year smallint NOT NULL,
  consumer UUID DEFAULT NULL,
  municipal varchar NOT NULL,
  int_municipal BIGINT GENERATED ALWAYS AS ( CAST(municipal AS BIGINT)  ) STORED,
  CONSTRAINT fk_consumerGroup
    FOREIGN KEY (consumerGroup)
      REFERENCES waterUsage.consumerGroups(id)
      ON DELETE SET NULL,
  CONSTRAINT fk_municipal
    FOREIGN KEY (municipal)
      REFERENCES geodata.shapes(key)
      ON DELETE CASCADE
);

-- name: check-area-keys
SELECT key
FROM geodata.shapes
WHERE key = ANY($1);

-- name: get-all-consumer-groups
SELECT parameter
FROM water_usage.consumer_groups;

-- name: check-consumer-groups
SELECT parameter
FROM water_usage.consumer_groups
WHERE parameter = ANY($1);