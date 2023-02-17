from dotenv import dotenv_values
from pathlib import Path

config = dotenv_values()
config["DATA_DIR"] = Path(config["DATA_DIR"])
