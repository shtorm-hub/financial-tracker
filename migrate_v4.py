import argparse
import sqlite3
from database import migrate_idempotency_v4

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Explicitly upgrade schema v3 to v4. Back up first.')
    parser.add_argument('--database', required=True)
    args = parser.parse_args()
    try:
        migrate_idempotency_v4(args.database)
    except (sqlite3.Error, RuntimeError) as error:
        parser.exit(1, f'Migration failed; no changes committed: {error}\n')
    print('Idempotency migration completed.')
