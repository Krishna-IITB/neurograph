"""Verify Neo4j credentials without running the full pipeline.

Usage:
    python -m scripts.check_neo4j

Prints connection state, password length (NOT value), and a simple write/read
test. Use this to debug AuraDB auth issues quickly — no LLM calls burned.
"""

from __future__ import annotations

import sys

from neo4j import GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable

from neurograph.config import settings


def main() -> None:
    print("=" * 60)
    print("  Neo4j connection check")
    print("=" * 60)
    print(f"  URI         : {settings.neo4j_uri}")
    print(f"  User        : {settings.neo4j_user}")
    if not settings.neo4j_password:
        print("  Password    : (EMPTY)")
        print("\n.env is missing NEO4J_PASSWORD. Aborting.")
        sys.exit(1)
    p = settings.neo4j_password
    print(f"  Password    : len={len(p)}, starts='{p[:2]}', ends='{p[-2:]}'")
    print(f"  (Whitespace check: leading={p[0].isspace()}, trailing={p[-1].isspace()})")
    print("=" * 60)

    if not settings.neo4j_uri:
        print("\nNEO4J_URI is empty. Aborting.")
        sys.exit(1)

    try:
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    except Exception as e:
        print(f"\n✗ Driver init failed: {e}")
        sys.exit(1)

    try:
        with driver.session() as s:
            result = s.run("RETURN 1 AS ok").single()
            assert result and result["ok"] == 1
        print("\n✓ Connection + auth OK")

        with driver.session() as s:
            stats = s.run(
                "MATCH (n:Entity) WITH count(n) AS nodes "
                "OPTIONAL MATCH ()-[r]->() RETURN nodes, count(r) AS rels"
            ).single()
            print(f"✓ Current graph: {stats['nodes']} entities, {stats['rels']} relationships")
    except AuthError:
        print("\n✗ Auth failed — password is wrong.")
        print("  Fix steps:")
        print("  1. Go to https://console.neo4j.io")
        print("  2. Open your instance → 'Reset password'")
        print("  3. Copy the new password into .env (NEO4J_PASSWORD=...)")
        print("  4. Re-run this script")
        sys.exit(1)
    except ServiceUnavailable as e:
        print(f"\n✗ Service unavailable: {e}")
        print("  The AuraDB instance might be paused (free tier auto-pauses).")
        print("  Go to https://console.neo4j.io and click 'Resume'.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {type(e).__name__}: {e}")
        sys.exit(1)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
