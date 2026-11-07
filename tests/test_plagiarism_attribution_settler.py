"""Direct-mode tests for the PlagiarismAttributionSettler contract."""

import hashlib
import json
import re
from datetime import datetime, timedelta

from gltest.direct import create_address

CASE_ID = "p0"
CREATOR_ADDR = create_address("creator")
ACCUSED_ADDR = create_address("accused")
CREATOR = "0x" + CREATOR_ADDR.hex()
ACCUSED = "0x" + ACCUSED_ADDR.hex()
AMOUNT = 1000
ORIGINAL_URL = "https://blog.example.com/original-post"
DISPUTED_URL = "https://blog.example.com/disputed-post"
TITLE = "Essay attribution dispute"
CLAIM = "Disputed post copies the original essay without credit."

PLAGIARIZED_JSON = json.dumps({"score": 80, "reasoning": "Clearly copied."})
NOT_PLAGIARIZED_JSON = json.dumps({"score": 20, "reasoning": "Independent work."})


def _create_case(
    contract,
    vm,
    amount=AMOUNT,
    response_window_seconds=3600,
):
    vm.sender = ACCUSED_ADDR
    vm.value = amount
    return contract.create_case(
        case_id=CASE_ID,
        original_creator=CREATOR,
        accused=ACCUSED,
        title=TITLE,
        claim_text=CLAIM,
        original_url=ORIGINAL_URL,
        disputed_url=DISPUTED_URL,
        license_amount=amount,
        response_window_seconds=response_window_seconds,
    )


def test_create_case_validates(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/plagiarism_attribution_settler.py")
    direct_vm.sender = ACCUSED_ADDR
    direct_vm.value = AMOUNT

    with direct_vm.expect_revert("Case id is required"):
        contract.create_case(case_id="", original_creator=CREATOR, accused=ACCUSED, title=TITLE, claim_text=CLAIM, original_url=ORIGINAL_URL, disputed_url=DISPUTED_URL, license_amount=AMOUNT, response_window_seconds=3600)
    with direct_vm.expect_revert("Creator and accused are required"):
        contract.create_case(case_id="p0", original_creator="", accused=ACCUSED, title=TITLE, claim_text=CLAIM, original_url=ORIGINAL_URL, disputed_url=DISPUTED_URL, license_amount=AMOUNT, response_window_seconds=3600)
    with direct_vm.expect_revert("Title and claim text are required"):
        contract.create_case(case_id="p0", original_creator=CREATOR, accused=ACCUSED, title="", claim_text=CLAIM, original_url=ORIGINAL_URL, disputed_url=DISPUTED_URL, license_amount=AMOUNT, response_window_seconds=3600)
    with direct_vm.expect_revert("Both content URLs are required"):
        contract.create_case(case_id="p0", original_creator=CREATOR, accused=ACCUSED, title=TITLE, claim_text=CLAIM, original_url="", disputed_url=DISPUTED_URL, license_amount=AMOUNT, response_window_seconds=3600)
    with direct_vm.expect_revert("License amount must be > 0"):
        direct_vm.value = 0
        contract.create_case(case_id="p0", original_creator=CREATOR, accused=ACCUSED, title=TITLE, claim_text=CLAIM, original_url=ORIGINAL_URL, disputed_url=DISPUTED_URL, license_amount=AMOUNT, response_window_seconds=3600)
    direct_vm.value = 5
    with direct_vm.expect_revert("License funding must equal the case total"):
        contract.create_case(case_id="p0", original_creator=CREATOR, accused=ACCUSED, title=TITLE, claim_text=CLAIM, original_url=ORIGINAL_URL, disputed_url=DISPUTED_URL, license_amount=AMOUNT, response_window_seconds=3600)
    direct_vm.value = AMOUNT
    with direct_vm.expect_revert("License funding must equal the case total"):
        contract.create_case(case_id="p0", original_creator=CREATOR, accused=ACCUSED, title=TITLE, claim_text=CLAIM, original_url=ORIGINAL_URL, disputed_url=DISPUTED_URL, license_amount=5, response_window_seconds=3600)
    with direct_vm.expect_revert("Response window must be at least 1 second"):
        contract.create_case(case_id="p0", original_creator=CREATOR, accused=ACCUSED, title=TITLE, claim_text=CLAIM, original_url=ORIGINAL_URL, disputed_url=DISPUTED_URL, license_amount=AMOUNT, response_window_seconds=0)
    with direct_vm.expect_revert("Response window cannot exceed 30 days"):
        contract.create_case(case_id="p0", original_creator=CREATOR, accused=ACCUSED, title=TITLE, claim_text=CLAIM, original_url=ORIGINAL_URL, disputed_url=DISPUTED_URL, license_amount=AMOUNT, response_window_seconds=2592001)

    cid = _create_case(contract, direct_vm)
    c = contract.get_case(cid)
    expected_hash = hashlib.sha256(f"{ORIGINAL_URL}|{DISPUTED_URL}".encode()).hexdigest()
    assert c["status"] == "open"
    assert c["license_amount"] == AMOUNT
    assert c["content_hash"] == expected_hash
    assert c["original_creator"] == CREATOR
    assert c["accused"] == ACCUSED


def test_settle_case_plagiarized_pays_creator(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/plagiarism_attribution_settler.py")
    cid = _create_case(contract, direct_vm)

    direct_vm.mock_web(re.escape(ORIGINAL_URL), {"status": 200, "body": "Original essay text..."})
    direct_vm.mock_web(re.escape(DISPUTED_URL), {"status": 200, "body": "Original essay text..."})
    direct_vm.mock_llm(re.escape("You are a plagiarism and attribution adjudicator"), PLAGIARIZED_JSON)
    res = contract.settle_case(case_id=cid)
    assert int(res.get("plagiarism_score")) == 80
    assert res.get("verdict") == "plagiarized"
    assert int(res.get("creator_payout")) == AMOUNT
    assert int(res.get("accused_return")) == 0
    c = contract.get_case(cid)
    assert c["status"] == "settled"
    assert c["creator_payout"] == AMOUNT


def test_settle_case_not_plagiarized_returns_accused(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/plagiarism_attribution_settler.py")
    cid = _create_case(contract, direct_vm)

    direct_vm.mock_web(re.escape(ORIGINAL_URL), {"status": 200, "body": "Original essay about oceans."})
    direct_vm.mock_web(re.escape(DISPUTED_URL), {"status": 200, "body": "Independent essay about mountains."})
    direct_vm.mock_llm(re.escape("You are a plagiarism and attribution adjudicator"), NOT_PLAGIARIZED_JSON)
    res = contract.settle_case(case_id=cid)
    assert int(res.get("plagiarism_score")) == 20
    assert res.get("verdict") == "not_plagiarized"
    assert int(res.get("creator_payout")) == 0
    assert int(res.get("accused_return")) == AMOUNT
    assert contract.get_case(cid)["status"] == "settled"


def test_settle_case_unreachable_content_scores_zero(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/plagiarism_attribution_settler.py")
    cid = _create_case(contract, direct_vm)

    direct_vm.mock_web(re.escape(ORIGINAL_URL), {"status": 200, "body": "Original essay text..."})
    direct_vm.mock_web(re.escape(DISPUTED_URL), {"status": 404, "body": "gone"})
    direct_vm.mock_llm(re.escape("You are a plagiarism and attribution adjudicator"), NOT_PLAGIARIZED_JSON)
    res = contract.settle_case(case_id=cid)
    assert int(res.get("plagiarism_score")) == 0
    assert res.get("verdict") == "not_plagiarized"
    assert int(res.get("accused_return")) == AMOUNT


def test_expire_case_after_window_releases_accused(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/plagiarism_attribution_settler.py")
    cid = _create_case(contract, direct_vm)

    direct_vm.warp((datetime.now() + timedelta(seconds=7200)).isoformat())
    res = contract.expire_case(case_id=cid)
    assert bool(res.get("released")) is True
    c = contract.get_case(cid)
    assert c["status"] == "released"
    assert c["accused_return"] == AMOUNT
    assert c["verdict"] == "expired"

    with direct_vm.expect_revert("Case is not open"):
        contract.expire_case(case_id=cid)


def test_expire_before_window_and_double_settle_revert(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/plagiarism_attribution_settler.py")
    cid = _create_case(contract, direct_vm)

    with direct_vm.expect_revert("Response window has not passed"):
        contract.expire_case(case_id=cid)

    direct_vm.mock_web(re.escape(ORIGINAL_URL), {"status": 200, "body": "Original essay text..."})
    direct_vm.mock_web(re.escape(DISPUTED_URL), {"status": 200, "body": "Independent text."})
    direct_vm.mock_llm(re.escape("You are a plagiarism and attribution adjudicator"), NOT_PLAGIARIZED_JSON)
    contract.settle_case(case_id=cid)

    with direct_vm.expect_revert("Case is not open"):
        contract.settle_case(case_id=cid)


def test_create_case_auth_address_and_duplicate_guards(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/plagiarism_attribution_settler.py")

    stranger = create_address("stranger")
    direct_vm.sender = stranger
    direct_vm.value = AMOUNT
    with direct_vm.expect_revert("Only accused can create a case"):
        contract.create_case(case_id="p9", original_creator=CREATOR, accused=ACCUSED, title=TITLE, claim_text=CLAIM, original_url=ORIGINAL_URL, disputed_url=DISPUTED_URL, license_amount=AMOUNT, response_window_seconds=3600)

    direct_vm.sender = ACCUSED_ADDR
    with direct_vm.expect_revert("Invalid Ethereum address"):
        contract.create_case(case_id="p9", original_creator="0x123", accused=ACCUSED, title=TITLE, claim_text=CLAIM, original_url=ORIGINAL_URL, disputed_url=DISPUTED_URL, license_amount=AMOUNT, response_window_seconds=3600)
    with direct_vm.expect_revert("Creator and accused must differ"):
        contract.create_case(case_id="p9", original_creator=ACCUSED, accused=ACCUSED, title=TITLE, claim_text=CLAIM, original_url=ORIGINAL_URL, disputed_url=DISPUTED_URL, license_amount=AMOUNT, response_window_seconds=3600)
    with direct_vm.expect_revert("Content URLs must be http(s) URLs"):
        contract.create_case(case_id="p9", original_creator=CREATOR, accused=ACCUSED, title=TITLE, claim_text=CLAIM, original_url="ftp://blog.example.com/original-post", disputed_url=DISPUTED_URL, license_amount=AMOUNT, response_window_seconds=3600)

    cid = _create_case(contract, direct_vm)
    assert cid == CASE_ID
    with direct_vm.expect_revert("Case already exists"):
        _create_case(contract, direct_vm)
