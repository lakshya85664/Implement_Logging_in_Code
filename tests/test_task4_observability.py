
import json
from io import StringIO

from workflow_logging import (
    InvoiceInput,
    FakeInvoiceAdapter,
    run_observable_adapter,
    run_task4_fixture,
)


def make_invoice():
    return InvoiceInput(
        invoice_id="INV-TEST-004",
        business_key="BUSINESS-TEST-004",
        amount=12000,
        currency="INR",
    )


def test_fake_adapter_success_is_observable():
    stream = StringIO()
    adapter = FakeInvoiceAdapter(outcome="success")

    result = run_observable_adapter(
        make_invoice(), adapter, stream
    )

    assert result["status"] == "completed"
    assert adapter.call_count == 1
    assert result["metrics"]["adapter_calls"] == 1
    assert result["metrics"]["successful_calls"] == 1
    assert result["metrics"]["failed_calls"] == 0


def test_fake_adapter_failure_is_observable():
    stream = StringIO()
    adapter = FakeInvoiceAdapter(outcome="failure")

    result = run_observable_adapter(
        make_invoice(), adapter, stream
    )

    assert result["status"] == "needs_review"
    assert adapter.call_count == 1
    assert result["metrics"]["failed_calls"] == 1
    assert result["trace"]["events"]


def test_structured_logs_are_valid_json():
    stream = StringIO()
    adapter = FakeInvoiceAdapter()

    run_observable_adapter(make_invoice(), adapter, stream)

    logs = [
        json.loads(line)
        for line in stream.getvalue().splitlines()
        if line.strip()
    ]

    assert logs
    assert all("event" in entry for entry in logs)
    assert all("correlation_id" in entry for entry in logs)


def test_adapter_failure_event_is_logged():
    stream = StringIO()
    adapter = FakeInvoiceAdapter(outcome="failure")

    run_observable_adapter(make_invoice(), adapter, stream)

    logs = [
        json.loads(line)
        for line in stream.getvalue().splitlines()
        if line.strip()
    ]

    events = [entry["event"] for entry in logs]

    assert "adapter.call.started" in events
    assert "adapter.call.failed" in events


def test_secrets_are_redacted_from_adapter_response():
    stream = StringIO()
    adapter = FakeInvoiceAdapter(
        response={
            "api_key": "SECRET-123",
            "customer_email": "private@example.com",
        }
    )

    result = run_observable_adapter(
        make_invoice(), adapter, stream
    )

    assert result["response"]["api_key"] == "[REDACTED]"
    assert result["response"]["customer_email"] == "[REDACTED]"


def test_task4_evidence_files_are_generated():
    evidence = run_task4_fixture()

    assert evidence["scenarios"]["success"]["status"] == "completed"
    assert evidence["scenarios"]["failure"]["status"] == "needs_review"
    assert evidence["measurement_report"]["total_adapter_calls"] == 2
    assert evidence["redaction_check"]["api_key"] == "[REDACTED]"
