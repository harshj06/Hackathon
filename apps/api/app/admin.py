"""Grant local content-review permissions to an existing adult account.

Run only as the database owner: python -m app.admin email@example.com
There is deliberately no public endpoint to self-promote an account.
"""
import argparse
from sqlalchemy import select
from .storage import Account, factory

def main():
    parser=argparse.ArgumentParser(description='Grant local content reviewer role')
    parser.add_argument('email')
    args=parser.parse_args()
    with factory.begin() as session:
        account=session.scalar(select(Account).where(Account.email==args.email.strip().lower()))
        if not account: raise SystemExit('Create the adult account first.')
        account.role='admin'
    print('Content review role granted. Sign in again to open the review queue.')

if __name__=='__main__': main()
