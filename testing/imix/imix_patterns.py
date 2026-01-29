#!/usr/bin/env python3
"""
IMIX Traffic Pattern Generator
Industry-standard mixed packet size distributions
"""

import random
from typing import List, Tuple, Dict
import logging

logger = logging.getLogger(__name__)

class IMIXProfile:
    """IMIX Traffic Profile"""
    
    # Standard IMIX profiles (packet_size, weight)
    IMIX_STANDARD = [
        (64, 7),      # 58.33%
        (590, 4),     # 33.33%
        (1518, 1)     # 8.33%
    ]
    
    IMIX_IETF = [
        (64, 58),
        (570, 33),
        (1518, 9)
    ]
    
    IMIX_CISCO = [
        (64, 50),
        (594, 25),
        (1280, 25)
    ]
    
    IMIX_QUADMODAL = [
        (64, 25),
        (128, 25),
        (512, 25),
        (1518, 25)
    ]
    
    IMIX_TRIMODAL = [
        (64, 33),
        (512, 33),
        (1518, 34)
    ]
    
    IMIX_VOICE = [
        (64, 60),     # RTP headers
        (200, 30),    # Voice payload (G.711)
        (400, 10)     # Signaling
    ]
    
    IMIX_VIDEO = [
        (64, 10),     # Small control packets
        (512, 20),    # Medium frames
        (1200, 40),   # HD frames
        (1518, 30)    # Full MTU frames
    ]
    
    IMIX_WEB = [
        (64, 40),     # ACKs and small requests
        (512, 30),    # Medium HTTP responses
        (1460, 30)    # Full MSS packets
    ]
    
    def __init__(self, profile: List[Tuple[int, int]] = None, name: str = "Custom"):
        """
        Initialize IMIX profile
        
        Args:
            profile: List of (packet_size, weight) tuples
            name: Profile name
        """
        if profile is None:
            profile = self.IMIX_STANDARD
        
        self.name = name
        self.distribution = profile
        
        # Calculate total weight
        self.total_weight = sum(weight for _, weight in profile)
        
        # Build cumulative distribution for fast sampling
        self.cumulative = []
        cumsum = 0
        for size, weight in profile:
            cumsum += weight
            self.cumulative.append((size, cumsum))
        
        logger.info(f"IMIX Profile '{name}' initialized: {len(profile)} sizes")
    
    def get_packet_size(self) -> int:
        """Get random packet size according to distribution"""
        rand_val = random.randint(1, self.total_weight)
        
        for size, cumsum in self.cumulative:
            if rand_val <= cumsum:
                return size
        
        # Fallback (should never reach here)
        return self.distribution[-1][0]
    
    def get_sizes_batch(self, count: int) -> List[int]:
        """Get batch of random packet sizes"""
        return [self.get_packet_size() for _ in range(count)]
    
    def get_stats(self) -> Dict:
        """Get profile statistics"""
        sizes = []
        weights = []
        
        for size, weight in self.distribution:
            sizes.append(size)
            weights.append(weight)
        
        # Calculate weighted average
        avg_size = sum(s * w for s, w in self.distribution) / self.total_weight
        
        # Calculate percentage distribution
        percentages = [(size, weight * 100.0 / self.total_weight) 
                      for size, weight in self.distribution]
        
        return {
            'name': self.name,
            'sizes': sizes,
            'weights': weights,
            'total_weight': self.total_weight,
            'avg_size': avg_size,
            'percentages': percentages
        }
    
    def __str__(self):
        stats = self.get_stats()
        result = f"IMIX Profile: {self.name}\n"
        result += f"  Average Size: {stats['avg_size']:.0f} bytes\n"
        result += f"  Distribution:\n"
        for size, pct in stats['percentages']:
            result += f"    {size:4d} bytes: {pct:5.1f}%\n"
        return result

class IMIXGenerator:
    """IMIX Traffic Generator"""
    
    def __init__(self, profile: IMIXProfile):
        self.profile = profile
        self.packets_generated = 0
        self.bytes_generated = 0
    
    def generate_packet(self, fill_byte: int = 0) -> bytes:
        """Generate single packet with IMIX size"""
        size = self.profile.get_packet_size()
        
        # Generate packet data (filled with specified byte)
        packet = bytes([fill_byte] * size)
        
        self.packets_generated += 1
        self.bytes_generated += size
        
        return packet
    
    def generate_stream(self, duration: float, pps: int, 
                       fill_byte: int = 0) -> List[Tuple[float, bytes]]:
        """
        Generate stream of packets with IMIX distribution
        
        Args:
            duration: Stream duration in seconds
            pps: Packets per second
            fill_byte: Byte to fill packets with
            
        Returns:
            List of (timestamp, packet_data) tuples
        """
        total_packets = int(duration * pps)
        interval = 1.0 / pps
        
        stream = []
        timestamp = 0.0
        
        for i in range(total_packets):
            size = self.profile.get_packet_size()
            packet = bytes([fill_byte] * size)
            
            stream.append((timestamp, packet))
            timestamp += interval
            
            self.packets_generated += 1
            self.bytes_generated += size
        
        logger.info(f"Generated IMIX stream: {total_packets} packets, "
                   f"{self.bytes_generated} bytes, {duration}s duration")
        
        return stream
    
    def get_stats(self) -> Dict:
        """Get generator statistics"""
        return {
            'profile': self.profile.name,
            'packets_generated': self.packets_generated,
            'bytes_generated': self.bytes_generated,
            'avg_packet_size': self.bytes_generated / self.packets_generated if self.packets_generated > 0 else 0
        }

class BurstPattern:
    """Burst traffic pattern generator"""
    
    def __init__(self, burst_size: int, burst_interval: float, 
                 packet_interval: float = 0.0):
        """
        Initialize burst pattern
        
        Args:
            burst_size: Number of packets per burst
            burst_interval: Time between bursts (seconds)
            packet_interval: Time between packets within burst (0 = back-to-back)
        """
        self.burst_size = burst_size
        self.burst_interval = burst_interval
        self.packet_interval = packet_interval
    
    def generate_pattern(self, num_bursts: int, imix: IMIXProfile = None) -> List[Tuple[float, int]]:
        """
        Generate burst pattern
        
        Args:
            num_bursts: Number of bursts to generate
            imix: Optional IMIX profile for packet sizes
            
        Returns:
            List of (timestamp, packet_size) tuples
        """
        pattern = []
        timestamp = 0.0
        
        for burst_num in range(num_bursts):
            # Generate burst
            for pkt_num in range(self.burst_size):
                if imix:
                    size = imix.get_packet_size()
                else:
                    size = 1518  # Default to max Ethernet frame
                
                pattern.append((timestamp, size))
                timestamp += self.packet_interval
            
            # Wait for next burst
            timestamp += self.burst_interval
        
        logger.info(f"Generated burst pattern: {num_bursts} bursts, "
                   f"{num_bursts * self.burst_size} packets")
        
        return pattern

class TrafficShape:
    """Traffic shaping patterns"""
    
    @staticmethod
    def constant_rate(pps: int, duration: float, packet_size: int = 1518) -> List[Tuple[float, int]]:
        """Constant rate traffic"""
        interval = 1.0 / pps
        num_packets = int(duration * pps)
        
        return [(i * interval, packet_size) for i in range(num_packets)]
    
    @staticmethod
    def ramp_up(start_pps: int, end_pps: int, duration: float, 
                packet_size: int = 1518) -> List[Tuple[float, int]]:
        """Linearly increasing traffic rate"""
        pattern = []
        timestamp = 0.0
        
        while timestamp < duration:
            # Calculate current PPS based on progress
            progress = timestamp / duration
            current_pps = start_pps + (end_pps - start_pps) * progress
            
            interval = 1.0 / current_pps
            pattern.append((timestamp, packet_size))
            timestamp += interval
        
        return pattern
    
    @staticmethod
    def ramp_down(start_pps: int, end_pps: int, duration: float,
                  packet_size: int = 1518) -> List[Tuple[float, int]]:
        """Linearly decreasing traffic rate"""
        return TrafficShape.ramp_up(end_pps, start_pps, duration, packet_size)
    
    @staticmethod
    def sine_wave(avg_pps: int, amplitude: int, period: float, 
                  duration: float, packet_size: int = 1518) -> List[Tuple[float, int]]:
        """Sinusoidal traffic pattern"""
        import math
        
        pattern = []
        timestamp = 0.0
        
        while timestamp < duration:
            # Calculate current PPS using sine wave
            phase = (timestamp / period) * 2 * math.pi
            current_pps = avg_pps + amplitude * math.sin(phase)
            current_pps = max(1, current_pps)  # Ensure positive
            
            interval = 1.0 / current_pps
            pattern.append((timestamp, packet_size))
            timestamp += interval
        
        return pattern
    
    @staticmethod
    def random_rate(min_pps: int, max_pps: int, duration: float,
                   change_interval: float = 1.0, packet_size: int = 1518) -> List[Tuple[float, int]]:
        """Random rate changes"""
        pattern = []
        timestamp = 0.0
        next_change = change_interval
        current_pps = random.randint(min_pps, max_pps)
        
        while timestamp < duration:
            if timestamp >= next_change:
                current_pps = random.randint(min_pps, max_pps)
                next_change += change_interval
            
            interval = 1.0 / current_pps
            pattern.append((timestamp, packet_size))
            timestamp += interval
        
        return pattern

# Test and examples
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("IMIX Traffic Pattern Generator Test")
    print("=" * 60)
    
    # Test 1: Standard IMIX
    print("\n1. Standard IMIX Profile:")
    imix = IMIXProfile(IMIXProfile.IMIX_STANDARD, "Standard")
    print(imix)
    
    # Generate sample
    sizes = imix.get_sizes_batch(1000)
    print(f"  Sample 1000 packets: min={min(sizes)}, max={max(sizes)}, avg={sum(sizes)/len(sizes):.0f}")
    
    # Test 2: Voice IMIX
    print("\n2. Voice IMIX Profile:")
    voice_imix = IMIXProfile(IMIXProfile.IMIX_VOICE, "Voice")
    print(voice_imix)
    
    # Test 3: IMIX Generator
    print("\n3. IMIX Generator:")
    gen = IMIXGenerator(imix)
    stream = gen.generate_stream(duration=1.0, pps=1000)
    print(f"  Generated stream: {len(stream)} packets")
    stats = gen.get_stats()
    print(f"  Total bytes: {stats['bytes_generated']}")
    print(f"  Avg size: {stats['avg_packet_size']:.0f} bytes")
    
    # Test 4: Burst Pattern
    print("\n4. Burst Pattern:")
    burst = BurstPattern(burst_size=10, burst_interval=1.0, packet_interval=0.001)
    pattern = burst.generate_pattern(num_bursts=5, imix=imix)
    print(f"  Generated {len(pattern)} packets in {5} bursts")
    
    # Test 5: Traffic Shaping
    print("\n5. Traffic Shaping:")
    ramp = TrafficShape.ramp_up(start_pps=100, end_pps=1000, duration=2.0)
    print(f"  Ramp-up pattern: {len(ramp)} packets")
    
    print("\n✓ IMIX module ready for integration")
