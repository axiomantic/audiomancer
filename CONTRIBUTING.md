# Contributing to audiomancer

Thanks for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/axiomantic/audiomancer
cd audiomancer
uv sync --extra dev
```

## Running Tests

```bash
uv run pytest
```

## Code Style

- **Linting:** `uv run ruff check src/`
- **Formatting:** `uv run ruff format src/`
- **Type checking:** `uv run pyright src/`

Pre-commit hooks run automatically on commit.

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run tests and linting
5. Commit with a descriptive message
6. Push and open a PR

## Commit Messages

Use conventional commits:
- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `test:` tests
- `chore:` maintenance

## Questions?

Open a discussion or issue on GitHub.
