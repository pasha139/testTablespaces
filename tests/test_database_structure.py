#coding:utf-8
"""
ID: database.structure.initialization
TITLE: Check initialized database structure and test data
DESCRIPTION: Verify that the database created by Firebird QA contains the expected tables, rows, indexes, and relations.
"""

import pytest
from firebird.qa import *
from tests.support import load_initialization_script


db = db_factory(filename="structure_test.fdb", init=load_initialization_script(), charset="UTF8")
act = python_act("db")


@pytest.mark.version(">=3.0")
def test_1(act: Action):
    with act.db.connect() as connection:
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
