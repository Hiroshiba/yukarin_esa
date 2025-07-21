"""テストの便利モジュール"""

import json
from collections.abc import Callable
from pathlib import Path

import numpy as np
import yaml

from hiho_pytorch_base.config import Config
from hiho_pytorch_base.data.sampling_data import SamplingData


def setup_data_and_config(base_config_path: Path, data_dir: Path) -> Config:
    """テストデータをセットアップし、設定を作る"""
    with base_config_path.open() as f:
        config_dict = yaml.safe_load(f)

    config = Config.from_dict(config_dict)
    assert config.dataset.valid is not None

    config.dataset.train.root_dir = data_dir
    config.dataset.valid.root_dir = data_dir

    root_dir = config.dataset.train.root_dir
    train_num, valid_num = 30, 10
    all_stems = list(map(str, range(train_num + valid_num)))

    def _setup_data(
        generator_func: Callable[[Path], None], data_type: str, extension: str
    ) -> None:
        train_pathlist_path = data_dir / f"train_{data_type}_pathlist.txt"
        valid_pathlist_path = data_dir / f"valid_{data_type}_pathlist.txt"

        setattr(config.dataset.train, f"{data_type}_pathlist_path", train_pathlist_path)
        setattr(config.dataset.valid, f"{data_type}_pathlist_path", valid_pathlist_path)

        data_dir_path = root_dir / data_type
        data_dir_path.mkdir(parents=True, exist_ok=True)

        all_relative_paths = [f"{data_type}/{stem}.{extension}" for stem in all_stems]
        for relative_path in all_relative_paths:
            file_path = root_dir / relative_path
            if not file_path.exists():
                generator_func(file_path)

        if not train_pathlist_path.exists():
            train_pathlist_path.write_text("\n".join(all_relative_paths[:train_num]))
        if not valid_pathlist_path.exists():
            valid_pathlist_path.write_text("\n".join(all_relative_paths[train_num:]))

    # 固定長特徴ベクトル
    def generate_feature_vector(file_path: Path) -> None:
        feature_vector = (
            np.random.default_rng()
            .normal(size=config.network.feature_vector_size)
            .astype(np.float32)
        )
        np.save(file_path, feature_vector)

    _setup_data(generate_feature_vector, "feature_vector", "npy")

    # 可変長特徴データ
    def generate_feature_variable(file_path: Path) -> None:
        variable_length = int(np.random.default_rng().integers(5, 15))
        feature_variable = (
            np.random.default_rng()
            .normal(size=(variable_length, config.network.feature_variable_size))
            .astype(np.float32)
        )
        np.save(file_path, feature_variable)

    _setup_data(generate_feature_variable, "feature_variable", "npy")

    # サンプリングデータ
    def generate_target_vector(file_path: Path) -> None:
        array_length = config.dataset.frame_length
        array = np.random.default_rng().integers(
            0, config.network.target_vector_size, size=array_length, dtype=np.int64
        )
        sampling_data = SamplingData(array=array, rate=config.dataset.frame_rate)
        sampling_data.save(file_path)

    _setup_data(generate_target_vector, "target_vector", "npy")

    # 回帰ターゲット
    def generate_target_scalar(file_path: Path) -> None:
        target_class = np.random.default_rng().integers(
            0, config.network.target_vector_size, dtype=np.int64
        )
        target_scalar = float(target_class) + np.random.default_rng().normal() * 0.1
        np.save(file_path, target_scalar)

    _setup_data(generate_target_scalar, "target_scalar", "npy")

    # 話者マッピング
    speaker_names = ["A", "B", "C"]
    speaker_dict = {name: [] for name in speaker_names}
    for stem in all_stems:
        speaker_name = speaker_names[int(stem) % len(speaker_names)]
        speaker_dict[speaker_name].append(stem)

    speaker_dict_path = data_dir / "speaker_dict.json"
    speaker_dict_path.write_text(json.dumps(speaker_dict))
    config.dataset.train.speaker_dict_path = speaker_dict_path
    config.dataset.valid.speaker_dict_path = speaker_dict_path

    return config
