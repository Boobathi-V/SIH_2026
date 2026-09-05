"""Utility functions for logging, reproducibility, and configuration."""

import os
import sys
import yaml
import random
import logging
from pathlib import Path
from typing import Any, Dict
import numpy as np
import torch


def setup_logger(name: str = "dr_screening", log_file: str = None, level: int = logging.INFO) -> logging.Logger:
    """Set up structured logger with console and optional file handlers."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(level)

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def seed_everything(seed: int = 42) -> None:
    """Ensure deterministic execution across Python, NumPy, and PyTorch."""
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def load_config(config_path: str = "dr_screening/configs/config.yaml") -> Dict[str, Any]:
    """Load and parse YAML configuration file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def get_device(requested_device: str = "cuda") -> torch.device:
    """Resolve compute device safely, falling back to CPU when CUDA is unavailable."""
    if requested_device == "cuda" and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")
