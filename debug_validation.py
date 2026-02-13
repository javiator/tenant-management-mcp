
import json
from tm_mcp.schemas import tenant_list_adapter

with open('tenants.json', 'r') as f:
    data = json.load(f)

try:
    tenants = tenant_list_adapter.validate_python(data['data'])
    print(f"Successfully validated {len(tenants)} tenants")
except Exception as e:
    print(f"Validation failed: {e}")
