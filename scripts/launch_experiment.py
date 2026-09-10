"""Submit a remote batch and exit without downloading experiment artifacts."""

import argparse
import json
import uuid
from datetime import datetime, timezone

import modal
from remote_experiment import APP_NAME, VOLUME_NAME
from shared_sandbox import EXPERIMENT_SECONDS, PROMPT, REFERENCE
from verify_pairings import PAIRINGS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", nargs="+", required=True, choices=PAIRINGS)
    parser.add_argument("--skip-evaluation", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if len(set(args.harness)) != len(args.harness):
        parser.error("Specify each harness once")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    batch_id = timestamp + "-" + uuid.uuid4().hex[:8].upper()
    plan = {
        "batch_id": batch_id,
        "harnesses": args.harness,
        "models": {h: PAIRINGS[h].model for h in args.harness},
        "seconds": EXPERIMENT_SECONDS,
        "reference": str(REFERENCE),
        "prompt": str(PROMPT),
        "evaluation": not args.skip_evaluation,
        "volume": VOLUME_NAME,
        "results_path": f"experiments/{batch_id}",
    }
    if not args.dry_run:
        controller = modal.Function.from_name(APP_NAME, "run_batch")
        call = controller.spawn(
            batch_id,
            args.harness,
            REFERENCE.read_bytes(),
            PROMPT.read_bytes(),
            args.skip_evaluation,
        )
        plan["call_id"] = call.object_id
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
