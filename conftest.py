import importlib.util
import os
import sys


def load_module(relative_path: str, module_name: str):
    path = os.path.join(os.path.dirname(__file__), relative_path)
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
