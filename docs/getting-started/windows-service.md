# Windows Service Installation

This guide explains how to run Wizarr natively on Windows without Docker.

## Prerequisites

- [Python](https://www.python.org/downloads/) 3.13 or later installed and added to your `PATH`
- [uv](https://docs.astral.sh/uv/) for dependency management
- [Node.js](https://nodejs.org/) (for building static assets)
- Optional: [NSSM](https://nssm.cc/) if you want to run Wizarr as a Windows service

## Setup Steps

1. Clone the repository and install dependencies:

```cmd
git clone https://github.com/wizarrrr/wizarr.git
cd wizarr
uv sync --locked
```

2. Build the assets and apply migrations:

```cmd
uv run pybabel compile -d app/translations
uv run flask db upgrade
uv run python -m app.legacy_migration.import_legacy
cd app\static
npm install
npm run build  REM builds assets (works cross-platform)
cd ..\..
```

3. Start Wizarr to verify everything is working:

```cmd
uv run python run.py
```

Wizarr will be available at <http://localhost:5690>. Set the `WIZARR_PORT`
environment variable if you need a different port.

## Running as a Service

If you installed NSSM you can run Wizarr in the background as a Windows service:

```cmd
nssm install wizarr "C:\\path\\to\\uv.exe" run python run.py
nssm start wizarr
```

The service can be controlled with `nssm start wizarr` and `nssm stop wizarr`.
