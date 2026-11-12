from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TABLESPACE_TABLES = {
    "CUSTOMERS": "TS_DATA",
    "PRODUCTS": "TS_DATA",
    "ORDERS": "TS_DATA",
    "ORDER_ITEMS": "TS_DATA",
    "PRODUCT_REVIEWS": "TS_ARCHIVE",
    "AUDIT_LOG": "TS_ARCHIVE",
}

EXPECTED_INDEXES = {
    "PK_CUSTOMERS",
    "UQ_CUSTOMERS_EMAIL",
    "PK_PRODUCTS",
    "PK_ORDERS",
    "PK_ORDER_ITEMS",
    "PK_PRODUCT_REVIEWS",
    "PK_AUDIT_LOG",
    "IDX_CUSTOMERS_FULL_NAME",
    "IDX_PRODUCTS_NAME",
    "IDX_ORDERS_CUSTOMER_DATE",
    "IDX_ORDER_ITEMS_PRODUCT",
    "IDX_REVIEWS_PRODUCT_RATING",
}

DEFAULT_COUNTS = {
    "CUSTOMERS": 5,
    "PRODUCTS": 6,
    "ORDERS": 4,
    "ORDER_ITEMS": 5,
    "PRODUCT_REVIEWS": 3,
    "AUDIT_LOG": 2,
}


def load_initialization_script():
    """Create schema and data first; tablespace paths are runtime-specific."""
    parts = [
        (PROJECT_ROOT / "sql" / "01_schema.sql").read_text(encoding="utf-8"),
        (PROJECT_ROOT / "sql" / "02_test_data.sql").read_text(encoding="utf-8"),
    ]
    return "\n".join(parts)


def _sql_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def _sql_identifier(value):
    return '"' + value.replace('"', '""') + '"'


def create_tablespaces(connection, tablespace_files):
    """
    Create three physical tablespaces using paths supplied by firebird.qa.
    tablespace_files: dict with TS_DATA, TS_INDEX and TS_ARCHIVE keys.
    """
    template = (PROJECT_ROOT / "sql" / "00_tablespace.sql").read_text(
        encoding="utf-8"
    )

    replacements = {}
    for name in ("TS_DATA", "TS_INDEX", "TS_ARCHIVE"):
        path = Path(tablespace_files[name]).resolve()
        # The tablespace file must not exist before CREATE TABLESPACE.
        if path.exists():
            path.unlink()
        replacements["{" + name + "_FILE}"] = _sql_literal(path)

    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value.strip("'"))

    cursor = connection.cursor()
    for statement in template.split(";"):
        statement = statement.strip()
        if statement:
            cursor.execute(statement)
    connection.commit()


def distribute_objects(connection):
    """Place table data in two tablespaces and every user index in TS_INDEX."""
    cursor = connection.cursor()

    for table_name, tablespace_name in TABLESPACE_TABLES.items():
        cursor.execute(
            f"ALTER TABLE {_sql_identifier(table_name)} "
            f"SET TABLESPACE TO {_sql_identifier(tablespace_name)}"
        )

    cursor.execute("""
        SELECT TRIM(RDB$INDEX_NAME)
        FROM RDB$INDICES
        WHERE COALESCE(RDB$SYSTEM_FLAG, 0) = 0
          AND RDB$INDEX_NAME IS NOT NULL
    """)
    index_names = [row[0] for row in cursor.fetchall()]

    for index_name in index_names:
        cursor.execute(
            f"ALTER INDEX {_sql_identifier(index_name)} "
            f"SET TABLESPACE TO \"TS_INDEX\""
        )

    connection.commit()


def prepare_tablespaces(connection, tablespace_files):
    create_tablespaces(connection, tablespace_files)
    distribute_objects(connection)


def assert_counts(cursor, expected_counts=None):
    expected_counts = expected_counts or DEFAULT_COUNTS
    for table_name, expected in expected_counts.items():
        cursor.execute(f"SELECT COUNT(*) FROM {_sql_identifier(table_name)}")
        actual = cursor.fetchone()[0]
        assert actual == expected, (
            f"{table_name}: ожидалось {expected}, получено {actual}"
        )


def _assert_no_rows(cursor, sql, message):
    cursor.execute(sql)
    actual = cursor.fetchone()[0]
    assert actual == 0, f"{message}: найдено {actual}"


def assert_referential_integrity(cursor):
    checks = [
        ("""
            SELECT COUNT(*)
            FROM ORDERS O
            LEFT JOIN CUSTOMERS C ON C.CUSTOMER_ID = O.CUSTOMER_ID
            WHERE C.CUSTOMER_ID IS NULL
        """, "Заказы без покупателя"),
        ("""
            SELECT COUNT(*)
            FROM ORDER_ITEMS I
            LEFT JOIN ORDERS O ON O.ORDER_ID = I.ORDER_ID
            WHERE O.ORDER_ID IS NULL
        """, "Позиции без заказа"),
        ("""
            SELECT COUNT(*)
            FROM ORDER_ITEMS I
            LEFT JOIN PRODUCTS P ON P.PRODUCT_ID = I.PRODUCT_ID
            WHERE P.PRODUCT_ID IS NULL
        """, "Позиции без товара"),
        ("""
            SELECT COUNT(*)
            FROM PRODUCT_REVIEWS R
            LEFT JOIN PRODUCTS P ON P.PRODUCT_ID = R.PRODUCT_ID
            WHERE P.PRODUCT_ID IS NULL
        """, "Отзывы без товара"),
        ("""
            SELECT COUNT(*)
            FROM PRODUCT_REVIEWS R
            LEFT JOIN CUSTOMERS C ON C.CUSTOMER_ID = R.CUSTOMER_ID
            WHERE C.CUSTOMER_ID IS NULL
        """, "Отзывы без покупателя"),
    ]
    for sql, message in checks:
        _assert_no_rows(cursor, sql, message)


def assert_indexes(cursor):
    cursor.execute("""
        SELECT TRIM(RDB$INDEX_NAME), TRIM(RDB$TABLESPACE_NAME)
        FROM RDB$INDICES
        WHERE COALESCE(RDB$SYSTEM_FLAG, 0) = 0
          AND RDB$INDEX_NAME IS NOT NULL
    """)
    actual = {name: tablespace for name, tablespace in cursor.fetchall()}

    missing = EXPECTED_INDEXES - set(actual)
    assert not missing, f"Отсутствуют индексы: {sorted(missing)}"

    wrong_tablespace = {
        name: tablespace
        for name, tablespace in actual.items()
        if tablespace != "TS_INDEX"
    }
    assert not wrong_tablespace, (
        "Индексы размещены не в TS_INDEX: "
        f"{wrong_tablespace}"
    )


def assert_blobs(cursor):
    cursor.execute("""
        SELECT COUNT(*)
        FROM PRODUCT_REVIEWS
        WHERE REVIEW_TEXT IS NOT NULL
    """)
    assert cursor.fetchone()[0] == 2

    cursor.execute(
        "SELECT REVIEW_TEXT FROM PRODUCT_REVIEWS WHERE REVIEW_ID = 1"
    )
    value = cursor.fetchone()[0]
    assert value is not None and "клавиатура" in value.lower()

    cursor.execute(
        "SELECT REVIEW_TEXT FROM PRODUCT_REVIEWS WHERE REVIEW_ID = 2"
    )
    assert cursor.fetchone()[0] is None


def assert_tablespace(cursor):
    cursor.execute("""
        SELECT TRIM(RDB$TABLESPACE_NAME)
        FROM RDB$TABLESPACES
        WHERE TRIM(RDB$TABLESPACE_NAME) IN (
            'TS_DATA', 'TS_INDEX', 'TS_ARCHIVE'
        )
    """)
    actual_tablespaces = {row[0] for row in cursor.fetchall()}
    expected_tablespaces = {"TS_DATA", "TS_INDEX", "TS_ARCHIVE"}
    assert actual_tablespaces == expected_tablespaces, (
        f"Ожидались {expected_tablespaces}, получены {actual_tablespaces}"
    )

    cursor.execute("""
        SELECT TRIM(RDB$RELATION_NAME), TRIM(RDB$TABLESPACE_NAME)
        FROM RDB$RELATIONS
        WHERE COALESCE(RDB$SYSTEM_FLAG, 0) = 0
          AND RDB$VIEW_BLR IS NULL
          AND TRIM(RDB$RELATION_NAME) IN (
              'CUSTOMERS', 'PRODUCTS', 'ORDERS', 'ORDER_ITEMS',
              'PRODUCT_REVIEWS', 'AUDIT_LOG'
          )
    """)
    actual_tables = dict(cursor.fetchall())
    assert actual_tables == TABLESPACE_TABLES, (
        f"Неверное размещение таблиц: {actual_tables}"
    )


def assert_database_state(cursor):
    assert_counts(cursor)
    assert_referential_integrity(cursor)
    assert_indexes(cursor)
    assert_blobs(cursor)
    assert_tablespace(cursor)
