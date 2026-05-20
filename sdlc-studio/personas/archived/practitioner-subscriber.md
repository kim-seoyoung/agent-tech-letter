# Practitioner Subscriber

## Quick Reference

| Attribute | Value |
|-----------|-------|
| **Category** | Stakeholder |
| **Amigo** | n/a |
| **Role** | Reader of the newsletter; less knowledge about coding |
| **Age** | adult professional |
| **Experience** | uses LLM agents for paper work and analyzing text, Excel files, and similar documents |
| **Technical Level** | Advanced (as a *user* of LLM agents — not as a coder) |

## Identity

### Who They Are

A knowledge worker — analyst, consultant, domain researcher, policy/legal/finance professional, or a non-CS academic — whose work involves a lot of reading, extracting, summarising, and cross-referencing. They have adopted LLM agents (Claude, ChatGPT, agentic copilots, custom GPTs, Notion AI, etc.) as a daily tool for that work, but they are not a programmer. They prompt; they don't pip-install. They subscribe to *Tech-Letter for HYL* because they want to know which LLM-agent tools and workflows are actually worth trying for their kind of work.

### Personality Traits

- **Tool-curious, not framework-curious:** they will happily try a new agent product if someone explains what it does and what kind of work it helps with. They are not going to learn what "RAG" is to evaluate it.
- **Outcome-oriented:** "does this make my next document-heavy week easier?" is the only test that matters.
- **Skeptical of demos:** has watched too many "look what AI did!" threads that don't survive contact with their actual messy PDFs or 30-tab spreadsheets.

### Communication Style

- **Formality:** Casual
- **Verbosity:** Wants concise, plain-language summaries; tunes out as soon as the writing turns into jargon (e.g., "function-calling schema," "token-level reranking")
- **Directness:** Practical; "what would this let me do tomorrow morning?" is their working question

## Professional Context

### Background

Works in a knowledge-heavy domain — law, finance, research, policy, consulting, science adjacent — where the daily reality is a stack of PDFs, transcripts, datasets, and spreadsheets that need to be read, compared, and summarised. Adopted ChatGPT or Claude early as a productivity tool; has since branched into agent products and "chat with your documents" workflows.

### Expertise Areas

- Their actual professional domain (where they hold deep expertise that an LLM does not have)
- Practical prompting patterns: what to ask, how to constrain, how to spot a confident-sounding wrong answer
- Knowing which questions LLMs handle well and which they don't, in their domain

### Blind Spots

- Architecture or implementation talk; they do not know what an "agent framework" is, and they shouldn't have to
- Distinguishing a real product capability from a demo built by an engineer who knows how to wire things up
- Cost / latency / privacy implications of any given tool — they generally trust the marketing copy unless burned

## Psychology

### Primary Goals

- Find LLM-agent tools that make their document-heavy work meaningfully easier.
- Avoid wasting a Saturday learning a tool that turns out to require coding or doesn't handle their real files.
- Understand what's "out there" — which agents exist, what they're for, who's using them — without having to track every venue themselves.

### Hidden Concerns

- That the newsletter will be written by engineers, for engineers, and they'll miss the parts that actually apply to them.
- That they'll recommend an agent to a colleague and it will turn out to be vapourware.
- That a tool they rely on will leak sensitive client data (regulatory or contractual exposure).

### Decision Drivers

- **Values:** plain language; concrete use-cases; honest framing of "production-ready vs. demo"; respect for non-coder users.
- **Evidence:** a screenshot of someone *like them* using the tool on a similar document; a "here's what to try first" walk-through; testimonials from non-engineers.
- **Red Flags:** any tool whose docs assume you know what an API is; agent demos that require Python; capability claims with no walkthrough.

### Frustrations

- Issues whose deep dives are about agent-framework internals they don't write code in.
- Items that link only to a GitHub repo with no "non-coder" path to actually trying the thing.
- Hype-y framings that turn out to be "you can do this if you write 200 lines of Python first."

### Delights

- A deep dive that ends with "and you can try it in your browser at $url, here's how it handles a 50-page PDF."
- A quick mention about a Claude/ChatGPT extension or product they hadn't heard of that solves a specific document-handling annoyance.
- An honest comparison of two competing LLM document-analysis tools, told without engineering jargon.

## Interaction Guide

### Questions They Typically Ask

- "Can I try this without writing code?"
- "Does this handle PDFs / Excel / scanned documents reasonably?"
- "Is this safe to use with confidential material?"
- "What does this cost? Is there a free tier?"
- "What's the difference between this and just using Claude/ChatGPT directly?"

### What Makes Them Approve

- A clear, jargon-free explanation of what the tool does and who it's for.
- A concrete example that resembles their own work.
- An honest "here are the gotchas" section.

### What Makes Them Push Back

- Coverage that assumes engineering background.
- Items where the only way to use the tool is to "clone the repo and run it locally."
- Summaries that confuse "you can build this" with "you can use this."

### Representative Quote

> "If you can't tell me how to try it from my browser before lunch, I'm probably not going to."

## Backstory

Started using ChatGPT to summarise long reports and was immediately productive — even with its quirks. From there, branched out to "chat with your PDF" tools, custom GPTs, and now agent products that can read and cross-reference whole folders of documents. Has been burned twice: once by a tool that quietly leaked uploaded content into a public training dataset, and once by an "AI agent" product that turned out to be a thin wrapper that needed configuration files. Since then, deeply values newsletters that vet tools from a *user's* perspective, not an *engineer's*.

---

*Consult this persona when: deciding how non-coder-friendly issue summaries should be, weighing whether to include "what to actually try" walkthrough text for tool items, deciding how much engineering jargon is acceptable, or considering items where the only available access is a GitHub repo (i.e., not usable for this persona).*
