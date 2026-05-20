# Tech-Letter for HYL

Automated weekly LLM-agent newsletter generator.

> Spec set lives in [`sdlc-studio/`](sdlc-studio/) — PRD, TRD, TSD, 4 epics, 22 stories, 4 test specs.
> Full quickstart will land via [US0017](sdlc-studio/stories/US0017-readme-quickstart-and-dev-loop.md).
> This stub satisfies PL0001's Definition of Done.

## Development

```bash
uv sync --all-extras
uv run pytest -q
uv run pyright techletter/ tests/
uv run ruff check . && uv run ruff format --check .
```

## License

MIT
