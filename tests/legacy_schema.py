"""Historical SQL fixtures use current table and column names."""

import re
from pathlib import Path


def current_table_names(sql):
    # Adapt historical fixtures to current storage identifiers, preserving SQL values.
    migration = (
        Path(__file__).resolve().parents[1]
        / "src/KIDSic/db/alembic/versions/0019_croatian_tables.sql"
    ).read_text()
    names = dict(re.findall(r"ALTER TABLE (\w+) RENAME TO (\w+);", migration))
    sql = re.sub(
        r"--[^\n]*|'(?:''|[^'])*'|\b(?:FROM|JOIN|UPDATE|INTO|REFERENCES|TABLE)\s+(\w+)",
        lambda match: (
            (match[0][: -len(match[1])] + names.get(match[1], match[1]))
            if match[1]
            else match[0]
        ),
        sql,
        flags=re.IGNORECASE,
    )

    columns_migration = (
        Path(__file__).resolve().parents[1]
        / "src/KIDSic/db/alembic/versions/0020_croatian_columns.sql"
    ).read_text()
    columns = dict(re.findall(r"RENAME COLUMN (\w+) TO (\w+);", columns_migration))
    return re.sub(
        r"--[^\n]*|'(?:''|[^'])*'|\b[A-Za-z_][A-Za-z_0-9]*\b",
        lambda match: columns.get(match[0], match[0]),
        sql,
    )
