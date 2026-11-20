import argparse
from database import migrate_security_v2

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Explicitly upgrade schema v1 to v2. Back up first.')
    parser.add_argument('--database', required=True, help='Path to the database to migrate')
    args = parser.parse_args()
    migrate_security_v2(args.database)
    print('Security migration completed.')
