# Project Personas

Personas for **Tech-Letter for HYL**. Product personas only — no Team / Three Amigos coverage in this project (solo author).

**Last updated:** 2026-05-19

---

## Team Personas

_None. This is a solo side project; the author is also the engineer. If team consultation becomes useful later, add archetypes via `/sdlc-studio persona create`._

---

## Stakeholder Personas

### End Users

| Persona | Role | Summary | File |
|---------|------|---------|------|
| HYL | Author / Editor | Curates and approves each weekly issue; values signal-over-noise and minimal weekly effort. | [Details](stakeholders/users/hyl-author.md) |
| Researcher Subscriber | Reader | Research-aware engineer who reads papers AND ships LLM-backed features; values rigour + production reality. | [Details](stakeholders/users/researcher-subscriber.md) |

### Archived

| Persona | Status | Notes |
|---------|--------|-------|
| Practitioner Subscriber | Archived as of PRD v0.4.0 | Non-coder knowledge worker. Scoped out — newsletter audience narrowed to research-aware engineers only. File preserved at [archived/practitioner-subscriber.md](archived/practitioner-subscriber.md) for reference if reintroduced. |

### Business Stakeholders

_None._

### Technical Stakeholders

_None._

---

## Consultation Defaults

For this project (solo / no Team personas), the default consultation pool is just the End Users.

| Artefact | Default consult |
|----------|-----------------|
| PRD | All three end-user personas |
| Epic | HYL + the subscriber persona most affected by the epic |
| User Story | The primary persona named in the story |
| Technical Spec | HYL (no separate engineering persona) |
| Test Strategy | HYL |

Override with `--persona` or skip with `--skip-personas`.

---

## Persona Sources

| Source | Count | Notes |
|--------|-------|-------|
| Archetypes | 0 | None used |
| Generated | 0 | Created interactively, not generated from PRD/code |
| Imported | 0 | — |
| Custom | 3 | All authored for this project |

---

## Usage

```bash
# Consult one persona on the PRD
/sdlc-studio consult hyl-author sdlc-studio/prd.md

# Consult all stakeholders (default for PRD)
/sdlc-studio consult stakeholders sdlc-studio/prd.md

# Interactive chat with a subscriber persona
/sdlc-studio chat researcher-subscriber

# Workshop a design decision across all three
/sdlc-studio chat --workshop "How to handle papers vs. tools balance" --context sdlc-studio/prd.md
```

---

*See [reference-persona.md](../../reference-persona.md) for full persona workflows.*
