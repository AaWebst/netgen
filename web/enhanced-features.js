/**
 * VEP1445 Enhanced Features - Functions Only
 * Tabs are now built into HTML, this just provides the functionality
 */

(function() {
    'use strict';
    
    console.log('🚀 Loading Enhanced Features Functions...');
    
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initEnhancedFeatures);
    } else {
        initEnhancedFeatures();
    }
    
    function initEnhancedFeatures() {
        console.log('✅ Initializing Enhanced Features');
        checkFeatureAvailability();
    }
    
    // ========================================================================
    // FEATURE FUNCTIONS
    // ========================================================================
    
    window.checkFeatureAvailability = async function() {
        try {
            const response = await fetch('/api/features/status');
            const data = await response.json();
            
            if (data.success) {
                let html = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;">';
                Object.entries(data.features).forEach(([feature, available]) => {
                    const icon = available ? '✅' : '❌';
                    const color = available ? 'var(--accent-green)' : 'var(--text-secondary)';
                    const status = available ? 'Available' : 'Not Available';
                    html += `
                        <div style="padding: 10px; border: 1px solid var(--border-color); border-radius: 6px; text-align: center;">
                            <div style="font-size: 24px;">${icon}</div>
                            <div style="font-weight: bold; text-transform: uppercase; margin-top: 5px;">${feature}</div>
                            <div style="color: ${color}; font-size: 12px;">${status}</div>
                        </div>
                    `;
                });
                html += '</div>';
                
                const statusDiv = document.getElementById('featureStatusContent');
                if (statusDiv) statusDiv.innerHTML = html;
            }
        } catch (error) {
            console.error('Feature check error:', error);
            const statusDiv = document.getElementById('featureStatusContent');
            if (statusDiv) statusDiv.innerHTML = '<p style="color: var(--accent-red);">Error loading feature status</p>';
        }
    };
    
    // SNMP Functions
    window.startSNMP = async function() {
        const baseIp = document.getElementById('snmp_base_ip').value;
        const count = parseInt(document.getElementById('snmp_count').value);
        
        try {
            const response = await fetch('/api/snmp/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({base_ip: baseIp, count: count})
            });
            const data = await response.json();
            
            if (data.success) {
                showStatus('snmp_status', `✅ Started ${data.agents} SNMP agents at ${data.base_ip}`, 'success');
            } else {
                showStatus('snmp_status', `❌ Error: ${data.error}`, 'error');
            }
        } catch (error) {
            showStatus('snmp_status', `❌ Error: ${error.message}`, 'error');
        }
    };
    
    window.stopSNMP = async function() {
        try {
            await fetch('/api/snmp/stop', {method: 'POST'});
            showStatus('snmp_status', '⏹ SNMP agents stopped', 'warning');
        } catch (error) {
            showStatus('snmp_status', `❌ Error: ${error.message}`, 'error');
        }
    };
    
    window.checkSNMPStatus = async function() {
        try {
            const response = await fetch('/api/snmp/status');
            const data = await response.json();
            
            if (data.success && data.stats) {
                const count = data.stats.agent_count || 0;
                const requests = data.stats.total_requests || 0;
                showStatus('snmp_status', `📊 Active Agents: ${count} | Total Requests: ${requests}`, 'info');
            }
        } catch (error) {
            showStatus('snmp_status', `❌ Error: ${error.message}`, 'error');
        }
    };
    
    // NetFlow Functions
    window.startNetFlow = async function() {
        const collector = document.getElementById('netflow_collector').value;
        const port = parseInt(document.getElementById('netflow_port').value);
        const fps = parseInt(document.getElementById('netflow_fps').value);
        const duration = parseInt(document.getElementById('netflow_duration').value);
        
        if (!collector) {
            showStatus('netflow_status', '❌ Please enter collector IP', 'error');
            return;
        }
        
        try {
            await fetch('/api/netflow/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    collector_ip: collector,
                    collector_port: port,
                    flows_per_sec: fps,
                    duration: duration
                })
            });
            showStatus('netflow_status', `✅ NetFlow started: ${fps} flows/sec → ${collector}:${port} for ${duration}s`, 'success');
        } catch (error) {
            showStatus('netflow_status', `❌ Error: ${error.message}`, 'error');
        }
    };
    
    // BGP Functions
    window.startBGP = async function() {
        const peer = document.getElementById('bgp_peer').value;
        const asn = parseInt(document.getElementById('bgp_asn').value);
        const routes = parseInt(document.getElementById('bgp_routes').value);
        
        if (!peer) {
            showStatus('bgp_status', '❌ Please enter peer IP', 'error');
            return;
        }
        
        try {
            await fetch('/api/bgp/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({peer_ip: peer, local_asn: asn, route_count: routes})
            });
            showStatus('bgp_status', `✅ BGP session started: Injecting ${routes} routes to ${peer} (AS${asn})`, 'success');
        } catch (error) {
            showStatus('bgp_status', `❌ Error: ${error.message}`, 'error');
        }
    };
    
    window.stopBGP = async function() {
        try {
            await fetch('/api/bgp/stop', {method: 'POST'});
            showStatus('bgp_status', '⏹ BGP session stopped', 'warning');
        } catch (error) {
            showStatus('bgp_status', `❌ Error: ${error.message}`, 'error');
        }
    };
    
    // QoS Functions
    window.startQoS = async function() {
        const src = document.getElementById('qos_src').value;
        const dst = document.getElementById('qos_dst').value;
        const scenario = document.getElementById('qos_scenario').value;
        const duration = parseInt(document.getElementById('qos_duration').value);
        
        if (!src || !dst) {
            showStatus('qos_results', '❌ Please enter source and destination IPs', 'error');
            return;
        }
        
        try {
            await fetch('/api/qos/test', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({src_ip: src, dst_ip: dst, scenario: scenario, duration: duration})
            });
            
            const resultDiv = document.getElementById('qos_results');
            resultDiv.innerHTML = `
                <div style="background: var(--secondary-bg); padding: 15px; border-radius: 6px; border-left: 3px solid var(--accent-green);">
                    ✅ QoS test started (${duration}s)<br>
                    <small style="color: var(--text-secondary);">Click "GET RESULTS" after test completes</small>
                </div>
            `;
        } catch (error) {
            showStatus('qos_results', `❌ Error: ${error.message}`, 'error');
        }
    };
    
    window.getQoSResults = async function() {
        try {
            const response = await fetch('/api/qos/results');
            const data = await response.json();
            
            if (data.results && data.results.length > 0) {
                let html = '<div style="background: var(--secondary-bg); padding: 15px; border-radius: 6px;">';
                html += '<h4 style="margin-top: 0;">QoS Test Results</h4>';
                html += '<table style="width:100%; color: var(--text-primary); border-collapse: collapse;">';
                html += '<tr style="border-bottom: 1px solid var(--border-color);"><th>Class</th><th>DSCP</th><th>Packets</th><th>Loss %</th><th>Latency</th><th>Jitter</th></tr>';
                
                data.results.forEach(r => {
                    const lossColor = r.loss_percent > 1 ? 'var(--accent-red)' : 'var(--accent-green)';
                    html += `<tr style="border-bottom: 1px solid var(--border-color);">
                        <td style="padding: 8px;"><strong>${r.class}</strong></td>
                        <td>${r.dscp}</td>
                        <td>${r.packets_sent.toLocaleString()}</td>
                        <td style="color: ${lossColor};">${r.loss_percent.toFixed(3)}%</td>
                        <td>${r.avg_latency_ms.toFixed(2)} ms</td>
                        <td>${r.avg_jitter_ms.toFixed(2)} ms</td>
                    </tr>`;
                });
                html += '</table></div>';
                
                document.getElementById('qos_results').innerHTML = html;
            } else {
                showStatus('qos_results', '⏳ No results yet - test may still be running', 'warning');
            }
        } catch (error) {
            showStatus('qos_results', `❌ Error: ${error.message}`, 'error');
        }
    };
    
    // Impairment Functions
    window.enableImpairments = async function() {
        const latency = parseInt(document.getElementById('imp_latency').value);
        const jitter = parseInt(document.getElementById('imp_jitter').value);
        const loss = parseFloat(document.getElementById('imp_loss').value);
        const burst = parseFloat(document.getElementById('imp_burst').value);
        
        try {
            await fetch('/api/impairments/enable', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    latency_ms: latency,
                    jitter_ms: jitter,
                    loss_percent: loss,
                    burst_loss_percent: burst
                })
            });
            
            let impairments = [];
            if (latency > 0) impairments.push(`${latency}ms latency`);
            if (jitter > 0) impairments.push(`${jitter}ms jitter`);
            if (loss > 0) impairments.push(`${loss}% loss`);
            if (burst > 0) impairments.push(`${burst}% burst loss`);
            
            const desc = impairments.length > 0 ? impairments.join(', ') : 'no impairments';
            showStatus('imp_status', `✅ Impairments enabled: ${desc}`, 'success');
        } catch (error) {
            showStatus('imp_status', `❌ Error: ${error.message}`, 'error');
        }
    };
    
    window.disableImpairments = async function() {
        try {
            await fetch('/api/impairments/disable', {method: 'POST'});
            showStatus('imp_status', '⏹ Impairments disabled - network restored to normal', 'warning');
        } catch (error) {
            showStatus('imp_status', `❌ Error: ${error.message}`, 'error');
        }
    };
    
    // DDoS Functions
    window.launchDDoS = async function() {
        const type = document.getElementById('ddos_type').value;
        const targetIp = document.getElementById('ddos_target_ip').value;
        const targetPort = parseInt(document.getElementById('ddos_target_port').value);
        const rate = document.getElementById('ddos_rate').value;
        const duration = parseInt(document.getElementById('ddos_duration').value);
        const srcIface = document.getElementById('ddos_src_iface').value;
        
        if (!targetIp) {
            showStatus('ddos_status', '❌ Please enter target IP address', 'error');
            return;
        }
        
        const bandwidthMap = {
            'low': 100,
            'medium': 500,
            'high': 1000,
            'extreme': 10000
        };
        const bandwidth = bandwidthMap[rate];
        
        let profileConfig = {
            name: `DDoS_${type}_${Date.now()}`,
            src_interface: srcIface === 'all' ? 'eno2' : srcIface,
            dst_interface: 'eno3',
            dst_ip: targetIp,
            dst_port: targetPort,
            duration: duration
        };
        
        switch(type) {
            case 'udp_flood':
                profileConfig.protocol = 'udp';
                profileConfig.bandwidth_mbps = bandwidth;
                profileConfig.packet_size = 64;
                break;
            case 'syn_flood':
                profileConfig.protocol = 'tcp';
                profileConfig.bandwidth_mbps = bandwidth;
                break;
            case 'http_flood':
                profileConfig.protocol = 'http';
                profileConfig.bandwidth_mbps = bandwidth;
                break;
            case 'dns_amp':
                profileConfig.protocol = 'udp';
                profileConfig.bandwidth_mbps = bandwidth;
                profileConfig.dst_port = 53;
                break;
        }
        
        try {
            const createResp = await fetch('/api/traffic-profiles', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(profileConfig)
            });
            
            if (!createResp.ok) throw new Error('Failed to create profile');
            
            const enableResp = await fetch(`/api/traffic-profiles/${profileConfig.name}/enable`, {
                method: 'POST'
            });
            
            if (!enableResp.ok) throw new Error('Failed to start attack');
            
            document.getElementById('ddos_status').innerHTML = `
                <div style="background: var(--accent-red); color: white; padding: 15px; border-radius: 6px; font-size: 16px;">
                    🔥 <strong>ATTACK LAUNCHED!</strong><br>
                    <div style="margin-top: 10px; font-size: 14px;">
                        Type: <strong>${type.toUpperCase().replace('_', ' ')}</strong><br>
                        Target: <strong>${targetIp}:${targetPort}</strong><br>
                        Rate: <strong>${bandwidth} Mbps</strong><br>
                        Duration: <strong>${duration}s</strong>
                    </div>
                </div>
            `;
            
            // Start metrics update
            window.ddosMetricsInterval = setInterval(() => updateDDoSMetrics(), 2000);
            
        } catch (error) {
            showStatus('ddos_status', `❌ Error: ${error.message}`, 'error');
        }
    };
    
    window.stopDDoS = async function() {
        try {
            const response = await fetch('/api/traffic-profiles');
            const data = await response.json();
            
            let stopped = 0;
            for (const [name, profile] of Object.entries(data.profiles || {})) {
                if (name.startsWith('DDoS_') && profile.enabled) {
                    await fetch(`/api/traffic-profiles/${name}/disable`, {method: 'POST'});
                    stopped++;
                }
            }
            
            if (window.ddosMetricsInterval) {
                clearInterval(window.ddosMetricsInterval);
                window.ddosMetricsInterval = null;
            }
            
            showStatus('ddos_status', `⏹ Stopped ${stopped} attack(s)`, 'warning');
            document.getElementById('ddos_metrics').innerHTML = '<p style="color: var(--text-secondary);">No active attack</p>';
        } catch (error) {
            showStatus('ddos_status', `❌ Error: ${error.message}`, 'error');
        }
    };
    
    async function updateDDoSMetrics() {
        try {
            const response = await fetch('/api/traffic/stats');
            const data = await response.json();
            
            if (data.success && data.stats) {
                let html = '<table style="width:100%; color: var(--text-primary); border-collapse: collapse;">';
                html += '<tr style="border-bottom: 1px solid var(--border-color);"><th>Interface</th><th>TX Packets</th><th>TX Bytes</th><th>Rate (Mbps)</th></tr>';
                
                Object.entries(data.stats).forEach(([iface, stats]) => {
                    const rateMbps = ((stats.tx_bytes * 8) / 1000000).toFixed(2);
                    html += `<tr style="border-bottom: 1px solid var(--border-color);">
                        <td style="padding: 8px;"><strong>${iface}</strong></td>
                        <td>${stats.tx_packets.toLocaleString()}</td>
                        <td>${(stats.tx_bytes / 1000000).toFixed(2)} MB</td>
                        <td style="color: var(--accent-cyan);">${rateMbps}</td>
                    </tr>`;
                });
                html += '</table>';
                
                document.getElementById('ddos_metrics').innerHTML = html;
            }
        } catch (error) {
            console.error('Metrics update error:', error);
        }
    }
    
    // Helper function for status messages
    function showStatus(elementId, message, type) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        const colors = {
            'success': 'var(--accent-green)',
            'error': 'var(--accent-red)',
            'warning': 'var(--accent-orange)',
            'info': 'var(--accent-cyan)'
        };
        
        element.innerHTML = `
            <div style="background: var(--secondary-bg); padding: 12px; border-radius: 6px; border-left: 3px solid ${colors[type]};">
                ${message}
            </div>
        `;
    }
    
    console.log('✅ Enhanced Features Functions loaded successfully');
})();
