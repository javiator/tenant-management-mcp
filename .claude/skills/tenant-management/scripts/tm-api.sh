#!/usr/bin/env bash
# Tenant Management API client script.
# Handles auth, validation, HTTP calls, response unwrapping, and error formatting.
#
# Usage: tm-api.sh <command> [id] [json-body]
#
# Commands:
#   list-properties                         List all properties
#   get-property <id>                       Get property by ID
#   create-property <json>                  Create a property
#   update-property <id> <json>             Update a property
#   delete-property <id>                    Delete a property
#   list-property-transactions <id>         List transactions for a property
#
#   list-tenants                            List all tenants
#   get-tenant <id>                         Get tenant by ID
#   create-tenant <json>                    Create a tenant
#   update-tenant <id> <json>               Update a tenant
#   delete-tenant <id>                      Delete a tenant
#   list-tenant-transactions <id>           List transactions for a tenant
#
#   list-transactions                       List all transactions
#   get-transaction <id>                    Get transaction by ID
#   create-transaction <json>               Create a transaction
#   update-transaction <id> <json>          Update a transaction
#   delete-transaction <id>                 Delete a transaction

set -euo pipefail

BASE_URL="${BACKEND_MCP_BASE_URL:-http://localhost:8080}"
BASE_URL="${BASE_URL%/}"
API_TOKEN="${BACKEND_MCP_API_TOKEN:-}"

VALID_TX_TYPES="rent security payment_received gas electricity water maintenance misc"

# ── helpers ──────────────────────────────────────────────────────────────────

die() { echo "ERROR: $*" >&2; exit 1; }

require_id() {
  local id="$1" label="$2"
  [[ -z "$id" ]] && die "$label is required."
  [[ "$id" =~ ^[1-9][0-9]*$ ]] || die "$label must be a positive integer, got '$id'."
}

require_body() {
  local body="$1"
  [[ -z "$body" ]] && die "JSON body is required."
  echo "$body" | jq empty 2>/dev/null || die "Invalid JSON body: $body"
}

require_field() {
  local body="$1" field="$2" label="$3"
  local val
  val=$(echo "$body" | jq -r ".$field // empty")
  [[ -z "$val" ]] && die "Required field '$field' missing in $label payload."
}

require_nonempty_string() {
  local body="$1" field="$2" label="$3"
  local val
  val=$(echo "$body" | jq -r ".$field // empty")
  [[ -z "$val" ]] && die "Required field '$field' must be a non-empty string in $label payload."
}

require_positive_int() {
  local body="$1" field="$2" label="$3"
  local val
  val=$(echo "$body" | jq -r ".$field // empty")
  [[ -z "$val" ]] && die "Required field '$field' missing in $label payload."
  [[ "$val" =~ ^[1-9][0-9]*$ ]] || die "Field '$field' must be a positive integer in $label payload, got '$val'."
}

require_number() {
  local body="$1" field="$2" label="$3"
  local val
  val=$(echo "$body" | jq -r ".$field // empty")
  [[ -z "$val" ]] && die "Required field '$field' missing in $label payload."
  [[ "$val" =~ ^-?[0-9]+\.?[0-9]*$ ]] || die "Field '$field' must be a number in $label payload, got '$val'."
}

validate_tx_type() {
  local body="$1"
  local t
  t=$(echo "$body" | jq -r '.type // empty')
  [[ -z "$t" ]] && die "Required field 'type' missing in transaction payload."
  local valid=false
  for v in $VALID_TX_TYPES; do
    [[ "$t" == "$v" ]] && valid=true && break
  done
  [[ "$valid" == "false" ]] && die "Invalid transaction type '$t'. Must be one of: $VALID_TX_TYPES"
}

require_at_least_one() {
  local body="$1" label="$2"
  local count
  count=$(echo "$body" | jq 'length')
  [[ "$count" -eq 0 ]] && die "At least one field must be provided in $label update payload."
}

# ── HTTP engine ──────────────────────────────────────────────────────────────

api_call() {
  local method="$1" path="$2" body="${3:-}"
  local url="${BASE_URL}${path}"

  local -a curl_args=(-s -w '\n%{http_code}')
  curl_args+=(-H "Accept: application/json")

  if [[ -n "$API_TOKEN" ]]; then
    curl_args+=(-H "Authorization: Bearer $API_TOKEN")
  fi

  if [[ -n "$body" ]]; then
    curl_args+=(-H "Content-Type: application/json" -d "$body")
  fi

  curl_args+=(-X "$method" "$url")

  local raw
  raw=$(curl "${curl_args[@]}")

  local http_code
  http_code=$(echo "$raw" | tail -n1)
  local response_body
  response_body=$(echo "$raw" | sed '$d')

  # Handle errors
  if [[ "$http_code" -ge 400 ]]; then
    echo "HTTP $http_code Error:" >&2
    if echo "$response_body" | jq empty 2>/dev/null; then
      echo "$response_body" | jq '.' >&2
    else
      echo "$response_body" >&2
    fi
    exit 1
  fi

  # Handle no content
  if [[ "$http_code" == "204" ]] || [[ -z "$response_body" ]]; then
    echo "Success (no content)"
    return 0
  fi

  # Unwrap {"data": ...} if present, then pretty-print
  if echo "$response_body" | jq empty 2>/dev/null; then
    echo "$response_body" | jq '.data // .'
  else
    echo "$response_body"
  fi
}

# ── command dispatch ─────────────────────────────────────────────────────────

cmd="${1:-}"
[[ -z "$cmd" ]] && die "Usage: tm-api.sh <command> [id] [json-body]. Run with --help for details."

case "$cmd" in

  # ── Properties ──

  list-properties)
    api_call GET /api/properties
    ;;

  get-property)
    require_id "${2:-}" "property_id"
    api_call GET "/api/properties/$2"
    ;;

  create-property)
    require_body "${2:-}"
    require_nonempty_string "$2" "address" "property"
    require_number "$2" "rent" "property"
    require_number "$2" "maintenance" "property"
    api_call POST /api/properties "$2"
    ;;

  update-property)
    require_id "${2:-}" "property_id"
    require_body "${3:-}"
    require_nonempty_string "$3" "address" "property"
    require_number "$3" "rent" "property"
    require_number "$3" "maintenance" "property"
    api_call PUT "/api/properties/$2" "$3"
    ;;

  delete-property)
    require_id "${2:-}" "property_id"
    api_call DELETE "/api/properties/$2"
    echo "Property $2 deleted successfully."
    ;;

  list-property-transactions)
    require_id "${2:-}" "property_id"
    api_call GET "/api/properties/$2/transactions"
    ;;

  # ── Tenants ──

  list-tenants)
    api_call GET /api/tenants
    ;;

  get-tenant)
    require_id "${2:-}" "tenant_id"
    api_call GET "/api/tenants/$2"
    ;;

  create-tenant)
    require_body "${2:-}"
    require_nonempty_string "$2" "name" "tenant"
    require_positive_int "$2" "propertyId" "tenant"
    api_call POST /api/tenants "$2"
    ;;

  update-tenant)
    require_id "${2:-}" "tenant_id"
    require_body "${3:-}"
    require_at_least_one "$3" "tenant"
    api_call PUT "/api/tenants/$2" "$3"
    ;;

  delete-tenant)
    require_id "${2:-}" "tenant_id"
    api_call DELETE "/api/tenants/$2"
    echo "Tenant $2 deleted successfully."
    ;;

  list-tenant-transactions)
    require_id "${2:-}" "tenant_id"
    api_call GET "/api/tenants/$2/transactions"
    ;;

  # ── Transactions ──

  list-transactions)
    api_call GET /api/transactions
    ;;

  get-transaction)
    require_id "${2:-}" "transaction_id"
    api_call GET "/api/transactions/$2"
    ;;

  create-transaction)
    require_body "${2:-}"
    require_positive_int "$2" "propertyId" "transaction"
    validate_tx_type "$2"
    require_number "$2" "amount" "transaction"
    require_nonempty_string "$2" "transactionDate" "transaction"
    api_call POST /api/transactions "$2"
    ;;

  update-transaction)
    require_id "${2:-}" "transaction_id"
    require_body "${3:-}"
    require_at_least_one "$3" "transaction"
    # Validate type if provided
    local_type=$(echo "$3" | jq -r '.type // empty')
    if [[ -n "$local_type" ]]; then
      validate_tx_type "$3"
    fi
    api_call PUT "/api/transactions/$2" "$3"
    ;;

  delete-transaction)
    require_id "${2:-}" "transaction_id"
    api_call DELETE "/api/transactions/$2"
    echo "Transaction $2 deleted successfully."
    ;;

  --help|-h)
    sed -n '2,/^$/p' "$0" | sed 's/^# \?//'
    ;;

  *)
    die "Unknown command '$cmd'. Run with --help for available commands."
    ;;
esac
