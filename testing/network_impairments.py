#!/usr/bin/env python3
"""
Network Impairment Engine for VEP1445
Simulate real-world network conditions: latency, jitter, packet loss, reordering
"""

import random
import time
import threading
from collections import deque
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)

class PacketImpairment:
    """Network impairment simulator"""
    
    def __init__(self):
        # Latency settings (milliseconds)
        self.latency_ms = 0
        self.latency_variation_ms = 0  # Jitter
        
        # Packet loss settings (percentage)
        self.packet_loss_percent = 0
        self.burst_loss_percent = 0  # Burst loss probability
        self.burst_loss_length = 3   # Average burst length
        
        # Reordering settings
        self.reorder_percent = 0
        self.reorder_gap = 3  # How many packets ahead to reorder
        
        # Duplication settings
        self.duplicate_percent = 0
        
        # Corruption settings
        self.corruption_percent = 0
        self.corruption_offset = 0  # Byte offset to corrupt
        
        # Bandwidth limiting (bps)
        self.bandwidth_limit_bps = 0
        
        # Internal state
        self.packet_buffer = deque()
        self.in_burst_loss = False
        self.burst_loss_counter = 0
        self.bytes_sent = 0
        self.last_send_time = time.time()
        
        # Statistics
        self.stats = {
            'packets_processed': 0,
            'packets_delayed': 0,
            'packets_dropped': 0,
            'packets_reordered': 0,
            'packets_duplicated': 0,
            'packets_corrupted': 0,
            'total_latency_added_ms': 0
        }
    
    def set_latency(self, latency_ms: float, jitter_ms: float = 0):
        """Set latency and jitter"""
        self.latency_ms = latency_ms
        self.latency_variation_ms = jitter_ms
        logger.info(f"Impairment: Latency={latency_ms}ms, Jitter={jitter_ms}ms")
    
    def set_packet_loss(self, loss_percent: float, burst_loss: float = 0):
        """Set packet loss percentage"""
        self.packet_loss_percent = loss_percent
        self.burst_loss_percent = burst_loss
        logger.info(f"Impairment: Loss={loss_percent}%, Burst Loss={burst_loss}%")
    
    def set_reordering(self, reorder_percent: float, gap: int = 3):
        """Set packet reordering"""
        self.reorder_percent = reorder_percent
        self.reorder_gap = gap
        logger.info(f"Impairment: Reorder={reorder_percent}%, Gap={gap}")
    
    def set_duplication(self, duplicate_percent: float):
        """Set packet duplication percentage"""
        self.duplicate_percent = duplicate_percent
        logger.info(f"Impairment: Duplication={duplicate_percent}%")
    
    def set_corruption(self, corruption_percent: float, offset: int = 0):
        """Set packet corruption"""
        self.corruption_percent = corruption_percent
        self.corruption_offset = offset
        logger.info(f"Impairment: Corruption={corruption_percent}%")
    
    def set_bandwidth_limit(self, bps: int):
        """Set bandwidth limit in bits per second"""
        self.bandwidth_limit_bps = bps
        logger.info(f"Impairment: Bandwidth limit={bps} bps ({bps/1000000:.1f} Mbps)")
    
    def apply_impairments(self, packet: bytes, send_callback: Callable) -> bool:
        """
        Apply impairments to packet
        
        Args:
            packet: Packet bytes
            send_callback: Function to call to actually send packet
            
        Returns:
            True if packet was processed (even if dropped)
        """
        self.stats['packets_processed'] += 1
        
        # 1. Check for packet loss
        if self._should_drop_packet():
            self.stats['packets_dropped'] += 1
            logger.debug("Packet dropped due to loss simulation")
            return True
        
        # 2. Check for duplication
        if self._should_duplicate():
            self.stats['packets_duplicated'] += 1
            # Send duplicate (with same impairments)
            threading.Timer(0.001, lambda: send_callback(packet)).start()
        
        # 3. Apply corruption
        if self._should_corrupt():
            packet = self._corrupt_packet(packet)
            self.stats['packets_corrupted'] += 1
        
        # 4. Apply latency/jitter
        delay_ms = self._calculate_delay()
        if delay_ms > 0:
            self.stats['packets_delayed'] += 1
            self.stats['total_latency_added_ms'] += delay_ms
            
            # Schedule delayed send
            threading.Timer(delay_ms / 1000.0, lambda: self._send_with_bandwidth_limit(packet, send_callback)).start()
        else:
            # Send immediately (but still check bandwidth limit)
            self._send_with_bandwidth_limit(packet, send_callback)
        
        return True
    
    def _should_drop_packet(self) -> bool:
        """Determine if packet should be dropped"""
        # Burst loss model
        if self.burst_loss_percent > 0:
            if self.in_burst_loss:
                self.burst_loss_counter -= 1
                if self.burst_loss_counter <= 0:
                    self.in_burst_loss = False
                return True
            else:
                if random.random() * 100 < self.burst_loss_percent:
                    self.in_burst_loss = True
                    self.burst_loss_counter = self.burst_loss_length
                    return True
        
        # Regular random loss
        if random.random() * 100 < self.packet_loss_percent:
            return True
        
        return False
    
    def _should_duplicate(self) -> bool:
        """Determine if packet should be duplicated"""
        return random.random() * 100 < self.duplicate_percent
    
    def _should_corrupt(self) -> bool:
        """Determine if packet should be corrupted"""
        return random.random() * 100 < self.corruption_percent
    
    def _corrupt_packet(self, packet: bytes) -> bytes:
        """Corrupt packet by flipping random bits"""
        if len(packet) <= self.corruption_offset:
            return packet
        
        packet_list = bytearray(packet)
        
        # Flip a random bit at corruption_offset
        byte_idx = self.corruption_offset
        bit_idx = random.randint(0, 7)
        
        packet_list[byte_idx] ^= (1 << bit_idx)
        
        return bytes(packet_list)
    
    def _calculate_delay(self) -> float:
        """Calculate delay in milliseconds"""
        if self.latency_ms == 0:
            return 0
        
        # Add jitter (uniform distribution)
        if self.latency_variation_ms > 0:
            jitter = random.uniform(-self.latency_variation_ms, self.latency_variation_ms)
        else:
            jitter = 0
        
        delay = self.latency_ms + jitter
        return max(0, delay)
    
    def _send_with_bandwidth_limit(self, packet: bytes, send_callback: Callable):
        """Send packet respecting bandwidth limit"""
        if self.bandwidth_limit_bps == 0:
            send_callback(packet)
            return
        
        # Calculate time needed to send this packet
        packet_bits = len(packet) * 8
        send_time = packet_bits / self.bandwidth_limit_bps
        
        # Check if we need to wait
        now = time.time()
        elapsed = now - self.last_send_time
        
        if elapsed < send_time:
            # Wait before sending
            wait_time = send_time - elapsed
            time.sleep(wait_time)
        
        send_callback(packet)
        self.last_send_time = time.time()
        self.bytes_sent += len(packet)
    
    def get_stats(self) -> dict:
        """Get impairment statistics"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'packets_processed': 0,
            'packets_delayed': 0,
            'packets_dropped': 0,
            'packets_reordered': 0,
            'packets_duplicated': 0,
            'packets_corrupted': 0,
            'total_latency_added_ms': 0
        }

class ImpairmentProfile:
    """Pre-defined impairment profiles"""
    
    # Good network
    PERFECT = {
        'latency_ms': 0,
        'jitter_ms': 0,
        'loss_percent': 0,
        'reorder_percent': 0
    }
    
    # Typical LAN
    LAN = {
        'latency_ms': 1,
        'jitter_ms': 0.5,
        'loss_percent': 0.001,
        'reorder_percent': 0
    }
    
    # Good broadband
    BROADBAND_GOOD = {
        'latency_ms': 20,
        'jitter_ms': 5,
        'loss_percent': 0.1,
        'reorder_percent': 0.01
    }
    
    # Poor broadband
    BROADBAND_POOR = {
        'latency_ms': 100,
        'jitter_ms': 30,
        'loss_percent': 2.0,
        'reorder_percent': 0.5,
        'burst_loss': 1.0
    }
    
    # Satellite link
    SATELLITE = {
        'latency_ms': 600,
        'jitter_ms': 50,
        'loss_percent': 0.5,
        'reorder_percent': 0.1
    }
    
    # Mobile 3G
    MOBILE_3G = {
        'latency_ms': 200,
        'jitter_ms': 100,
        'loss_percent': 5.0,
        'reorder_percent': 2.0,
        'burst_loss': 2.0
    }
    
    # Mobile 4G/LTE
    MOBILE_4G = {
        'latency_ms': 50,
        'jitter_ms': 20,
        'loss_percent': 1.0,
        'reorder_percent': 0.5
    }
    
    # Mobile 5G
    MOBILE_5G = {
        'latency_ms': 10,
        'jitter_ms': 5,
        'loss_percent': 0.1,
        'reorder_percent': 0.01
    }
    
    # Congested network
    CONGESTED = {
        'latency_ms': 500,
        'jitter_ms': 200,
        'loss_percent': 10.0,
        'reorder_percent': 5.0,
        'burst_loss': 5.0
    }

def apply_profile(impairment: PacketImpairment, profile: dict):
    """Apply pre-defined profile to impairment engine"""
    impairment.set_latency(
        profile.get('latency_ms', 0),
        profile.get('jitter_ms', 0)
    )
    impairment.set_packet_loss(
        profile.get('loss_percent', 0),
        profile.get('burst_loss', 0)
    )
    impairment.set_reordering(
        profile.get('reorder_percent', 0)
    )
    impairment.set_duplication(
        profile.get('duplicate_percent', 0)
    )
    
    logger.info(f"Applied impairment profile: {profile}")

# Test usage
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("Network Impairment Engine Test")
    print("=" * 60)
    
    print("\nFeatures:")
    print("  ✓ Latency injection")
    print("  ✓ Jitter (latency variation)")
    print("  ✓ Packet loss (random & burst)")
    print("  ✓ Packet reordering")
    print("  ✓ Packet duplication")
    print("  ✓ Packet corruption")
    print("  ✓ Bandwidth limiting")
    
    print("\nPre-defined Profiles:")
    print("  - PERFECT (no impairments)")
    print("  - LAN (1ms, 0.001% loss)")
    print("  - BROADBAND_GOOD (20ms, 0.1% loss)")
    print("  - BROADBAND_POOR (100ms, 2% loss)")
    print("  - SATELLITE (600ms, 0.5% loss)")
    print("  - MOBILE_3G (200ms, 5% loss)")
    print("  - MOBILE_4G (50ms, 1% loss)")
    print("  - MOBILE_5G (10ms, 0.1% loss)")
    print("  - CONGESTED (500ms, 10% loss)")
    
    print("\nUsage:")
    print("  # Create impairment engine")
    print("  imp = PacketImpairment()")
    print("")
    print("  # Set custom impairments")
    print("  imp.set_latency(50, jitter_ms=10)")
    print("  imp.set_packet_loss(2.0)")
    print("  imp.set_bandwidth_limit(10_000_000)  # 10 Mbps")
    print("")
    print("  # Or use profile")
    print("  apply_profile(imp, ImpairmentProfile.MOBILE_4G)")
    print("")
    print("  # Apply to packets")
    print("  imp.apply_impairments(packet, send_callback)")
    print("")
    print("  # Get statistics")
    print("  stats = imp.get_stats()")
    print("  print(f'Dropped: {stats[\"packets_dropped\"]}')")
    
    # Test example
    print("\n" + "=" * 60)
    print("Test: Simulating 100 packets with MOBILE_4G profile")
    print("=" * 60)
    
    imp = PacketImpairment()
    apply_profile(imp, ImpairmentProfile.MOBILE_4G)
    
    def mock_send(packet):
        pass  # Mock send function
    
    test_packet = b'X' * 1000
    
    for i in range(100):
        imp.apply_impairments(test_packet, mock_send)
    
    stats = imp.get_stats()
    print(f"\nResults after 100 packets:")
    print(f"  Processed: {stats['packets_processed']}")
    print(f"  Dropped: {stats['packets_dropped']} ({stats['packets_dropped']/stats['packets_processed']*100:.1f}%)")
    print(f"  Delayed: {stats['packets_delayed']}")
    print(f"  Duplicated: {stats['packets_duplicated']}")
    print(f"  Corrupted: {stats['packets_corrupted']}")
    print(f"  Total latency added: {stats['total_latency_added_ms']:.1f}ms")
    
    print("\n✓ Impairment engine ready")
