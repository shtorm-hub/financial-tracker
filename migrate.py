import argparse
from database import migrate_database

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Explicitly initialize or migrate a SQLite database. Back it up first.')
    parser.add_argument('--database', required=True, help='Path to the database to migrate')
    args = parser.parse_args()
    migrate_database(args.database)
    print('Migration completed. Existing transactions remain unassigned.')
