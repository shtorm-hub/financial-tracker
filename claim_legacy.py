import argparse
import sqlite3
from contextlib import closing

from database import FinancialConflict, assert_reserves, check_database, connect


def claim_unassigned(path, user_id, expected_count):
    check_database(path)
    with closing(connect(path)) as connection:
        try:
            connection.execute('BEGIN IMMEDIATE')
            if not connection.execute('SELECT 1 FROM users WHERE id = ?', (user_id,)).fetchone():
                raise ValueError('User does not exist')
            count = connection.execute('SELECT COUNT(*) FROM transactions WHERE user_id IS NULL').fetchone()[0]
            if count != expected_count:
                raise ValueError('Unassigned transaction count differs from the confirmed count')
            connection.execute('UPDATE transactions SET user_id = ? WHERE user_id IS NULL', (user_id,))
            assert_reserves(connection, user_id)
            connection.commit()
            return count
        except Exception:
            connection.rollback()
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Assign all unassigned legacy transactions to one existing user. Back up first.')
    parser.add_argument('--database', required=True)
    parser.add_argument('--user-id', type=int, required=True)
    parser.add_argument('--expected-count', type=int, required=True,
                        help='Count reviewed beforehand; the operation fails if it differs')
    parser.add_argument('--confirm', action='store_true', required=True)
    args = parser.parse_args()
    try:
        count = claim_unassigned(args.database, args.user_id, args.expected_count)
    except (FinancialConflict, sqlite3.Error, ValueError, RuntimeError) as error:
        parser.exit(1, f'Assignment failed; no changes committed: {error}\n')
    print(f'Assigned {count} transactions.')
