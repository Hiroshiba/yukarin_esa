"""データセットをチェックする"""

import argparse
import multiprocessing
import traceback
from functools import partial
from pathlib import Path

import yaml
from torch.utils.data import DataLoader
from tqdm import tqdm

from hiho_pytorch_base.batch import collate_dataset_output
from hiho_pytorch_base.config import Config
from hiho_pytorch_base.dataset import Dataset, create_dataset


def check_dataset(config_yaml_path: Path, trials: int) -> None:
    """データセットの整合性をチェックする"""
    with config_yaml_path.open() as f:
        config_dict = yaml.safe_load(f)

    config = Config.from_dict(config_dict)

    num_processes = config.train.num_processes
    batch_size = config.train.batch_size
    pin_memory = config.train.use_gpu

    datasets = create_dataset(config.dataset)

    wrapper = partial(
        _check,
        num_processes=num_processes,
        batch_size=batch_size,
        pin_memory=pin_memory,
    )

    for i in range(trials):
        print(f"try {i}")
        wrapper(datasets.train, desc="train", drop_last=True)
        wrapper(datasets.test, desc="test", drop_last=False)
        if datasets.eval is not None:
            wrapper(datasets.eval, desc="eval", drop_last=False)
        if datasets.valid is not None:
            wrapper(datasets.valid, desc="valid", drop_last=False)


def _check(
    dataset,
    desc: str,
    num_processes: int | None,
    batch_size: int,
    pin_memory: bool,
    drop_last: bool,
) -> None:
    wrapper = partial(_wrapper, dataset=dataset)

    pool_processes = None if num_processes == 0 else num_processes
    with multiprocessing.Pool(processes=pool_processes) as pool:
        it = pool.imap_unordered(wrapper, range(len(dataset)), chunksize=2**8)
        for i, error in tqdm(it, desc=desc, total=len(dataset)):
            if error is not None:
                print(f"error at {i}")
                traceback.print_exception(type(error), error, error.__traceback__)
                breakpoint()
                raise error

    it = DataLoader(
        dataset=dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_processes if num_processes is not None else 0,
        collate_fn=collate_dataset_output,
        pin_memory=pin_memory,
        drop_last=drop_last,
        timeout=0 if num_processes == 0 else 15,
    )
    for _, _ in tqdm(enumerate(it), desc=desc, total=len(dataset) // batch_size):
        pass


def _wrapper(index: int, dataset: Dataset):
    try:
        dataset[index]
        return index, None
    except Exception as e:
        return index, e


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config_yaml_path", type=Path)
    parser.add_argument("--trials", type=int, default=10)
    check_dataset(**vars(parser.parse_args()))
