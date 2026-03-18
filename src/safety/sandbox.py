"""
Static analysis of handler source code via ast.

Walks the AST looking for suspicious patterns:
  - os.system(), subprocess with shell=True
  - file deletions (os.remove, shutil.rmtree)
  - network calls (urllib, socket)
  - exec(), eval()
  - environment variable access (os.environ)

Findings are informational — they don't block execution but are
highlighted to the user during code review (import / learn mode).
"""

import ast

from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from src.config.settings import DESTRUCTIVE_PATTERNS

console = Console()

# patterns keyed by (module, attribute/function) or just function name
_SUSPICIOUS_CALLS = {
    # shell execution
    ("os", "system"):      ("high", "Shell command execution"),
    ("os", "popen"):       ("high", "Shell command execution"),
    ("subprocess", "call"):  ("high", "Subprocess execution"),
    ("subprocess", "run"):   ("medium", "Subprocess execution"),
    ("subprocess", "Popen"): ("high", "Subprocess execution"),

    # file deletion
    ("os", "remove"):      ("high", "File deletion"),
    ("os", "unlink"):      ("high", "File deletion"),
    ("os", "rmdir"):       ("high", "Directory deletion"),
    ("shutil", "rmtree"):  ("high", "Recursive directory deletion"),

    # network
    ("urllib", "urlopen"):         ("medium", "Network request"),
    ("urllib.request", "urlopen"): ("medium", "Network request"),
    ("socket", "socket"):         ("medium", "Raw socket creation"),

    # dynamic execution
    ("builtins", "exec"):   ("high", "Dynamic code execution"),
    ("builtins", "eval"):   ("high", "Dynamic code evaluation"),
    ("builtins", "compile"): ("medium", "Dynamic code compilation"),

    # environment access
    ("os", "environ"):    ("medium", "Environment variable access"),
    ("os", "getenv"):     ("medium", "Environment variable access"),
}

# bare function names (no module prefix)
_SUSPICIOUS_BARE = {
    "exec":    ("high", "Dynamic code execution"),
    "eval":    ("high", "Dynamic code evaluation"),
    "compile": ("medium", "Dynamic code compilation"),
    "__import__": ("high", "Dynamic module import"),
}


def analyze_handler_code(source_code):
    """parse source and return a list of findings.

    each finding is a dict:
        {
            "pattern": str,       — what was detected
            "line": int,          — 1-based line number
            "severity": str,      — "high" or "medium"
            "description": str,   — human-readable explanation
        }
    """
    findings = []

    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        findings.append({
            "pattern": "SyntaxError",
            "line": e.lineno or 0,
            "severity": "high",
            "description": f"Code has a syntax error: {e.msg}",
        })
        return findings

    for node in ast.walk(tree):
        # --- function calls ---
        if isinstance(node, ast.Call):
            _check_call(node, findings)

        # --- import statements ---
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            _check_import(node, findings)

        # --- attribute access (os.environ without calling it) ---
        if isinstance(node, ast.Attribute):
            _check_attribute(node, findings)

    # --- check for destructive shell patterns in string literals ---
    _check_string_literals(tree, findings)

    return findings


def _check_call(node, findings):
    """inspect a Call node for suspicious function invocations."""
    func = node.func
    line = getattr(node, "lineno", 0)

    # module.function() — e.g., os.system("...")
    if isinstance(func, ast.Attribute):
        # get the full dotted name
        parts = _get_dotted_name(func)
        if parts and len(parts) >= 2:
            module = ".".join(parts[:-1])
            attr = parts[-1]
            key = (module, attr)
            if key in _SUSPICIOUS_CALLS:
                severity, desc = _SUSPICIOUS_CALLS[key]
                findings.append({
                    "pattern": f"{module}.{attr}()",
                    "line": line,
                    "severity": severity,
                    "description": desc,
                })

        # also check for shell=True in subprocess calls
        if isinstance(func.value, ast.Name) and func.value.id == "subprocess":
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    findings.append({
                        "pattern": f"subprocess.{func.attr}(shell=True)",
                        "line": line,
                        "severity": "high",
                        "description": "Subprocess with shell=True — command injection risk",
                    })

    # bare function call — e.g., exec("...")
    elif isinstance(func, ast.Name):
        if func.id in _SUSPICIOUS_BARE:
            severity, desc = _SUSPICIOUS_BARE[func.id]
            findings.append({
                "pattern": f"{func.id}()",
                "line": line,
                "severity": severity,
                "description": desc,
            })


def _check_import(node, findings):
    """flag imports of suspicious modules."""
    line = getattr(node, "lineno", 0)
    suspicious_modules = {"subprocess", "socket", "ctypes", "multiprocessing"}

    if isinstance(node, ast.Import):
        for alias in node.names:
            if alias.name in suspicious_modules:
                findings.append({
                    "pattern": f"import {alias.name}",
                    "line": line,
                    "severity": "medium",
                    "description": f"Imports '{alias.name}' module",
                })
    elif isinstance(node, ast.ImportFrom):
        if node.module and any(node.module.startswith(m) for m in suspicious_modules):
            findings.append({
                "pattern": f"from {node.module} import ...",
                "line": line,
                "severity": "medium",
                "description": f"Imports from '{node.module}' module",
            })


def _check_attribute(node, findings):
    """flag direct attribute access like os.environ."""
    line = getattr(node, "lineno", 0)
    if (isinstance(node.value, ast.Name) and
            node.value.id == "os" and node.attr == "environ"):
        findings.append({
            "pattern": "os.environ",
            "line": line,
            "severity": "medium",
            "description": "Environment variable access",
        })


def _check_string_literals(tree, findings):
    """scan string constants for destructive shell command patterns."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            for pattern in DESTRUCTIVE_PATTERNS:
                if pattern in node.value.lower():
                    findings.append({
                        "pattern": f'"{pattern}" in string literal',
                        "line": getattr(node, "lineno", 0),
                        "severity": "medium",
                        "description": f"String contains destructive pattern: {pattern}",
                    })
                    break  # one finding per string, not per pattern


def _get_dotted_name(node):
    """recursively extract a dotted name from an Attribute chain."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    parts.reverse()
    return parts


# ---------------------------------------------------------------------------
# display helpers
# ---------------------------------------------------------------------------

def display_findings(findings):
    """render findings as a rich table. returns True if any high-severity found."""
    if not findings:
        console.print("[green]No suspicious patterns detected.[/]")
        return False

    table = Table(title="Static Analysis Findings", show_lines=True)
    table.add_column("Line", style="dim", justify="right")
    table.add_column("Severity")
    table.add_column("Pattern")
    table.add_column("Description")

    has_high = False
    for f in findings:
        sev = f["severity"]
        if sev == "high":
            sev_fmt = "[red bold]HIGH[/]"
            has_high = True
        else:
            sev_fmt = "[yellow]MEDIUM[/]"
        table.add_row(
            str(f["line"]),
            sev_fmt,
            f["pattern"],
            f["description"],
        )

    console.print(table)
    return has_high


def display_code_with_findings(source_code, findings, language="python"):
    """display syntax-highlighted code, then findings table."""
    syntax = Syntax(source_code, language, theme="monokai", line_numbers=True)
    console.print(syntax)
    console.print()
    return display_findings(findings)


def auto_detect_flags(source_code):
    """analyze code and return suggested token flags.

    returns a dict with keys: destructive, downloads, uploads
    based on patterns found in the source.
    """
    findings = analyze_handler_code(source_code)
    flags = {"destructive": False, "downloads": False, "uploads": False}

    for f in findings:
        pattern = f["pattern"].lower()
        desc = f["description"].lower()

        if any(word in desc for word in ("deletion", "destructive")):
            flags["destructive"] = True
        if any(word in desc for word in ("network", "download", "socket")):
            flags["downloads"] = True
        if any(word in pattern for word in ("upload",)):
            flags["uploads"] = True

    # check string literals for destructive patterns
    for f in findings:
        if "destructive pattern" in f.get("description", "").lower():
            flags["destructive"] = True

    return flags


def has_extract_operands(source_code):
    """check whether handler source defines an extract_operands function.

    flagged tokens (destructive/downloads/uploads) should implement:
        def extract_operands(sentence) -> (token_name, parameters, context)

    returns True if the function definition exists, False otherwise.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "extract_operands":
            return True

    return False
