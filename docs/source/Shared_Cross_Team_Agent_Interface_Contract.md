# Fashion Commerce Platform - Shared Cross-Team Agent Interface Contract

## Source-of-truth ownership
Side A owns market, product, claim, price, factory, quality, policy and operating truth. Side B owns schema, API, software state, security, build, deployment and runtime truth. Shared decisions require a decision-log record. Neither agent may silently invent or overwrite the other side's source truth.

## Handoff requirements
Every handoff contains a stable ID, sender/receiver, work-package and artifact IDs, purpose, files/data, schema/version, confirmed facts, assumptions, questions, acceptance criteria, validation steps, need-by gate/date, impact, fallback and change-control statement. The receiver must explicitly accept, conditionally accept or reject it.

## Evidence statuses
DRAFT, SELF-VALIDATED, AUTOMATED-TESTED, HUMAN-VERIFIED, EXTERNALLY-VERIFIED, BLOCKED and REJECTED are the only valid readiness statuses.

## Gate rule
No calendar deadline overrides a failed gate. Conditional launch requires a named risk owner, explicit impact, compensating control and recorded go/no-go authority.

## External reality boundary
Physical inspections, laboratory tests, factory audits, signed contracts, legal/tax/customs conclusions, registrations, provider approvals, real shipment results and app-store approval require human or external evidence. An agent prepares and controls those actions but does not fabricate them.
