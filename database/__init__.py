# -*- coding: utf-8 -*-

import psycopg2
from schema import (
    CREATE_TABLES_SQL,
    INSERT_LESSON_TIMES_SQL,
    INSERT_TEST_DATA_SQL,
)

def main():
    conn = psycopg2.connect(
        dbname="schedule_bot_db",
        user="bot_user",
        password="postgres",
        host="localhost",
        port=5432,
    )
    conn.autocommit = True

    with conn.cursor() as cur:
        cur.execute(CREATE_TABLES_SQL)
        cur.execute(INSERT_LESSON_TIMES_SQL)
        cur.execute(INSERT_TEST_DATA_SQL)

    conn.close()
    print("✅ База инициализирована")

if __name__ == "__main__":
    main()
