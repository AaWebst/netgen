# VEP1445 API Documentation

## Base URL
```
http://YOUR_SERVER:5000/api
```

## Authentication
No authentication required (local network use)

---

## Interface Management

### GET /api/interfaces
Get all network interfaces

**Response:**
```json
{
  "success": true,
  "interfaces": {
    "eno2": {
      "name": "eno2",
      "mac_address": "00:11:22:33:44:55",
      "ip_address": "24.1.6.142",
      "subnet_mask": "255.255.255.224",
      "enabled": true
    }
  }
}
```

### GET /api/interfaces/<name>
Get specific interface details

### POST /api/interfaces
Add new interface

**Request:**
```json
{
  "name": "eno2",
  "mac_address": "00:11:22:33:44:55",
  "ip_address": "24.1.6.142",
  "subnet_mask": "255.255.255.224",
  "use_dhcp": true
}
```

### GET /api/capabilities
Get interface capabilities (speed, DPDK, etc.)

---

## Neighbor Discovery

### POST /api/neighbors/discover
Discover neighbors on all or specified interfaces

**Request:**
```json
{
  "interfaces": ["eno2", "eno3"]
}
```

**Response:**
```json
{
  "success": true,
  "neighbors": {
    "eno2": {
      "arp_neighbors": [
        {
          "ip": "24.1.6.129",
          "mac": "aa:bb:cc:dd:ee:ff",
          "state": "REACHABLE"
        }
      ],
      "lldp_neighbors": [
        {
          "system_name": "Switch1",
          "port_id": "Gi0/1",
          "chassis_id": "aa:bb:cc:dd:ee:ff"
        }
      ],
      "link_status": {
        "up": true,
        "speed": "1000Mb/s",
        "duplex": "Full"
      }
    }
  }
}
```

### GET /api/neighbors/<interface>
Get cached neighbor info for specific interface

---

## Traffic Profiles

### GET /api/traffic-profiles
Get all traffic profiles

### POST /api/traffic-profiles
Create new traffic profile

**Request:**
```json
{
  "name": "UDP_Test",
  "src_interface": "eno2",
  "dst_interface": "eno3",
  "dst_ip": "24.1.1.139",
  "protocol": "udp",
  "dst_port": 9999,
  "bandwidth_mbps": 100,
  "packet_size": 1400,
  "enabled": false
}
```

### PUT /api/traffic-profiles/<name>
Update existing profile

### DELETE /api/traffic-profiles/<name>
Delete profile

### POST /api/traffic-profiles/<name>/enable
Enable profile (starts traffic)

### POST /api/traffic-profiles/<name>/disable
Disable profile (stops traffic)

---

## Traffic Control

### POST /api/traffic/start
Start all enabled profiles

### POST /api/traffic/stop
Stop all traffic

### GET /api/traffic/stats
Get traffic statistics

**Response:**
```json
{
  "success": true,
  "stats": {
    "eno2": {
      "tx_packets": 150000,
      "tx_bytes": 210000000,
      "rx_packets": 145000,
      "rx_bytes": 203000000
    }
  }
}
```

---

## SNMP Agent Farm (NEW)

### POST /api/snmp/start
Start SNMP agent simulation

**Request:**
```json
{
  "base_ip": "192.168.100.1",
  "count": 10
}
```

Creates 10 SNMP agents at IPs:
- 192.168.100.1
- 192.168.100.2
- ... 
- 192.168.100.10

**Response:**
```json
{
  "success": true,
  "agents": 10,
  "base_ip": "192.168.100.1"
}
```

### POST /api/snmp/stop
Stop all SNMP agents

### GET /api/snmp/status
Get SNMP agent statistics

**Response:**
```json
{
  "success": true,
  "stats": {
    "agent_count": 10,
    "total_requests": 5420,
    "active": true
  }
}
```

---

## NetFlow/IPFIX Generation (NEW)

### POST /api/netflow/start
Start NetFlow generation

**Request:**
```json
{
  "collector_ip": "192.168.1.100",
  "collector_port": 2055,
  "flows_per_sec": 1000,
  "duration": 60
}
```

Generates 1000 flows/second for 60 seconds to collector

**Response:**
```json
{
  "success": true
}
```

---

## BGP Route Injection (NEW)

### POST /api/bgp/start
Start BGP session and inject routes

**Request:**
```json
{
  "peer_ip": "192.168.1.1",
  "local_asn": 65000,
  "route_count": 1000
}
```

**Response:**
```json
{
  "success": true
}
```

### POST /api/bgp/stop
Stop BGP session

---

## QoS Validation (NEW)

### POST /api/qos/test
Run QoS validation test

**Request:**
```json
{
  "src_ip": "192.168.1.1",
  "dst_ip": "192.168.1.2",
  "duration": 60,
  "scenario": "voice_video_data"
}
```

**Scenarios:**
- `voice_video_data` - 3-class test (Voice, Video, Data)
- `eight_class` - 8-class QoS model

**Response:**
```json
{
  "success": true,
  "message": "QoS test started"
}
```

### GET /api/qos/results
Get QoS test results

**Response:**
```json
{
  "success": true,
  "results": [
    {
      "class": "Voice",
      "dscp": 46,
      "packets_sent": 3000,
      "loss_percent": 0.05,
      "avg_latency_ms": 45.2,
      "avg_jitter_ms": 2.1
    }
  ]
}
```

---

## Network Impairments (NEW)

### POST /api/impairments/enable
Enable network impairments

**Request:**
```json
{
  "latency_ms": 100,
  "jitter_ms": 20,
  "loss_percent": 2.0,
  "burst_loss_percent": 1.0,
  "reorder_percent": 0.5,
  "duplicate_percent": 0.1
}
```

**Response:**
```json
{
  "success": true
}
```

### POST /api/impairments/disable
Disable all impairments

---

## Feature Status

### GET /api/features/status
Check which features are available

**Response:**
```json
{
  "success": true,
  "features": {
    "snmp": true,
    "netflow": true,
    "bgp": true,
    "qos": true,
    "impairments": true,
    "tcp_optimized": true
  }
}
```

---

## RFC2544 Testing

### POST /api/rfc2544/start
Start RFC2544 benchmark tests

**Request:**
```json
{
  "profile_name": "UDP_Test"
}
```

### GET /api/rfc2544/results/<profile_name>
Get RFC2544 test results

---

## Configuration

### POST /api/config/save
Save current configuration to file

### POST /api/config/load
Load configuration from file

**Request:**
```json
{
  "filename": "/path/to/config.json"
}
```

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "success": false,
  "error": "Description of error"
}
```

HTTP Status Codes:
- 200: Success
- 400: Bad request (invalid parameters)
- 404: Resource not found
- 500: Internal server error

---

## Examples

### Complete Workflow

```bash
# 1. Check available features
curl http://localhost:5000/api/features/status

# 2. Discover neighbors
curl -X POST http://localhost:5000/api/neighbors/discover \
  -H "Content-Type: application/json" \
  -d '{"interfaces": ["eno2", "eno3"]}'

# 3. Create traffic profile
curl -X POST http://localhost:5000/api/traffic-profiles \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My_Test",
    "src_interface": "eno2",
    "dst_interface": "eno3",
    "dst_ip": "24.1.1.139",
    "protocol": "udp",
    "bandwidth_mbps": 100
  }'

# 4. Enable profile
curl -X POST http://localhost:5000/api/traffic-profiles/My_Test/enable

# 5. Check stats
curl http://localhost:5000/api/traffic/stats

# 6. Start SNMP agents
curl -X POST http://localhost:5000/api/snmp/start \
  -H "Content-Type: application/json" \
  -d '{"base_ip": "192.168.100.1", "count": 10}'

# 7. Start NetFlow
curl -X POST http://localhost:5000/api/netflow/start \
  -H "Content-Type: application/json" \
  -d '{
    "collector_ip": "192.168.1.100",
    "flows_per_sec": 1000
  }'
```

---

## Rate Limits

None - local network use only

## Notes

- All timestamps are in Unix epoch format
- All IP addresses are IPv4
- All ports are 0-65535
- Bandwidth is in Mbps
- Packet sizes are in bytes
