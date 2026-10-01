-- Runs once, the first time the Postgres volume is created.
-- A separate database for the test suite so tests never touch dev data.
CREATE DATABASE ledgerlet_test;
