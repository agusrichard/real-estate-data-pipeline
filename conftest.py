import importlib.util
import os
import sys


def load_module(
    relative_path: str, module_name: str, extra_sys_paths: list[str] = None
):
    root = os.path.dirname(__file__)
    if extra_sys_paths:
        for p in extra_sys_paths:
            abs_path = os.path.join(root, p)
            if abs_path not in sys.path:
                sys.path.insert(0, abs_path)
    path = os.path.join(root, relative_path)
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
