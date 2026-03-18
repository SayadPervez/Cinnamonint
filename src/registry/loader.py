"""
Dynamic handler loading — resolve handler_path to callable handle() function.
"""

import importlib
import importlib.util
import os
from src.config.settings import PROJECT_ROOT


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
