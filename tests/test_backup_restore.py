#coding:utf-8
"""
ID: database.backup.restore
TITLE: Check database backup and restore with gbak
DESCRIPTION: Create a backup of the initialized test database, restore it to a new database file, and verify restored data and metadata.
"""

from firebird.qa import *
from firebird.driver import connect
from tests.support import load_initialization_script


db = db_factory(filename="backup_restore_source.fdb", init=load_initialization_script(), charset="UTF8")
act = python_act("db")
backup_file = temp_file("backup_restore.fbk")
restored_file = temp_file("backup_restore_restored.fdb")


@pytest.mark.version(">=3.0")
def test_1(act: Action, backup_file, restored_file):
    act.gbak(switches=["-b", act.db.dsn, str(backup_file)])
    assert backup_file.exists()
    assert backup_file.stat().st_size > 0

    act.reset()
    act.gbak(switches=["-c", str(backup_file), str(restored_file)])
    assert restored_file.exists()

    with connect(
        str(restored_file),
        user=act.db.user,
        password=act.db.password,
        charset="UTF8",
    ) as connection:
        cursor = connection.cursor()

        expected_counts = {
            "CUSTOMERS": 3,
            "PRODUCTS": 4,
            "ORDERS": 3,
            "ORDER_ITEMS": 4,
        }

        for table_name, expected_count in expected_counts.items():
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            actual_count = cursor.fetchone()[0]
            assert actual_count == expected_count

        cursor.execute("""
            SELECT COUNT(*)
            FROM ORDERS O
            LEFT JOIN CUSTOMERS C ON C.CUSTOMER_ID = O.CUSTOMER_ID
            WHERE C.CUSTOMER_ID IS NULL
        """)
        assert cursor.fetchone()[0] == 0

        cursor.execute("""
            SELECT COUNT(*)
            FROM ORDER_ITEMS I
            LEFT JOIN PRODUCTS P ON P.PRODUCT_ID = I.PRODUCT_ID
            WHERE P.PRODUCT_ID IS NULL
        """)
        assert cursor.fetchone()[0] == 0

        cursor.execute("""
            SELECT COUNT(*)
            FROM RDB$INDICES
            WHERE COALESCE(RDB$SYSTEM_FLAG, 0) = 0
              AND TRIM(RDB$INDEX_NAME) IN (
                  'IDX_CUSTOMERS_FULL_NAME',
                  'IDX_PRODUCTS_NAME',
                  'IDX_ORDERS_CUSTOMER_DATE',
                  'IDX_ORDER_ITEMS_PRODUCT'
              )
        """)
        assert cursor.fetchone()[0] == 4
