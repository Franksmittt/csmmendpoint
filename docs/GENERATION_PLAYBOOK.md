# Content generation playbook (Endpoint Media CRM)

## How the pipeline uses client data

CrewAI receives from SQLite (via Streamlit):

| Field | Used for |
|-------|----------|
| `company_name`, `industry` | Agent roles + grounding |
| `brand_context` | **Strategy + creative truth** (include visual identity here for image prompts) |
| `tone` | Voice constraints |
| `services_list` | Concrete services/brands/promotions to cite |
| `target_markets` | Audience framing |
| `photography_style` | **Camera / lens / lighting / anti-AI-gloss rules** for `Image_Generation_Prompt` |
| + `post_format`, `content_pillar` | Per-run instructions |
| **Featured brand** (UI) | Optional co-brand from `src/config/brand_vault.py` — slogans, HEX/visual rules, psychology |

**Rule:** If it’s not in the client row, the model may hallucinate. Keep `brand_context` and `services_list` **current**.

## Brand bibles (per client)

- Index: [brands/README.md](./brands/README.md)
- **Alberton Tyre Clinic:** [brands/alberton-tyre-clinic.md](./brands/alberton-tyre-clinic.md)

## Operator checklist (each generate)

1. Correct **client** selected.
2. **Format** matches where the asset will run (1:1 feed vs 9:16 story).
3. **Pillar** matches the campaign (one pillar per run — tasks enforce this).
4. **Plan Summary** (Intent Preview) read for sanity.
5. After run: check **caption**, **image prompt** (aspect ratio + brand colours), **Heading/Footer** overlay JSON.

## Syncing Alberton from the bible

**Option A — UI:** Edit client in CRM; paste the four blocks from `docs/brands/alberton-tyre-clinic.md`.

**Option B — Script:** From repo root (after `uv sync`):

```bash
uv run python scripts/upsert_alberton_brand.py
```

Updates the row whose `company_name` contains `Alberton Tyre Clinic` (case-insensitive). Adjust the name in the script if your DB label differs.

## Editing agent behaviour

- Agents: `src/config/agents.yaml`
- Tasks: `src/config/tasks.yaml`

Global rules (e.g. “image prompt must follow visual DNA in `brand_context`”) live in **tasks** so every client benefits; client-specific detail stays in **CRM + brand markdown**.
