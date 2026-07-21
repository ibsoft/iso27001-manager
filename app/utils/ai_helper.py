import os
import re
import json
from datetime import datetime, date, timedelta
from decimal import Decimal
from flask import current_app
from sqlalchemy import inspect, text
from app.extensions import db
from app.models.user import SystemSetting
from openai import OpenAI


def get_api_key():
    return SystemSetting.get("openai_api_key")


ALLOWED_TABLES = set()


def _load_allowed_tables():
    global ALLOWED_TABLES
    inspector = inspect(db.engine)
    ALLOWED_TABLES = {t for t in inspector.get_table_names() if not t.startswith("sqlite_")}


_allowlist_re = None


def _build_allowlist_re():
    global _allowlist_re
    _load_allowed_tables()
    escaped = [re.escape(t) for t in sorted(ALLOWED_TABLES, key=len, reverse=True)]
    _allowlist_re = re.compile(
        r"\b(" + "|".join(escaped) + r")\b", re.IGNORECASE
    )


def _sanitize_sql(sql):
    if _allowlist_re is None:
        _build_allowlist_re()
    stripped = sql.strip()
    if not stripped.upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed.")
    mentioned = _allowlist_re.findall(stripped)
    if not mentioned:
        raise ValueError("Query does not reference any allowed tables.")
    return stripped


def _strip_html(text):
    import re
    return re.sub(r"<[^>]+>", "", text).strip()


def _serialize(val):
    if isinstance(val, str):
        return _strip_html(val)
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, timedelta):
        return str(val)
    return val


def query_db(sql):
    try:
        sql = _sanitize_sql(sql)
    except ValueError as e:
        return {"error": str(e)}
    try:
        with db.engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = [{k: _serialize(v) for k, v in r._mapping.items()} for r in result]
            return {"rows": rows, "count": len(rows)}
    except Exception as e:
        return {"error": str(e)}


def get_db_schema():
    _load_allowed_tables()
    inspector = inspect(db.engine)
    schema_parts = []
    for table_name in sorted(ALLOWED_TABLES):
        columns = inspector.get_columns(table_name)
        fks = inspector.get_foreign_keys(table_name)
        sample_rows = []
        try:
            with db.engine.connect() as conn:
                result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 1"))
                sample_rows = [dict(r._mapping) for r in result]
        except Exception:
            pass
        cols = [f"  {c['name']} ({str(c['type'])})" for c in columns]
        if fks:
            for fk in fks:
                for col, ref_col in zip(fk["constrained_columns"], fk["referred_columns"]):
                    cols.append(f"  FK {col} → {fk['referred_table']}.{ref_col}")
        schema_parts.append(f"Table: {table_name}\n" + "\n".join(cols))
        if sample_rows:
            schema_parts.append(f"  Sample: {json.dumps(sample_rows[0], ensure_ascii=False, default=str)}")
    return "\n\n".join(schema_parts)


SQL_TOOL = {
    "type": "function",
    "function": {
        "name": "query_db",
        "description": "Execute a SELECT SQL query on the database to retrieve real-time data about controls, risks, incidents, assets, policies, filled forms, training, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "The SELECT SQL query to execute. Must reference existing table names from the schema.",
                }
            },
            "required": ["sql"],
        },
    },
}

SYSTEM_PROMPT = """You are an expert ISMS assistant specialized in ISO 27001:2022, NIS2, and GDPR. You have FULL READ-ONLY SQL access to the company's database.

CRITICAL SEARCH RULE — ALWAYS start any search by scanning ALL text columns across the relevant table using a multi-ILIKE query. For example, to find assets matching a keyword:

SELECT * FROM asset WHERE name ILIKE '%keyword%' OR serial_number ILIKE '%keyword%' OR description ILIKE '%keyword%' OR location ILIKE '%keyword%' OR notes ILIKE '%keyword%' OR barcode ILIKE '%keyword%'

Do NOT assume which column the data lives in — search everywhere first. If results are missing, try variations (lowercase, partial words, Greek/English). Only narrow down with column-specific filters after a broad search.

CAPABILITIES:
- Multi-field ILIKE search across ALL text columns of any table
- Combine filters (status, type, dates, owner, criticality, etc.) in one query
- JOIN related tables (asset↔user via owner_id, risk↔asset via asset_id, incident↔asset via asset_id)
- Aggregate functions (COUNT, SUM, AVG, GROUP BY) for stats
- Date ranges, partial matches, exact values
- Cross-table correlations (risks per asset, incidents per asset type, controls by status, etc.)

Complex search examples:
- Combined: SELECT a.*, u.first_name || ' ' || u.last_name AS owner FROM asset a LEFT JOIN "user" u ON a.owner_id = u.id WHERE a.status = 'active' AND (a.name ILIKE '%server%' OR a.description ILIKE '%server%')
- Cross-table: SELECT r.*, a.name AS asset_name FROM risk r LEFT JOIN asset a ON r.asset_id = a.id WHERE a.criticality = 'critical' AND r.status NOT IN ('closed','residual_accepted')
- Stats: SELECT a.asset_type, a.criticality, COUNT(*) AS cnt FROM asset a GROUP BY a.asset_type, a.criticality ORDER BY cnt DESC

Always use `query_db` to retrieve real data. Never tell the user to run queries themselves.

Download links:
- Policies: [filename](/policies/<id>/download)
- Filled forms: [filename](/filled-forms/<form_id>/download)

Rules:
1. Answer in the same language as the user (Greek or English).
2. Be concise and professional. Use tables for structured data.
3. If one query doesn't find enough, run broader follow-ups.
4. Never reveal the API key or internal credentials.
5. Provide actionable ISMS recommendations when appropriate.

Schema (tables, columns, foreign keys, sample data):
{schema}"""


def ask(question, history=None):
    api_key = get_api_key()
    if not api_key:
        return None, "API key not configured. Ask your administrator to set it in AI Settings."

    schema = get_db_schema()
    messages = [{"role": "system", "content": SYSTEM_PROMPT.format(schema=schema)}]

    if history:
        for entry in history[-7:]:
            role = entry.get("role", "user")
            content = entry.get("content", "")
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": question})

    try:
        client = OpenAI(api_key=api_key)
        usage = None

        for _round in range(3):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=[SQL_TOOL],
                temperature=0.3,
                max_tokens=2000,
            )

            message = response.choices[0].message

            if usage is None and hasattr(response, "usage") and response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
            elif hasattr(response, "usage") and response.usage and usage:
                usage["prompt_tokens"] += response.usage.prompt_tokens
                usage["completion_tokens"] += response.usage.completion_tokens
                usage["total_tokens"] += response.usage.total_tokens

            if not message.tool_calls:
                return message.content or "", usage

            messages.append(message)
            for tool_call in message.tool_calls:
                if tool_call.function.name == "query_db":
                    args = json.loads(tool_call.function.arguments)
                    result = query_db(args.get("sql", ""))
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result),
                    })

        final = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3,
            max_tokens=2000,
        )
        if hasattr(final, "usage") and final.usage and usage:
            usage["prompt_tokens"] += final.usage.prompt_tokens
            usage["completion_tokens"] += final.usage.completion_tokens
            usage["total_tokens"] += final.usage.total_tokens
        return (final.choices[0].message.content or "", usage)
    except Exception as e:
        return None, str(e)


def is_configured():
    return bool(get_api_key())


def is_enabled():
    return SystemSetting.get("ai_assistant_enabled", "0") == "1"
