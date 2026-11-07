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
- 6/6 direct-mode unit tests (create validation + hash binding, plagiarized → creator full, not plagiarized → accused full, unreachable content → score 0, expiry after window, expiry/double-settle guards)
- `genvm-lint check` + validation pass (5 methods: 2 view, 3 write)
- On-chain verified on studionet: payable creation with hash match, funding/missing-URL/duplicate guards, expire-before-window revert

## Live Deployment
Deployed on GenLayer studionet (chain `61999`):
[`0xA99b3Cc956b78CA49dB4238dD876783AE9C2e1F1`](https://explorer-studio.genlayer.com/address/0xA99b3Cc956b78CA49dB4238dD876783AE9C2e1F1)

## Source Code
See `contracts/plagiarism_attribution_settler.py`
