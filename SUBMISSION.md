# Submission: PlagiarismAttributionSettler

## Category
Intelligent Contracts

## Contract Name
PlagiarismAttributionSettler

## Summary
A reusable GenLayer primitive for plagiarism and attribution disputes: the accused deposits a license fee in escrow, GenLayer validators fetch both the original and disputed contents on-chain, score the plagiarism, and a binary verdict pays the full license fee to the original creator (if plagiarized) or returns it to the accused.

## What Makes This Unique
- **Binary attribution verdict**: plagiarism score >= 50 → original creator gets the full license fee; < 50 → accused gets it back
- **Dual on-chain fetch**: both original and disputed URLs are fetched by the contract itself; unreachable content deterministically scores 0
- **Hash-bound comparison**: `sha256(original_url|disputed_url)` binds exactly which two contents were judged
- **No fund locks**: after the response window, `expire_case` returns the full license fee to the accused

## How Consensus Is Used
The contract uses `gl.vm.run_nondet_unsafe()` with a custom validator for `settle_case`: each validator independently fetches both content URLs and re-scores the plagiarism. Consensus requires exact agreement with the leader (`SCORE_TOLERANCE = 5`). Unreachable content deterministically scores 0.

## Technical Details
- Python-based GenLayer Intelligent Contract
- Integer-only domain (wei amounts; `u256`/`bool`/`str`); time gates via `datetime` against consensus time
- Funding invariant: actual payable value must equal the recorded amount (`License funding must equal the case total`)
- Storage: `AttributionCase` dataclass under `TreeMap` with `u256`/`bool`/`str` fields
- Constants: `MAX_CASES = 100`, `MAX_RESPONSE_WINDOW_SECONDS = 2592000`, `SCORE_TOLERANCE = 5`, `PLAGIARISM_THRESHOLD = 50`

## Use Case
Content-reuse disputes where an accused party posts a license fee so that a neutral, evidence-backed attribution verdict decides whether the original creator is compensated.

## Verification
- 7/7 direct-mode unit tests (create validation + hash binding, plagiarized → creator full, not plagiarized → accused full, unreachable content → score 0, expiry after window, expiry/double-settle guards, auth/address/duplicate guards)
- `genvm-lint check` + validation pass (5 methods: 2 view, 3 write)
- On-chain verified on studionet: payable creation with hash match, funding/missing-URL/duplicate guards, expire-before-window revert
- Full AI-consensus integration test (leader_only=False, all methods): settle_case tx `0x8374278c7ee86898e4a69da0cd7bfe9e5cda6811c99686373d5adb42b6774620` settled via validators (score 100, verdict plagiarized, creator payout 1000/0); double settle reverted; expire after window released to accused; receipt stderr is empty (no storage-read-in-nondet warning)

## Live Deployment
Deployed on GenLayer studionet (chain `61999`):
[`0x9CbbDCA2e259a6F16BB893D71127B2Da8be93B26`](https://explorer-studio.genlayer.com/address/0x9CbbDCA2e259a6F16BB893D71127B2Da8be93B26)

## Source Code
See `contracts/plagiarism_attribution_settler.py`
