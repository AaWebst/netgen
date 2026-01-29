#!/usr/bin/env python3
"""
HTTP/1.1 Client - Built on TCP Connection Manager
Supports GET, POST, PUT, DELETE with headers and keep-alive
"""

import time
from typing import Dict, Optional, List
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

class HTTPResponse:
    """HTTP Response Parser"""
    
    def __init__(self, raw_data: bytes):
        self.raw = raw_data
        self.status_code = 0
        self.status_text = ""
        self.headers = {}
        self.body = b''
        
        self._parse()
    
    def _parse(self):
        """Parse HTTP response"""
        try:
            # Split headers and body
            header_end = self.raw.find(b'\r\n\r\n')
            if header_end == -1:
                return
            
            header_data = self.raw[:header_end].decode('utf-8', errors='ignore')
            self.body = self.raw[header_end + 4:]
            
            # Parse status line
            lines = header_data.split('\r\n')
            if lines:
                status_line = lines[0]
                parts = status_line.split(' ', 2)
                if len(parts) >= 3:
                    self.status_code = int(parts[1])
                    self.status_text = parts[2]
            
            # Parse headers
            for line in lines[1:]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    self.headers[key.strip().lower()] = value.strip()
            
            # Handle chunked encoding
            if self.headers.get('transfer-encoding') == 'chunked':
                self.body = self._decode_chunked(self.body)
        
        except Exception as e:
            logger.error(f"HTTP response parse error: {e}")
    
    def _decode_chunked(self, data: bytes) -> bytes:
        """Decode chunked transfer encoding"""
        result = b''
        offset = 0
        
        while offset < len(data):
            # Find chunk size line
            line_end = data.find(b'\r\n', offset)
            if line_end == -1:
                break
            
            try:
                chunk_size = int(data[offset:line_end], 16)
            except:
                break
            
            if chunk_size == 0:
                break
            
            # Extract chunk data
            chunk_start = line_end + 2
            chunk_end = chunk_start + chunk_size
            result += data[chunk_start:chunk_end]
            
            # Move to next chunk
            offset = chunk_end + 2  # Skip trailing \r\n
        
        return result
    
    def __repr__(self):
        return f"<HTTPResponse {self.status_code} {self.status_text}>"

class HTTPClient:
    """HTTP/1.1 Client"""
    
    def __init__(self, tcp_manager):
        self.tcp_manager = tcp_manager
        self.default_headers = {
            'User-Agent': 'VEP1445-Traffic-Generator/1.0',
            'Accept': '*/*',
            'Connection': 'keep-alive'
        }
    
    def request(self, method: str, url: str, 
                headers: Optional[Dict[str, str]] = None,
                body: Optional[bytes] = None,
                src_ip: str = None, src_port: int = None,
                interface: str = None,
                timeout: float = 10.0) -> Optional[HTTPResponse]:
        """Make HTTP request"""
        
        # Parse URL
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or 80
        path = parsed.path or '/'
        if parsed.query:
            path += '?' + parsed.query
        
        # Resolve host to IP (simplified - use DNS in production)
        import socket
        try:
            dst_ip = socket.gethostbyname(host)
        except:
            logger.error(f"Failed to resolve {host}")
            return None
        
        # Create TCP connection
        if not src_port:
            src_port = 10000 + (int(time.time() * 1000) % 50000)
        
        try:
            conn = self.tcp_manager.create_connection(
                src_ip, src_port, dst_ip, port, interface
            )
            
            # Connect
            if not conn.connect(timeout=5.0):
                logger.error(f"HTTP: Failed to connect to {host}:{port}")
                return None
            
            # Build request
            request_data = self._build_request(method, path, host, headers, body)
            
            # Send request
            conn.send(request_data.encode('utf-8'))
            
            # Receive response
            response_data = b''
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                data = conn.receive(65536)
                if data:
                    response_data += data
                    
                    # Check if we have complete response
                    if b'\r\n\r\n' in response_data:
                        # Parse headers to check Content-Length
                        header_end = response_data.find(b'\r\n\r\n')
                        headers_text = response_data[:header_end].decode('utf-8', errors='ignore')
                        
                        content_length = None
                        for line in headers_text.split('\r\n'):
                            if line.lower().startswith('content-length:'):
                                content_length = int(line.split(':', 1)[1].strip())
                                break
                        
                        if content_length is not None:
                            body_start = header_end + 4
                            if len(response_data) >= body_start + content_length:
                                break
                        else:
                            # No content-length, check for chunked or connection close
                            if b'transfer-encoding: chunked' in response_data.lower():
                                if b'0\r\n\r\n' in response_data:
                                    break
                            elif b'connection: close' in response_data.lower():
                                time.sleep(0.1)  # Wait a bit more
                                break
                
                time.sleep(0.01)
            
            # Close connection
            conn.close()
            
            # Parse response
            if response_data:
                return HTTPResponse(response_data)
            else:
                logger.error("HTTP: No response received")
                return None
        
        except Exception as e:
            logger.error(f"HTTP request error: {e}")
            return None
    
    def get(self, url: str, **kwargs) -> Optional[HTTPResponse]:
        """HTTP GET request"""
        return self.request('GET', url, **kwargs)
    
    def post(self, url: str, data: bytes = None, **kwargs) -> Optional[HTTPResponse]:
        """HTTP POST request"""
        return self.request('POST', url, body=data, **kwargs)
    
    def put(self, url: str, data: bytes = None, **kwargs) -> Optional[HTTPResponse]:
        """HTTP PUT request"""
        return self.request('PUT', url, body=data, **kwargs)
    
    def delete(self, url: str, **kwargs) -> Optional[HTTPResponse]:
        """HTTP DELETE request"""
        return self.request('DELETE', url, **kwargs)
    
    def _build_request(self, method: str, path: str, host: str,
                      headers: Optional[Dict[str, str]], body: Optional[bytes]) -> str:
        """Build HTTP request string"""
        
        # Request line
        request = f"{method} {path} HTTP/1.1\r\n"
        
        # Merge headers
        all_headers = self.default_headers.copy()
        if headers:
            all_headers.update(headers)
        
        # Required headers
        all_headers['Host'] = host
        
        # Content-Length for body
        if body:
            all_headers['Content-Length'] = str(len(body))
        
        # Add headers
        for key, value in all_headers.items():
            request += f"{key}: {value}\r\n"
        
        # End headers
        request += "\r\n"
        
        # Add body (as string for now, will encode to bytes)
        if body:
            request = request.encode('utf-8') + body
            return request.decode('utf-8', errors='ignore')
        
        return request

# Test usage
if __name__ == '__main__':
    # Example usage (requires TCP manager)
    logging.basicConfig(level=logging.INFO)
    
    print("HTTP Client module loaded")
    print("Usage:")
    print("  client = HTTPClient(tcp_manager)")
    print("  response = client.get('http://example.com/', src_ip='192.168.1.1', interface='eth0')")
    print("  print(response.status_code, response.body)")
