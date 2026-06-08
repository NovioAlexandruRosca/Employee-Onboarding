#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE auth_db;
    CREATE DATABASE hr_db;
    CREATE DATABASE manager_db;
    CREATE DATABASE finance_db;
    CREATE DATABASE it_db;
EOSQL
