<div align="center">

# PlagiarismAttributionSettler

**License-fee escrow for plagiarism disputes: the accused deposits a license fee, validators fetch both original and disputed content on-chain, and a binary attribution verdict decides who gets it.**

![GenLayer](https://img.shields.io/badge/GenLayer-Intelligent%20Contract-6a4cff)
![Python](https://img.shields.io/badge/Python-3.12-3776AB)
![Status](https://img.shields.io/badge/status-live%20on%20studionet-2ea44f)
![Tests](https://img.shields.io/badge/tests-7%20passed-2ea44f)

[Live Contract](https://explorer-studio.genlayer.com/address/0x9CbbDCA2e259a6F16BB893D71127B2Da8be93B26)

[GenLayer Docs](https://docs.genlayer.com)

</div>

---

## Why

Content reuse disputes need a neutral way to decide whether a disputed work actually copied the original. Both contents are public evidence; the judgment is whether one copies the other — a call that cannot be reduced to a single deterministic check. PlagiarismAttributionSettler freezes a license fee from the accused, fetches both original and disputed content on-chain, scores the plagiarism, and settles with a binary verdict.

Reference: [GenLayer Use Cases — Content and information assessment](https://docs.genlayer.com/understand-genlayer-protocol/typical-use-cases) (plagiarism or attribution review).

## Live Deployment

| | |
|---|---|
| **Contract** | [PlagiarismAttributionSettler](https://explorer-studio.genlayer.com/address/0x9CbbDCA2e259a6F16BB893D71127B2Da8be93B26) |
| **Address** | `0x9CbbDCA2e259a6F16BB893D71127B2Da8be93B26` |
| **Network** | GenLayer studionet (chain `61999`) |
| **Status** | Deployed + verified on-chain |

## Highlights

- **Binary attribution verdict**: plagiarism score ≥ 50 → original creator gets the full license fee; < 50 → accused gets it back
- **Dual on-chain fetch**: both original and disputed URLs are fetched by the contract itself; unreachable content deterministically scores 0 (accused is made whole)
- **Hash-bound comparison**: `sha256(original_url|disputed_url)` binds exactly which two contents were judged
- **No fund locks**: after the response window, `expire_case` returns the full license fee to the accused

## How It Works

```
create_case (payable; creator, accused, title, claim, both URLs, response_window)
      |
      v
settle_case (permissionless; consensus plagiarism score → binary verdict, full fee to one side)
      |
      v (no settle)
expire_case (after window → accused reclaims full fee)
```

## Methods

| Role | Method | Guard |
|---|---|---|
| Any (funder) | `create_case` | payable; funding == amount; both URLs required; unique id |
| Any | `settle_case` | status open; consensus plagiarism score ≥ 50 threshold |
| Any | `expire_case` | status open; after response window |
| Any | `get_case`, `get_all_cases` | read-only |

## Security Model

- **Caller binding (audit fix)**: only the accused (`accused == sender`) can fund a case; strangers cannot create cases in someone else's name (addresses validated as `0x` + 40 hex; creator ≠ accused)
- Funding invariant: actual payable value must equal the recorded amount (`License funding must equal the case total`)
- Content-hash binding prevents substituting different URLs after creation
- LLM scoring with exact agreement (`SCORE_TOLERANCE = 5`); unreachable content → deterministic deny (score 0)
- Binary settlement pays the full fee to exactly one party (atomic, no partial locks)
- **Anti-lock**: after the response window, `expire_case` returns the full license fee to the accused — funds can never lock forever
- `reasoning` is descriptive-only: it is stored as an audit note and never reused in any later consequential computation (there is no appeal path)

## Test

```bash
gltest tests/ -q   # 7 passed
```

## Lint

```bash
genvm-lint check contracts/plagiarism_attribution_settler.py
```

## Live Deployment

Deployed on GenLayer studionet (chain `61999`):
[`0x9CbbDCA2e259a6F16BB893D71127B2Da8be93B26`](https://explorer-studio.genlayer.com/address/0x9CbbDCA2e259a6F16BB893D71127B2Da8be93B26)
