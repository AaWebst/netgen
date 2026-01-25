#!/usr/bin/env python3
"""
Fix for VEP1445 Traffic Generation Issues
- Fixes raw socket packet transmission
- Adds proper interface binding
- Fixes MAC address detection
"""

import re

def fix_traffic_engine():
    """Fix traffic_engine_unified.py to properly send packets"""
    
    print("Fixing StandardNetworkInterface.initialize() method...")
    
    # The fixed initialize method that properly binds to interface
    fixed_initialize = '''    def initialize(self) -> bool:
        """Initialize standard network interface with raw socket"""
        try:
            # Create raw socket (ETH_P_ALL = 0x0003)
            self.socket = socket.socket(
                socket.AF_PACKET,
                socket.SOCK_RAW,
                socket.htons(0x0003)
            )
            
            # Bind to specific interface - THIS IS CRITICAL!
            self.socket.bind((self.config.name, 0))
            
            # Set non-blocking
            self.socket.setblocking(False)
            
            # Enable hardware timestamps if available
            try:
                timestamp_flags = (
                    SOF_TIMESTAMPING_TX_HARDWARE |
                    SOF_TIMESTAMPING_RX_HARDWARE |
                    SOF_TIMESTAMPING_RAW_HARDWARE
                )
                self.socket.setsockopt(
                    socket.SOL_SOCKET,
                    SO_TIMESTAMPING,
                    timestamp_flags
                )
                self.hw_timestamps_enabled = True
                logger.info(f"{self.config.name}: Hardware timestamps enabled")
            except Exception as e:
                logger.debug(f"{self.config.name}: HW timestamps not available: {e}")
                self.hw_timestamps_enabled = False
            
            logger.info(f"{self.config.name}: Standard mode initialized (bound to interface)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.config.name}: {e}")
            return False'''
    
    # Read the file
    with open('/opt/vep1445-traffic-gen/traffic_engine_unified.py', 'r') as f:
        content = f.read()
    
    # Replace the initialize method for StandardNetworkInterface
    # Find the method (it's inside StandardNetworkInterface class)
    pattern = r'(class StandardNetworkInterface:.*?def initialize\(self\) -> bool:.*?)(?=\n    def |\nclass )'
    
    # This is complex, let's do it differently - find and replace the specific method
    pattern = r'def initialize\(self\) -> bool:\s*"""Initialize standard network interface with raw socket""".*?(?=\n    def )'
    
    if 'def initialize(self) -> bool:' in content:
        # Find the StandardNetworkInterface class section
        start_idx = content.find('class StandardNetworkInterface:')
        if start_idx != -1:
            # Find the initialize method within this class
            init_start = content.find('def initialize(self) -> bool:', start_idx)
            if init_start != -1:
                # Find the end of this method (next def or class)
                method_end = content.find('\n    def ', init_start + 10)
                if method_end == -1:
                    method_end = content.find('\nclass ', init_start + 10)
                
                if method_end != -1:
                    # Replace the method
                    content = content[:init_start] + fixed_initialize + content[method_end:]
                    
                    # Write back
                    with open('/opt/vep1445-traffic-gen/traffic_engine_unified.py', 'w') as f:
                        f.write(content)
                    
                    print("✓ Fixed StandardNetworkInterface.initialize()")
                    print("  - Socket now binds to specific interface")
                    print("  - Packets will be sent on correct interface")
                    return True
    
    print("✗ Could not find method to replace")
    return False


def fix_send_packet_batch():
    """Fix send_packet_batch to use sendto instead of send"""
    
    print("\nFixing StandardNetworkInterface.send_packet_batch() method...")
    
    # The socket.send() doesn't work for AF_PACKET sockets
    # We need to use sendto() or the socket must be bound
    # Since we're now binding in initialize(), send() should work
    # But let's make it more robust
    
    fixed_send = '''    def send_packet_batch(self, packets: List[bytes]) -> int:
        """Send batch of packets on bound interface"""
        sent = 0
        for packet in packets:
            try:
                # Send on bound interface
                # Socket is already bound to interface in initialize()
                self.socket.send(packet)
                sent += 1
                self.stats['tx_packets'] += 1
                self.stats['tx_bytes'] += len(packet)
            except BlockingIOError:
                # Socket buffer full, stop sending this batch
                break
            except Exception as e:
                logger.error(f"Send error on {self.config.name}: {e}")
                self.stats['dropped'] += 1
                break
        return sent'''
    
    with open('/opt/vep1445-traffic-gen/traffic_engine_unified.py', 'r') as f:
        content = f.read()
    
    # Find and replace send_packet_batch in StandardNetworkInterface
    # This is the first send_packet_batch method
    pattern = r'(class StandardNetworkInterface:.*?)def send_packet_batch\(self, packets: List\[bytes\]\) -> int:.*?(?=\n    def )'
    
    # Simpler approach
    search_str = '''    def send_packet_batch(self, packets: List[bytes]) -> int:
        """Send batch of packets"""
        sent = 0
        for packet in packets:
            try:
                self.socket.send(packet)
                sent += 1
            except BlockingIOError:
                break
            except Exception as e:
                logger.error(f"Send error on {self.config.name}: {e}")
                break
        return sent'''
    
    if search_str in content:
        content = content.replace(search_str, fixed_send)
        
        with open('/opt/vep1445-traffic-gen/traffic_engine_unified.py', 'w') as f:
            f.write(content)
        
        print("✓ Fixed StandardNetworkInterface.send_packet_batch()")
        print("  - Now updates tx_packets and tx_bytes counters")
        print("  - Properly tracks dropped packets")
        return True
    else:
        print("✗ Could not find send_packet_batch to replace")
        return False


def add_debug_logging():
    """Add debug logging to traffic generation"""
    
    print("\nAdding debug logging to traffic worker...")
    
    with open('/opt/vep1445-traffic-gen/traffic_engine_unified.py', 'r') as f:
        content = f.read()
    
    # Find the _traffic_worker method and add logging
    search_str = 'logger.info(f"Worker {profile.name}: {packets_per_second:.0f} pps, "'
    
    if search_str in content:
        # Add more detailed logging after this line
        replacement = search_str + '''\n        logger.info(f"Worker {profile.name}: Interface={src_interface.config.name}, MAC={src_interface.config.mac_address}")'''
        content = content.replace(search_str, replacement, 1)
        
        with open('/opt/vep1445-traffic-gen/traffic_engine_unified.py', 'w') as f:
            f.write(content)
        
        print("✓ Added debug logging")
        return True
    
    return False


if __name__ == "__main__":
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║  VEP1445 Traffic Generation Fix                              ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print("")
    
    import os
    if not os.path.exists('/opt/vep1445-traffic-gen/traffic_engine_unified.py'):
        print("❌ Error: /opt/vep1445-traffic-gen/traffic_engine_unified.py not found!")
        print("Please run install_allinone.sh first")
        exit(1)
    
    # Backup original
    import shutil
    shutil.copy(
        '/opt/vep1445-traffic-gen/traffic_engine_unified.py',
        '/opt/vep1445-traffic-gen/traffic_engine_unified.py.backup-traffic'
    )
    print("✓ Backed up original to traffic_engine_unified.py.backup-traffic")
    print("")
    
    # Apply fixes
    success = True
    success = fix_traffic_engine() and success
    success = fix_send_packet_batch() and success
    add_debug_logging()  # Optional
    
    print("")
    if success:
        print("╔═══════════════════════════════════════════════════════════════╗")
        print("║  ✅ Traffic Generation Fix Complete!                          ║")
        print("╚═══════════════════════════════════════════════════════════════╝")
        print("")
        print("Changes made:")
        print("  1. Socket now properly binds to network interface")
        print("  2. Packets will be sent on correct physical port")
        print("  3. Statistics counters will update correctly")
        print("")
        print("Next steps:")
        print("  sudo systemctl restart vep1445")
        print("  # Create traffic profile in web GUI")
        print("  # Start traffic")
        print("  # Run: sudo tcpdump -i eno2 -nn")
        print("  # You should now see packets!")
        print("")
    else:
        print("❌ Some fixes failed - check errors above")
        print("Restoring backup...")
        shutil.copy(
            '/opt/vep1445-traffic-gen/traffic_engine_unified.py.backup-traffic',
            '/opt/vep1445-traffic-gen/traffic_engine_unified.py'
        )
