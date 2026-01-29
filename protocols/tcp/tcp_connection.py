#!/usr/bin/env python3
"""
TCP Connection Manager - Full Stateful TCP Implementation
Handles connection lifecycle, state machine, retransmission
"""

import time
import threading
import socket
import random
from enum import Enum
from typing import Dict, Optional, Callable
from collections import deque
import logging

logger = logging.getLogger(__name__)

class TCPState(Enum):
    """TCP Connection States (RFC 793)"""
    CLOSED = "CLOSED"
    LISTEN = "LISTEN"
    SYN_SENT = "SYN_SENT"
    SYN_RECEIVED = "SYN_RECEIVED"
    ESTABLISHED = "ESTABLISHED"
    FIN_WAIT_1 = "FIN_WAIT_1"
    FIN_WAIT_2 = "FIN_WAIT_2"
    CLOSE_WAIT = "CLOSE_WAIT"
    CLOSING = "CLOSING"
    LAST_ACK = "LAST_ACK"
    TIME_WAIT = "TIME_WAIT"

class TCPConnection:
    """Stateful TCP Connection"""
    
    def __init__(self, src_ip: str, src_port: int, dst_ip: str, dst_port: int,
                 send_callback: Callable, interface_name: str):
        # Connection 4-tuple
        self.src_ip = src_ip
        self.src_port = src_port
        self.dst_ip = dst_ip
        self.dst_port = dst_port
        self.interface_name = interface_name
        
        # State
        self.state = TCPState.CLOSED
        self.send_callback = send_callback
        
        # Sequence numbers
        self.seq_num = random.randint(0, 2**32 - 1)
        self.ack_num = 0
        self.initial_seq = self.seq_num
        
        # Window
        self.send_window = 65535
        self.recv_window = 65535
        self.mss = 1460
        
        # Buffers
        self.send_buffer = deque()
        self.recv_buffer = deque()
        self.out_of_order = {}
        
        # Retransmission
        self.unacked_packets = {}  # seq_num -> (packet, timestamp, retries)
        self.rto = 1.0  # Initial RTO: 1 second
        self.srtt = None  # Smoothed RTT
        self.rttvar = None  # RTT variance
        
        # Timers
        self.last_activity = time.time()
        self.time_wait_start = None
        
        # Statistics
        self.bytes_sent = 0
        self.bytes_received = 0
        self.packets_sent = 0
        self.packets_received = 0
        self.retransmits = 0
        
        # Connection callback
        self.on_established = None
        self.on_data = None
        self.on_closed = None
        
        self.lock = threading.Lock()
    
    def connect(self, timeout: float = 5.0) -> bool:
        """Initiate TCP connection (active open)"""
        with self.lock:
            if self.state != TCPState.CLOSED:
                return False
            
            # Send SYN
            from tcp_packet import build_syn_packet
            syn_packet = build_syn_packet(
                self.src_ip, self.dst_ip,
                self.src_port, self.dst_port,
                self.seq_num, self.mss
            )
            
            self._send_packet(syn_packet)
            self.state = TCPState.SYN_SENT
            self.seq_num += 1
            
            # Add to retransmit queue
            self.unacked_packets[self.initial_seq] = (syn_packet, time.time(), 0)
        
        # Wait for connection establishment
        start = time.time()
        while time.time() - start < timeout:
            with self.lock:
                if self.state == TCPState.ESTABLISHED:
                    logger.info(f"TCP connection established: {self.src_ip}:{self.src_port} -> {self.dst_ip}:{self.dst_port}")
                    return True
            time.sleep(0.01)
        
        logger.error(f"TCP connection timeout: {self.dst_ip}:{self.dst_port}")
        return False
    
    def send(self, data: bytes) -> int:
        """Send data over established connection"""
        with self.lock:
            if self.state != TCPState.ESTABLISHED:
                raise Exception(f"Cannot send: connection not established (state={self.state})")
            
            # Segment data based on MSS
            bytes_sent = 0
            offset = 0
            
            while offset < len(data):
                chunk_size = min(self.mss, len(data) - offset)
                chunk = data[offset:offset + chunk_size]
                
                from tcp_packet import build_data_packet
                data_packet = build_data_packet(
                    self.src_ip, self.dst_ip,
                    self.src_port, self.dst_port,
                    self.seq_num, self.ack_num,
                    chunk
                )
                
                self._send_packet(data_packet)
                
                # Add to retransmit queue
                self.unacked_packets[self.seq_num] = (data_packet, time.time(), 0)
                
                self.seq_num += len(chunk)
                bytes_sent += len(chunk)
                offset += chunk_size
            
            return bytes_sent
    
    def receive(self, max_bytes: int = 65536) -> bytes:
        """Receive data from connection"""
        with self.lock:
            if not self.recv_buffer:
                return b''
            
            data = b''.join(self.recv_buffer)
            self.recv_buffer.clear()
            
            return data[:max_bytes]
    
    def close(self):
        """Close connection (active close)"""
        with self.lock:
            if self.state == TCPState.ESTABLISHED:
                # Send FIN
                from tcp_packet import build_fin_packet
                fin_packet = build_fin_packet(
                    self.src_ip, self.dst_ip,
                    self.src_port, self.dst_port,
                    self.seq_num, self.ack_num
                )
                
                self._send_packet(fin_packet)
                self.state = TCPState.FIN_WAIT_1
                self.seq_num += 1
            
            elif self.state == TCPState.CLOSE_WAIT:
                # Send FIN (passive close)
                from tcp_packet import build_fin_packet
                fin_packet = build_fin_packet(
                    self.src_ip, self.dst_ip,
                    self.src_port, self.dst_port,
                    self.seq_num, self.ack_num
                )
                
                self._send_packet(fin_packet)
                self.state = TCPState.LAST_ACK
                self.seq_num += 1
    
    def handle_packet(self, packet_data: Dict):
        """Handle incoming TCP packet (state machine)"""
        with self.lock:
            self.last_activity = time.time()
            self.packets_received += 1
            
            # Update RTT if this is an ACK
            if packet_data['has_ack'] and packet_data['ack_num'] in self.unacked_packets:
                sent_time = self.unacked_packets[packet_data['ack_num']][1]
                rtt = time.time() - sent_time
                self._update_rto(rtt)
            
            # State machine
            if self.state == TCPState.SYN_SENT:
                self._handle_syn_sent(packet_data)
            elif self.state == TCPState.ESTABLISHED:
                self._handle_established(packet_data)
            elif self.state == TCPState.FIN_WAIT_1:
                self._handle_fin_wait_1(packet_data)
            elif self.state == TCPState.FIN_WAIT_2:
                self._handle_fin_wait_2(packet_data)
            elif self.state == TCPState.CLOSE_WAIT:
                self._handle_close_wait(packet_data)
            elif self.state == TCPState.LAST_ACK:
                self._handle_last_ack(packet_data)
    
    def _handle_syn_sent(self, packet_data: Dict):
        """Handle packet in SYN_SENT state"""
        if packet_data['has_syn'] and packet_data['has_ack']:
            # Received SYN-ACK
            self.ack_num = packet_data['seq_num'] + 1
            
            # Remove SYN from retransmit queue
            if self.initial_seq in self.unacked_packets:
                del self.unacked_packets[self.initial_seq]
            
            # Send ACK
            from tcp_packet import build_ack_packet
            ack_packet = build_ack_packet(
                self.src_ip, self.dst_ip,
                self.src_port, self.dst_port,
                self.seq_num, self.ack_num
            )
            
            self._send_packet(ack_packet)
            self.state = TCPState.ESTABLISHED
            
            if self.on_established:
                self.on_established(self)
    
    def _handle_established(self, packet_data: Dict):
        """Handle packet in ESTABLISHED state"""
        # Handle ACK
        if packet_data['has_ack']:
            ack_num = packet_data['ack_num']
            # Remove ACKed packets from retransmit queue
            to_remove = [seq for seq in self.unacked_packets if seq < ack_num]
            for seq in to_remove:
                del self.unacked_packets[seq]
        
        # Handle data
        if packet_data['data']:
            expected_seq = self.ack_num
            received_seq = packet_data['seq_num']
            
            if received_seq == expected_seq:
                # In-order data
                self.recv_buffer.append(packet_data['data'])
                self.ack_num += len(packet_data['data'])
                self.bytes_received += len(packet_data['data'])
                
                # Send ACK
                from tcp_packet import build_ack_packet
                ack_packet = build_ack_packet(
                    self.src_ip, self.dst_ip,
                    self.src_port, self.dst_port,
                    self.seq_num, self.ack_num
                )
                self._send_packet(ack_packet)
                
                if self.on_data:
                    self.on_data(self, packet_data['data'])
            else:
                # Out-of-order data (store for later)
                self.out_of_order[received_seq] = packet_data['data']
        
        # Handle FIN
        if packet_data['has_fin']:
            self.ack_num = packet_data['seq_num'] + 1
            
            # Send ACK
            from tcp_packet import build_ack_packet
            ack_packet = build_ack_packet(
                self.src_ip, self.dst_ip,
                self.src_port, self.dst_port,
                self.seq_num, self.ack_num
            )
            self._send_packet(ack_packet)
            
            self.state = TCPState.CLOSE_WAIT
    
    def _handle_fin_wait_1(self, packet_data: Dict):
        """Handle packet in FIN_WAIT_1 state"""
        if packet_data['has_ack']:
            self.state = TCPState.FIN_WAIT_2
        
        if packet_data['has_fin']:
            self.ack_num = packet_data['seq_num'] + 1
            
            from tcp_packet import build_ack_packet
            ack_packet = build_ack_packet(
                self.src_ip, self.dst_ip,
                self.src_port, self.dst_port,
                self.seq_num, self.ack_num
            )
            self._send_packet(ack_packet)
            
            self.state = TCPState.TIME_WAIT
            self.time_wait_start = time.time()
    
    def _handle_fin_wait_2(self, packet_data: Dict):
        """Handle packet in FIN_WAIT_2 state"""
        if packet_data['has_fin']:
            self.ack_num = packet_data['seq_num'] + 1
            
            from tcp_packet import build_ack_packet
            ack_packet = build_ack_packet(
                self.src_ip, self.dst_ip,
                self.src_port, self.dst_port,
                self.seq_num, self.ack_num
            )
            self._send_packet(ack_packet)
            
            self.state = TCPState.TIME_WAIT
            self.time_wait_start = time.time()
    
    def _handle_close_wait(self, packet_data: Dict):
        """Handle packet in CLOSE_WAIT state"""
        pass  # Waiting for application to close
    
    def _handle_last_ack(self, packet_data: Dict):
        """Handle packet in LAST_ACK state"""
        if packet_data['has_ack']:
            self.state = TCPState.CLOSED
            if self.on_closed:
                self.on_closed(self)
    
    def _send_packet(self, packet: bytes):
        """Send packet via callback"""
        self.send_callback(packet, self.interface_name)
        self.packets_sent += 1
        self.bytes_sent += len(packet)
    
    def _update_rto(self, rtt: float):
        """Update RTO using Jacobson/Karels algorithm"""
        if self.srtt is None:
            self.srtt = rtt
            self.rttvar = rtt / 2
        else:
            alpha = 0.125
            beta = 0.25
            self.rttvar = (1 - beta) * self.rttvar + beta * abs(self.srtt - rtt)
            self.srtt = (1 - alpha) * self.srtt + alpha * rtt
        
        self.rto = self.srtt + 4 * self.rttvar
        self.rto = max(1.0, min(60.0, self.rto))  # Clamp between 1-60 seconds
    
    def check_retransmit(self):
        """Check and perform retransmissions"""
        with self.lock:
            now = time.time()
            for seq_num, (packet, sent_time, retries) in list(self.unacked_packets.items()):
                if now - sent_time > self.rto:
                    if retries < 5:
                        # Retransmit
                        self._send_packet(packet)
                        self.unacked_packets[seq_num] = (packet, now, retries + 1)
                        self.retransmits += 1
                        self.rto *= 2  # Exponential backoff
                    else:
                        # Give up
                        logger.error(f"TCP retransmit failed after 5 attempts: {self.dst_ip}:{self.dst_port}")
                        self.state = TCPState.CLOSED
                        del self.unacked_packets[seq_num]
    
    def is_time_wait_expired(self) -> bool:
        """Check if TIME_WAIT period expired (2*MSL = 120 seconds)"""
        if self.state == TCPState.TIME_WAIT and self.time_wait_start:
            return time.time() - self.time_wait_start > 120
        return False
    
    def get_stats(self) -> Dict:
        """Get connection statistics"""
        return {
            'state': self.state.value,
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'packets_sent': self.packets_sent,
            'packets_received': self.packets_received,
            'retransmits': self.retransmits,
            'rto': self.rto,
            'srtt': self.srtt,
            'unacked_packets': len(self.unacked_packets)
        }

class TCPConnectionManager:
    """Manages multiple TCP connections"""
    
    def __init__(self, send_callback: Callable):
        self.connections: Dict[tuple, TCPConnection] = {}
        self.send_callback = send_callback
        self.lock = threading.Lock()
        
        # Start retransmission thread
        self.running = True
        self.retransmit_thread = threading.Thread(target=self._retransmit_worker, daemon=True)
        self.retransmit_thread.start()
    
    def create_connection(self, src_ip: str, src_port: int, dst_ip: str, dst_port: int,
                         interface_name: str) -> TCPConnection:
        """Create new TCP connection"""
        key = (src_ip, src_port, dst_ip, dst_port)
        
        with self.lock:
            if key in self.connections:
                raise Exception(f"Connection already exists: {key}")
            
            conn = TCPConnection(src_ip, src_port, dst_ip, dst_port, 
                               self.send_callback, interface_name)
            self.connections[key] = conn
            
            return conn
    
    def handle_packet(self, packet_data: Dict):
        """Route incoming packet to appropriate connection"""
        key = (packet_data['dst_ip'], packet_data['dst_port'],
               packet_data['src_ip'], packet_data['src_port'])
        
        with self.lock:
            if key in self.connections:
                self.connections[key].handle_packet(packet_data)
    
    def close_connection(self, src_ip: str, src_port: int, dst_ip: str, dst_port: int):
        """Close and remove connection"""
        key = (src_ip, src_port, dst_ip, dst_port)
        
        with self.lock:
            if key in self.connections:
                conn = self.connections[key]
                conn.close()
                # Don't remove yet - wait for TIME_WAIT
    
    def _retransmit_worker(self):
        """Background thread for retransmissions"""
        while self.running:
            with self.lock:
                # Check retransmissions
                for conn in list(self.connections.values()):
                    conn.check_retransmit()
                
                # Clean up TIME_WAIT connections
                to_remove = []
                for key, conn in self.connections.items():
                    if conn.state == TCPState.CLOSED or conn.is_time_wait_expired():
                        to_remove.append(key)
                
                for key in to_remove:
                    del self.connections[key]
            
            time.sleep(0.1)
    
    def get_all_stats(self) -> Dict:
        """Get statistics for all connections"""
        with self.lock:
            return {
                str(key): conn.get_stats()
                for key, conn in self.connections.items()
            }
    
    def shutdown(self):
        """Shutdown manager"""
        self.running = False
        self.retransmit_thread.join()
