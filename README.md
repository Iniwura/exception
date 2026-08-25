# Exception

Exception is a GenLayer Intelligent Contract for deciding whether a real-world situation legitimately qualifies for a predefined exception to a deterministic rule.

Traditional smart contracts are good at enforcing rules such as:

`condition met -> execute`

`condition not met -> reject`

But many real agreements contain clauses like:

> Late submissions are rejected except where the delay resulted from circumstances outside the participant's reasonable control.

That final judgment is difficult to encode deterministically. Exception isolates that subjective step and resolves it through GenLayer validator consensus.

## Core flow

`Base rule + exception clause + case + evidence -> GenLayer consensus -> GRANTED / DENIED / INCONCLUSIVE`

A deterministic system can therefore fail its normal rule, ask Exception whether the agreed exception applies, and then continue or reject based on the returned verdict.

## Why GenLayer

Exception depends on interpretation rather than arithmetic. Validators must read the predefined natural-language exception clause, examine the case and submitted evidence, and decide whether the circumstances fall within that clause.

The contract uses `gl.vm.run_nondet` and independent validator evaluation. Consensus compares only the state-changing verdict, not free-form reasoning, so validators may explain the same conclusion differently without causing unnecessary disagreement.

Supported verdicts:

- `GRANTED` — the evidence supports applying the exception.
- `DENIED` — the evidence does not satisfy the exception clause.
- `INCONCLUSIVE` — the available evidence is insufficient for a reliable decision.

## Contract design

### Definitions

The contract owner creates exception definitions containing:

- deterministic base rule
- natural-language exception clause
- creator-scoped reference
- creator address
- deterministic SHA-256 fingerprint

Definitions are stored before any case is evaluated, so the exception terms cannot be rewritten after seeing a particular dispute.

### Cases

Any caller can submit a case against an existing definition with:

- case description
- evidence
- submitter-scoped reference
- submitter address
- definition ID
- deterministic SHA-256 fingerprint

New cases begin in `PENDING` state.

### Resolution

`resolve_case(case_id)` asks GenLayer validators whether the submitted circumstances satisfy the stored exception clause.

The model output is strictly validated and must contain exactly:

```json
{
  "verdict": "GRANTED | DENIED | INCONCLUSIVE",
  "reasoning": "..."
}
```

After successful consensus, the case becomes `RESOLVED` and the final verdict and leader reasoning are persisted onchain. A resolved case cannot be resolved again.

State is updated only after consensus succeeds, preventing failed or malformed resolutions from partially mutating a case.

## Public methods

### Writes

- `create_definition(base_rule, exception_clause, reference)`
- `submit_case(definition_id, case_description, evidence, case_reference)`
- `resolve_case(case_id)`

### Views

- `ping()`
- `get_definition_count()`
- `get_case_count()`
- `get_definition(definition_id)`
- `get_case(case_id)`
- `is_definition_reference_used(creator, reference)`
- `is_case_reference_used(submitter, reference)`

## Testing

The contract has a comprehensive direct-mode test suite covering:

- definition creation
- owner-only definition creation
- creator-scoped references
- case creation
- submitter-scoped case references
- `GRANTED`
- `DENIED`
- `INCONCLUSIVE`
- malformed model responses
- same verdict with different reasoning
- validator disagreement on different verdicts
- duplicate resolution prevention
- persistence
- deterministic fingerprints
- invalid IDs
- empty and oversized input rejection
- failed resolution without partial state mutation

Final local verification:

```text
23 passed
```

Python syntax checks also passed before deployment.

## Bradbury deployment

Network: GenLayer Bradbury

Contract:

```text
0x5881B3312124caaD9b901577951C22c1C34723df
```

Deployment transaction:

```text
0xfcd3dca5b795514b2d69f718d6bfed5ce334f6dea8759088a35dcbdc3bf4e88a
```

Deployment completed with:

```text
ACCEPTED
AGREE
FINISHED_WITH_RETURN
```

`ping()` returned:

```text
exception-v1
```

## Live Bradbury proof

A live definition was created with the rule:

> Grant milestones submitted after August 30 are rejected.

and the exception clause:

> A late milestone may be accepted when the delay resulted from circumstances outside the participant's reasonable control.

Definition transaction:

```text
0x38bf70283d55996a5b15e5826d8fca99cc2442bfa1843a896396fa671b54d795
```

A case was submitted describing a September 2 milestone submission with evidence that a critical deployment provider outage prevented timely submission.

GenLayer resolved the case to:

```text
GRANTED
```

Resolution transaction:

```text
0x51b6d0f99e413e506b41e3c6165861e3eebe91567e64de1ab9212152f72481e0
```

The transaction completed with `ACCEPTED / AGREE / FINISHED_WITH_RETURN`; four validators agreed and one timed out. Reading the case afterward confirmed persisted state:

```text
status: RESOLVED
verdict: GRANTED
```

The stored reasoning was:

> The delay was caused by a critical deployment provider outage, which is outside the participant's reasonable control.

## Example applications

Exception can act as an interpretation layer beside deterministic contracts for:

- grant deadlines
- insurance exclusions and exceptions
- escrow release conditions
- SLA exceptions
- procurement rules
- DAO programs
- vesting conditions
- service agreements
- deadline and force-majeure style clauses

The deterministic contract remains responsible for normal execution. Exception handles only the part conventional smart contracts struggle with: deciding whether real-world circumstances fall within a previously agreed natural-language exception.

## Development

Install dependencies in a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the test suite:

```bash
gltest
```

Deploy to Bradbury with the GenLayer CLI:

```bash
genlayer deploy \
  --contract contracts/exception.py \
  --rpc https://rpc-bradbury.genlayer.com
```

## License

MIT
