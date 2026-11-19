
import json
import logging
from io import StringIO

import pytest
from pydantic import ValidationError

from workflow_logging import (
    create_structured_logger,
    log_event,
    run_logged_invoice_workflow,
    run_task2_fixture,
    WorkflowRun,
    InvoiceInput,
)


def valid_invoice():
    return {
        "invoice_id": "INV-TEST-001",
        "business_key": "BUSINESS-TEST-001",
        "amount": 12000,
        "currency": "INR",
    }


def test_successful_invoice_workflow():
    stream = StringIO()

    result = run_logged_invoice_workflow(
        valid_invoice(),
        stream
    )

    assert result["status"] == "completed"
    assert result["logging"] == "structured_json"
    assert len(result["tasks"]) == 3
    assert all(
        task["status"] == "completed"
        for task in result["tasks"]
    )


def test_invalid_invoice_is_rejected():
    stream = StringIO()

    invalid_data = {
        "invoice_id": "INV-INVALID",
        "business_key": "BUSINESS-INVALID",
        "amount": -500,
        "currency": "INR",
    }

    with pytest.raises(ValidationError):
        run_logged_invoice_workflow(
            invalid_data,
            stream
        )


def test_logs_are_valid_json():
    stream = StringIO()

    run_logged_invoice_workflow(valid_invoice(), stream)

    lines = stream.getvalue().splitlines()

    assert len(lines) >= 4

    records = [json.loads(line) for line in lines]

    assert all("timestamp" in record for record in records)
    assert all("level" in record for record in records)
    assert all("event" in record for record in records)


def test_correlation_id_is_present_in_every_log():
    stream = StringIO()

    result = run_logged_invoice_workflow(
        valid_invoice(),
        stream
    )

    records = [
        json.loads(line)
        for line in stream.getvalue().splitlines()
    ]

    assert records

    for record in records:
        assert record["run_id"] == result["run_id"]
        assert record["correlation_id"] == result["correlation_id"]


def test_sensitive_data_is_redacted():
    stream = StringIO()
    logger = create_structured_logger(
        stream,
        logger_name="redaction_test"
    )

    invoice = InvoiceInput(
        invoice_id="INV-REDACT",
        business_key="BUSINESS-REDACT",
        amount=1000
    )

    run = WorkflowRun(
        run_id="RUN-REDACT",
        correlation_id="CORR-REDACT",
        invoice=invoice
    )

    log_event(
        logger,
        logging.INFO,
        "security.redaction_test",
        run,
        "Testing sensitive data redaction",
        {
            "customer_email": "private@example.com",
            "phone_number": "9999999999",
            "api_key": "secret-key-value",
            "invoice_id": "INV-REDACT",
        }
    )

    record = json.loads(stream.getvalue())

    assert record["details"]["customer_email"] == "[REDACTED]"
    assert record["details"]["phone_number"] == "[REDACTED]"
    assert record["details"]["api_key"] == "[REDACTED]"
    assert record["details"]["invoice_id"] == "INV-REDACT"


def test_audit_event_is_generated():
    stream = StringIO()

    run_logged_invoice_workflow(valid_invoice(), stream)

    records = [
        json.loads(line)
        for line in stream.getvalue().splitlines()
    ]

    audit_records = [
        record for record in records
        if record["event"].startswith("audit.")
    ]

    assert len(audit_records) == 1
    assert audit_records[0]["details"]["action"] == "invoice_processed"
    assert audit_records[0]["details"]["outcome"] == "success"


def test_task2_evidence_file_is_generated():
    evidence = run_task2_fixture()

    assert evidence["task"] == "Task 2 - Logging Implementation"
    assert evidence["log_count"] >= 4
    assert evidence["workflow_result"]["status"] == "completed"
