# Client brand bibles

Structured **source-of-truth** docs for CrewAI + the Streamlit CRM. Each file contains:

- Paste-ready **Brand context**, **Tone**, **Services/brands**, **Target markets**
- **Visual rules** for `Image_Generation_Prompt` (must match website aesthetic)
- **Voice guardrails** (what to say / what to avoid)
- **Pillar mapping** — how dashboard “Content pillar” options map to real campaigns

## Clients

| Client | Doc |
|--------|-----|
| Alberton Tyre Clinic | [alberton-tyre-clinic.md](./alberton-tyre-clinic.md) |

## Workflow

1. Open the client’s markdown bible.
2. In **Endpoint Media CRM** → onboard or edit the client → paste the four CRM blocks into the matching fields.
3. In **Generation Hub**, pick format + pillar → **Authorize & Execute Plan**.
4. When changing website copy or offers, **update the bible first**, then sync the CRM (manual paste or `scripts/upsert_alberton_brand.py`).

See also: [GENERATION_PLAYBOOK.md](../GENERATION_PLAYBOOK.md).
