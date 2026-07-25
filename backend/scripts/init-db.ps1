Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location (Split-Path $PSScriptRoot -Parent)
alembic upgrade head

# For a database created before Alembic was introduced, first verify that its
# schema matches the initial migration, then run: alembic stamp head
