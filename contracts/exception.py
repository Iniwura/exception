# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import hashlib
import json
import typing

from genlayer import *


MAX_RULE_LENGTH = 8000
MAX_CLAUSE_LENGTH = 8000
MAX_CASE_LENGTH = 8000
MAX_EVIDENCE_LENGTH = 12000
MAX_REFERENCE_LENGTH = 128
MAX_REASONING_LENGTH = 10000


def _require_text(value: str, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must not be empty")
    if len(value) > maximum:
        raise ValueError(f"{field} is too long")
    return value


def _address(value: Address) -> str:
    if isinstance(value, bytes):
        return "0x" + value.hex()
    return str(value).lower().strip()


def _fingerprint(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _parse_response(response: typing.Any) -> dict:
    if isinstance(response, str):
        response = json.loads(response)
    if type(response) is not dict or set(response.keys()) != {"verdict", "reasoning"}:
        raise ValueError("model response must contain only verdict and reasoning")

    verdict = response["verdict"]
    reasoning = response["reasoning"]
    if type(verdict) is not str or verdict not in {"GRANTED", "DENIED", "INCONCLUSIVE"}:
        raise ValueError("model response contains an invalid verdict")
    if type(reasoning) is not str or not reasoning.strip():
        raise ValueError("model reasoning must be a non-empty string")
    if len(reasoning) > MAX_REASONING_LENGTH:
        raise ValueError("model reasoning is too long")
    return {"verdict": verdict, "reasoning": reasoning}


@allow_storage
class Definition:
    base_rule: str
    exception_clause: str
    reference: str
    creator: str
    fingerprint: str


@allow_storage
class Case:
    definition_id: u256
    case_description: str
    evidence: str
    reference: str
    submitter: str
    fingerprint: str
    status: str
    verdict: str
    reasoning: str


class Exception(gl.Contract):
    owner: Address
    definition_count: u256
    case_count: u256
    definitions: TreeMap[u256, Definition]
    cases: TreeMap[u256, Case]
    definition_references: TreeMap[str, bool]
    case_references: TreeMap[str, bool]

    def __init__(self):
        self.owner = gl.message.sender_address
        self.definition_count = u256(0)
        self.case_count = u256(0)

    @staticmethod
    def _reference_key(creator: str, reference: str) -> str:
        return creator + "\x00" + reference

    @staticmethod
    def _validate_id(identifier: int, count: u256, label: str) -> None:
        if type(identifier) is not int or identifier < 0 or identifier >= int(count):
            raise ValueError(f"unknown {label} id")

    @gl.public.view
    def ping(self) -> str:
        return "exception-v1"

    @gl.public.write
    def create_definition(
        self, base_rule: str, exception_clause: str, reference: str
    ) -> int:
        if gl.message.sender_address != self.owner:
            raise gl.vm.UserError("only owner can create definitions")
        _require_text(base_rule, "base rule", MAX_RULE_LENGTH)
        _require_text(exception_clause, "exception clause", MAX_CLAUSE_LENGTH)
        _require_text(reference, "reference", MAX_REFERENCE_LENGTH)

        creator = _address(gl.message.sender_address)
        reference_key = self._reference_key(creator, reference)
        if self.definition_references.get(reference_key, False):
            raise ValueError("reference already used by creator")

        definition_id = self.definition_count
        fingerprint = _fingerprint({
            "base_rule": base_rule,
            "exception_clause": exception_clause,
            "reference": reference,
            "creator": creator,
        })
        definition = Definition()
        definition.base_rule = base_rule
        definition.exception_clause = exception_clause
        definition.reference = reference
        definition.creator = creator
        definition.fingerprint = fingerprint
        self.definitions[definition_id] = definition
        self.definition_references[reference_key] = True
        self.definition_count += u256(1)
        return int(definition_id)

    @gl.public.write
    def submit_case(
        self,
        definition_id: int,
        case_description: str,
        evidence: str,
        case_reference: str,
    ) -> int:
        self._validate_id(definition_id, self.definition_count, "definition")
        _require_text(case_description, "case description", MAX_CASE_LENGTH)
        _require_text(evidence, "evidence", MAX_EVIDENCE_LENGTH)
        _require_text(case_reference, "case reference", MAX_REFERENCE_LENGTH)

        submitter = _address(gl.message.sender_address)
        reference_key = self._reference_key(submitter, case_reference)
        if self.case_references.get(reference_key, False):
            raise ValueError("case reference already used by submitter")

        case_id = self.case_count
        fingerprint = _fingerprint({
            "definition_id": definition_id,
            "case_description": case_description,
            "evidence": evidence,
            "reference": case_reference,
            "submitter": submitter,
        })
        case = Case()
        case.definition_id = u256(definition_id)
        case.case_description = case_description
        case.evidence = evidence
        case.reference = case_reference
        case.submitter = submitter
        case.fingerprint = fingerprint
        case.status = "PENDING"
        case.verdict = ""
        case.reasoning = ""
        self.cases[case_id] = case
        self.case_references[reference_key] = True
        self.case_count += u256(1)
        return int(case_id)

    def _prompt(self, case_id: int) -> str:
        definition = self.definitions[self.cases[case_id].definition_id]
        case = self.cases[case_id]
        return (
            "Determine whether the case qualifies for the exception clause to the base rule.\n\n"
            "BASE RULE:\n" + definition.base_rule + "\n\n"
            "EXCEPTION CLAUSE:\n" + definition.exception_clause + "\n\n"
            "CASE:\n" + case.case_description + "\n\n"
            "EVIDENCE:\n" + case.evidence + "\n\n"
            "Return JSON with exactly two keys: verdict and reasoning. verdict must be "
            "exactly GRANTED, DENIED, or INCONCLUSIVE. GRANTED means the evidence "
            "supports the exception, DENIED means it does not, and INCONCLUSIVE means "
            "the information is insufficient. reasoning must be a concise explanation."
        )

    @gl.public.write
    def resolve_case(self, case_id: int) -> dict:
        self._validate_id(case_id, self.case_count, "case")
        if self.cases[case_id].status != "PENDING":
            raise ValueError("case has already been resolved")
        prompt = self._prompt(case_id)

        def leader():
            return gl.nondet.exec_prompt(prompt, response_format="json")

        def validator(result):
            if not isinstance(result, gl.vm.Return):
                return False
            try:
                leader_response = _parse_response(result.calldata)
                validator_response = _parse_response(
                    gl.nondet.exec_prompt(prompt, response_format="json")
                )
                return leader_response["verdict"] == validator_response["verdict"]
            except Exception:
                return False

        response = _parse_response(gl.vm.run_nondet(leader, validator))
        case = self.cases[case_id]
        case.status = "RESOLVED"
        case.verdict = response["verdict"]
        case.reasoning = response["reasoning"]
        return response

    @gl.public.view
    def get_definition_count(self) -> u256:
        return self.definition_count

    @gl.public.view
    def get_case_count(self) -> u256:
        return self.case_count

    @gl.public.view
    def get_definition(self, definition_id: int) -> dict:
        self._validate_id(definition_id, self.definition_count, "definition")
        definition = self.definitions[definition_id]
        return {
            "id": definition_id,
            "base_rule": definition.base_rule,
            "exception_clause": definition.exception_clause,
            "reference": definition.reference,
            "creator": definition.creator,
            "fingerprint": definition.fingerprint,
        }

    @gl.public.view
    def get_case(self, case_id: int) -> dict:
        self._validate_id(case_id, self.case_count, "case")
        case = self.cases[case_id]
        return {
            "id": case_id,
            "definition_id": int(case.definition_id),
            "case_description": case.case_description,
            "evidence": case.evidence,
            "reference": case.reference,
            "submitter": case.submitter,
            "fingerprint": case.fingerprint,
            "status": case.status,
            "verdict": case.verdict,
            "reasoning": case.reasoning,
        }

    @gl.public.view
    def is_definition_reference_used(self, creator: Address, reference: str) -> bool:
        return self.definition_references.get(
            self._reference_key(_address(creator), reference), False
        )

    @gl.public.view
    def is_case_reference_used(self, submitter: Address, reference: str) -> bool:
        return self.case_references.get(
            self._reference_key(_address(submitter), reference), False
        )