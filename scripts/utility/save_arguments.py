"""関数の引数をYAMLファイルに保存するユーティリティ"""

import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from upath import UPath

from hiho_pytorch_base.dataset import DatasetType


def _str_represent(dumper, data):
    return dumper.represent_str(str(data))


yaml.SafeDumper.add_multi_representer(Path, _str_represent)
yaml.SafeDumper.add_multi_representer(UPath, _str_represent)
yaml.SafeDumper.add_representer(DatasetType, _str_represent)


def save_arguments(path: Path, target_function: Callable, arguments: dict[str, Any]):
    """対象関数の引数を抽出してYAMLファイルに保存する"""
    args = inspect.getfullargspec(target_function).args
    obj = {k: v for k, v in arguments.items() if k in args}

    with path.open(mode="w") as f:
        yaml.safe_dump(obj, f)
