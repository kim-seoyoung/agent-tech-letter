# US0021: Telegram channel adapter (Bot API, 4096-char splitting, HTML escape)

> **Status:** Draft
> **Epic:** [EP0004: Multi-channel Delivery](../epics/EP0004-multichannel-delivery.md)
> **Owner:** HYL
> **Reviewer:** HYL
> **Created:** 2026-05-19

## User Story

**As** the Researcher Subscriber who reads the newsletter on Telegram
**I want** each weekly issue posted to my Telegram chat/channel as cleanly formatted messages
**So that** I can read it on mobile during a commute without leaving Telegram.

## Context

### Persona Reference
**Researcher Subscriber** — beneficiary. Mobile-first reading context. Telegram-specific concerns: 4,096-char message limit (hard), HTML parse mode escaping, link previews.
[Persona details](../personas/stakeholders/users/researcher-subscriber.md)

### Background
Telegram's Bot API accepts HTML or `MarkdownV2` parse modes; HTML is simpler (smaller list of allowed tags + obvious escaping rules). The 4,096-char limit per message is a hard cap — exceeding it returns 400. Splitter strategy mirrors Slack but with different limit and conversion.

---

## Inherited Constraints

| Source | Type | Constraint | AC Implication |
|--------|------|------------|----------------|
| Epic | Protocol | Implements `ChannelAdapter` from US0018 | Adapter must be protocol-conformant |
| PRD | Transport | Telegram Bot API `sendMessage` | One POST per message |
| Epic | Splitter | Messages split to respect 4,096-char limit | Splitter parameterised with `limit_chars=4096` |
| PRD | Parse mode | `HTML` (default, per `channels.yaml`) | Convert markdown → Telegram HTML; escape special chars |
| Epic | Failure isolation | Per-recipient (per-chat) failure logged | Try/except per chat id |
| Epic | Reliability | tenacity-wrapped retries | Backoff on 429 / 5xx |

---

## Acceptance Criteria

### AC1: Adapter is discoverable and conformant
- **Given** the package `techletter.delivery.telegram` exists
- **When** an engineer imports `from techletter.delivery.telegram import TelegramAdapter`
- **Then** `TelegramAdapter(config: TelegramConfig, bot_token: str)` is the constructor
- **And** `adapter.name == "telegram"` and `adapter.send(issue, recipients) -> SendReport` matches the `ChannelAdapter` protocol
- **And** `recipients` are Telegram chat IDs (strings)

### AC2: Bot token from env
- **Given** the env var `TELEGRAM_BOT_TOKEN` is set
- **When** the adapter is constructed (e.g., via `from_env`)
- **Then** the bot token is captured and used as the path component in API URLs (`https://api.telegram.org/bot<token>/sendMessage`)
- **And** missing token causes a clear construction-time error (channel skipped at runtime)

### AC3: CommonMark → Telegram HTML conversion
- **Given** the issue's markdown body
- **When** the adapter renders for Telegram (HTML parse mode)
- **Then** these conversions are applied:
  - HTML-escape `<`, `>`, `&` *before* substituting other markup (escape first, format second)
  - `**bold**` → `<b>bold</b>`
  - `_italic_` and CommonMark `*italic*` → `<i>italic</i>`
  - `[text](url)` → `<a href="url">text</a>` (URL-escape the href)
  - Inline backticks → `<code>code</code>`
  - Fenced code blocks → `<pre>...</pre>` (Telegram supports this)
  - Headings → bold on a line with blank line after (Telegram HTML has no headings)
  - Bullets and numbered lists → preserved with line breaks (Telegram doesn't render them as lists; they render as plain text with line breaks)

### AC4: Splitting at 4,096-char limit
- **Given** the converted HTML body exceeds 4,096 chars
- **When** the adapter prepares to send
- **Then** the body is split into N messages, each ≤ 4,096 chars (with conservative headroom: use 3,900 chars target to be safe against the escape expansion)
- **And** splits occur at paragraph boundaries (`\n\n`); never mid-tag (e.g., not in the middle of `<a href="...">...</a>`)
- **And** opened tags at chunk boundary are closed before the boundary and reopened in the next chunk (simple cases only — see edge cases)

### AC5: One POST per chat per chunk
- **Given** N chat IDs configured and M chunks needed
- **When** the adapter sends
- **Then** N × M POST requests are made
- **And** per chat, chunks are sent sequentially (preserve order)
- **And** the POST body is JSON: `{"chat_id": "<id>", "text": "<chunk>", "parse_mode": "HTML", "disable_web_page_preview": false}`

### AC6: Disable / enable preview based on config
- **Given** `TelegramConfig.disable_web_page_preview` (default `false`)
- **When** the POST is constructed
- **Then** the field `disable_web_page_preview` is included with the config value
- **And** the default `false` allows link previews (subscribers may want them); HYL can flip to `true` if previews become annoying

### AC7: Per-chat failure isolation
- **Given** 3 chats configured; chat #2 has been blocked by the user (403 Forbidden)
- **When** the adapter sends
- **Then** chats #1 and #3 receive all chunks
- **And** chat #2's failure is logged with the API error message (`"Forbidden: bot was blocked by the user"`)
- **And** `SendReport.failures` contains one entry per failed chat

### AC8: Empty recipient list → no-op
- **Given** `recipients=[]`
- **When** `send` is called
- **Then** no HTTP requests are made; `SendReport(recipients_count=0, status="ok")` returned

---

## Scope

### In Scope
- `techletter/delivery/telegram.py` defining `TelegramAdapter`.
- `commonmark_to_telegram_html(markdown_text: str) -> str` helper.
- `split_for_telegram(text: str, limit_chars: int = 3900) -> list[str]` splitter helper (HTML-tag-aware).
- HTTP POST via `httpx` to Bot API.
- tenacity decorators for 429 / 5xx retries.
- Unit tests for conversion, splitting, escaping, and the adapter's `send`.

### Out of Scope
- `MarkdownV2` parse mode (PRD chose HTML; simpler escape rules).
- Telegram inline keyboards / commands / bot interactions.
- File uploads (e.g., issue as a PDF) — out of scope for v1.
- Message editing (e.g., updating a previously-sent issue) — out of scope.
- Multi-bot support — one bot serves all chats.

---

## Technical Notes

- HTML escape order matters: `&` must be escaped *first* (to `&amp;`), then `<` and `>`. Otherwise `<` becomes `&amp;lt;`. Use `html.escape(s, quote=False)` from stdlib for the initial pass on user content (link text), then assemble tags.
- The splitter must track tag state. v1 limitation: if a split would land mid-`<code>` or mid-`<pre>`, the splitter shifts the cut backward to the previous paragraph boundary. If a single block is itself > 3,900 chars, log WARN and accept the API rejection rather than silently corrupt output.
- Bot tokens are sensitive; never log the full token. Mask: `token[:6] + "..." + token[-4:]` for any debug log.
- Telegram chat IDs can be negative (group/channel IDs) or positive (private chats). Pass them through unchanged.

### API Contracts
- `TelegramAdapter(config: TelegramConfig, bot_token: str)` — constructor.
- `TelegramAdapter.from_env(config) -> TelegramAdapter` — class method reading `TELEGRAM_BOT_TOKEN`.
- `send(issue, recipients) -> SendReport`.
- `commonmark_to_telegram_html(text) -> str` — pure helper.
- `split_for_telegram(text, limit_chars) -> list[str]` — pure helper.

### Data Requirements
- Chat IDs in `SubscribersConfig.telegram`.
- `TELEGRAM_BOT_TOKEN` env var.

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour |
|----------|-------------------|
| Empty recipient list | No-op, `status="ok"` |
| `TELEGRAM_BOT_TOKEN` missing | Construction fails; channel skipped at runtime |
| Bot blocked by user (403) | That chat fails; others proceed |
| Bot kicked from group (400) | That chat fails; others proceed |
| Issue body with raw HTML-like chars (`<script>`) | Escaped before tag substitution; renders as visible `<script>` in chat |
| Issue body with a markdown link whose URL contains `&` or `<` | URL-escape the href; link still works |
| Issue body with a single 5,000-char code block | Splitter logs WARN; sends the oversized chunk; Telegram 400; failure recorded for that chat |
| Telegram rate-limits with `retry_after` in body | tenacity respects `Retry-After` or response body's `parameters.retry_after`; backs off accordingly |
| Network timeout | tenacity retries; eventual failure |
| Markdown construct unsupported (e.g., a table) | Pass through as plain text after escaping; not pretty but readable |
| Markdown image `![alt](url)` | Convert to `<a href="url">alt</a>` (Telegram HTML doesn't render images this way; the link is the next best thing) |
| Same chat id appears twice in config | Adapter sends to each independently (dedupe at registry, US0022) |
| Chat id is a string of all-digits, no negative prefix | Treated as a private-chat user id; valid |
| Chat id is invalid (chat not found, 400) | That chat fails with clear error in `failures` |
| HTTP 200 but Telegram response `ok: false` (e.g., parse error in HTML) | Adapter checks the response body; treats `ok: false` as failure for that chat |
| Unicode emoji in body | Telegram handles UTF-8 natively |
| Very long URLs in markdown links (>2,000 chars) | Telegram may reject; failure recorded for that chunk; subsequent chunks still attempted for the same chat after the rejected one |

---

## Test Scenarios

- [ ] `TelegramAdapter()` assignable to `ChannelAdapter` per pyright.
- [ ] `commonmark_to_telegram_html("&<>")` → `"&amp;&lt;&gt;"` (escape order correct).
- [ ] `commonmark_to_telegram_html("**bold** [link](https://example.com)")` → `"<b>bold</b> <a href=\"https://example.com\">link</a>"`.
- [ ] `commonmark_to_telegram_html("```\ncode\n```")` → `"<pre>code</pre>"`.
- [ ] `split_for_telegram` text < limit → single chunk.
- [ ] `split_for_telegram` 5,000 chars → 2 chunks; each ≤ 3,900.
- [ ] `split_for_telegram` does not split inside a `<pre>` block.
- [ ] Send to 2 chats, fake HTTP returns 200 for both → `success=2, status="ok"`.
- [ ] Send to 2 chats, one returns 403 (bot blocked) → `success=1, failure=1, status="partial"`.
- [ ] tenacity: 429 with `retry_after` × 2 then 200 → success.
- [ ] tenacity: 429 × 5 → that chat marked failed.
- [ ] Empty recipients → no HTTP calls.
- [ ] Per-chat sequencing: chunks for chat A go in order; verify by inspecting fake-server log.
- [ ] Bot token never appears in any log line (verified by parsing test log output).

---

## Dependencies

### Story Dependencies

| Story | Type | What's Needed | Status |
|-------|------|---------------|--------|
| [US0018](US0018-channel-adapter-protocol-and-config-loaders.md) | Schema | `ChannelAdapter`, `SendReport`, `TelegramConfig` | Draft |
| [US0011](US0011-compose-blog-quick-mentions-and-issue-assembly.md) | Schema | `RenderedIssue` | Draft |

### External Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| `httpx` library | Library | Already added |
| `tenacity` library | Library | Already added |
| `TELEGRAM_BOT_TOKEN` GitHub Secret | Secret | Optional — only needed if Telegram channel is enabled |

---

## Estimation

**Story Points:** 3
**Complexity:** Low-Medium. Same overall shape as US0020 (Slack), with different escape rules and stricter char limit. The HTML-escape-then-format ordering is the trickiest piece — get it wrong and special chars in link text break the message.

---

## Open Questions

_None._

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-19 | HYL | Initial story created from EP0004. |
