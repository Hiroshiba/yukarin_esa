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

    # 共通のフレーム長を生成（F0とvolumeで一致させる）
    np.random.seed(42)  # 再現性のため
    frame_lengths = {stem: int(np.random.randint(50, 200)) for stem in all_stems}

    # F0データ
    def generate_f0(file_path: Path) -> None:
        stem = file_path.stem
        f0_length = frame_lengths[stem]
        f0_data = np.random.uniform(80, 300, f0_length).astype(np.float32)  # F0値 (Hz)
        # 一部を無声（0）にする
        unvoiced_mask = np.random.random(f0_length) < 0.3
        f0_data[unvoiced_mask] = 0.0
        # SamplingDataで保存（200Hzのフレームレート）
        sampling_data = SamplingData(array=f0_data[:, np.newaxis], rate=200.0)
        sampling_data.save(file_path)

    _setup_data(generate_f0, "f0", "npy")

    # ボリュームデータ
    def generate_volume(file_path: Path) -> None:
        stem = file_path.stem
        volume_length = frame_lengths[stem]  # F0と同じ長さを使用
        volume_data = np.random.uniform(-60, -20, volume_length).astype(
            np.float32
        )  # dB
        # SamplingDataで保存（200Hzのフレームレート）
        sampling_data = SamplingData(array=volume_data[:, np.newaxis], rate=200.0)
        sampling_data.save(file_path)

    _setup_data(generate_volume, "volume", "npy")

    # LABデータ（音素情報）
    def generate_lab(file_path: Path) -> None:
        # ArpaPhoneme形式のLABファイルを生成

        stem = file_path.stem
        frame_length = frame_lengths[stem]
        frame_rate = 200.0
        total_duration = frame_length / frame_rate  # F0/volumeデータの総時間

        # ランダムに音素を選択（母音と子音を混合）
        vowel_phonemes = ["AA1", "EH0", "IY2", "AE1", "OW0"]
        consonant_phonemes = ["pau", "B", "T", "NG", "K"]
        phoneme_names = vowel_phonemes + consonant_phonemes

        num_phonemes = int(np.random.randint(3, 8))
        # 最低1つの母音を保証
        selected_phonemes = [np.random.choice(vowel_phonemes)]
        remaining_count = num_phonemes - 1
        if remaining_count > 0:
            selected_phonemes.extend(np.random.choice(phoneme_names, remaining_count))
        selected_phonemes = np.array(selected_phonemes[:num_phonemes])

        # 音素の継続時間を総時間に比例配分
        duration_weights = np.random.uniform(0.5, 2.0, num_phonemes)
        duration_weights = duration_weights / np.sum(duration_weights)  # 正規化
        durations = duration_weights * total_duration  # 総時間に合わせる

        # 音素の時間情報を生成
        current_time = 0.0
        lab_lines = []
        for phoneme, duration in zip(selected_phonemes, durations, strict=False):
            end_time = current_time + duration
            lab_lines.append(f"{current_time:.4f}\t{end_time:.4f}\t{phoneme}")
            current_time = end_time

        file_path.write_text("\n".join(lab_lines))

    _setup_data(generate_lab, "lab", "lab")

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
