import argparse
import sqlite3
from database import migrate_goals_v3

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Explicitly upgrade schema v2 to v3. Back up first.')
    parser.add_argument('--database', required=True)
    args = parser.parse_args()
    try:
        migrate_goals_v3(args.database)
    except (sqlite3.Error, RuntimeError) as error:
        parser.exit(1, f'Migration failed; no changes committed: {error}\n')
    print('Goals migration completed.')
