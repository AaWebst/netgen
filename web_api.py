#!/usr/bin/env python3
"""
VEP1445 Unified Web API Backend
RESTful API for controlling mixed copper/SFP traffic generation
Supports: Standard copper (1G) + DPDK SFP (10G) in single interface
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import threading
import time
from typing import Dict, List
import os
import sys

# Import the unified traffic engine
from traffic_engine_unified import (
    UnifiedTrafficEngine as TrafficEngineCore, 
    InterfaceConfig, 
    TrafficProfile,
    InterfaceType
)
from neighbor_discovery import neighbor_discovery

# Import new feature modules (optional - will work even if not available)
try:
    from monitoring.snmp_agent import SNMPAgentFarm
except ImportError:
    SNMPAgentFarm = None

try:
    from monitoring.netflow_generator import FlowGenerator
except ImportError:
    FlowGenerator = None

try:
    from protocols.bgp_routing import BGPSession
except ImportError:
    BGPSession = None

try:
    from testing.qos_validation import QoSValidator, QoSTestScenarios
except ImportError:
    QoSValidator = None
    QoSTestScenarios = None

try:
    from testing.network_impairments import PacketImpairment, ImpairmentProfile
except ImportError:
    PacketImpairment = None
    ImpairmentProfile = None

try:
    from protocols.tcp_performance_optimized import HighPerformanceTCPEngine
except ImportError:
    HighPerformanceTCPEngine = None

app = Flask(__name__, static_folder='web')
CORS(app)

# Global traffic engine instance
engine = TrafficEngineCore()
engine_lock = threading.Lock()

# Configuration file
CONFIG_FILE = '/home/claude/vep1445_runtime_config.json'

# State for new features
feature_state = {
    'snmp_farm': None,
    'netflow_gen': None,
    'bgp_session': None,
    'qos_validator': None,
    'impairment_engine': None,
    'tcp_engine': None
}


@app.route('/')
def index():
    """Serve the main web interface"""
    return send_from_directory('web', 'index.html')


@app.route('/api/interfaces', methods=['GET'])
def get_interfaces():
    """Get all network interfaces and their status"""
    with engine_lock:
        interfaces = engine.get_interface_status()
        return jsonify({
            'success': True,
            'interfaces': interfaces
        })


@app.route('/api/interfaces/<interface_name>', methods=['GET'])
def get_interface(interface_name):
    """Get specific interface details"""
    with engine_lock:
        status = engine.get_interface_status()
        capabilities = engine.get_interface_capabilities()
        
        if interface_name in status:
            interface_data = status[interface_name]
            if interface_name in capabilities:
                interface_data.update(capabilities[interface_name])
            
            return jsonify({
                'success': True,
                'interface': interface_data
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Interface not found'
            }), 404


@app.route('/api/capabilities', methods=['GET'])
def get_capabilities():
    """Get capabilities of all interfaces"""
    with engine_lock:
        capabilities = engine.get_interface_capabilities()
        return jsonify({
            'success': True,
            'capabilities': capabilities
        })


@app.route('/api/interfaces', methods=['POST'])
def add_interface():
    """Add a new network interface"""
    data = request.json
    
    try:
        config = InterfaceConfig(
            name=data['name'],
            mac_address=data.get('mac_address', '00:00:00:00:00:00'),
            ip_address=data.get('ip_address'),
            subnet_mask=data.get('subnet_mask'),
            ipv6_address=data.get('ipv6_address'),
            gateway=data.get('gateway'),
            vlan_id=data.get('vlan_id')
        )
        
        with engine_lock:
            engine.add_interface(config)
            
            # Initialize the interface
            interface = engine.interfaces[config.name]
            interface.initialize(
                use_dhcp=data.get('use_dhcp', True),
                use_arp_discovery=data.get('use_arp_discovery', True)
            )
            interface.create_raw_socket()
            
        return jsonify({
            'success': True,
            'message': f'Interface {config.name} added successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/interfaces/<interface_name>/discover', methods=['POST'])
def rediscover_interface(interface_name):
    """Re-run discovery on an interface"""
    try:
        with engine_lock:
            if interface_name not in engine.interfaces:
                return jsonify({
                    'success': False,
                    'error': 'Interface not found'
                }), 404
                
            interface = engine.interfaces[interface_name]
            interface.initialize(use_dhcp=True, use_arp_discovery=True)
            
        return jsonify({
            'success': True,
            'message': 'Discovery completed',
            'interface': engine.get_interface_status()[interface_name]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/traffic-profiles', methods=['GET'])
def get_traffic_profiles():
    """Get all traffic profiles"""
    with engine_lock:
        profiles = {
            name: {
                'name': p.name,
                'src_interface': p.src_interface,
                'dst_interface': p.dst_interface,
                'dst_ip': p.dst_ip,
                'bandwidth_mbps': p.bandwidth_mbps,
                'packet_size': p.packet_size,
                'protocol': p.protocol,
                'enabled': p.enabled,
                'dscp': p.dscp,
                'latency_ms': p.latency_ms,
                'jitter_ms': p.jitter_ms,
                'packet_loss_percent': p.packet_loss_percent,
                'vlan_outer': p.vlan_outer,
                'vlan_inner': p.vlan_inner,
                'vni': p.vni,
                'mpls_label': p.mpls_label,
                'rfc2544_enabled': p.rfc2544_enabled
            }
            for name, p in engine.traffic_profiles.items()
        }
        
    return jsonify({
        'success': True,
        'profiles': profiles
    })


@app.route('/api/traffic-profiles', methods=['POST'])
def add_traffic_profile():
    """Add a new traffic profile"""
    data = request.json
    
    try:
        profile = TrafficProfile(
            name=data['name'],
            src_interface=data['src_interface'],
            dst_interface=data['dst_interface'],
            dst_ip=data['dst_ip'],
            bandwidth_mbps=float(data.get('bandwidth_mbps', 10.0)),
            packet_size=int(data.get('packet_size', 1024)),
            protocol=data.get('protocol', 'ipv4'),
            dscp=int(data.get('dscp', 0)),
            vlan_outer=data.get('vlan_outer'),
            vlan_inner=data.get('vlan_inner'),
            vni=data.get('vni'),
            mpls_label=data.get('mpls_label'),
            enabled=data.get('enabled', False),
            latency_ms=float(data.get('latency_ms', 0.0)),
            jitter_ms=float(data.get('jitter_ms', 0.0)),
            packet_loss_percent=float(data.get('packet_loss_percent', 0.0)),
            rfc2544_enabled=data.get('rfc2544_enabled', False)
        )
        
        with engine_lock:
            engine.add_traffic_profile(profile)
            
        return jsonify({
            'success': True,
            'message': f'Traffic profile {profile.name} added successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/traffic-profiles/<profile_name>', methods=['PUT'])
def update_traffic_profile(profile_name):
    """Update an existing traffic profile"""
    data = request.json
    
    try:
        with engine_lock:
            if profile_name not in engine.traffic_profiles:
                return jsonify({
                    'success': False,
                    'error': 'Profile not found'
                }), 404
                
            profile = engine.traffic_profiles[profile_name]
            
            # Update fields
            if 'bandwidth_mbps' in data:
                profile.bandwidth_mbps = float(data['bandwidth_mbps'])
            if 'packet_size' in data:
                profile.packet_size = int(data['packet_size'])
            if 'dst_ip' in data:
                profile.dst_ip = data['dst_ip']
            if 'dscp' in data:
                profile.dscp = int(data['dscp'])
            if 'latency_ms' in data:
                profile.latency_ms = float(data['latency_ms'])
            if 'jitter_ms' in data:
                profile.jitter_ms = float(data['jitter_ms'])
            if 'packet_loss_percent' in data:
                profile.packet_loss_percent = float(data['packet_loss_percent'])
            if 'enabled' in data:
                profile.enabled = data['enabled']
            if 'vlan_outer' in data:
                profile.vlan_outer = data['vlan_outer']
            if 'vlan_inner' in data:
                profile.vlan_inner = data['vlan_inner']
            if 'vni' in data:
                profile.vni = data['vni']
            if 'mpls_label' in data:
                profile.mpls_label = data['mpls_label']
            if 'rfc2544_enabled' in data:
                profile.rfc2544_enabled = data['rfc2544_enabled']
                
        return jsonify({
            'success': True,
            'message': f'Profile {profile_name} updated successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/traffic-profiles/<profile_name>', methods=['DELETE'])
def delete_traffic_profile(profile_name):
    """Delete a traffic profile"""
    try:
        with engine_lock:
            if profile_name not in engine.traffic_profiles:
                return jsonify({
                    'success': False,
                    'error': 'Profile not found'
                }), 404
                
            # Stop traffic if running
            if profile_name in engine.generator_threads:
                engine.traffic_profiles[profile_name].enabled = False
                time.sleep(0.5)
                
            del engine.traffic_profiles[profile_name]
            
        return jsonify({
            'success': True,
            'message': f'Profile {profile_name} deleted successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/traffic/start', methods=['POST'])
def start_traffic():
    """Start traffic generation"""
    try:
        with engine_lock:
            if not engine.running:
                engine.start_traffic()
                
        return jsonify({
            'success': True,
            'message': 'Traffic generation started'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/traffic/stop', methods=['POST'])
def stop_traffic():
    """Stop traffic generation"""
    try:
        with engine_lock:
            if engine.running:
                engine.stop_traffic()
                
        return jsonify({
            'success': True,
            'message': 'Traffic generation stopped'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/traffic/stats', methods=['GET'])
def get_traffic_stats():
    """Get traffic statistics"""
    with engine_lock:
        stats = engine.get_traffic_stats()
        running = engine.running
        
    return jsonify({
        'success': True,
        'running': running,
        'stats': stats
    })


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get complete configuration"""
    with engine_lock:
        config = engine.get_config()
        
    return jsonify({
        'success': True,
        'config': config
    })


@app.route('/api/config', methods=['POST'])
def save_config():
    """Save configuration to file"""
    try:
        filename = request.json.get('filename', CONFIG_FILE)
        
        with engine_lock:
            engine.save_config(filename)
            
        return jsonify({
            'success': True,
            'message': f'Configuration saved to {filename}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/config/load', methods=['POST'])
def load_config():
    """Load configuration from file"""
    try:
        filename = request.json.get('filename', CONFIG_FILE)
        
        with engine_lock:
            # Stop any running traffic
            if engine.running:
                engine.stop_traffic()
                
            # Clear existing configuration
            engine.traffic_profiles.clear()
            
            # Load new configuration
            engine.load_config(filename)
            
            # Re-initialize interfaces
            engine.initialize_interfaces()
            
        return jsonify({
            'success': True,
            'message': f'Configuration loaded from {filename}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/rfc2544/start', methods=['POST'])
def start_rfc2544():
    """Start RFC2544 testing"""
    data = request.json
    profile_name = data.get('profile_name')
    
    try:
        with engine_lock:
            if profile_name not in engine.traffic_profiles:
                return jsonify({
                    'success': False,
                    'error': 'Profile not found'
                }), 404
                
            profile = engine.traffic_profiles[profile_name]
            
            # Run tests in background
            def run_tests():
                results = {}
                
                if profile.rfc2544_throughput_test:
                    results['throughput'] = engine.rfc2544.run_throughput_test(
                        profile, None, None
                    )
                    
                if profile.rfc2544_latency_test:
                    results['latency'] = engine.rfc2544.run_latency_test(
                        profile, None, None
                    )
                    
                if profile.rfc2544_frame_loss_test:
                    results['frame_loss'] = engine.rfc2544.run_frame_loss_test(
                        profile, None, None
                    )
                    
                if profile.rfc2544_back_to_back_test:
                    results['back_to_back'] = engine.rfc2544.run_back_to_back_test(
                        profile, None, None
                    )
                    
                # Store results
                engine.rfc2544.results[profile_name] = results
                
            test_thread = threading.Thread(target=run_tests, daemon=True)
            test_thread.start()
            
        return jsonify({
            'success': True,
            'message': 'RFC2544 testing started'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/rfc2544/results/<profile_name>', methods=['GET'])
def get_rfc2544_results(profile_name):
    """Get RFC2544 test results"""
    with engine_lock:
        if profile_name in engine.rfc2544.results:
            return jsonify({
                'success': True,
                'results': engine.rfc2544.results[profile_name]
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No results available'
            }), 404


@app.route('/api/system/status', methods=['GET'])
def get_system_status():
    """Get overall system status"""
    with engine_lock:
        stats = engine.get_stats()
        status = {
            'running': engine.running,
            'num_interfaces': len(engine.interfaces),
            'num_profiles': len(engine.traffic_profiles),
            'active_profiles': sum(1 for p in engine.traffic_profiles.values() if p.enabled),
            'total_tx_packets': sum(s.get('tx_packets', 0) for s in stats.values()),
            'total_tx_bytes': sum(s.get('tx_bytes', 0) for s in stats.values()),
            'total_dropped': sum(s.get('dropped', 0) for s in stats.values())
        }
        
    return jsonify({
        'success': True,
        'status': status
    })


def initialize_default_config():
    """Initialize with default configuration: 5 copper LANs + 2 SFP 10G ports"""
    
    import logging
    logger = logging.getLogger(__name__)
    
    # Add 5 copper LAN ports (eth1-eth5) - 1G, optimized mode
    for i in range(1, 6):
        config = InterfaceConfig(
            name=f"eth{i}",
            mac_address=f"00:11:22:33:44:{i:02x}",
            interface_type=InterfaceType.COPPER_OPTIMIZED,
            speed_mbps=1000
        )
        engine.add_interface(config)
    
    # Add 2 SFP 10G ports (sfp1-sfp2) - 10G, DPDK mode
    for i in range(1, 3):
        config = InterfaceConfig(
            name=f"sfp{i}",
            mac_address=f"00:11:22:33:55:{i:02x}",
            interface_type=InterfaceType.SFP_10G_DPDK,
            speed_mbps=10000
        )
        engine.add_interface(config)
    
    logger.info(f"Initialized {len(engine.interfaces)} interfaces:")
    logger.info(f"  - 5 copper ports (eth1-eth5): 1Gbps optimized mode")
    logger.info(f"  - 2 SFP ports (sfp1-sfp2): 10Gbps DPDK mode")
    
    # Try to initialize interfaces with network discovery
    try:
        # For copper ports, try DHCP discovery
        for name in [f"eth{i}" for i in range(1, 6)]:
            if name in engine.interfaces:
                interface = engine.interfaces[name]
                # In unified engine, interfaces are already initialized
                logger.info(f"  {name}: ready")
        
        # For SFP ports, they're ready for traffic (no DHCP needed usually)
        for name in [f"sfp{i}" for i in range(1, 3)]:
            if name in engine.interfaces:
                logger.info(f"  {name}: ready (DPDK mode)")
                
    except Exception as e:
        logger.warning(f"Could not fully initialize interfaces: {e}")
        logger.info("This is normal if running outside actual hardware environment")


@app.route('/api/neighbors/discover', methods=['POST'])
def discover_neighbors():
    """Discover neighbors on specified interfaces"""
    try:
        data = request.json
        interfaces = data.get('interfaces', [])
        
        if not interfaces:
            # Discover all interfaces
            interfaces = list(engine.interfaces.keys())
        
        results = neighbor_discovery.discover_all_interfaces(interfaces)
        
        return jsonify({
            'success': True,
            'neighbors': results
        })
    
    except Exception as e:
        logger.error(f"Neighbor discovery error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/neighbors/<interface_name>', methods=['GET'])
def get_neighbors(interface_name):
    """Get cached neighbor information for an interface"""
    try:
        if interface_name not in engine.interfaces:
            return jsonify({
                'success': False,
                'error': 'Interface not found'
            }), 404
        
        # Get cached scan or perform new scan
        if interface_name in neighbor_discovery.last_scan:
            result = neighbor_discovery.last_scan[interface_name]
        else:
            result = neighbor_discovery.discover_interface(interface_name)
        
        # Get best neighbor info for display
        neighbor_info = neighbor_discovery.get_best_neighbor_info(interface_name)
        
        return jsonify({
            'success': True,
            'interface': interface_name,
            'neighbor_info': neighbor_info,
            'arp_neighbors': result.get('arp_neighbors', []),
            'lldp_neighbors': result.get('lldp_neighbors', []),
            'link_status': result.get('link_status', {})
        })
    
    except Exception as e:
        logger.error(f"Get neighbors error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# NEW FEATURES - SNMP, NetFlow, BGP, QoS, Impairments
# ============================================================================

@app.route('/api/snmp/start', methods=['POST'])
def snmp_start():
    """Start SNMP agent farm"""
    if not SNMPAgentFarm:
        return jsonify({'success': False, 'error': 'SNMP module not available'}), 400
    
    try:
        data = request.json
        base_ip = data.get('base_ip', '192.168.100.1')
        count = data.get('count', 10)
        
        with engine_lock:
            if not feature_state['snmp_farm']:
                feature_state['snmp_farm'] = SNMPAgentFarm()
            
            feature_state['snmp_farm'].create_agents(base_ip=base_ip, count=count)
            feature_state['snmp_farm'].start_all()
        
        return jsonify({'success': True, 'agents': count, 'base_ip': base_ip})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/snmp/stop', methods=['POST'])
def snmp_stop():
    """Stop SNMP agent farm"""
    try:
        with engine_lock:
            if feature_state['snmp_farm']:
                feature_state['snmp_farm'].stop_all()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/snmp/status', methods=['GET'])
def snmp_status():
    """Get SNMP agent status"""
    with engine_lock:
        if feature_state['snmp_farm']:
            stats = feature_state['snmp_farm'].get_total_stats()
            return jsonify({'success': True, 'stats': stats})
        return jsonify({'success': True, 'stats': {'agent_count': 0}})


@app.route('/api/netflow/start', methods=['POST'])
def netflow_start():
    """Start NetFlow generation"""
    if not FlowGenerator:
        return jsonify({'success': False, 'error': 'NetFlow module not available'}), 400
    
    try:
        data = request.json
        collector_ip = data['collector_ip']
        collector_port = data.get('collector_port', 2055)
        flows_per_sec = data.get('flows_per_sec', 1000)
        duration = data.get('duration', 60)
        
        with engine_lock:
            if not feature_state['netflow_gen']:
                feature_state['netflow_gen'] = FlowGenerator('netflow5')
        
        def netflow_worker():
            feature_state['netflow_gen'].simulate_traffic_pattern(
                duration=duration,
                flows_per_second=flows_per_sec,
                collector_ip=collector_ip,
                collector_port=collector_port
            )
        
        threading.Thread(target=netflow_worker, daemon=True).start()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/bgp/start', methods=['POST'])
def bgp_start():
    """Start BGP session"""
    if not BGPSession:
        return jsonify({'success': False, 'error': 'BGP module not available'}), 400
    
    try:
        data = request.json
        peer_ip = data['peer_ip']
        local_asn = data.get('local_asn', 65000)
        route_count = data.get('route_count', 1000)
        
        def bgp_worker():
            with engine_lock:
                session = BGPSession(local_asn=local_asn, router_id="1.1.1.1")
                feature_state['bgp_session'] = session
            
            if session.connect(peer_ip, 179):
                session.send_open()
                for i in range(route_count):
                    prefix = f"10.{i//256}.{i%256}.0/24"
                    session.advertise_route(prefix, next_hop=peer_ip)
        
        threading.Thread(target=bgp_worker, daemon=True).start()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/bgp/stop', methods=['POST'])
def bgp_stop():
    """Stop BGP session"""
    try:
        with engine_lock:
            if feature_state['bgp_session']:
                feature_state['bgp_session'].close()
                feature_state['bgp_session'] = None
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/qos/test', methods=['POST'])
def qos_test():
    """Run QoS validation test"""
    if not QoSValidator or not QoSTestScenarios:
        return jsonify({'success': False, 'error': 'QoS module not available'}), 400
    
    try:
        data = request.json
        src_ip = data['src_ip']
        dst_ip = data['dst_ip']
        duration = data.get('duration', 60)
        scenario = data.get('scenario', 'voice_video_data')
        
        def qos_worker():
            validator = QoSValidator(src_ip, dst_ip)
            
            if scenario == 'voice_video_data':
                profiles = QoSTestScenarios.voice_video_data_test()
            elif scenario == 'eight_class':
                profiles = QoSTestScenarios.eight_class_test()
            else:
                profiles = QoSTestScenarios.voice_video_data_test()
            
            for profile in profiles:
                validator.add_profile(profile)
            
            validator.run_test(duration=duration)
            results = validator.get_all_results()
            
            with engine_lock:
                feature_state['qos_results'] = results
        
        threading.Thread(target=qos_worker, daemon=True).start()
        return jsonify({'success': True, 'message': 'QoS test started'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/qos/results', methods=['GET'])
def qos_results():
    """Get QoS test results"""
    with engine_lock:
        results = feature_state.get('qos_results', [])
        return jsonify({'success': True, 'results': results})


@app.route('/api/impairments/enable', methods=['POST'])
def impairments_enable():
    """Enable network impairments"""
    if not PacketImpairment:
        return jsonify({'success': False, 'error': 'Impairment module not available'}), 400
    
    try:
        data = request.json
        
        with engine_lock:
            if not feature_state['impairment_engine']:
                feature_state['impairment_engine'] = PacketImpairment()
            
            feature_state['impairment_engine'].latency_ms = data.get('latency_ms', 0)
            feature_state['impairment_engine'].jitter_ms = data.get('jitter_ms', 0)
            feature_state['impairment_engine'].loss_percent = data.get('loss_percent', 0)
            feature_state['impairment_engine'].burst_loss_percent = data.get('burst_loss_percent', 0)
            feature_state['impairment_engine'].reorder_percent = data.get('reorder_percent', 0)
            feature_state['impairment_engine'].duplicate_percent = data.get('duplicate_percent', 0)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/impairments/disable', methods=['POST'])
def impairments_disable():
    """Disable network impairments"""
    with engine_lock:
        feature_state['impairment_engine'] = None
    return jsonify({'success': True})


@app.route('/api/features/status', methods=['GET'])
def features_status():
    """Get status of all features"""
    return jsonify({
        'success': True,
        'features': {
            'snmp': SNMPAgentFarm is not None,
            'netflow': FlowGenerator is not None,
            'bgp': BGPSession is not None,
            'qos': QoSValidator is not None,
            'impairments': PacketImpairment is not None,
            'tcp_optimized': HighPerformanceTCPEngine is not None
        }
    })


if __name__ == '__main__':
    # Initialize default configuration
    initialize_default_config()
    
    # Start the web server
    print("="*60)
    print("VEP1445 Traffic Generator & Impairment Tool")
    print("="*60)
    print(f"Web Interface: http://0.0.0.0:5000")
    print(f"API Endpoints: http://0.0.0.0:5000/api/")
    print("="*60)
    
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
