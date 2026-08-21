#!/bin/bash
# Smoke test suite — runs the tests that must pass on EVERY deploy.
# Uses tests that don't require seed demo data + auth-boundary checks.
#
# Usage:
#   REACT_APP_BACKEND_URL=https://funzionabene.it ./run_smoke_tests.sh
#
# For local dev:
#   ./run_smoke_tests.sh
set -e

if [ -z "$REACT_APP_BACKEND_URL" ]; then
    export REACT_APP_BACKEND_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env 2>/dev/null | cut -d '=' -f2)
fi

echo "==== SMOKE TESTS on ${REACT_APP_BACKEND_URL} ===="
cd "$(dirname "$0")"

python3 -m pytest \
    tests/test_iteration18_consent_reviews.py \
    tests/test_public_routes.py::TestBookingFlow::test_prenota_requires_auth \
    tests/test_public_routes.py::TestBookingFlow::test_prenota_requires_paziente_role \
    -v --tb=short

echo ""
echo "==== SMOKE TESTS COMPLETED ===="
