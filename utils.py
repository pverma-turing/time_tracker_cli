import datetime
import json
import os
from typing import Dict, Any

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


def read_config_file(config_path: str) -> Dict[str, Any]:
    """
    Read and parse a JSON configuration file.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)

        if not isinstance(config_data, dict):
            raise ValueError("Config file must contain a JSON object")

        return config_data
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON format in config file: {config_path}")