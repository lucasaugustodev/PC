"""Create Vultr GPU VM."""
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

PLAN = "vcg-a100-12c-120g-80vram"

# Find regions for this plan
print("Finding regions...")
regions = api("GET", "/regions")
available = []
for r in regions.get('regions', []):
    if PLAN in r.get('plans', []):
        available.append(r)
        print(f"  {r['id']}: {r['city']}, {r['country']}")

if not available:
    # Check plan locations field
    plans = api("GET", "/plans?type=all&per_page=500")
    for p in plans.get('plans', []):
        if p['id'] == PLAN:
            locs = p.get('locations', [])
            print(f"Plan locations: {locs}")
            for r in regions.get('regions', []):
                if r['id'] in locs:
                    available.append(r)
                    print(f"  {r['id']}: {r['city']}, {r['country']}")
            break

if not available:
    print("No regions available for A100 80GB!")
    # Try smaller - A100 40GB
    PLAN = "vcg-a100-6c-60g-40vram"
    print(f"\nTrying {PLAN}...")
    for r in regions.get('regions', []):
        if PLAN in r.get('plans', []):
            available.append(r)
            print(f"  {r['id']}: {r['city']}, {r['country']}")
    if not available:
        plans = api("GET", "/plans?type=all&per_page=500")
        for p in plans.get('plans', []):
            if p['id'] == PLAN:
                locs = p.get('locations', [])
                print(f"Plan locations: {locs}")
                for r in regions.get('regions', []):
                    if r['id'] in locs:
                        available.append(r)
                        print(f"  {r['id']}: {r['city']}, {r['country']}")
                break

if not available:
    print("No regions for A100 40GB either! Trying L40S 48GB...")
    PLAN = "vcg-l40s-16c-180g-48vram"
    for r in regions.get('regions', []):
        if PLAN in r.get('plans', []):
            available.append(r)
            print(f"  {r['id']}: {r['city']}, {r['country']}")
    if not available:
        plans_data = api("GET", "/plans?type=all&per_page=500")
        for p in plans_data.get('plans', []):
            if p['id'] == PLAN:
                locs = p.get('locations', [])
                print(f"Plan locations: {locs}")
                for r in regions.get('regions', []):
                    if r['id'] in locs:
                        available.append(r)
                        print(f"  {r['id']}: {r['city']}, {r['country']}")
                break

if not available:
    print("\nNo GPU regions available! Listing ALL gpu plan availability:")
    plans_data = api("GET", "/plans?type=all&per_page=500")
    for p in plans_data.get('plans', []):
        if p.get('gpu_vram_gb', 0) >= 40:
            locs = p.get('locations', [])
            print(f"  {p['id']} ({p.get('gpu_vram_gb')}GB): locations={locs}")
    sys.exit(1)

region = available[0]
print(f"\nUsing: plan={PLAN} region={region['id']} ({region['city']})")

# Upload SSH key
print("\nSetting up SSH key...")
ssh_keys = api("GET", "/ssh-keys")
ssh_key_id = None
if ssh_keys and ssh_keys.get('ssh_keys'):
    ssh_key_id = ssh_keys['ssh_keys'][0]['id']
    print(f"  Existing key: {ssh_key_id}")
else:
    with open("C:/Users/PC/.ssh/id_ed25519.pub", "r") as f:
        pub_key = f.read().strip()
    result = api("POST", "/ssh-keys", {"name": "claude-key", "ssh_key": pub_key})
    if result:
        ssh_key_id = result['ssh_key']['id']
        print(f"  Uploaded key: {ssh_key_id}")

# List OS options
os_list = api("GET", "/os")
ubuntu_id = None
for o in os_list.get('os', []):
    if 'Ubuntu 24.04' in o.get('name', '') and o.get('arch') == 'x64':
        ubuntu_id = o['id']
        print(f"  OS: {o['name']} (id={o['id']})")
        break
if not ubuntu_id:
    for o in os_list.get('os', []):
        if 'Ubuntu 22.04' in o.get('name', '') and o.get('arch') == 'x64':
            ubuntu_id = o['id']
            print(f"  OS: {o['name']} (id={o['id']})")
            break

# Create VM
print(f"\n=== CREATING VM ===")
create_data = {
    "region": region['id'],
    "plan": PLAN,
    "os_id": ubuntu_id,
    "label": "heretic-gpu",
    "hostname": "heretic-gpu",
    "backups": "disabled",
}
if ssh_key_id:
    create_data["sshkey_id"] = [ssh_key_id]

print(json.dumps(create_data, indent=2))
result = api("POST", "/instances", create_data)
if result:
    inst = result.get('instance', {})
    print(f"\nVM CREATED!")
    print(f"  ID: {inst.get('id')}")
    print(f"  IP: {inst.get('main_ip')}")
    print(f"  Status: {inst.get('status')}")
    print(f"  Password: {inst.get('default_password')}")
    print(f"  Plan: {PLAN}")
    with open("C:/Users/PC/vultr_instance.json", "w") as f:
        json.dump(inst, f, indent=2)
    print("Saved to vultr_instance.json")
else:
    print("Failed to create VM!")
