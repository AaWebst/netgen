/**
 * VEP1445 Neighbor Discovery Module
 * Adds ARP/LLDP neighbor detection to port status display
 */

class NeighborDiscovery {
    constructor() {
        this.updateInterval = null;
        this.scanInterval = 10000; // 10 seconds
        this.lastScan = {};
    }

    /**
     * Initialize neighbor discovery
     */
    init() {
        console.log('🔍 Initializing neighbor discovery...');
        this.startAutoUpdate();
        this.discoverAll(); // Initial scan
    }

    /**
     * Start automatic updates
     */
    startAutoUpdate() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }

        this.updateInterval = setInterval(() => {
            this.discoverAll();
        }, this.scanInterval);
    }

    /**
     * Stop automatic updates
     */
    stopAutoUpdate() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    /**
     * Discover neighbors on all interfaces
     */
    async discoverAll() {
        try {
            const response = await fetch('/api/neighbors/discover', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    interfaces: ['eno2', 'eno3', 'eno4', 'eno5', 'eno6']
                })
            });

            if (!response.ok) {
                console.warn('Neighbor discovery failed:', response.status);
                return;
            }

            const data = await response.json();
            
            if (data.success) {
                this.lastScan = data.neighbors;
                this.updatePortDisplay(data.neighbors);
            }
        } catch (error) {
            console.error('Neighbor discovery error:', error);
        }
    }

    /**
     * Get neighbor info for a specific interface
     */
    async getNeighbor(interfaceName) {
        try {
            const response = await fetch(`/api/neighbors/${interfaceName}`);
            
            if (!response.ok) {
                return null;
            }

            const data = await response.json();
            return data.success ? data : null;
        } catch (error) {
            console.error(`Error getting neighbor for ${interfaceName}:`, error);
            return null;
        }
    }

    /**
     * Update port display with neighbor information
     */
    updatePortDisplay(neighbors) {
        Object.entries(neighbors).forEach(([iface, info]) => {
            const portCard = document.querySelector(`[data-port="${iface}"]`);
            if (!portCard) return;

            // Update link status
            const linkStatus = portCard.querySelector('.port-link-status');
            if (linkStatus && info.link_status) {
                if (info.link_status.up) {
                    linkStatus.textContent = `⬆ ${info.link_status.speed || 'UP'}`;
                    linkStatus.style.color = 'var(--accent-primary)';
                } else {
                    linkStatus.textContent = '⬇ DOWN';
                    linkStatus.style.color = 'var(--accent-danger)';
                }
            }

            // Update neighbor info
            const neighborDiv = portCard.querySelector('.port-neighbor');
            const statusNote = portCard.querySelector('.port-status-note');

            if (neighborDiv) {
                // Prefer LLDP info
                if (info.lldp_neighbors && info.lldp_neighbors.length > 0) {
                    const lldp = info.lldp_neighbors[0];
                    const systemName = lldp.system_name || 'Switch';
                    const portId = lldp.port_id || '';
                    const chassisId = lldp.chassis_id ? ` (${lldp.chassis_id.substring(0, 8)}...)` : '';
                    
                    neighborDiv.textContent = `→ ${systemName}${portId ? ':' + portId : ''}`;
                    neighborDiv.style.display = 'block';

                    if (statusNote && lldp.system_desc) {
                        statusNote.textContent = lldp.system_desc.substring(0, 30);
                        statusNote.style.display = 'block';
                    }
                }
                // Fall back to ARP
                else if (info.arp_neighbors && info.arp_neighbors.length > 0) {
                    const arp = info.arp_neighbors[0];
                    neighborDiv.textContent = `→ ${arp.ip} (${arp.mac.substring(0, 8)}...)`;
                    neighborDiv.style.display = 'block';

                    if (statusNote) {
                        statusNote.textContent = `State: ${arp.state}`;
                        statusNote.style.display = 'block';
                    }
                }
                // No neighbors
                else if (info.link_status && info.link_status.up) {
                    neighborDiv.textContent = '';
                    neighborDiv.style.display = 'none';
                    
                    if (statusNote) {
                        statusNote.textContent = 'No neighbors detected';
                        statusNote.style.display = 'block';
                    }
                } else {
                    neighborDiv.style.display = 'none';
                    if (statusNote) statusNote.style.display = 'none';
                }
            }

            // Add visual indicator for detected neighbors
            if (info.lldp_neighbors && info.lldp_neighbors.length > 0) {
                portCard.classList.add('has-lldp');
                portCard.style.borderLeft = '3px solid var(--accent-green)';
            } else if (info.arp_neighbors && info.arp_neighbors.length > 0) {
                portCard.classList.add('has-arp');
                portCard.style.borderLeft = '3px solid var(--accent-secondary)';
            } else {
                portCard.classList.remove('has-lldp', 'has-arp');
                portCard.style.borderLeft = '';
            }
        });

        // Update last scan timestamp
        const timestampEl = document.getElementById('last-update-time');
        if (timestampEl) {
            const now = new Date();
            timestampEl.textContent = now.toLocaleTimeString();
        }
    }

    /**
     * Get formatted neighbor summary
     */
    getNeighborSummary(interfaceName) {
        if (!this.lastScan[interfaceName]) {
            return 'No data';
        }

        const info = this.lastScan[interfaceName];

        if (info.lldp_neighbors && info.lldp_neighbors.length > 0) {
            const lldp = info.lldp_neighbors[0];
            return `${lldp.system_name || 'Switch'}:${lldp.port_id || '?'}`;
        }

        if (info.arp_neighbors && info.arp_neighbors.length > 0) {
            const arp = info.arp_neighbors[0];
            return `${arp.ip}`;
        }

        if (info.link_status && info.link_status.up) {
            return 'Link UP (no neighbors)';
        }

        return 'Link DOWN';
    }

    /**
     * Force immediate scan
     */
    forceScan() {
        console.log('🔍 Force scanning neighbors...');
        this.discoverAll();
    }

    /**
     * Set scan interval
     */
    setScanInterval(seconds) {
        this.scanInterval = seconds * 1000;
        if (this.updateInterval) {
            this.stopAutoUpdate();
            this.startAutoUpdate();
        }
    }
}

// Create global instance
const neighborDiscovery = new NeighborDiscovery();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        neighborDiscovery.init();
    });
} else {
    neighborDiscovery.init();
}

// Connect buttons if they exist
document.addEventListener('DOMContentLoaded', () => {
    const refreshBtn = document.getElementById('refresh-ports-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            neighborDiscovery.forceScan();
        });
    }

    const forceScanBtn = document.getElementById('force-scan-btn');
    if (forceScanBtn) {
        forceScanBtn.addEventListener('click', () => {
            neighborDiscovery.forceScan();
        });
    }

    // Update scan interval selector if it exists
    const scanIntervalSelect = document.getElementById('scan-interval-select');
    if (scanIntervalSelect) {
        scanIntervalSelect.addEventListener('change', (e) => {
            neighborDiscovery.setScanInterval(parseInt(e.target.value));
        });
    }
});

console.log('✅ Neighbor Discovery module loaded');
