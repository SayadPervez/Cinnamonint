"""
Dynamic handler loading — resolve handler_path to callable handle() function.
Supports two execution modes: subprocess (safe) and direct import (fast).
"""

import importlib
import importlib.util
import os
import subprocess
import sys

from src.config.settings import (
    PROJECT_ROOT,
    HANDLER_TIMEOUT_SECONDS,
    HANDLER_EXECUTION_MODE,
)


def load_handler(handler_path, raw_module=False):
    """load a handler module from its path and return the handle() function.

    handler_path is relative to the project root, e.g. 'tokens/math/plus.py'.

    if raw_module is True, return the entire module object instead of just
    the handle() function (used to inspect additional exports like
    extract_operands).

    returns the handle callable (or module), or raises on failure.
    """
    abs_path = os.path.join(PROJECT_ROOT, handler_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"handler file not found: {abs_path}")

    module_name = handler_path.replace(os.sep, ".").replace("/", ".").removesuffix(".py")
    spec = importlib.util.spec_from_file_location(module_name, abs_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load spec for {abs_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if raw_module:
        return module

    if not hasattr(module, "handle"):
        raise AttributeError(f"handler {handler_path} has no handle() function")

    return module.handle


def execute_handler(handler_path, sentence, timeout=HANDLER_TIMEOUT_SECONDS,
                    inherit_stderr=False):
    """execute a handler on the given sentence using the configured mode.

    in subprocess mode: spawns a new python process per call, passes the
    sentence via stdin, captures stdout as result. enforces timeout.

    in direct mode: loads the handler in-process and calls it (fast, no
    isolation).

    timeout: seconds before killing the subprocess. None = no limit.
    inherit_stderr: if True, stderr goes directly to the terminal
                    for real-time output (countdowns, progress, etc.).

    returns the modified sentence string.
    raises RuntimeError on handler crash or timeout.
    """
    if HANDLER_EXECUTION_MODE == "direct":
        return _execute_direct(handler_path, sentence)
    return _execute_subprocess(handler_path, sentence, timeout=timeout,
                               inherit_stderr=inherit_stderr)


def _execute_direct(handler_path, sentence):
    """load and call handler in-process (current behavior)."""
    handler = load_handler(handler_path)
    return handler(sentence)


def _execute_subprocess(handler_path, sentence, timeout=HANDLER_TIMEOUT_SECONDS,
                        inherit_stderr=False):
    """run handler in an isolated subprocess.

    the subprocess reads the sentence from stdin and prints the result
    to stdout. this ensures handler code cannot access engine internals.
    """
    abs_path = os.path.join(PROJECT_ROOT, handler_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"handler file not found: {abs_path}")

    # build a minimal script that imports the handler and runs it.
    # redirect handler's stdout (print calls) to stderr so side-effect
    # output (greetings, countdowns, etc.) stays separate from the
    # return value — only the final result goes to real stdout.
    script = (
        "import sys\n"
        f"sys.path.insert(0, {PROJECT_ROOT!r})\n"
        f"from {_handler_module_path(handler_path)} import handle\n"
        "sentence = sys.stdin.read()\n"
        "_real_stdout = sys.stdout\n"
        "sys.stdout = sys.stderr\n"
        "result = handle(sentence)\n"
        "sys.stdout = _real_stdout\n"
        "sys.stdout.write(result)\n"
    )

    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            input=sentence,
            stdout=subprocess.PIPE,
            stderr=None if inherit_stderr else subprocess.PIPE,
            text=True,
            timeout=timeout,
            cwd=PROJECT_ROOT,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"handler {handler_path} timed out after {timeout}s"
        )

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise RuntimeError(
            f"handler {handler_path} crashed (exit {result.returncode}): {stderr}"
        )

    # display any buffered side-effect output (when stderr was captured)
    if not inherit_stderr and result.stderr:
        print(result.stderr, end="")

    return result.stdout


def _handler_module_path(handler_path):
    """convert 'tokens/math/plus.py' to 'tokens.math.plus' for import."""
    return handler_path.replace(os.sep, ".").replace("/", ".").removesuffix(".py")
