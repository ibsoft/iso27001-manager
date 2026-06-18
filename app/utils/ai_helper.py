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


def _serialize(val):
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
        sample_rows = []
        try:
            with db.engine.connect() as conn:
                result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 2"))
                sample_rows = [dict(r._mapping) for r in result]
        except Exception:
            pass
        cols = [f"  - {c['name']} ({str(c['type'])})" for c in columns]
        schema_parts.append(f"Table: {table_name}\n" + "\n".join(cols))
        if sample_rows:
            schema_parts.append(f"  Sample data: {sample_rows}")
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

SYSTEM_PROMPT = """You are an expert ISMS (Information Security Management System) assistant specialized in ISO 27001:2022, NIS2 Directive, and GDPR compliance. You help manage and complete the corporate ISMS.

You have FULL READ-ONLY access to the company's ISMS database. You MUST use the `query_db` tool to retrieve real data whenever the user asks about the current state of the system (counts, lists, statuses, etc.). Never tell the user to run their own queries — you run them.

When listing documents (policies, filled forms), include a download link with each item using markdown format:
- Policies: [filename](/policies/<id>/download)
- Filled forms: [filename](/filled-forms/<form_id>/download)

Rules:
1. Always answer in the same language the user wrote in (Greek or English).
2. Be concise, professional, and helpful. Use tables or bullet points for structured data.
3. Use the `query_db` tool to answer data questions. If the answer needs multiple queries, ask clarifying questions first.
4. Never reveal the API key or internal system credentials.
5. If you don't know something, say so honestly.
6. Provide actionable recommendations for improving the ISMS.

Here is the database schema for reference:
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
