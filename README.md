# Exception

Exception is a GenLayer Intelligent Contract for adjudicating whether a submitted case qualifies for a predefined natural-language exception to a deterministic rule.

Traditional smart contracts are good at enforcing deterministic conditions. Real agreements often contain exceptions that require interpretation. Exception isolates that subjective step and binds the result through GenLayer validator consensus.

## Core flow

`Base rule + exception clause + submitted case record -> GenLayer consensus -> GRANTED / DENIED / INCONCLUSIVE`

A deterministic integration can fail its normal rule, ask Exception whether a previously agreed exception applies to the submitted record, and then continue or reject based on the persisted verdict.

## Trust model

Exception is deliberately an adjudication primitive over a caller-supplied case record.

The stored base rule and exception clause define what validators must interpret. `case_description` and `evidence` are caller-supplied inputs and are authoritative only as the record being adjudicated. Exception does not claim that those inputs independently prove external real-world facts, authenticate provenance, or establish that an event actually occurred.

For example, if the submitted record says that a deployment-provider outage caused a delay, Exception answers: does that submitted circumstance satisfy the stored exception clause? It does not answer: did the outage independently occur?

Integrations that require authenticated external facts should verify or acquire those facts before submitting the case record, or use a separate evidence-acquisition primitive. This boundary is intentional and keeps Exception focused on reusable policy interpretation rather than external fact acquisition.

## Why GenLayer

Exception depends on interpretation rather than arithmetic. Validators independently evaluate the same stored rule, stored exception clause, case description, and evidence.

Resolution uses `gl.vm.run_nondet`. The leader produces a structured verdict and reasoning. Validators independently prompt on the same case record and compare the decision-bearing `verdict`. Free-form reasoning may differ without changing the state transition.

Supported verdicts:

- `GRANTED` — the submitted record supports applying the exception.
- `DENIED` — the submitted record does not satisfy the exception clause.
- `INCONCLUSIVE` — the submitted record is insufficient for a reliable decision.

## Consensus and state boundary

The contract keeps deterministic state handling separate from nondeterministic interpretation:

1. Definitions and cases are stored deterministically.
2. A deterministic prompt is built from the stored rule and submitted case record.
3. The leader and validators perform nondeterministic model evaluation inside `gl.vm.run_nondet`.
4. Validators bind consensus to the normalized verdict.
5. Only after consensus succeeds does the contract mutate the case to `RESOLVED` and persist the verdict and reasoning.

A failed consensus does not partially resolve the case. A resolved case cannot be resolved again.

## Prompt isolation

All evaluation fields are serialized into a single JSON payload:

- base rule
- exception clause
- case description
- evidence

The evaluation policy is kept outside that payload. Validators are explicitly instructed to treat payload contents as untrusted case data rather than instructions and to ignore embedded commands, role changes, fake system messages, output-format instructions, and verdict overrides.

This preserves the adjudication semantics while reducing the ability of adversarial case text to impersonate contract instructions.

## Contract design

### Definitions

The owner creates definitions containing a deterministic base rule, natural-language exception clause, scoped reference, creator identity, and deterministic SHA-256 fingerprint. Definitions are committed before cases are evaluated, preventing exception terms from being rewritten after a dispute appears.

### Cases

Any caller can submit a case against an existing definition. Cases contain the definition ID, case description, evidence, submitter-scoped reference, submitter identity, and deterministic SHA-256 fingerprint. New cases begin as `PENDING`.

### Resolution

`resolve_case(case_id)` asks GenLayer validators whether the submitted circumstances satisfy the stored exception clause relative to the base rule.

Model output is strictly validated and must contain exactly:

```json
{
  "verdict": "GRANTED | DENIED | INCONCLUSIVE",
  "reasoning": "..."
}
```

After successful consensus, the case becomes `RESOLVED`; the verdict and leader reasoning are persisted onchain.

## Public methods

Writes:

- `create_definition(base_rule, exception_clause, reference)`
- `submit_case(definition_id, case_description, evidence, case_reference)`
- `resolve_case(case_id)`

Views:

- `ping()`
- `get_definition_count()`
- `get_case_count()`
- `get_definition(definition_id)`
- `get_case(case_id)`
- `is_definition_reference_used(creator, reference)`
- `is_case_reference_used(submitter, reference)`

## Verification

The exact source deployed below was checked with the current GenVM linter:

```text
genvm-lint check contracts/exception.py

✓ Lint passed (3 checks)
✓ Validation passed
  Contract: Exception
  Methods: 10 (7 view, 3 write)
```

The complete local test suite also passes:

```text
gltest test/test_exception.py -q
............................. [100%]
29 passed
```

The suite covers `GRANTED`, `DENIED`, and `INCONCLUSIVE` resolutions; strict model-output validation; persistence; replay-protected scoped references; fingerprints; invalid and oversized inputs; failed resolution without partial state mutation; validator agreement/disagreement behavior; and adversarial prompt-injection payloads across the rule, exception clause, case description, and evidence.

## Current Bradbury deployment

Network: GenLayer Bradbury

Contract:

```text
0x89B56fCae62BF0099778e18534999731F99Ba892
```

Deployment transaction:

```text
0x4dcfa7da476a3466c31e89846b67557ded3af901bbcd522841a8e311b9a71224
```

Deployment consensus completed with validator agreement and `FINISHED_WITH_RETURN`.

Live `ping()` returns:

```text
exception-v1
```

Explorer:

- Contract: https://explorer-bradbury.genlayer.com/address/0x89B56fCae62BF0099778e18534999731F99Ba892
- Deployment transaction: https://explorer-bradbury.genlayer.com/tx/0x4dcfa7da476a3466c31e89846b67557ded3af901bbcd522841a8e311b9a71224

## Live Bradbury adjudication

A fresh definition was created on the current lint-clean deployment:

```text
Base rule:
Grant milestones submitted after August 30 are rejected.

Exception clause:
A late milestone may be accepted when the delay resulted from circumstances outside the participant's reasonable control.

Reference:
grant-deadline-v2-001
```

Definition transaction:

```text
0xf5e8959ece5c5a90b18dd9bf69ecf27ab99a6fc731b074ca64ec8678dd66d6ee
```

A case was then submitted:

```text
Case:
The grant milestone was submitted on September 2, after the August 30 deadline.

Evidence:
A critical deployment provider outage prevented submission during the deadline window.

Reference:
grant-case-v2-001
```

Case submission transaction:

```text
0x61610571e0de50d2ec39928c0ddf9841343ddda33e5061148dccc1691b79ca64
```

Reading case `0` after resolution confirmed persisted state:

```text
status: RESOLVED
verdict: GRANTED
reasoning: The evidence describes a critical provider outage outside the participant's control, which directly satisfies the exception clause for delays beyond reasonable control.
```

This live result demonstrates the intended primitive: GenLayer interprets whether the authoritative submitted case record falls within a previously committed natural-language exception, and persists the consensus result for downstream deterministic use.

## Reviewer links

- Repository: https://github.com/Iniwura/exception
- Contract source: https://github.com/Iniwura/exception/blob/main/contracts/exception.py
- Tests: https://github.com/Iniwura/exception/blob/main/test/test_exception.py
- README: https://github.com/Iniwura/exception/blob/main/README.md
- Bradbury contract: https://explorer-bradbury.genlayer.com/address/0x89B56fCae62BF0099778e18534999731F99Ba892
- Deployment transaction: https://explorer-bradbury.genlayer.com/tx/0x4dcfa7da476a3466c31e89846b67557ded3af901bbcd522841a8e311b9a71224
- Definition transaction: https://explorer-bradbury.genlayer.com/tx/0xf5e8959ece5c5a90b18dd9bf69ecf27ab99a6fc731b074ca64ec8678dd66d6ee
- Case submission transaction: https://explorer-bradbury.genlayer.com/tx/0x61610571e0de50d2ec39928c0ddf9841343ddda33e5061148dccc1691b79ca64

## Example applications

Exception can serve as an interpretation layer beside deterministic contracts for grant deadlines, insurance exceptions, escrow conditions, SLAs, procurement rules, DAO programs, vesting conditions, service agreements, and force-majeure-style clauses.

The deterministic integration remains responsible for normal execution and for any external evidence-authentication requirements. Exception handles the interpretation step: deciding whether the submitted circumstances fall within a previously agreed natural-language exception.

## Development

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the current acceptance checks:

```bash
genvm-lint check contracts/exception.py
gltest test/test_exception.py -q
```

Deploy to Bradbury:

```bash
genlayer deploy \
  --contract contracts/exception.py \
  --rpc https://rpc-bradbury.genlayer.com
```

## License

MIT
