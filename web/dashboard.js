// VEP1445 Dashboard - Complete JavaScript with all features
const API_BASE = window.location.origin + '/api';
let updateInterval;
let impairmentStatus = false;

// ============================================================================
// Utility Functions
// ============================================================================

function formatNumber(num) {
    if (num >= 1e9) return (num / 1e9).toFixed(2) + 'G';
    if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M';
    if (num >= 1e3) return (num / 1e3).toFixed(2) + 'K';
    return num.toString();
}

function showAlert(message, type = 'success') {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    document.querySelector('.container').insertBefore(alert, document.querySelector('.tabs'));
    setTimeout(() => alert.remove(), 4000);
}

function showTab(tabName) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    
    event.target.classList.add('active');
    document.getElementById(tabName).classList.add('active');
}

// ============================================================================
// Dashboard Updates
// ============================================================================

async function updateDashboard() {
    try {
        // Get system stats
        const statsResp = await fetch(`${API_BASE}/stats`);
        const statsData = await statsResp.json();
        
        if (statsData.success) {
            const stats = statsData.stats;
            
            // Update status badge
            const badge = document.getElementById('status-badge');
            if (statsData.running) {
                badge.textContent = 'RUNNING';
                badge.className = 'status-badge status-running';
            } else {
                badge.textContent = 'STOPPED';
                badge.className = 'status-badge status-stopped';
            }
            
            // Update traffic stats
            document.getElementById('stat-packets').textContent = formatNumber(stats.packets_sent || 0);
            document.getElementById('stat-bytes').textContent = formatNumber(stats.bytes_sent || 0);
            document.getElementById('stat-connections').textContent = formatNumber(stats.connections_created || 0);
            
            // Update TCP stats
            if (stats.tcp_pool_utilization !== undefined) {
                document.getElementById('stat-pool').textContent = stats.tcp_pool_utilization.toFixed(1) + '%';
            }
            if (stats.tcp_active !== undefined) {
                document.getElementById('stat-tcp-active').textContent = formatNumber(stats.tcp_active);
            }
            
            // Update monitoring stats
            document.getElementById('stat-snmp').textContent = stats.snmp_requests || 0;
            document.getElementById('stat-netflow').textContent = stats.flows_sent || 0;
            document.getElementById('stat-bgp').textContent = stats.bgp_routes || 0;
        }

        // Get interfaces
        const ifacesResp = await fetch(`${API_BASE}/interfaces`);
        const ifacesData = await ifacesResp.json();
        
        if (ifacesData.success) {
            updateInterfacesTable(ifacesData.interfaces);
            document.getElementById('stat-interfaces').textContent = ifacesData.interfaces.length;
        }

        // Get profiles
        const profilesResp = await fetch(`${API_BASE}/profiles`);
        const profilesData = await profilesResp.json();
        
        if (profilesData.success) {
            updateProfilesTable(profilesData.profiles);
            const activeCount = profilesData.profiles.filter(p => p.enabled).length;
            document.getElementById('stat-profiles').textContent = activeCount;
        }
    } catch (error) {
        console.error('Dashboard update failed:', error);
    }
}

function updateInterfacesTable(interfaces) {
    const tbody = document.getElementById('interfaces-tbody');
    
    if (interfaces.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #64748b;">No interfaces detected.</td></tr>';
        return;
    }
    
    tbody.innerHTML = interfaces.map(iface => `
        <tr>
            <td>${iface.name}</td>
            <td>${iface.ip || 'N/A'}</td>
            <td>${iface.mac || 'N/A'}</td>
            <td>${iface.network || 'N/A'}</td>
            <td>${formatNumber(iface.tx_packets || 0)}</td>
            <td>${formatNumber(iface.rx_packets || 0)}</td>
        </tr>
    `).join('');
}

function updateProfilesTable(profiles) {
    const tbody = document.getElementById('profiles-tbody');
    
    if (profiles.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: #64748b;">No profiles defined.</td></tr>';
        return;
    }
    
    tbody.innerHTML = profiles.map(profile => `
        <tr>
            <td>${profile.name}</td>
            <td style="text-transform: uppercase;">${profile.type}</td>
            <td>${profile.src_interface} → ${profile.dst_interface}</td>
            <td>${profile.bandwidth_mbps || 'N/A'} Mbps</td>
            <td>${formatNumber(profile.packets_sent || 0)}</td>
            <td>
                <span class="${profile.enabled ? 'status-enabled' : 'status-disabled'}">
                    ${profile.enabled ? '✓ Enabled' : '○ Disabled'}
                </span>
            </td>
            <td>
                ${profile.enabled ? 
                    `<button class="btn btn-danger" onclick="toggleProfile('${profile.id}', false)" style="padding: 6px 12px; font-size: 0.85em;">Disable</button>` :
                    `<button class="btn btn-success" onclick="toggleProfile('${profile.id}', true)" style="padding: 6px 12px; font-size: 0.85em;">Enable</button>`
                }
                <button class="btn btn-secondary" onclick="deleteProfile('${profile.id}')" style="padding: 6px 12px; font-size: 0.85em;">Delete</button>
            </td>
        </tr>
    `).join('');
}

// ============================================================================
// Traffic Control
// ============================================================================

async function startTraffic() {
    try {
        const resp = await fetch(`${API_BASE}/traffic/start`, { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            showAlert('✓ Traffic generation started!', 'success');
        } else {
            showAlert('✗ Failed to start: ' + data.error, 'error');
        }
    } catch (error) {
        showAlert('✗ Error: ' + error.message, 'error');
    }
}

async function stopTraffic() {
    try {
        const resp = await fetch(`${API_BASE}/traffic/stop`, { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            showAlert('✓ Traffic generation stopped', 'success');
        }
    } catch (error) {
        showAlert('✗ Error: ' + error.message, 'error');
    }
}

async function resetStats() {
    try {
        const resp = await fetch(`${API_BASE}/stats/reset`, { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            showAlert('✓ Statistics reset', 'success');
            updateDashboard();
        }
    } catch (error) {
        showAlert('✗ Error: ' + error.message, 'error');
    }
}

async function autoDetect() {
    try {
        showAlert('🔍 Detecting interfaces and generating profiles...', 'success');
        const resp = await fetch(`${API_BASE}/auto-detect`, { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            showAlert(`✓ Detected ${data.interfaces} interfaces and generated ${data.profiles} profiles!`, 'success');
            updateDashboard();
        } else {
            showAlert('✗ Auto-detect failed: ' + data.error, 'error');
        }
    } catch (error) {
        showAlert('✗ Error: ' + error.message, 'error');
    }
}

// ============================================================================
// Profile Management
// ============================================================================

async function toggleProfile(profileId, enable) {
    try {
        const action = enable ? 'enable' : 'disable';
        const resp = await fetch(`${API_BASE}/profiles/${profileId}/${action}`, { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            updateDashboard();
        }
    } catch (error) {
        showAlert('✗ Error: ' + error.message, 'error');
    }
}

async function deleteProfile(profileId) {
    if (!confirm('Delete this profile?')) return;
    
    try {
        const resp = await fetch(`${API_BASE}/profiles/${profileId}`, { method: 'DELETE' });
        const data = await resp.json();
        if (data.success) {
            showAlert('✓ Profile deleted', 'success');
            updateDashboard();
        }
    } catch (error) {
        showAlert('✗ Error: ' + error.message, 'error');
    }
}

function showCreateProfile() {
    showAlert('Profile creation form coming soon!', 'success');
    // TODO: Implement profile creation modal
}

// ============================================================================
// SNMP Agent Farm
// ============================================================================

async function startSNMP() {
    try {
        const baseIp = document.getElementById('snmp-base-ip').value;
        const count = parseInt(document.getElementById('snmp-count').value);
        
        const resp = await fetch(`${API_BASE}/snmp/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ base_ip: baseIp, count: count })
        });
        
        const data = await resp.json();
        if (data.success) {
            showAlert(`✓ Started ${count} SNMP agents at ${baseIp}`, 'success');
            document.getElementById('snmp-active-count').textContent = count;
        } else {
            showAlert('✗ Failed: ' + data.error, 'error');
        }
    } catch (error) {
        showAlert('✗ Error: ' + error.message, 'error');
    }
}

async function stopSNMP() {
    try {
        const resp = await fetch(`${API_BASE}/snmp/stop`, { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            showAlert('✓ SNMP agents stopped', 'success');
            document.getElementById('snmp-active-count').textContent = '0';
        }
    } catch (error) {
        showAlert('✗ Error: ' + error.message, 'error');
    }
}

// ============================================================================
// NetFlow Generation
// ============================================================================

async function startNetFlow() {
    try {
        const collectorIp = document.getElementById('netflow-collector-ip').value;
        const port = parseInt(document.getElementById('netflow-port').value);
        const rate = parseInt(document.getElementById('netflow-rate').value);
        const duration = parseInt(document.getElementById('netflow-duration').value);
        
        const resp = await fetch(`${API_BASE}/netflow/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                collector_ip: collectorIp,
                collector_port: port,
                flows_per_sec: rate,
                duration: duration
            })
        });
        
        const data = await resp.json();
        if (data.success) {
            showAlert(`✓ NetFlow started: ${rate} flows/sec to ${collectorIp}:${port}`, 'success');
        } else {
            showAlert('✗ Failed: ' + data.error, 'error');
        }
    } catch (error) {
        showAlert('✗ Error: ' + error.message, 'error');
    }
}

async function stopNetFlow() {
    try {
        const resp = await fetch(`${API_BASE}/netflow/stop`, { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            showAlert('✓ NetFlow stopped', 'success');
        }
    } catch (error) {
        showAlert('✗ Error: ' + error.message, 'error');
    }
}

// ============================================================================
// BGP Route Injection
// ============================================================================

async function startBGP() {
    try {
        const peerIp = document.getElementById('bgp-peer-ip').value;
        const localAsn = parseInt(document.getElementById('bgp-local-asn').value);
        const routeCount = parseInt(document.getElementById('bgp-route-count').value);
        
        const resp = await fetch(`${API_BASE}/bgp/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                peer_ip: peerIp,
                local_asn: localAsn,
                route_count: routeCount
            })
        });
        
        const data = await resp.json();
        if (data.success) {
            showAlert(`✓ BGP session started: injecting ${routeCount} routes to ${peerIp}`, 'success');
        } else {
            showAlert('✗ Failed: ' + data.error, 'error');
        }
    } catch (error) {
        showAlert('✗ Error: ' + error.message, 'error');
    }
}

async function stopBGP() {
    try {
        const resp = await fetch(`${API_BASE}/bgp/stop`, { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            showAlert('✓ BGP session stopped', 'success');
        }
    } catch (error) {
        showAlert('✗ Error: ' + error.message, 'error');
    }
}

// ============================================================================
// QoS Testing
// ============================================================================

async function startQoSTest() {
    try {
        const srcIp = document.getElementById('qos-src-ip').value;
        const dstIp = document.getElementById('qos-dst-ip').value;
        const duration = parseInt(document.getElementById('qos-duration').value);
        const scenario = document.getElementById('qos-scenario').value;
        
        showAlert('🔄 Running QoS test...', 'success');
        
        const resp = await fetch(`${API_BASE}/qos/test`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                src_ip: srcIp,
                dst_ip: dstIp,
                duration: duration,
                scenario: scenario
            })
        });
        
        const data = await resp.json();
        if (data.success) {
            showAlert('✓ QoS test completed', 'success');
            displayQoSResults(data.results);
        } else {
            showAlert('✗ Test failed: ' + data.error, 'error');
        }
    } catch (error) {
        showAlert('✗ Error: ' + error.message, 'error');
    }
}

function displayQoSResults(results) {
    const resultsDiv = document.getElementById('qos-results');
    const tbody = document.getElementById('qos-results-tbody');
    
    tbody.innerHTML = results.map(r => `
        <tr>
            <td>${r.name}</td>
            <td>${r.dscp}</td>
            <td>${r.packets_sent}</td>
            <td style="color: ${r.loss_percent > r.expected_loss_percent ? '#ef4444' : '#10b981'}">${r.loss_percent.toFixed(2)}%</td>
            <td style="color: ${r.avg_latency_ms > r.expected_latency_ms ? '#ef4444' : '#10b981'}">${r.avg_latency_ms.toFixed(2)}</td>
            <td>${r.avg_jitter_ms.toFixed(2)}</td>
            <td>
                <span style="color: ${r.latency_met && r.loss_met ? '#10b981' : '#ef4444'}">
                    ${r.latency_met && r.loss_met ? '✓ PASS' : '✗ FAIL'}
                </span>
            </td>
        </tr>
    `).join('');
    
    resultsDiv.style.display = 'block';
}

function viewQoSResults() {
    const resultsDiv = document.getElementById('qos-results');
    resultsDiv.style.display = resultsDiv.style.display === 'none' ? 'block' : 'none';
}

// ============================================================================
// Network Impairments
// ============================================================================

const impairmentProfiles = {
    none: { latency: 0, jitter: 0, loss: 0, burst_loss: 0, reorder: 0, duplicate: 0, bandwidth: 0 },
    lan: { latency: 1, jitter: 0.5, loss: 0.001, burst_loss: 0, reorder: 0, duplicate: 0, bandwidth: 0 },
    broadband_good: { latency: 20, jitter: 5, loss: 0.1, burst_loss: 0, reorder: 0, duplicate: 0, bandwidth: 0 },
    broadband_poor: { latency: 100, jitter: 30, loss: 2, burst_loss: 1, reorder: 0.1, duplicate: 0, bandwidth: 0 },
    mobile_3g: { latency: 200, jitter: 100, loss: 5, burst_loss: 2, reorder: 0.5, duplicate: 0, bandwidth: 3 },
    mobile_4g: { latency: 50, jitter: 20, loss: 1, burst_loss: 0.5, reorder: 0, duplicate: 0, bandwidth: 50 },
    mobile_5g: { latency: 10, jitter: 5, loss: 0.1, burst_loss: 0, reorder: 0, duplicate: 0, bandwidth: 1000 },
    satellite: { latency: 600, jitter: 50, loss: 0.5, burst_loss: 0, reorder: 0, duplicate: 0, bandwidth: 0 },
    congested: { latency: 500, jitter: 200, loss: 10, burst_loss: 5, reorder: 1, duplicate: 0.1, bandwidth: 0 }
};

function loadImpairmentProfile() {
    const profile = document.getElementById('impair-profile').value;
    const settings = impairmentProfiles[profile];
    
    if (settings) {
        document.getElementById('impair-latency').value = settings.latency;
        document.getElementById('impair-jitter').value = settings.jitter;
        document.getElementById('impair-loss').value = settings.loss;
        document.getElementById('impair-burst-loss').value = settings.burst_loss;
        document.getElementById('impair-reorder').value = settings.reorder;
        document.getElementById('impair-duplicate').value = settings.duplicate;
        document.getElementById('impair-bandwidth').value = settings.bandwidth;
    }
}

async function enableImpairments() {
    try {
        const settings = {
            latency_ms: parseFloat(document.getElementById('impair-latency').value),
            jitter_ms: parseFloat(document.getElementById('impair-jitter').value),
            loss_percent: parseFloat(document.getElementById('impair-loss').value),
            burst_loss_percent: parseFloat(document.getElementById('impair-burst-loss').value),
            reorder_percent: parseFloat(document.getElementById('impair-reorder').value),
            duplicate_percent: parseFloat(document.getElementById('impair-duplicate').value),
            bandwidth_mbps: parseFloat(document.getElementById('impair-bandwidth').value)
        };
        
        const resp = await fetch(`${API_BASE}/impairments/enable`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        
        const data = await resp.json();
        if (data.success) {
            showAlert('✓ Network impairments enabled', 'success');
            const badge = document.getElementById('impair-status');
            badge.textContent = 'Enabled';
            badge.className = 'status-badge status-running';
            impairmentStatus = true;
        } else {
            showAlert('✗ Failed: ' + data.error, 'error');
        }
    } catch (error) {
        showAlert('✗ Error: ' + error.message, 'error');
    }
}

async function disableImpairments() {
    try {
        const resp = await fetch(`${API_BASE}/impairments/disable`, { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            showAlert('✓ Network impairments disabled', 'success');
            const badge = document.getElementById('impair-status');
            badge.textContent = 'Disabled';
            badge.className = 'status-badge status-stopped';
            impairmentStatus = false;
        }
    } catch (error) {
        showAlert('✗ Error: ' + error.message, 'error');
    }
}

// ============================================================================
// Advanced Features
// ============================================================================

async function applyPerfSettings() {
    try {
        const settings = {
            tcp_pool_size: parseInt(document.getElementById('tcp-pool-size').value),
            batch_size: parseInt(document.getElementById('batch-size').value),
            use_zerocopy: document.getElementById('zero-copy').value === 'true'
        };
        
        const resp = await fetch(`${API_BASE}/config/performance`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        
        const data = await resp.json();
        if (data.success) {
            showAlert('✓ Performance settings applied', 'success');
        } else {
            showAlert('✗ Failed: ' + data.error, 'error');
        }
    } catch (error) {
        showAlert('✗ Error: ' + error.message, 'error');
    }
}

async function loadConfig() {
    showAlert('Configuration loading coming soon!', 'success');
}

async function saveConfig() {
    showAlert('Configuration saving coming soon!', 'success');
}

async function exportStats() {
    try {
        const resp = await fetch(`${API_BASE}/stats/export`);
        const data = await resp.json();
        
        if (data.success) {
            const blob = new Blob([JSON.stringify(data.stats, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `vep1445-stats-${new Date().toISOString()}.json`;
            a.click();
            showAlert('✓ Stats exported', 'success');
        }
    } catch (error) {
        showAlert('✗ Error: ' + error.message, 'error');
    }
}

async function viewLogs() {
    const logsDisplay = document.getElementById('logs-display');
    logsDisplay.style.display = logsDisplay.style.display === 'none' ? 'block' : 'none';
    
    if (logsDisplay.style.display === 'block') {
        try {
            const resp = await fetch(`${API_BASE}/logs`);
            const data = await resp.json();
            if (data.success) {
                logsDisplay.textContent = data.logs.join('\n');
            }
        } catch (error) {
            logsDisplay.textContent = 'Failed to load logs: ' + error.message;
        }
    }
}

async function clearLogs() {
    if (!confirm('Clear all logs?')) return;
    
    try {
        const resp = await fetch(`${API_BASE}/logs/clear`, { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            showAlert('✓ Logs cleared', 'success');
            document.getElementById('logs-display').textContent = '';
        }
    } catch (error) {
        showAlert('✗ Error: ' + error.message, 'error');
    }
}

// ============================================================================
// Initialization
// ============================================================================

// Start auto-update
updateDashboard();
updateInterval = setInterval(updateDashboard, 2000);

// Load default impairment profile
loadImpairmentProfile();

console.log('VEP1445 Dashboard loaded successfully');
