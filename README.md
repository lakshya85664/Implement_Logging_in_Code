# Implement Logging in Code — Workflow Orchestration

## Project overview

This project implements an observable invoice-processing workflow. It models workflow state, records structured events, protects sensitive fields in logs, handles bounded retry and replay scenarios, and isolates an external dependency behind an injectable adapter.

The implementation is a local educational simulation. It uses deterministic fake dependencies and does not connect to a payment provider, ERP, database, or production monitoring service.

## Learning objectives

- Define an explicit workflow contract with typed invoice input, states, events, and legal transitions.
- Emit structured JSON logs with run and correlation identifiers.
- Redact sensitive values before they appear in structured output.
- Classify failures and apply bounded retries.
- Prevent duplicate processing within the lifetime of an in-memory idempotency store.
- Isolate an external dependency behind an adapter contract.
- Record adapter success/failure events, traces, and basic execution metrics.

## Project structure

```text
Implement_Logging_in_Code/
├── workflow_logging.py
├── requirements.txt
├── .gitignore
├── tests/
│   ├── test_task1_contract.py
│   ├── test_task2_logging.py
│   ├── test_task3_recovery.py
│   └── test_task4_observability.py
├── outputs/
│   ├── task2_logging.json
│   ├── task3_recovery.json
│   ├── task4_measurement_report.json
│   └── task4_observability.json
└── traces/
    ├── task3_recovery_traces.json
    └── task4_adapter_traces.json
```

## Environment setup

Run these commands from the project directory in Windows CMD:

```cmd
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run the demonstrations

Task 1 / basic workflow fixture:

```cmd
python -c "from workflow_logging import run_topic_fixture; import json; print(json.dumps(run_topic_fixture(), indent=4))"
```

Task 2 — structured logging:

```cmd
python -c "from workflow_logging import run_task2_fixture; import json; print(json.dumps(run_task2_fixture(), indent=4))"
```

Task 3 — failure, retry, and replay safety:

```cmd
python -c "from workflow_logging import run_task3_fixture; import json; print(json.dumps(run_task3_fixture(), indent=4))"
```

Task 4 — adapter boundary and observability:

```cmd
python -c "from workflow_logging import run_task4_fixture; import json; print(json.dumps(run_task4_fixture(), indent=4))"
```

Run the complete test suite:

```cmd
python -m pytest -v
```

The verified assessment run completed with **26 passed** tests: 6 Task 1 tests, 7 Task 2 tests, 7 Task 3 tests, and 6 Task 4 tests.

## Workflow contract and operational behavior

The workflow states are `created`, `running`, `waiting`, `completed`, and `needs_review`. Legal transitions are explicitly mapped. An illegal transition raises `ValueError`.

Structured log records include timestamps, severity, logger, event name, run ID, correlation ID, message, and details. Sensitive values under configured keys (including API keys, tokens, passwords, email, phone, account number, customer name, and address) are redacted.

Task 3 classifies timeouts as retryable. Malformed responses and permanent failures are sent to operator review. The retry count is bounded by `MAX_RETRIES = 3`, meaning at most four total attempts (one initial attempt plus three retries). A duplicate business key already marked processed is prevented from running again by the in-memory idempotency store.

Task 4 defines an `InvoiceAdapter` protocol and `FakeInvoiceAdapter`. The observable runner records adapter start, completion, or failure events; captures a correlation-linked workflow trace; and reports adapter call counts and elapsed milliseconds. The fake adapter supports deterministic success and failure tests.

## Operator runbook

| Situation | Evidence / signal | Operator action |
|---|---|---|
| Success | Workflow status is `completed`; adapter completion event exists | Confirm the invoice/business reference and retain the trace |
| Timeout | Task 3 recovery trace records timeout and retry actions | Allow only the configured bounded retries; inspect the final status |
| Malformed or permanent failure | Status is `needs_review` | Inspect the safe error type and trace; verify source data/dependency response before an approved manual retry |
| Duplicate replay | Status is `duplicate_prevented` | Do not submit again; check the existing business-key record |
| Adapter failure | `adapter.call.failed` event and `failed_calls` metric | Check dependency availability and error type; escalate for review; do not expose secrets in tickets/logs |

### Evidence and measurement files

- `outputs/task2_logging.json` — Task 2 workflow result and structured log records.
- `outputs/task3_recovery.json` — timeout recovery, malformed response, and duplicate replay scenarios.
- `traces/task3_recovery_traces.json` — per-attempt recovery traces.
- `outputs/task4_observability.json` — adapter success/failure scenarios, logs, redaction check, and metrics.
- `outputs/task4_measurement_report.json` — compact metric summary.
- `traces/task4_adapter_traces.json` — event traces for adapter success and failure.

A verified Task 4 fixture run recorded two adapter calls: one successful and one failed. The successful call recorded one success and zero failures; the failed call recorded zero successes and one failure. Example local durations in the captured run were 0.284 ms and 0.138 ms respectively. Durations vary between runs and are not service-level benchmarks.

## Known limitations

1. The external integration is a fake adapter; no real provider or network call is implemented.
2. The idempotency store is in-memory and is lost when the process exits. Production use requires durable, atomic storage and concurrency-safe uniqueness.
3. The retry fixture simulates outcomes; it does not implement real network timeouts, backoff delays, or cancellation.
4. Metrics are local counters and elapsed-time measurements, not a production metrics backend.
5. Redaction is key-based. Production systems should also review free-text messages, exception payloads, nested provider objects, and any newly introduced sensitive fields.
6. The workflow and traces are demonstration artifacts and are not a substitute for durable audit storage.

## Reflection

This project helped me understand that logging is not simply printing messages when something goes wrong. In a workflow, logs, state transitions, correlation identifiers, retry decisions, and audit events must work together so that an operator can reconstruct what happened. I began by defining a typed invoice contract and explicit workflow states. This made valid transitions clear and allowed illegal transitions to fail early instead of silently changing the workflow.

The structured logging task showed the value of machine-readable JSON. Including run IDs and correlation IDs makes events from one execution easier to follow, while severity levels distinguish normal progress from diagnostic information and failures. I also implemented key-based redaction so sensitive values such as API keys and customer email addresses are not exposed in the generated evidence. This reinforced that observability must be designed with data protection in mind.

The retry and replay exercises clarified why not every failure should be retried. A timeout may be temporary, whereas a malformed response or permanent failure should be sent for review. A bounded retry policy prevents endless attempts, and an idempotency key helps prevent duplicate business actions. The in-memory implementation is suitable for this assessment, but a real system would need persistent, atomic storage.

Finally, the adapter exercise demonstrated the benefit of separating workflow logic from external services. An injectable interface and fake adapter made success and failure behavior testable without a live dependency. The traces and metrics provide useful evidence, although they are only local measurements. Overall, the project improved my understanding of building workflows that are easier to debug, test, operate, and extend safely.
