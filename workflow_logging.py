from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# --------------------------------------------------
# 1. Workflow states and events
# --------------------------------------------------

class WorkflowState(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    NEEDS_REVIEW = "needs_review"


class WorkflowEvent(str, Enum):
    START = "start"
    COMPLETE = "complete"
    PAUSE = "pause"
    RESUME = "resume"
    FAIL = "fail"


# --------------------------------------------------
# 2. Typed input model
# --------------------------------------------------

class InvoiceInput(BaseModel):
    invoice_id: str
    business_key: str
    amount: float = Field(gt=0)
    currency: str = "INR"


# --------------------------------------------------
# 3. Task and event models
# --------------------------------------------------

class TaskRecord(BaseModel):
    task_id: str
    task_name: str
    status: str = "pending"
    attempts: int = 0


class EventRecord(BaseModel):
    run_id: str
    correlation_id: str
    event: str
    state: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    details: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------
# 4. Result and trace models
# --------------------------------------------------

class WorkflowResult(BaseModel):
    run_id: str
    status: str
    message: str
    completed_at: datetime | None = None


class WorkflowTrace(BaseModel):
    run_id: str
    correlation_id: str
    events: list[EventRecord] = Field(default_factory=list)


# --------------------------------------------------
# 5. Workflow run model
# --------------------------------------------------

class WorkflowRun(BaseModel):
    run_id: str
    correlation_id: str
    invoice: InvoiceInput
    state: WorkflowState = WorkflowState.CREATED
    attempts: int = 0
    tasks: list[TaskRecord] = Field(default_factory=list)
    events: list[EventRecord] = Field(default_factory=list)


# --------------------------------------------------
# 6. Legal transition rules
# --------------------------------------------------

TRANSITIONS = {
    (WorkflowState.CREATED, WorkflowEvent.START):
        WorkflowState.RUNNING,

    (WorkflowState.RUNNING, WorkflowEvent.COMPLETE):
        WorkflowState.COMPLETED,

    (WorkflowState.RUNNING, WorkflowEvent.PAUSE):
        WorkflowState.WAITING,

    (WorkflowState.WAITING, WorkflowEvent.RESUME):
        WorkflowState.RUNNING,

    (WorkflowState.RUNNING, WorkflowEvent.FAIL):
        WorkflowState.NEEDS_REVIEW,
}


# --------------------------------------------------
# 7. Event recording
# --------------------------------------------------

def record_event(
    run: WorkflowRun,
    event: str,
    details: dict[str, Any] | None = None
) -> EventRecord:

    record = EventRecord(
        run_id=run.run_id,
        correlation_id=run.correlation_id,
        event=event,
        state=run.state.value,
        details=details or {}
    )

    run.events.append(record)
    return record


# --------------------------------------------------
# 8. State transition function
# --------------------------------------------------

def transition(
    run: WorkflowRun,
    event: WorkflowEvent
) -> WorkflowRun:

    key = (run.state, event)

    next_state = TRANSITIONS.get(key)

    if next_state is None:
        raise ValueError(
            f"Illegal transition: {run.state.value} + {event.value}"
        )

    run.state = next_state

    record_event(
        run,
        event.value,
        {"previous_state": key[0].value}
    )

    return run


# --------------------------------------------------
# 9. Create a workflow run
# --------------------------------------------------

def create_workflow(invoice: InvoiceInput) -> WorkflowRun:

    run = WorkflowRun(
        run_id=str(uuid4()),
        correlation_id=str(uuid4()),
        invoice=invoice,
        tasks=[
            TaskRecord(
                task_id="TASK-001",
                task_name="validate_invoice"
            ),
            TaskRecord(
                task_id="TASK-002",
                task_name="process_invoice"
            ),
            TaskRecord(
                task_id="TASK-003",
                task_name="finalize_invoice"
            )
        ]
    )

    record_event(
        run,
        "workflow.created",
        {"invoice_id": invoice.invoice_id}
    )

    return run


# --------------------------------------------------
# 10. Demonstration
# --------------------------------------------------

def run_topic_fixture() -> dict[str, Any]:

    invoice = InvoiceInput(
        invoice_id="INV-1001",
        business_key="BUSINESS-1001",
        amount=15000,
        currency="INR"
    )

    run = create_workflow(invoice)

    transition(run, WorkflowEvent.START)
    transition(run, WorkflowEvent.COMPLETE)

    result = WorkflowResult(
        run_id=run.run_id,
        status=run.state.value,
        message="Invoice workflow completed",
        completed_at=datetime.now(timezone.utc)
    )

    trace = WorkflowTrace(
        run_id=run.run_id,
        correlation_id=run.correlation_id,
        events=run.events
    )

    return {
        "status": run.state.value,
        "run_id": run.run_id,
        "correlation_id": run.correlation_id,
        "result": result.model_dump(mode="json"),
        "trace": trace.model_dump(mode="json")
    }


if __name__ == "__main__":
    import json

    output = run_topic_fixture()
    print(json.dumps(output, indent=4))

import json
import logging
import os
import sys
from datetime import datetime, timezone
from enum import Enum
from io import StringIO
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# ==================================================
# TASK 1 — WORKFLOW CONTRACT AND STATE MODEL
# ==================================================

class WorkflowState(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    NEEDS_REVIEW = "needs_review"


class WorkflowEvent(str, Enum):
    START = "start"
    COMPLETE = "complete"
    PAUSE = "pause"
    RESUME = "resume"
    FAIL = "fail"


class InvoiceInput(BaseModel):
    invoice_id: str
    business_key: str
    amount: float = Field(gt=0)
    currency: str = "INR"


class TaskRecord(BaseModel):
    task_id: str
    task_name: str
    status: str = "pending"
    attempts: int = 0


class EventRecord(BaseModel):
    run_id: str
    correlation_id: str
    event: str
    state: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    details: dict[str, Any] = Field(default_factory=dict)


class WorkflowResult(BaseModel):
    run_id: str
    status: str
    message: str
    completed_at: datetime | None = None


class WorkflowTrace(BaseModel):
    run_id: str
    correlation_id: str
    events: list[EventRecord] = Field(default_factory=list)


class WorkflowRun(BaseModel):
    run_id: str
    correlation_id: str
    invoice: InvoiceInput
    state: WorkflowState = WorkflowState.CREATED
    attempts: int = 0
    tasks: list[TaskRecord] = Field(default_factory=list)
    events: list[EventRecord] = Field(default_factory=list)


TRANSITIONS = {
    (WorkflowState.CREATED, WorkflowEvent.START):
        WorkflowState.RUNNING,
    (WorkflowState.RUNNING, WorkflowEvent.COMPLETE):
        WorkflowState.COMPLETED,
    (WorkflowState.RUNNING, WorkflowEvent.PAUSE):
        WorkflowState.WAITING,
    (WorkflowState.WAITING, WorkflowEvent.RESUME):
        WorkflowState.RUNNING,
    (WorkflowState.RUNNING, WorkflowEvent.FAIL):
        WorkflowState.NEEDS_REVIEW,
}


def record_event(
    run: WorkflowRun,
    event: str,
    details: dict[str, Any] | None = None
) -> EventRecord:

    record = EventRecord(
        run_id=run.run_id,
        correlation_id=run.correlation_id,
        event=event,
        state=run.state.value,
        details=details or {}
    )

    run.events.append(record)
    return record


def transition(
    run: WorkflowRun,
    event: WorkflowEvent
) -> WorkflowRun:

    key = (run.state, event)
    next_state = TRANSITIONS.get(key)

    if next_state is None:
        raise ValueError(
            f"Illegal transition: {run.state.value} + {event.value}"
        )

    previous_state = run.state
    run.state = next_state

    record_event(
        run,
        event.value,
        {"previous_state": previous_state.value}
    )

    return run


def create_workflow(invoice: InvoiceInput) -> WorkflowRun:

    run = WorkflowRun(
        run_id=str(uuid4()),
        correlation_id=str(uuid4()),
        invoice=invoice,
        tasks=[
            TaskRecord(
                task_id="TASK-001",
                task_name="validate_invoice"
            ),
            TaskRecord(
                task_id="TASK-002",
                task_name="process_invoice"
            ),
            TaskRecord(
                task_id="TASK-003",
                task_name="finalize_invoice"
            )
        ]
    )

    record_event(
        run,
        "workflow.created",
        {"invoice_id": invoice.invoice_id}
    )

    return run


def run_topic_fixture() -> dict[str, Any]:

    invoice = InvoiceInput(
        invoice_id="INV-1001",
        business_key="BUSINESS-1001",
        amount=15000,
        currency="INR"
    )

    run = create_workflow(invoice)

    transition(run, WorkflowEvent.START)
    transition(run, WorkflowEvent.COMPLETE)

    result = WorkflowResult(
        run_id=run.run_id,
        status=run.state.value,
        message="Invoice workflow completed",
        completed_at=datetime.now(timezone.utc)
    )

    trace = WorkflowTrace(
        run_id=run.run_id,
        correlation_id=run.correlation_id,
        events=run.events
    )

    return {
        "status": run.state.value,
        "run_id": run.run_id,
        "correlation_id": run.correlation_id,
        "result": result.model_dump(mode="json"),
        "trace": trace.model_dump(mode="json")
    }


# ==================================================
# TASK 2 — STRUCTURED LOGGING
# ==================================================

SENSITIVE_KEYS = {
    "email",
    "customer_email",
    "phone",
    "phone_number",
    "account_number",
    "customer_name",
    "address",
    "password",
    "token",
    "api_key",
    "secret",
}


def redact_sensitive_data(value: Any) -> Any:
    """Recursively redact values stored under sensitive keys."""

    if isinstance(value, dict):
        cleaned = {}

        for key, item in value.items():
            if key.lower() in SENSITIVE_KEYS:
                cleaned[key] = "[REDACTED]"
            else:
                cleaned[key] = redact_sensitive_data(item)

        return cleaned

    if isinstance(value, list):
        return [redact_sensitive_data(item) for item in value]

    return value


class StructuredJsonFormatter(logging.Formatter):
    """Format log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:

        details = getattr(record, "details", {})
        safe_details = redact_sensitive_data(details)

        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", "application.log"),
            "run_id": getattr(record, "run_id", None),
            "correlation_id": getattr(
                record,
                "correlation_id",
                None
            ),
            "message": record.getMessage(),
            "details": safe_details,
        }

        return json.dumps(payload, default=str)


def create_structured_logger(
    stream: StringIO,
    logger_name: str = "invoice_workflow"
) -> logging.Logger:
    """Create a JSON logger writing to the supplied stream."""

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # Avoid duplicate handlers when tests call this more than once.
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(StructuredJsonFormatter())

    logger.addHandler(handler)

    return logger


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    run: WorkflowRun,
    message: str,
    details: dict[str, Any] | None = None
) -> None:
    """Write one structured log record."""

    logger.log(
        level,
        message,
        extra={
            "event": event,
            "run_id": run.run_id,
            "correlation_id": run.correlation_id,
            "details": details or {},
        }
    )


def run_logged_invoice_workflow(
    invoice_data: dict[str, Any],
    stream: StringIO
) -> dict[str, Any]:
    """Validate and process an invoice with structured logs."""

    logger = create_structured_logger(stream)

    # Validate input before starting workflow side effects.
    invoice = InvoiceInput(**invoice_data)
    run = create_workflow(invoice)

    log_event(
        logger,
        logging.INFO,
        "workflow.created",
        run,
        "Invoice workflow created",
        {"invoice_id": invoice.invoice_id}
    )

    transition(run, WorkflowEvent.START)

    log_event(
        logger,
        logging.INFO,
        "workflow.started",
        run,
        "Invoice workflow started",
        {"state": run.state.value}
    )

    # Demonstration of debug-level diagnostic information.
    log_event(
        logger,
        logging.DEBUG,
        "invoice.validation.completed",
        run,
        "Invoice input validation completed",
        {
            "invoice_id": invoice.invoice_id,
            "amount": invoice.amount,
            "currency": invoice.currency,
        }
    )

    # Simulated business processing.
    run.tasks[0].status = "completed"
    run.tasks[1].status = "completed"
    run.tasks[2].status = "completed"

    # Audit event: records a business action without exposing private data.
    log_event(
        logger,
        logging.INFO,
        "audit.invoice.processed",
        run,
        "Invoice processing action recorded",
        {
            "action": "invoice_processed",
            "invoice_id": invoice.invoice_id,
            "business_key": invoice.business_key,
            "outcome": "success",
        }
    )

    transition(run, WorkflowEvent.COMPLETE)

    log_event(
        logger,
        logging.INFO,
        "workflow.completed",
        run,
        "Invoice workflow completed successfully",
        {"state": run.state.value}
    )

    result = WorkflowResult(
        run_id=run.run_id,
        status=run.state.value,
        message="Invoice workflow completed successfully",
        completed_at=datetime.now(timezone.utc)
    )

    return {
        "status": run.state.value,
        "run_id": run.run_id,
        "correlation_id": run.correlation_id,
        "result": result.model_dump(mode="json"),
        "tasks": [
            task.model_dump(mode="json")
            for task in run.tasks
        ],
        "event_count": len(run.events),
        "logging": "structured_json",
    }


def run_task2_fixture() -> dict[str, Any]:
    """Run a deterministic Task 2 scenario and save its evidence."""

    log_stream = StringIO()

    invoice_data = {
        "invoice_id": "INV-TASK2-001",
        "business_key": "BUSINESS-TASK2-001",
        "amount": 25000,
        "currency": "INR",
    }

    result = run_logged_invoice_workflow(
        invoice_data,
        log_stream
    )

    log_lines = [
        json.loads(line)
        for line in log_stream.getvalue().splitlines()
        if line.strip()
    ]

    evidence = {
        "task": "Task 2 - Logging Implementation",
        "workflow_result": result,
        "log_count": len(log_lines),
        "logs": log_lines,
        "audit_events": [
            entry for entry in log_lines
            if entry["event"].startswith("audit.")
        ],
        "redaction_check": "Sensitive fields are redacted by formatter",
    }

    os.makedirs("outputs", exist_ok=True)

    output_path = os.path.join(
        "outputs",
        "task2_logging.json"
    )

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(evidence, file, indent=4, default=str)

    return evidence


if __name__ == "__main__":
    evidence = run_task2_fixture()

    print("=" * 60)
    print("TASK 2 - LOGGING IMPLEMENTATION")
    print("=" * 60)
    print(json.dumps(evidence, indent=4, default=str))
    print("\nEvidence saved to: outputs/task2_logging.json")


# ==================================================
# TASK 3 — FAILURE, RETRY, AND REPLAY SAFETY
# ==================================================

class FailureType(str, Enum):
    TIMEOUT = "timeout"
    MALFORMED_RESPONSE = "malformed_response"
    PERMANENT = "permanent"


class RecoveryAction(str, Enum):
    RETRY = "retry"
    COMPLETED = "completed"
    NEEDS_REVIEW = "needs_review"
    DUPLICATE_PREVENTED = "duplicate_prevented"


MAX_RETRIES = 3


class IdempotencyStore:
    """In-memory store to prevent duplicate invoice side effects."""

    def __init__(self):
        self.processed_keys: set[str] = set()

    def already_processed(self, key: str) -> bool:
        return key in self.processed_keys

    def mark_processed(self, key: str) -> None:
        self.processed_keys.add(key)


def classify_failure(failure: FailureType) -> RecoveryAction:
    """Determine whether a failure is recoverable."""

    if failure == FailureType.TIMEOUT:
        return RecoveryAction.RETRY

    if failure == FailureType.MALFORMED_RESPONSE:
        return RecoveryAction.NEEDS_REVIEW

    return RecoveryAction.NEEDS_REVIEW


def execute_invoice_with_recovery(
    invoice: InvoiceInput,
    outcomes: list[str],
    idempotency_store: IdempotencyStore,
    max_retries: int = MAX_RETRIES,
) -> dict[str, Any]:
    """
    Simulate invoice processing with bounded retries and replay safety.

    Supported outcomes:
      success
      timeout
      malformed_response
      permanent
    """

    if max_retries < 0:
        raise ValueError("max_retries cannot be negative")

    if idempotency_store.already_processed(invoice.business_key):
        return {
            "status": RecoveryAction.DUPLICATE_PREVENTED.value,
            "action": RecoveryAction.DUPLICATE_PREVENTED.value,
            "attempts": 0,
            "business_key": invoice.business_key,
            "message": "Duplicate invoice processing prevented",
        }

    attempts = 0
    recovery_trace = []

    for outcome in outcomes:
        if attempts >= max_retries + 1:
            break

        attempts += 1

        if outcome == "success":
            idempotency_store.mark_processed(invoice.business_key)

            recovery_trace.append({
                "attempt": attempts,
                "outcome": "success",
                "action": RecoveryAction.COMPLETED.value,
            })

            return {
                "status": RecoveryAction.COMPLETED.value,
                "action": RecoveryAction.COMPLETED.value,
                "attempts": attempts,
                "business_key": invoice.business_key,
                "recovery_trace": recovery_trace,
                "message": "Invoice processed successfully",
            }

        try:
            failure = FailureType(outcome)
        except ValueError:
            failure = FailureType.PERMANENT

        action = classify_failure(failure)

        if action == RecoveryAction.RETRY and attempts <= max_retries:
            next_action = RecoveryAction.RETRY
        else:
            next_action = RecoveryAction.NEEDS_REVIEW

        recovery_trace.append({
            "attempt": attempts,
            "outcome": failure.value,
            "action": next_action.value,
        })

        if next_action == RecoveryAction.NEEDS_REVIEW:
            return {
                "status": RecoveryAction.NEEDS_REVIEW.value,
                "action": RecoveryAction.NEEDS_REVIEW.value,
                "attempts": attempts,
                "business_key": invoice.business_key,
                "recovery_trace": recovery_trace,
                "message": "Invoice requires operator review",
            }

    return {
        "status": RecoveryAction.NEEDS_REVIEW.value,
        "action": RecoveryAction.NEEDS_REVIEW.value,
        "attempts": attempts,
        "business_key": invoice.business_key,
        "recovery_trace": recovery_trace,
        "message": "Retry limit reached; operator review required",
    }


def run_task3_fixture() -> dict[str, Any]:
    """Run deterministic recovery, malformed-response, and replay scenarios."""

    store = IdempotencyStore()

    invoice_timeout = InvoiceInput(
        invoice_id="INV-TASK3-001",
        business_key="BUSINESS-TASK3-001",
        amount=18000,
        currency="INR",
    )

    timeout_result = execute_invoice_with_recovery(
        invoice_timeout,
        ["timeout", "timeout", "success"],
        store,
    )

    invoice_malformed = InvoiceInput(
        invoice_id="INV-TASK3-002",
        business_key="BUSINESS-TASK3-002",
        amount=22000,
        currency="INR",
    )

    malformed_result = execute_invoice_with_recovery(
        invoice_malformed,
        ["malformed_response", "success"],
        store,
    )

    # Replaying the successfully processed first invoice must not
    # create another side effect.
    replay_result = execute_invoice_with_recovery(
        invoice_timeout,
        ["success"],
        store,
    )

    evidence = {
        "task": "Task 3 - Failure, Retry, and Replay Safety",
        "max_retries": MAX_RETRIES,
        "scenarios": {
            "timeout_recovery": timeout_result,
            "malformed_response": malformed_result,
            "duplicate_replay": replay_result,
        },
        "summary": {
            "timeout_recovered": (
                timeout_result["status"]
                == RecoveryAction.COMPLETED.value
            ),
            "malformed_response_requires_review": (
                malformed_result["status"]
                == RecoveryAction.NEEDS_REVIEW.value
            ),
            "duplicate_prevented": (
                replay_result["status"]
                == RecoveryAction.DUPLICATE_PREVENTED.value
            ),
        },
    }

    os.makedirs("outputs", exist_ok=True)
    os.makedirs("traces", exist_ok=True)

    with open(
        "outputs/task3_recovery.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(evidence, file, indent=4)

    with open(
        "traces/task3_recovery_traces.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            {
                "timeout_recovery": timeout_result["recovery_trace"],
                "malformed_response": malformed_result["recovery_trace"],
            },
            file,
            indent=4,
        )

    return evidence


# ==================================================
# TASK 4 — INTEGRATION BOUNDARY AND OBSERVABILITY
# ==================================================

from typing import Protocol
from time import perf_counter


class InvoiceAdapter(Protocol):
    """Contract for an external invoice-processing dependency."""

    def process_invoice(self, invoice: InvoiceInput) -> dict[str, Any]:
        ...


class FakeInvoiceAdapter:
    """Deterministic fake dependency for local testing."""

    def __init__(
        self,
        outcome: str = "success",
        response: dict[str, Any] | None = None,
    ):
        self.outcome = outcome
        self.response = response or {}
        self.call_count = 0

    def process_invoice(self, invoice: InvoiceInput) -> dict[str, Any]:
        self.call_count += 1

        if self.outcome == "failure":
            raise RuntimeError("Simulated external dependency failure")

        if self.outcome != "success":
            raise ValueError("Unsupported fake adapter outcome")

        return {
            "status": "success",
            "invoice_id": invoice.invoice_id,
            "business_key": invoice.business_key,
            **self.response,
        }


def run_observable_adapter(
    invoice: InvoiceInput,
    adapter: InvoiceAdapter,
    stream: StringIO,
) -> dict[str, Any]:
    """Call an injected adapter and record structured observability data."""

    logger = create_structured_logger(
        stream,
        logger_name="task4_invoice_workflow",
    )

    run = create_workflow(invoice)
    transition(run, WorkflowEvent.START)

    metrics = {
        "adapter_calls": 0,
        "successful_calls": 0,
        "failed_calls": 0,
        "duration_ms": 0.0,
    }

    start_time = perf_counter()
    metrics["adapter_calls"] += 1

    log_event(
        logger,
        logging.INFO,
        "adapter.call.started",
        run,
        "External invoice adapter call started",
        {"adapter": type(adapter).__name__},
    )

    try:
        response = adapter.process_invoice(invoice)

        if not isinstance(response, dict):
            raise ValueError("Adapter response must be a dictionary")

        if response.get("status") != "success":
            raise ValueError("Adapter returned an unsuccessful response")

        metrics["successful_calls"] += 1
        metrics["duration_ms"] = round(
            (perf_counter() - start_time) * 1000, 3
        )

        log_event(
            logger,
            logging.INFO,
            "adapter.call.completed",
            run,
            "External invoice adapter call completed",
            {
                "adapter": type(adapter).__name__,
                "response_status": response["status"],
                "duration_ms": metrics["duration_ms"],
            },
        )

        transition(run, WorkflowEvent.COMPLETE)
        final_status = "completed"

    except Exception as exc:
        metrics["failed_calls"] += 1
        metrics["duration_ms"] = round(
            (perf_counter() - start_time) * 1000, 3
        )

        # Do not log exception text: it may contain sensitive information.
        log_event(
            logger,
            logging.ERROR,
            "adapter.call.failed",
            run,
            "External invoice adapter call failed",
            {
                "adapter": type(adapter).__name__,
                "error_type": type(exc).__name__,
                "duration_ms": metrics["duration_ms"],
            },
        )

        transition(run, WorkflowEvent.FAIL)
        final_status = "needs_review"
        response = {"status": "failed"}

    trace = {
        "run_id": run.run_id,
        "correlation_id": run.correlation_id,
        "events": [
            event.model_dump(mode="json")
            for event in run.events
        ],
    }

    return {
        "status": final_status,
        "response": redact_sensitive_data(response),
        "metrics": metrics,
        "trace": trace,
    }


def run_task4_fixture() -> dict[str, Any]:
    """Run success and failure scenarios using fake adapters."""

    os.makedirs("outputs", exist_ok=True)
    os.makedirs("traces", exist_ok=True)

    invoice = InvoiceInput(
        invoice_id="INV-TASK4-001",
        business_key="BUSINESS-TASK4-001",
        amount=32000,
        currency="INR",
    )

    success_stream = StringIO()
    success_adapter = FakeInvoiceAdapter(
        outcome="success",
        response={
            "provider_reference": "FAKE-REF-001",
            "api_key": "DO-NOT-EXPOSE-THIS",
            "customer_email": "private@example.com",
        },
    )

    success_result = run_observable_adapter(
        invoice,
        success_adapter,
        success_stream,
    )

    failure_stream = StringIO()
    failure_adapter = FakeInvoiceAdapter(outcome="failure")

    failure_result = run_observable_adapter(
        invoice,
        failure_adapter,
        failure_stream,
    )

    success_logs = [
        json.loads(line)
        for line in success_stream.getvalue().splitlines()
        if line.strip()
    ]

    failure_logs = [
        json.loads(line)
        for line in failure_stream.getvalue().splitlines()
        if line.strip()
    ]

    evidence = {
        "task": "Task 4 - Integration Boundary and Observability",
        "dependency": "FakeInvoiceAdapter",
        "scenarios": {
            "success": success_result,
            "failure": failure_result,
        },
        "adapter_call_counts": {
            "success": success_adapter.call_count,
            "failure": failure_adapter.call_count,
        },
        "logs": {
            "success": success_logs,
            "failure": failure_logs,
        },
        "measurement_report": {
            "success_metrics": success_result["metrics"],
            "failure_metrics": failure_result["metrics"],
            "total_adapter_calls": (
                success_result["metrics"]["adapter_calls"]
                + failure_result["metrics"]["adapter_calls"]
            ),
            "total_successful_calls": (
                success_result["metrics"]["successful_calls"]
                + failure_result["metrics"]["successful_calls"]
            ),
            "total_failed_calls": (
                success_result["metrics"]["failed_calls"]
                + failure_result["metrics"]["failed_calls"]
            ),
        },
        "redaction_check": {
            "api_key": success_result["response"].get("api_key"),
            "customer_email": success_result["response"].get(
                "customer_email"
            ),
        },
    }

    with open(
        "outputs/task4_measurement_report.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(evidence["measurement_report"], file, indent=4)

    with open(
        "outputs/task4_observability.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(evidence, file, indent=4)

    with open(
        "traces/task4_adapter_traces.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            {
                "success": success_result["trace"],
                "failure": failure_result["trace"],
            },
            file,
            indent=4,
        )

    return evidence
