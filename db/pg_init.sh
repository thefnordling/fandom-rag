#!/bin/bash
# Usage: ./pg_init.sh <PGHOST> <PGADMIN_USER> <PGADMIN_PASS> <DB_NAME> <DB_USER> <DB_PASS>
# Example: ./pg_init.sh localhost postgres adminpassword my_kb kb query

set -e

if [ "$#" -ne 6 ]; then
  echo "Usage: $0 <PGHOST> <PGADMIN_USER> <PGADMIN_PASS> <DB_NAME> <DB_USER> <DB_PASS>"
  exit 1
fi

PGHOST="$1"
PGADMIN_USER="$2"
PGADMIN_PASS="$3"
DB_NAME="$4"
DB_USER="$5"
DB_PASS="$6"

export PGPASSWORD="$PGADMIN_PASS"

# Determine the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Create the database only if it does not exist
PGPASSWORD="$PGADMIN_PASS" psql -v ON_ERROR_STOP=1 -h "$PGHOST" -U "$PGADMIN_USER" -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME';" | grep -q 1 || \
PGPASSWORD="$PGADMIN_PASS" psql -v ON_ERROR_STOP=1 -h "$PGHOST" -U "$PGADMIN_USER" -d postgres -c "CREATE DATABASE \"$DB_NAME\";"

# 2. Run the combined init_db.sql with variable substitution
sed "s/\$DB_USER/$DB_USER/g; s/\$DB_PASS/$DB_PASS/g; s/\$DB_NAME/$DB_NAME/g" "$SCRIPT_DIR/init_db.sql" > "$SCRIPT_DIR/init_db_expanded.sql"
PGPASSWORD="$PGADMIN_PASS" psql -v ON_ERROR_STOP=1 -h "$PGHOST" -U "$PGADMIN_USER" -d "$DB_NAME" -f "$SCRIPT_DIR/init_db_expanded.sql"

rm "$SCRIPT_DIR/init_db_expanded.sql"

unset PGPASSWORD

echo "Database initialization complete."
