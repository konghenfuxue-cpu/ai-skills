"""Check pinned versions and imports without installing or accessing the network."""

from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


IMPORT_NAMES = {"PyYAML": "yaml", "Pillow": "PIL"}


def check(requirements: Path) -> list[str]:
    problems = []
    for line in requirements.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, expected = line.split("==", 1)
        try:
            actual = version(name)
        except PackageNotFoundError:
            problems.append(f"Missing dependency: {name}=={expected}")
            continue
        if actual != expected:
            problems.append(f"Version mismatch: {name}=={actual}; expected {expected}")
            continue
        try:
            import_module(IMPORT_NAMES.get(name, name))
        except Exception as exc:
            problems.append(f"Cannot import {name}: {type(exc).__name__}: {exc}")
    return problems


if __name__ == "__main__":
    errors = check(Path(__file__).with_name("requirements.txt"))
    for error in errors:
        print(error)
    if not errors:
        print("Pinned dependency versions and imports OK.")
    raise SystemExit(1 if errors else 0)
