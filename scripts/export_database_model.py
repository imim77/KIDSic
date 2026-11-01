"""Export structure only from a migrated PostgreSQL database; never exports rows."""

import asyncio
import html
import json
import os
from pathlib import Path
import re

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
DDL = ROOT / "src/KIDSic/db/alembic/versions/0001_simple_rag.sql"
GROUPS = {
    "Izvori": ["data_source", "source_record"],
    "Vrtići i pretraga": ["kindergarten", "location", "program"],
    "Mjesta i upisi": ["availability", "enrolment"],
    "RAG": ["knowledge_chunk"],
}
COLORS = ["#eaf3ff", "#e7f6ef", "#fff2d8", "#fcebf1", "#f0eaff"]


def markdown(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


async def export():
    connection = await asyncpg.connect(os.environ["DATABASE_URL"])
    names = re.findall(r"CREATE TABLE (\w+) \(", DDL.read_text())
    model = {"revision": "0001_simple_rag", "tables": {}, "views": {}}
    try:
        revision = await connection.fetchval("SELECT version_num FROM alembic_version")
        if revision != model["revision"]:
            raise RuntimeError("Update the export's table inventory for the current revision.")
        for name in names:
            columns = await connection.fetch(
                """SELECT a.attname AS name, format_type(a.atttypid, a.atttypmod) AS type,
                          NOT a.attnotnull AS nullable,
                          pg_get_expr(d.adbin, d.adrelid) AS default_expression,
                          a.attgenerated <> '' AS generated
                   FROM pg_attribute a
                   JOIN pg_class t ON t.oid=a.attrelid
                   JOIN pg_namespace n ON n.oid=t.relnamespace
                   LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
                   WHERE n.nspname='public' AND t.relname=$1 AND a.attnum>0 AND NOT a.attisdropped
                   ORDER BY a.attnum""", name,
            )
            constraints = await connection.fetch(
                """SELECT c.conname AS name, c.contype::text AS kind,
                          pg_get_constraintdef(c.oid) AS definition,
                          ARRAY(SELECT a.attname FROM unnest(c.conkey) WITH ORDINALITY k(num,ord)
                                JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.num
                                ORDER BY k.ord) AS columns,
                          CASE WHEN c.contype='f' THEN c.confrelid::regclass::text END AS target,
                          ARRAY(SELECT a.attname FROM unnest(c.confkey) WITH ORDINALITY k(num,ord)
                                JOIN pg_attribute a ON a.attrelid=c.confrelid AND a.attnum=k.num
                                ORDER BY k.ord) AS target_columns
                   FROM pg_constraint c WHERE c.conrelid=to_regclass('public.' || $1)
                   ORDER BY c.contype, c.conname""", name,
            )
            indexes = await connection.fetch(
                "SELECT indexname AS name, indexdef AS definition FROM pg_indexes WHERE schemaname='public' AND tablename=$1 ORDER BY indexname", name,
            )
            model["tables"][name] = {
                "columns": [dict(row) for row in columns],
                "constraints": [dict(row) for row in constraints],
                "indexes": [dict(row) for row in indexes],
            }
        for name in ():
            model["views"][name] = await connection.fetchval("SELECT pg_get_viewdef(to_regclass($1), true)", name)
    finally:
        await connection.close()

    destination = ROOT / "database"
    destination.mkdir(exist_ok=True)
    (destination / "schema-manifest.json").write_text(json.dumps(model, indent=2, ensure_ascii=False) + "\n")
    lines = ["# Rječnik podataka — KIDSic", "", "Generirano iz migrirane baze naredbom `uv run python scripts/export_database_model.py`.",
             "Revizija: `0001_simple_rag`. PK = primarni ključ, FK = strani ključ, UQ = jedinstveno ograničenje.",
             "Kod složenih ključeva oznaka u retku označava sudjelovanje u ključu; puni sastav naveden je pod ograničenjima.",
             "`NULL` znači nepoznatu/neprimjenjivu vrijednost prema pravilima u [ERA.md](ERA.md).", ""]
    for group, tables in GROUPS.items():
        lines += [f"## {group}", ""]
        for name in tables:
            table = model["tables"][name]
            lines += [f"### `{name}`", "", "| Stupac | PostgreSQL tip | NULL | Ključ | Zadano / generirano |", "|---|---|---|---|---|"]
            for column in table["columns"]:
                keys = [dict(p="PK", f="FK", u="UQ")[c["kind"]] for c in table["constraints"]
                        if c["kind"] in "pfu" and column["name"] in c["columns"]]
                keys = list(dict.fromkeys(keys))
                default = column["default_expression"] or "—"
                if column["generated"]:
                    default = f"GENERATED: {default}"
                lines.append(f"| `{column['name']}` | `{column['type']}` | {'da' if column['nullable'] else 'ne'} | {', '.join(keys) or '—'} | {markdown(default)} |")
            lines += ["", "Ograničenja:", ""]
            lines += [f"- `{c['name']}`: `{markdown(c['definition'])}`" for c in table["constraints"]]
            lines += ["", "Indeksi:", ""]
            lines += [f"- `{i['name']}`: `{markdown(i['definition'])}`" for i in table["indexes"]]
            lines += [""]
    lines += ["## Pogledi", ""]
    for name, definition in model["views"].items():
        lines += [f"### `{name}`", "", "```sql", definition.strip(), "```", ""]
    (destination / "rjecnik-podataka.md").write_text("\n".join(lines))

    dot = ['digraph ERA {', 'graph [rankdir=LR, bgcolor="white", fontname="Helvetica", fontsize=18, pad="0.4", nodesep="0.45", ranksep="1.1", splines=polyline, label="KIDSic — ERA / 8 tablica\n1 = obvezan roditelj; 0..1 = opcionalan; 0..N = više potomaka", labelloc=t];',
           'node [shape=plain, fontname="Helvetica", fontsize=10];',
           'edge [color="#68778b", fontname="Helvetica", fontsize=8, arrowsize=0.5, arrowhead=none];']
    for index, (group, tables) in enumerate(GROUPS.items()):
        dot += [f'subgraph cluster_{index} {{', f'label={json.dumps(group, ensure_ascii=False)}; color="#ccd5df"; style="rounded";']
        for name in tables:
            table = model["tables"][name]
            keys = {col: [] for col in [c["name"] for c in table["columns"]]}
            for constraint in table["constraints"]:
                if constraint["kind"] in "pfu":
                    for column in constraint["columns"]:
                        keys[column].append({"p": "PK", "f": "FK", "u": "UQ"}[constraint["kind"]])
            rows = [f'<TR><TD COLSPAN="2" BGCOLOR="{COLORS[index]}"><B>{name}</B></TD></TR>']
            for column in table["columns"]:
                # Every column is shown; detailed CHECK/index definitions remain in the dictionary.
                key = ",".join(dict.fromkeys(keys[column["name"]]))
                label = html.escape(column["name"]) + (" ?" if column["nullable"] else "")
                kind = html.escape(column["type"])
                rows.append(f'<TR><TD PORT="{column["name"]}" ALIGN="LEFT">{label}</TD><TD ALIGN="LEFT">{key or kind}</TD></TR>')
            dot.append(f'{name} [label=<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4" COLOR="#9baabd">{"".join(rows)}</TABLE>>];')
        dot.append('}')
    for child, table in model["tables"].items():
        for constraint in table["constraints"]:
            if constraint["kind"] != "f":
                continue
            columns = set(constraint["columns"])
            unique = any(c["kind"] in "pu" and set(c["columns"]).issubset(columns) for c in table["constraints"])
            optional = any(c["nullable"] for c in table["columns"] if c["name"] in columns)
            parent = constraint["target"]
            tip = constraint["definition"]
            dot.append(f'{parent}:{constraint["target_columns"][0]}:e -> {child}:{constraint["columns"][0]}:w [taillabel="{"0..1" if optional else "1"}", headlabel="{"0..1" if unique else "0..N"}", tooltip={json.dumps(tip)}];')
    dot.append('}')
    (destination / "era.dot").write_text("\n".join(dot) + "\n")
    print(f"Exported {len(names)} tables and {len(model['views'])} views to {destination}")


if __name__ == "__main__":
    asyncio.run(export())
