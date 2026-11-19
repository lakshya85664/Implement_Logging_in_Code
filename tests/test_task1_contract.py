
import pytest

from workflow_logging import (
    InvoiceInput,
    WorkflowEvent,
    WorkflowState,
    create_workflow,
    transition,
)


def sample_invoice():
    return InvoiceInput(
        invoice_id="INV-1001",
        business_key="BUSINESS-1001",
        amount=15000,
        currency="INR"
    )


def test_workflow_creation():
    run = create_workflow(sample_invoice())

    assert run.state == WorkflowState.CREATED
    assert run.run_id
    assert run.correlation_id
    assert len(run.tasks) == 3


def test_legal_transition():
    run = create_workflow(sample_invoice())

    transition(run, WorkflowEvent.START)

    assert run.state == WorkflowState.RUNNING


def test_illegal_transition():
    run = create_workflow(sample_invoice())

    with pytest.raises(ValueError):
        transition(run, WorkflowEvent.COMPLETE)


def test_workflow_completion():
    run = create_workflow(sample_invoice())

    transition(run, WorkflowEvent.START)
    transition(run, WorkflowEvent.COMPLETE)

    assert run.state == WorkflowState.COMPLETED


def test_pause_and_resume():
    run = create_workflow(sample_invoice())

    transition(run, WorkflowEvent.START)
    transition(run, WorkflowEvent.PAUSE)

    assert run.state == WorkflowState.WAITING

    transition(run, WorkflowEvent.RESUME)

    assert run.state == WorkflowState.RUNNING


def test_event_trace_records_correlation_id():
    run = create_workflow(sample_invoice())

    transition(run, WorkflowEvent.START)

    assert len(run.events) == 2
    assert run.events[-1].correlation_id == run.correlation_id
    assert run.events[-1].event == "start"
