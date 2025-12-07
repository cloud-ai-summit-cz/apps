# Agent Service Security Notes

Detail the threat model and controls unique to this service. Align with `../../platform/SECURITY.md`.

## Threat Model Snapshot
| Asset | Threat | Mitigation |
| --- | --- | --- |
| Chat sessions | Cross-tenant data leakage | HPK isolation (`ownerId`, `sessionId`); enforce owner on every read/write; Cosmos RBAC via Managed Identity |
| Tool orchestration | Prompt injection leading to unwanted actions | Strict tool allow-list; user input sanitization; model system prompts enforce constraints; require confirmation for mutating tools |
| Downstream calls | Unauthorized orders/actions | Forward caller token; verify scopes with Toy/Trip/Add-on services; audit tool logs |
| OpenAI access | Token/key exposure | Managed Identity to Azure OpenAI; no static keys in code or repo |

## Controls Checklist
- Authentication/Authorization: Bearer JWT required; only owners may access sessions; system scope `System.AgentWorker` allowed for async completions.
- Secrets handling: Managed Identity for Cosmos/OpenAI/Service Bus; no shared secrets; redact user content in logs.
- Network: Internal-only via gateway; rate limit chat endpoint to protect downstreams.
- Data protection: Truncate stored chat history; avoid storing raw tool responses if sensitive.

## Testing & Monitoring
- Security tests: cross-tenant access attempts; prompt-injection guardrails; authorization on mutating tool calls.
- Monitoring: `auth_failures_total{service="agent"}`; alerts on surge in denied tool calls.

## Exceptions
- None; document if temporary key-based Azure OpenAI access is ever needed.