#!/usr/bin/env bash
# Local Stripe billing smoke test (API + Checkout session creation).
set -euo pipefail
cd "$(dirname "$0")/.."

source venv/bin/activate
set -a
[ -f .env ] && . ./.env
[ -f .env.local ] && . ./.env.local
set +a

BASE="${STRIPE_TEST_BASE_URL:-http://127.0.0.1:8520}"

echo "=== Service-layer checks ==="
python3 - <<'PY'
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))
from dotenv import load_dotenv
load_dotenv(); load_dotenv('.env.local', override=True)
from services.stripe_billing_service import _price_id, create_checkout_session, is_billing_enabled
assert is_billing_enabled(), 'Set ENABLE_STRIPE_BILLING=true in .env.local'
for plan in ('starter', 'professional'):
    print(f'  price {plan}:', _price_id(plan))
session = create_checkout_session(
    os.getenv('STRIPE_TEST_EMAIL', 'billing-test@idpetech.com'),
    'starter',
    success_url=f'{os.getenv("STRIPE_TEST_BASE_URL", "http://127.0.0.1:8520")}/dashboard?billing=success&session_id={{CHECKOUT_SESSION_ID}}',
    cancel_url=f'{os.getenv("STRIPE_TEST_BASE_URL", "http://127.0.0.1:8520")}/dashboard?billing=canceled',
)
print('  checkout session:', session['session_id'])
print('  checkout url:', session['checkout_url'])
PY

echo ""
echo "=== HTTP checks ($BASE) ==="
curl -sf "$BASE/api/feature-flags" | python3 -c "import sys,json; f=json.load(sys.stdin); assert f.get('advanced_billing'), f; print('  advanced_billing=true')"

EMAIL="stripe-local-$(date +%s)@idpetech.com"
PASS='TestBilling123!'
REG=$(curl -sf -X POST "$BASE/api/auth/register" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\",\"display_name\":\"Stripe Local Test\"}")
TOKEN=$(echo "$REG" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
echo "  registered: $EMAIL"

TRIAL=$(curl -sf "$BASE/api/auth/trial" -H "Authorization: Bearer $TOKEN")
echo "$TRIAL" | python3 -c "import sys,json; t=json.load(sys.stdin); assert t.get('enabled'); assert t.get('billing_status')=='trial'; print('  trial API ok, billing_status=trial')"

CHK=$(curl -sf -X POST "$BASE/api/billing/checkout" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"plan":"starter"}')
echo "$CHK" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('checkout_url'); print('  checkout API ok'); print('  open:', d['checkout_url'])"

echo ""
echo "Done. Complete payment in browser with test card 4242 4242 4242 4242."
echo "For webhooks locally: stripe listen --forward-to localhost:8520/api/billing/webhook"
