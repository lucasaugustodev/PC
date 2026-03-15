"""Setup Vultr GPU VM for Heretic."""
import json, urllib.request, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

API_KEY = "2BSQFQU3VO3WFEZTMMVCSIZC2AUBQCCO7I2Q"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

def api(method, endpoint, data=None):
    url = f"https://api.vultr.com/v2{endpoint}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"ERROR {e.code}: {err}")
        return None

# 1. List GPU plans
print("=== GPU PLANS ===")
result = api("GET", "/plans?type=all&per_page=500")
if not result:
    sys.exit(1)
plans = result.get('plans', [])
gpu_plans = [p for p in plans if p.get('gpu_vram_gb', 0) > 0]
print(f"Found {len(gpu_plans)} GPU plans:")
for p in sorted(gpu_plans, key=lambda x: x.get('gpu_vram_gb', 0)):
    pid = p['id']
    vcpu = p.get('vcpu_count', 0)
    ram = p.get('ram', 0)
    vram = p.get('gpu_vram_gb', 0)
    cost = p.get('monthly_cost', 0)
    gtype = p.get('gpu_type', '')
    print(f"  {pid}: {vcpu}vcpu {ram}MB gpu={vram}GB ${cost}/mo {gtype}")
