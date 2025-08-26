"""学習済みモデルをONNX形式にエクスポートする"""

import argparse
from pathlib import Path

import torch
import yaml
from torch import Tensor, nn

from hiho_pytorch_base.config import Config
from hiho_pytorch_base.network.predictor import Predictor, create_predictor


class PredictorWrapper(nn.Module):
    """ONNXエクスポート用のPredictorラッパー"""

    def __init__(self, predictor: Predictor) -> None:
        super().__init__()
        self.predictor = predictor

    def forward(  # noqa: D102
        self,
        feature_vector: Tensor,
        feature_variable: Tensor,
        speaker_id: Tensor,
    ) -> tuple[Tensor, Tensor, Tensor]:
        return self.predictor(
            feature_vector=feature_vector,
            feature_variable_list=[feature_variable],
            speaker_id=speaker_id,
        )


def export_onnx(config_yaml_path: Path, output_path: Path, verbose: bool) -> None:
    """設定からPredictorを作成してONNX形式でエクスポートする"""
    output_path.parent.mkdir(exist_ok=True, parents=True)

    with config_yaml_path.open() as f:
        config_dict = yaml.safe_load(f)

    config = Config.from_dict(config_dict)

    predictor = create_predictor(config.network)
    wrapper = PredictorWrapper(predictor)
    wrapper.eval()

    batch_size = 1
    max_length = 50

    feature_vector = torch.randn(batch_size, config.network.feature_vector_size)
    feature_variable = torch.randn(max_length, config.network.feature_variable_size)
    speaker_id = torch.randint(0, config.network.speaker_size, (batch_size,))

    example_inputs = (feature_vector, feature_variable, speaker_id)

    torch.onnx.export(
        wrapper,
        example_inputs,
        str(output_path),
        input_names=[
            "feature_vector",
            "feature_variable",
            "speaker_id",
        ],
        output_names=["vector_output", "variable_output_list", "scalar_output"],
        dynamic_axes={
            "feature_vector": {0: "batch_size"},
            "feature_variable": {0: "max_length"},
            "speaker_id": {0: "batch_size"},
            "vector_output": {0: "batch_size"},
            "scalar_output": {0: "batch_size"},
        },
        verbose=verbose,
    )
    print(f"ONNX model exported to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config_yaml_path", type=Path)
    parser.add_argument("output_path", type=Path)
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    export_onnx(**vars(parser.parse_args()))
