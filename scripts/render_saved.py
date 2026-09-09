"""Regenerate inspection views from a saved run without invoking an agent."""
import argparse
import json
from pathlib import Path

from run_experiment import evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_folder', type=Path)
    parser.add_argument('--exclude-object', action='append', default=[])
    args = parser.parse_args()
    result = evaluate(args.run_folder, exclude_objects=args.exclude_object)
    (args.run_folder / 'inspection-result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    if result['status'] != 'complete':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
