#!/usr/bin/env python3
"""
Load Auto-Profiles into VEP1445 - CORRECTED VERSION
Uses correct API field names: src_interface, dst_interface, dst_ip
"""

import json
import requests
import sys

print("╔═══════════════════════════════════════════════════════════════╗")
print("║  Loading Auto-Profiles into VEP1445 (Corrected)              ║")
print("╚═══════════════════════════════════════════════════════════════╝")
print("")

# Read auto_config.json
try:
    with open('/opt/vep1445-traffic-gen/auto_config.json', 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    print("❌ Error: auto_config.json not found!")
    sys.exit(1)

auto_profiles = config.get('auto_profiles', [])

if not auto_profiles:
    print("⚠️  No auto-profiles found")
    sys.exit(1)

print(f"Found {len(auto_profiles)} profiles to load")
print("")

# Check if VEP1445 is running
try:
    response = requests.get("http://localhost:5000/api/status", timeout=2)
    print("✓ VEP1445 is running")
except:
    print("❌ VEP1445 is not running!")
    print("Start it: sudo systemctl start vep1445")
    sys.exit(1)

print("")

# Load each profile with CORRECT field names
api_url = "http://localhost:5000/api/traffic-profiles"
success = 0
failed = 0

for p in auto_profiles:
    profile_name = p['name']
    print(f"Creating: {profile_name}...")
    
    # CRITICAL: Use the correct API field names!
    data = {
        'name': p['name'],
        'src_interface': p['source_interface'],      # API wants src_interface
        'dst_interface': p['dest_interface'],        # API wants dst_interface  
        'dst_ip': p['dest_ip'],                      # API wants dst_ip
        'bandwidth_mbps': p['bandwidth_mbps'],
        'packet_size': p['packet_size'],
        'protocol': p['protocol'],
        'enabled': False
    }
    
    try:
        r = requests.post(api_url, json=data, timeout=5)
        
        if r.status_code in [200, 201]:
            result = r.json()
            if result.get('success'):
                print(f"  ✓ {profile_name}: {p['source_ip']} -> {p['dest_ip']}")
                success += 1
            else:
                print(f"  ✗ API returned error: {result.get('error')}")
                failed += 1
        else:
            print(f"  ✗ HTTP {r.status_code}: {r.text[:150]}")
            failed += 1
    except Exception as e:
        print(f"  ✗ Error: {e}")
        failed += 1

print("")
print("─────────────────────────────────────────────────────────────")
print(f"Results: {success} created, {failed} failed")
print("")

if success > 0:
    print("✅ Profiles loaded successfully!")
    print("")
    print("Refresh your browser: http://localhost:5000")
    print("Go to 'Traffic Profiles' tab")
    print("")
    sys.exit(0)
else:
    print("❌ No profiles were created")
    print("")
    if failed > 0:
        print("All attempts failed. Check logs:")
        print("  sudo journalctl -u vep1445 -n 50")
    print("")
    sys.exit(1)
