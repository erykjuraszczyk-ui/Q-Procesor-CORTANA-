"""Portable runtime and host information collector, with best-effort memory data."""
from __future__ import annotations
import os
import platform
import sys

def _total_memory_bytes():
    try:
        if hasattr(os, "sysconf"):
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            if isinstance(pages, int) and isinstance(page_size, int) and pages > 0 and page_size > 0:
                return pages * page_size
    except (OSError, ValueError, AttributeError):
        pass
    return None

def collect_runtime_info():
    """Return stable, JSON-serializable platform metadata without optional dependencies."""
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "python_executable": sys.executable,
        "os_system": platform.system(),
        "os_release": platform.release(),
        "machine_architecture": platform.machine(),
        "processor_description": platform.processor() or None,
        "logical_cpu_count": os.cpu_count(),
        "total_memory_bytes": _total_memory_bytes()
    }


def main(argv=None):
    import argparse, json
    from pathlib import Path
    parser = argparse.ArgumentParser(description="Write QWP-777 runtime/environment metadata as JSON.")
    parser.add_argument("-o", "--output", help="write report JSON to this path")
    args = parser.parse_args(argv)
    rendered = json.dumps({"report_schema": "qwp777-runtime-info-1", "runtime": collect_runtime_info()}, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
