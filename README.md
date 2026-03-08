# pyramid-introspector

A library that helps introspect Pyramid views and extract their metadata and information.

## Installation

```bash
pip install pyramid-introspector
```

Or with uv:

```bash
uv add pyramid-introspector
```

## Usage

```python
import pyramid_introspector
```

## Development

### Setup

```bash
git clone https://github.com/your-org/pyramid-introspector.git
cd pyramid-introspector
uv sync --dev
```

### Run tests

```bash
uv run pytest
```

### Lint and format

```bash
uv run ruff check .
uv run black .
```

### Build documentation

```bash
uv run mkdocs serve
```

## License

MIT
