#!/usr/bin/env python3
"""
HSMR 누락 의존성 한 번에 확인
- HSMR 코드에서 사용하는 모든 외부 패키지(import)를 수집
- requirements-hsmr.txt + Dockerfile 추가 패키지와 비교해 누락 후보 출력

사용법:
  python3 scripts/check_hsmr_imports.py
  python3 scripts/check_hsmr_imports.py --path ../HSMR
"""
from pathlib import Path
import re
import sys
import argparse

# Python 표준 라이브러리 (일반적으로 pip 설치 불필요)
STDLIB = {
    "__future__", "abc", "aifc", "argparse", "array", "ast", "asynchat", "asyncio", "asyncore",
    "atexit", "audioop", "base64", "bdb", "binascii", "binhex", "bisect", "builtins",
    "bz2", "calendar", "cgi", "cgitb", "chunk", "cmath", "cmd", "code", "codecs",
    "codeop", "collections", "colorsys", "compileall", "concurrent", "configparser",
    "contextlib", "copy", "copyreg", "cProfile", "crypt", "csv", "ctypes", "curses",
    "dataclasses", "datetime", "dbm", "decimal", "difflib", "dis", "distutils",
    "doctest", "email", "encodings", "enum", "errno", "faulthandler", "fcntl",
    "filecmp", "fileinput", "fnmatch", "fractions", "ftplib", "functools", "gc",
    "getopt", "getpass", "gettext", "glob", "graphlib", "grp", "gzip", "hashlib",
    "heapq", "hmac", "html", "http", "idlelib", "imaplib", "imghdr", "imp",
    "importlib", "inspect", "io", "ipaddress", "itertools", "json", "keyword",
    "lib2to3", "linecache", "locale", "logging", "lzma", "mailbox", "mailcap",
    "marshal", "math", "mimetypes", "mmap", "modulefinder", "multiprocessing",
    "netrc", "nis", "nntplib", "numbers", "operator", "optparse", "os", "ossaudiodev",
    "pathlib", "pdb", "pickle", "pickletools", "pipes", "pkgutil", "platform",
    "plistlib", "poplib", "posix", "posixpath", "pprint", "profile", "pstats",
    "pty", "pwd", "py_compile", "pyclbr", "pydoc", "queue", "quopri", "random",
    "re", "readline", "reprlib", "resource", "rlcompleter", "runpy", "sched",
    "secrets", "select", "selectors", "shelve", "shlex", "shutil", "signal",
    "site", "smtpd", "smtplib", "sndhdr", "socket", "socketserver", "spwd", "sqlite3",
    "ssl", "stat", "statistics", "string", "stringprep", "struct", "subprocess",
    "symtable", "sys", "sysconfig", "syslog", "tabnanny", "tarfile", "telnetlib",
    "tempfile", "termios", "test", "textwrap", "threading", "time", "timeit",
    "tkinter", "token", "tokenize", "trace", "traceback", "tracemalloc", "tty",
    "turtle", "turtledemo", "types", "typing", "unicodedata", "unittest", "urllib",
    "uu", "uuid", "venv", "warnings", "wave", "weakref", "webbrowser", "winreg",
    "winsound", "wsgiref", "xdrlib", "xml", "xmlrpc", "zipapp", "zipfile", "zipimport",
    "zlib", "_thread",
}

# 로컬 패키지 (HSMR 내부) 또는 detectron2/프로젝트 서브모듈
LOCAL_PREFIXES = ("lib", "exp", "detectron2", "tools", "projects", "vision", "train_net", "skel", "densepose", "point_sup", "tensormask", "tridentnet", "deeplearning", "train-net", "point-sup")

# requirements-hsmr.txt에서 제거하는 항목 (필터링됨)
FILTERED_IN_REQUIREMENTS = {"lib", "chumpy"}

# 패키지명 정규화: PyPI 이름 <-> import 이름
CANONICAL = {
    "PIL": "Pillow",
    "pil": "Pillow",
    "cv2": "opencv-python",
    "yaml": "PyYAML",
    "sklearn": "scikit-learn",
    "dateutil": "python-dateutil",
    "cv2": "opencv-python",
}


def extract_imports_from_file(filepath: Path) -> set:
    """한 .py 파일에서 top-level import 패키지명 수집"""
    names = set()
    try:
        text = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return names
    # import foo
    for m in re.finditer(r"^\s*import\s+([a-zA-Z_][a-zA-Z0-9_]*)", text, re.MULTILINE):
        names.add(m.group(1).split(".")[0])
    # from foo import ... / from foo.bar import ...
    for m in re.finditer(r"^\s*from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import", text, re.MULTILINE):
        top = m.group(1).split(".")[0]
        names.add(top)
    return names


def collect_imports(root: Path) -> set:
    """HSMR 루트 아래 모든 .py에서 외부 패키지 수집"""
    all_imports = set()
    for py in root.rglob("*.py"):
        if "detectron2" in py.parts and py.parts[-1].startswith("_"):
            continue
        for name in extract_imports_from_file(py):
            if name in STDLIB:
                continue
            if any(name.startswith(p) for p in LOCAL_PREFIXES):
                continue
            pkg = CANONICAL.get(name, name)
            # PyPI는 보통 소문자+하이픈
            pkg_normalized = pkg.replace("_", "-").lower()
            if pkg != pkg_normalized:
                all_imports.add(pkg_normalized)
            all_imports.add(pkg)
            all_imports.add(name)
    return all_imports


def requirements_set(requirements_path: Path, filtered: set) -> set:
    """requirements 파일에서 패키지명만 추출 (버전 제거, 필터 제외)"""
    names = set()
    if not requirements_path.exists():
        return names
    for line in requirements_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip().split("#")[0]
        if not line or line.startswith("-"):
            continue
        # package==1.0.0 or package[extra]
        base = re.split(r"\[|==|>=|<=|>|<|~=", line)[0].strip()
        base = base.replace("_", "-").lower()
        if base in filtered:
            continue
        names.add(base)
    return names


def main():
    parser = argparse.ArgumentParser(description="Check HSMR imports vs requirements")
    parser.add_argument("--path", type=str, default=None, help="HSMR repo path (default: ../HSMR from D-PoSE)")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent.parent
    hsmr_root = Path(args.path) if args.path else (base / "HSMR")
    if not hsmr_root.exists():
        hsmr_root = base / ".." / "HSMR"
    hsmr_root = hsmr_root.resolve()
    if not hsmr_root.exists():
        print("HSMR 경로를 찾을 수 없습니다:", hsmr_root, file=sys.stderr)
        sys.exit(1)

    req_path = hsmr_root / "requirements-hsmr.txt"
    declared = requirements_set(req_path, FILTERED_IN_REQUIREMENTS)

    # Dockerfile에서 추가로 설치하는 패키지 (버전 제외)
    dockerfile_extras = {"rich", "colorlog", "wis3d"}
    declared.update(dockerfile_extras)

    # import 이름 -> PyPI 이름 후보
    def to_pypi_candidates(name: str) -> set:
        c = CANONICAL.get(name, name)
        n = c.replace("_", "-").lower()
        return {c, n, name}

    code_imports = collect_imports(hsmr_root)
    declared_normalized = set()
    for d in declared:
        declared_normalized.add(d.replace("_", "-").lower())
        declared_normalized.add(d)

    # 선택적/개발용 또는 detectron2가 알아서 설치하는 패키지 제외
    skip = {"ipdb", "black", "sphinx", "recommonmark", "docutils", "pygments", "caffe2",
            "onnx", "pkg_resources", "pkg-resources", "av", "tyro", "nimblephysics",
            "psbody", "oven", "fvcore", "iopath", "lvis", "panopticapi", "pycocotools",
            "lightning_fabric", "lightning-fabric", "fairscale", "pytorch3d", "mmcv", "mmdet",
            "tabulate", "termcolor", "cloudpickle", "shapely", "psutil"}
    missing = []
    for imp in sorted(code_imports):
        if imp in STDLIB or imp.startswith("_"):
            continue
        if imp in skip or imp.replace("_", "-").lower() in {s.replace("_", "-") for s in skip}:
            continue
        if any(imp.startswith(p) for p in LOCAL_PREFIXES):
            continue
        candidates = to_pypi_candidates(imp)
        if any(c in declared or c in declared_normalized for c in candidates):
            continue
        if imp.replace("_", "-").lower() in declared_normalized:
            continue
        missing.append(imp)

    print("=== HSMR 의존성 검사 (requirements-hsmr.txt + Dockerfile 추가) ===\n")
    print("검사 경로:", hsmr_root)
    print("requirements-hsmr.txt:", req_path)
    print("Dockerfile 추가 패키지: rich, colorlog, wis3d\n")

    if not missing:
        print("결과: 누락된 외부 패키지 없음.")
        return 0

    print("결과: 아래 패키지가 requirements에 없을 수 있습니다 (코드에서 import됨).")
    print("       Dockerfile에 추가하거나 requirements-hsmr.txt에 넣어주세요.\n")
    for m in sorted(set(missing)):
        print(" ", m)
    print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
