import psycopg

DATABASE_URL = (
    "postgresql://ledger_user:ledger_dev_password"
    "@localhost:5432/ledger_db"
)

def get_connection():
    return psycopg.connect(DATABASE_URL)