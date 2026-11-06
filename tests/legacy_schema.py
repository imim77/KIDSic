"""Historical SQL fixtures keep testing immutable migrations after table renames."""
from pathlib import Path
import re


def current_table_names(sql):
    # Only table identifiers change; SQL values and public column names must not.
    migration = (Path(__file__).resolve().parents[1] /
                 'src/KIDSic/db/alembic/versions/0019_croatian_tables.sql').read_text()
    names = dict(re.findall(r'ALTER TABLE (\w+) RENAME TO (\w+);', migration))
    return re.sub(r"--[^\n]*|'(?:''|[^'])*'|\b(?:FROM|JOIN|UPDATE|INTO|REFERENCES|TABLE)\s+(\w+)",
                  lambda match: (match[0][:-len(match[1])] + names.get(match[1], match[1]))
                  if match[1] else match[0], sql, flags=re.IGNORECASE)
