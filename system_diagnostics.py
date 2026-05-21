import socket
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent


def check(name, func):
    try:
        detail = func()
    except Exception as exc:
        print(f"[FAIL] {name}: {exc}")
        return False
    print(f"[ OK ] {name}{': ' + detail if detail else ''}")
    return True


def python_version():
    return sys.version.split()[0]


def requirements():
    result = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stdout + result.stderr).strip())
    return result.stdout.strip()


def timezone_data():
    return str(ZoneInfo("Asia/Manila"))


def import_app():
    from app import app

    return f"{len(list(app.url_map.iter_rules()))} routes"


def database_schema():
    from app import app, db
    from sqlalchemy import inspect

    with app.app_context():
        db.create_all()
        tables = sorted(inspect(db.engine).get_table_names())
    required = {"applicant", "employee", "role", "permission", "position"}
    missing = required.difference(tables)
    if missing:
        raise RuntimeError(f"missing tables: {', '.join(sorted(missing))}")
    return f"{len(tables)} tables"


def port_5000():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        result = sock.connect_ex(("127.0.0.1", 5000))
    if result == 0:
        return "already in use; app may already be running"
    return "available"


def main():
    checks = [
        ("Python", python_version),
        ("Dependencies", requirements),
        ("Timezone data", timezone_data),
        ("App import", import_app),
        ("Database schema", database_schema),
        ("Port 5000", port_5000),
    ]
    ok = all(check(name, func) for name, func in checks)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
