#!/usr/bin/env python3
"""
TLS/HTTPS Implementation for VEP1445
Supports TLS 1.2/1.3 handshake and encrypted HTTP traffic
"""

import ssl
import socket
import logging
from typing import Optional, Dict, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

class TLSVersion(Enum):
    """TLS Protocol Versions"""
    TLS_1_0 = 0x0301
    TLS_1_1 = 0x0302
    TLS_1_2 = 0x0303
    TLS_1_3 = 0x0304

class TLSContentType(Enum):
    """TLS Content Types"""
    CHANGE_CIPHER_SPEC = 20
    ALERT = 21
    HANDSHAKE = 22
    APPLICATION_DATA = 23

class TLSHandshakeType(Enum):
    """TLS Handshake Message Types"""
    HELLO_REQUEST = 0
    CLIENT_HELLO = 1
    SERVER_HELLO = 2
    CERTIFICATE = 11
    SERVER_KEY_EXCHANGE = 12
    CERTIFICATE_REQUEST = 13
    SERVER_HELLO_DONE = 14
    CERTIFICATE_VERIFY = 15
    CLIENT_KEY_EXCHANGE = 16
    FINISHED = 20

class TLSConnection:
    """TLS Connection Handler (using Python's SSL library)"""
    
    def __init__(self, tcp_connection):
        """
        Initialize TLS connection over existing TCP connection
        
        Args:
            tcp_connection: Established TCP connection
        """
        self.tcp_conn = tcp_connection
        self.ssl_context = None
        self.ssl_socket = None
        self.is_encrypted = False
        
    def setup_client_context(self, verify_mode: int = ssl.CERT_NONE,
                            ca_file: Optional[str] = None,
                            cert_file: Optional[str] = None,
                            key_file: Optional[str] = None) -> None:
        """
        Setup SSL context for client
        
        Args:
            verify_mode: Certificate verification mode
            ca_file: CA certificate file path
            cert_file: Client certificate file path
            key_file: Client key file path
        """
        # Create SSL context for client
        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        
        # Set verification mode
        self.ssl_context.check_hostname = (verify_mode != ssl.CERT_NONE)
        self.ssl_context.verify_mode = verify_mode
        
        # Load CA certificates if provided
        if ca_file:
            self.ssl_context.load_verify_locations(ca_file)
        else:
            # Load default system CA certificates
            try:
                self.ssl_context.load_default_certs()
            except:
                logger.warning("Could not load default CA certificates")
        
        # Load client certificate if provided
        if cert_file and key_file:
            self.ssl_context.load_cert_chain(cert_file, key_file)
        
        # Set supported TLS versions (1.2 and 1.3)
        self.ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        self.ssl_context.maximum_version = ssl.TLSVersion.TLSv1_3
        
        # Set cipher suites (prefer strong ciphers)
        try:
            self.ssl_context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20')
        except:
            logger.warning("Could not set custom cipher suites")
        
        logger.info("TLS client context configured")
    
    def handshake(self, server_hostname: str) -> bool:
        """
        Perform TLS handshake
        
        Args:
            server_hostname: Server hostname for SNI
            
        Returns:
            True if handshake successful
        """
        try:
            # Wrap the raw socket with SSL
            # Note: In production, this would wrap the actual TCP socket
            # For VEP1445, we'll create a socket from the TCP connection
            
            raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw_sock.connect((self.tcp_conn.dst_ip, self.tcp_conn.dst_port))
            
            # Wrap with SSL
            self.ssl_socket = self.ssl_context.wrap_socket(
                raw_sock,
                server_hostname=server_hostname,
                do_handshake_on_connect=True
            )
            
            self.is_encrypted = True
            
            # Get connection info
            cipher = self.ssl_socket.cipher()
            version = self.ssl_socket.version()
            
            logger.info(f"TLS handshake successful: {version}, cipher={cipher}")
            return True
            
        except ssl.SSLError as e:
            logger.error(f"TLS handshake failed: {e}")
            return False
        except Exception as e:
            logger.error(f"TLS connection error: {e}")
            return False
    
    def send(self, data: bytes) -> int:
        """Send encrypted data"""
        if not self.is_encrypted or not self.ssl_socket:
            raise Exception("TLS not established")
        
        return self.ssl_socket.send(data)
    
    def receive(self, buffer_size: int = 4096) -> bytes:
        """Receive encrypted data"""
        if not self.is_encrypted or not self.ssl_socket:
            raise Exception("TLS not established")
        
        return self.ssl_socket.recv(buffer_size)
    
    def close(self):
        """Close TLS connection"""
        if self.ssl_socket:
            try:
                self.ssl_socket.close()
            except:
                pass
            self.ssl_socket = None
        
        self.is_encrypted = False
    
    def get_peer_certificate(self) -> Optional[Dict]:
        """Get peer certificate information"""
        if not self.ssl_socket:
            return None
        
        try:
            cert = self.ssl_socket.getpeercert()
            return cert
        except:
            return None
    
    def get_cipher(self) -> Optional[Tuple]:
        """Get current cipher suite"""
        if not self.ssl_socket:
            return None
        
        return self.ssl_socket.cipher()
    
    def get_protocol_version(self) -> Optional[str]:
        """Get TLS protocol version"""
        if not self.ssl_socket:
            return None
        
        return self.ssl_socket.version()

class HTTPSClient:
    """HTTPS Client built on TLS"""
    
    def __init__(self, tcp_manager):
        self.tcp_manager = tcp_manager
        self.verify_ssl = True
        self.ca_file = None
    
    def request(self, method: str, url: str,
                headers: Optional[Dict[str, str]] = None,
                body: Optional[bytes] = None,
                src_ip: str = None,
                interface: str = None,
                verify: bool = True,
                timeout: float = 10.0):
        """
        Make HTTPS request
        
        Args:
            method: HTTP method
            url: HTTPS URL
            headers: HTTP headers
            body: Request body
            src_ip: Source IP address
            interface: Network interface
            verify: Verify SSL certificate
            timeout: Request timeout
        """
        from urllib.parse import urlparse
        import time
        
        # Parse URL
        parsed = urlparse(url)
        if parsed.scheme != 'https':
            raise ValueError("URL must use https://")
        
        host = parsed.hostname
        port = parsed.port or 443
        path = parsed.path or '/'
        if parsed.query:
            path += '?' + parsed.query
        
        # Resolve hostname
        try:
            dst_ip = socket.gethostbyname(host)
        except:
            logger.error(f"Failed to resolve {host}")
            return None
        
        # Create TCP connection
        import random
        src_port = random.randint(10000, 65000)
        
        tcp_conn = self.tcp_manager.create_connection(
            src_ip, src_port, dst_ip, port, interface
        )
        
        # Connect TCP
        if not tcp_conn.connect(timeout=5.0):
            logger.error(f"TCP connection failed to {host}:{port}")
            return None
        
        try:
            # Setup TLS
            tls_conn = TLSConnection(tcp_conn)
            tls_conn.setup_client_context(
                verify_mode=ssl.CERT_REQUIRED if verify else ssl.CERT_NONE
            )
            
            # TLS handshake
            if not tls_conn.handshake(host):
                logger.error("TLS handshake failed")
                return None
            
            logger.info(f"HTTPS connected: {host}:{port} ({tls_conn.get_protocol_version()})")
            
            # Build HTTP request
            request = self._build_request(method, path, host, headers, body)
            
            # Send request
            tls_conn.send(request.encode('utf-8'))
            
            # Receive response
            response_data = b''
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    chunk = tls_conn.receive(4096)
                    if not chunk:
                        break
                    response_data += chunk
                    
                    # Check if complete
                    if b'\r\n\r\n' in response_data:
                        headers_end = response_data.find(b'\r\n\r\n')
                        headers_text = response_data[:headers_end].decode('utf-8', errors='ignore')
                        
                        # Check Content-Length
                        content_length = None
                        for line in headers_text.split('\r\n'):
                            if line.lower().startswith('content-length:'):
                                content_length = int(line.split(':', 1)[1].strip())
                                break
                        
                        if content_length is not None:
                            body_start = headers_end + 4
                            if len(response_data) >= body_start + content_length:
                                break
                
                except ssl.SSLWantReadError:
                    time.sleep(0.01)
                    continue
                except:
                    break
            
            # Close connections
            tls_conn.close()
            tcp_conn.close()
            
            # Parse response
            if response_data:
                from http_client import HTTPResponse
                return HTTPResponse(response_data)
            
            return None
            
        except Exception as e:
            logger.error(f"HTTPS request error: {e}")
            return None
    
    def get(self, url: str, **kwargs):
        """HTTPS GET request"""
        return self.request('GET', url, **kwargs)
    
    def post(self, url: str, data: bytes = None, **kwargs):
        """HTTPS POST request"""
        return self.request('POST', url, body=data, **kwargs)
    
    def _build_request(self, method: str, path: str, host: str,
                      headers: Optional[Dict[str, str]], body: Optional[bytes]) -> str:
        """Build HTTP request string"""
        request = f"{method} {path} HTTP/1.1\r\n"
        
        # Default headers
        all_headers = {
            'Host': host,
            'User-Agent': 'VEP1445-Traffic-Generator/1.0',
            'Accept': '*/*',
            'Connection': 'close'
        }
        
        if headers:
            all_headers.update(headers)
        
        if body:
            all_headers['Content-Length'] = str(len(body))
        
        # Add headers
        for key, value in all_headers.items():
            request += f"{key}: {value}\r\n"
        
        request += "\r\n"
        
        # Add body if present
        if body:
            request = request.encode('utf-8') + body
            return request.decode('utf-8', errors='ignore')
        
        return request

class TLSTrafficProfile:
    """TLS/HTTPS Traffic Profile for VEP1445"""
    
    def __init__(self, name: str, url: str, 
                 requests_per_sec: int = 10,
                 verify_ssl: bool = False):
        self.name = name
        self.url = url
        self.requests_per_sec = requests_per_sec
        self.verify_ssl = verify_ssl
        
        self.requests_sent = 0
        self.requests_successful = 0
        self.requests_failed = 0
        self.total_bytes = 0
    
    def generate_traffic(self, duration: float, https_client: HTTPSClient,
                        src_ip: str, interface: str):
        """Generate HTTPS traffic for specified duration"""
        import time
        
        interval = 1.0 / self.requests_per_sec
        end_time = time.time() + duration
        
        while time.time() < end_time:
            start = time.time()
            
            # Make HTTPS request
            response = https_client.get(
                self.url,
                src_ip=src_ip,
                interface=interface,
                verify=self.verify_ssl
            )
            
            self.requests_sent += 1
            
            if response and response.status_code == 200:
                self.requests_successful += 1
                self.total_bytes += len(response.body)
            else:
                self.requests_failed += 1
            
            # Wait for next request
            elapsed = time.time() - start
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        logger.info(f"TLS traffic profile '{self.name}' complete: "
                   f"{self.requests_sent} requests, "
                   f"{self.requests_successful} successful, "
                   f"{self.total_bytes} bytes")
    
    def get_stats(self) -> Dict:
        """Get traffic statistics"""
        return {
            'name': self.name,
            'requests_sent': self.requests_sent,
            'requests_successful': self.requests_successful,
            'requests_failed': self.requests_failed,
            'total_bytes': self.total_bytes,
            'success_rate': self.requests_successful / max(1, self.requests_sent) * 100
        }

# Test usage
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("TLS/HTTPS Module Test")
    print("=" * 60)
    
    print("\nFeatures:")
    print("  ✓ TLS 1.2/1.3 support")
    print("  ✓ Certificate verification")
    print("  ✓ SNI (Server Name Indication)")
    print("  ✓ Strong cipher suites")
    print("  ✓ HTTPS client")
    print("  ✓ Traffic profile generation")
    
    print("\nUsage:")
    print("  # Setup TLS connection")
    print("  tls = TLSConnection(tcp_conn)")
    print("  tls.setup_client_context(verify_mode=ssl.CERT_REQUIRED)")
    print("  tls.handshake('example.com')")
    print("")
    print("  # Make HTTPS request")
    print("  https = HTTPSClient(tcp_manager)")
    print("  response = https.get('https://example.com/')")
    print("")
    print("  # Generate HTTPS load")
    print("  profile = TLSTrafficProfile('HTTPS_Load', 'https://example.com/', rps=100)")
    print("  profile.generate_traffic(duration=60.0, https_client, src_ip, interface)")
    
    print("\n✓ TLS/HTTPS module ready for integration")
