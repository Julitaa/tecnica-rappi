# Operations Analyzer

## Requisitos

- [uv](https://docs.astral.sh/uv/getting-started/installation/) — gestor de entornos y dependencias Python

## Backend

```bash
cd backend
uv run uvicorn app.main:app --reload
```

## Tests

```bash
cd backend
uv run pytest
```

> **Windows PowerShell:** si `uv` no está en PATH, agregarlo primero:
> ```powershell
> $env:Path += ";$env:USERPROFILE\.local\bin"
> ```
