
import json

from workflow_logging import (
    InvoiceInput,
    IdempotencyStore,
    RecoveryAction,
    execute_invoice_with_recovery,
    run_task3_fixture,
)


def sample_invoice():
    return InvoiceInput(
        invoice_id="INV-RECOVERY-001",
        business_key="BUSINESS-RECOVERY-001",
        amount=15000,
        currency="INR",
    )


def test_timeout_is_retried_until_success():
    result = execute_invoice_with_recovery(
        sample_invoice(),
        ["timeout", "timeout", "success"],
        IdempotencyStore(),
    )

    assert result["status"] == RecoveryAction.COMPLETED.value
    assert result["attempts"] == 3
    assert result["recovery_trace"][0]["action"] == "retry"


def test_retry_limit_is_bounded():
    result = execute_invoice_with_recovery(
        sample_invoice(),
        ["timeout", "timeout", "timeout", "success"],
        IdempotencyStore(),
        max_retries=2,
    )

    assert result["status"] == RecoveryAction.NEEDS_REVIEW.value
    assert result["attempts"] == 3


def test_malformed_response_requires_review():
    result = execute_invoice_with_recovery(
        sample_invoice(),
        ["malformed_response", "success"],
        IdempotencyStore(),
    )

    assert result["status"] == RecoveryAction.NEEDS_REVIEW.value
    assert result["attempts"] == 1


def test_permanent_failure_is_not_retried():
    result = execute_invoice_with_recovery(
        sample_invoice(),
        ["permanent", "success"],
        IdempotencyStore(),
    )

    assert result["status"] == RecoveryAction.NEEDS_REVIEW.value
    assert result["attempts"] == 1


def test_duplicate_processing_is_prevented():
    store = IdempotencyStore()
    invoice = sample_invoice()

    first = execute_invoice_with_recovery(
        invoice,
        ["success"],
        store,
    )

    second = execute_invoice_with_recovery(
        invoice,
        ["success"],
        store,
    )

    assert first["status"] == RecoveryAction.COMPLETED.value
    assert second["status"] == RecoveryAction.DUPLICATE_PREVENTED.value
    assert second["attempts"] == 0


def test_negative_retry_limit_is_rejected():
    try:
        execute_invoice_with_recovery(
            sample_invoice(),
            ["success"],
            IdempotencyStore(),
            max_retries=-1,
        )
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "max_retries" in str(error)


def test_task3_evidence_files_are_generated():
    evidence = run_task3_fixture()

    assert evidence["task"] == (
        "Task 3 - Failure, Retry, and Replay Safety"
    )
    assert evidence["summary"]["timeout_recovered"] is True
    assert evidence["summary"]["malformed_response_requires_review"] is True
    assert evidence["summary"]["duplicate_prevented"] is True

    with open(
        "outputs/task3_recovery.json",
        encoding="utf-8",
    ) as file:
        saved = json.load(file)

    assert saved["summary"] == evidence["summary"]
