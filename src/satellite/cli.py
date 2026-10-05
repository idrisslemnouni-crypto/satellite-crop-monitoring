import argparse
import json
import logging
from pathlib import Path

from satellite.catalog import discover
from satellite.pipeline import run


def main():
    parser = argparse.ArgumentParser(description="Process fixed real Sentinel-2 scenes")
    parser.add_argument("command", choices=["run", "discover"])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    root = args.root.resolve()
    if args.command == "discover":
        config = json.loads((root / "configs/default.json").read_text())
        print(json.dumps(discover(config), indent=2))
        return
    result = run(root)
    print(
        json.dumps(
            {
                "scenes": len(result["scenes"]),
                "common_pixels": result["common_pixels"],
                "common_fraction": result["common_fraction"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
