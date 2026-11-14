#!/usr/bin/env bash
set -Eeuo pipefail

region="Haworth"
skip_install=false

usage() {
    cat <<'EOF'
Usage: bash scripts/prepare_demo.sh [options]

Prepare and build the hackathon demo.

Options:
  --region NAME       Lunar region to prepare (default: Haworth)
  --skip-install      Skip uv sync and npm ci after the first setup
  -h, --help          Show this help message
EOF
}

while (($# > 0)); do
    case "$1" in
        --region)
            if (($# < 2)); then
                echo "error: --region requires a value" >&2
                exit 2
            fi
            region="$2"
            shift 2
            ;;
        --skip-install)
            skip_install=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "error: unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

if ! command -v uv >/dev/null 2>&1; then
    echo "error: uv is not installed or is not on PATH." >&2
    echo "Install it from https://docs.astral.sh/uv/." >&2
    exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
    echo "error: npm is not installed or is not on PATH." >&2
    echo "Install Node.js 22 or newer." >&2
    exit 1
fi

run_step() {
    local name="$1"
    shift
    printf '\n==> %s\n' "$name"
    "$@"
}

if [[ "$skip_install" == false ]]; then
    run_step "Synchronizing locked Python dependencies" \
        uv sync --locked --all-extras
fi

run_step "Running the integrated Moon pipeline for $region" \
    uv run --locked --all-extras python -m integration.run_all --region "$region"

region_slug="$(
    printf '%s' "$region" \
        | tr '[:upper:]' '[:lower:]' \
        | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//'
)"

run_step "Exporting validated $region data for the web app" \
    uv run --locked --all-extras python app/scripts/export_data.py --region "$region_slug"

if [[ "$skip_install" == false ]]; then
    run_step "Installing locked web dependencies" npm ci --prefix app
fi

run_step "Building the production web app" npm run build --prefix app

printf '\nDemo preparation completed successfully.\n'
echo "Start it with: npm run dev --prefix app"

