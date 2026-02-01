/**
 * VEP1445 Enhanced Features - GUI Extensions
 * Adds Advanced Features tab and DDoS Testing tab to the existing GUI
 * 
 * Installation:
 * 1. Save this file as: /opt/netgen/web/enhanced-features.js
 * 2. Add to index.html before </body>: <script src="enhanced-features.js"></script>
 * 3. Reload the page
 */

(function() {
    'use strict';
    
    console.log('🚀 Loading Enhanced Features...');
    
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initEnhancedFeatures);
    } else {
        initEnhancedFeatures();
    }
    
    function initEnhancedFeatures() {
        console.log('✅ Initializing Enhanced Features');
        addAdvancedTab();
        addDDoSTab();
        checkFeatureAvailability();
    }
    
    // ========================================================================
    // ADVANCED FEATURES TAB
    // ========================================================================
    
    function addAdvancedTab() {
        const tabsDiv = document.querySelector('.tabs');
        if (!tabsDiv) {
            console.error('Tabs container not found');
            return;
        }
        
        // Add tab button
        const advBtn = document.createElement('button');
        advBtn.className = 'tab';
        advBtn.setAttribute('data-tab', 'advanced');
        advBtn.innerHTML = '⚡ Advanced';
        tabsDiv.appendChild(advBtn);
        
        // Add tab content
        const container = document.querySelector('.container');
        const advTab = document.createElement('div');
        advTab.id = 'advanced';
        advTab.className = 'tab-content';
        advTab.innerHTML = `
            <div class="section">
                <div class="section-title">⚡ Advanced Features</div>
                
                <!-- Feature Availability Status -->
                <div id="featureStatus" class="card" style="margin-bottom: 20px; background: var(--secondary-bg);">
                    <h3>📡 Feature Availability</h3>
                    <div id="featureStatusContent">Loading...</div>
                </div>
                
                <!-- SNMP Agent Farm -->
                <div class="card" style="margin-bottom: 20px;">
                    <h3>📡 SNMP Agent Farm</h3>
                    <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 15px;">
                        Simulate hundreds of SNMP-enabled devices for testing network monitoring systems.
                    </p>
                    <div class="form-grid">
                        <div class="form-group">
                            <label class="form-label">Base IP Address</label>
                            <input type="text" id="snmp_base_ip" class="form-input" value="192.168.100.1" placeholder="192.168.100.1">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Number of Agents</label>
                            <input type="number" id="snmp_count" class="form-input" value="10" min="1" max="1000">
                        </div>
                    </div>
                    <button class="btn btn-primary" onclick="window.startSNMP()">▶ START SNMP AGENTS</button>
                    <button class="btn btn-danger" onclick="window.stopSNMP()">⏹ STOP</button>
                    <button class="btn btn-secondary" onclick="window.checkSNMPStatus()">📊 STATUS</button>
                    <div id="snmp_status" style="margin-top: 15px; padding: 10px; border-radius: 6px;"></div>
                </div>
                
                <!-- NetFlow Generation -->
                <div class="card" style="margin-bottom: 20px;">
                    <h3>🌊 NetFlow/IPFIX Generation</h3>
                    <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 15px;">
                        Generate realistic NetFlow v5/v9 or IPFIX records for collector testing.
                    </p>
                    <div class="form-grid">
                        <div class="form-group">
                            <label class="form-label">Collector IP</label>
                            <input type="text" id="netflow_collector" class="form-input" placeholder="192.168.1.100">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Collector Port</label>
                            <input type="number" id="netflow_port" class="form-input" value="2055">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Flows per Second</label>
                            <input type="number" id="netflow_fps" class="form-input" value="1000" min="1" max="100000">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Duration (seconds)</label>
                            <input type="number" id="netflow_duration" class="form-input" value="60">
                        </div>
                    </div>
                    <button class="btn btn-primary" onclick="window.startNetFlow()">▶ START NETFLOW</button>
                    <div id="netflow_status" style="margin-top: 15px; padding: 10px; border-radius: 6px;"></div>
                </div>
                
                <!-- BGP Route Injection -->
                <div class="card" style="margin-bottom: 20px;">
                    <h3>🔀 BGP Route Injection</h3>
                    <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 15px;">
                        Establish BGP sessions and inject routing table entries for scalability testing.
                    </p>
                    <div class="form-grid">
                        <div class="form-group">
                            <label class="form-label">Peer IP Address</label>
                            <input type="text" id="bgp_peer" class="form-input" placeholder="192.168.1.1">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Local ASN</label>
                            <input type="number" id="bgp_asn" class="form-input" value="65000">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Number of Routes</label>
                            <input type="number" id="bgp_routes" class="form-input" value="1000" min="1" max="100000">
                        </div>
                    </div>
                    <button class="btn btn-primary" onclick="window.startBGP()">▶ START BGP SESSION</button>
                    <button class="btn btn-danger" onclick="window.stopBGP()">⏹ STOP</button>
                    <div id="bgp_status" style="margin-top: 15px; padding: 10px; border-radius: 6px;"></div>
                </div>
                
                <!-- QoS Testing -->
                <div class="card" style="margin-bottom: 20px;">
                    <h3>📊 QoS Validation Testing</h3>
                    <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 15px;">
                        Validate Quality of Service (DSCP) markings with multi-class traffic profiles.
                    </p>
                    <div class="form-grid">
                        <div class="form-group">
                            <label class="form-label">Source IP</label>
                            <input type="text" id="qos_src" class="form-input" placeholder="24.1.6.142">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Destination IP</label>
                            <input type="text" id="qos_dst" class="form-input" placeholder="24.1.1.139">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Test Scenario</label>
                            <select id="qos_scenario" class="form-select">
                                <option value="voice_video_data">Voice/Video/Data (3-class)</option>
                                <option value="eight_class">Eight Class QoS Model</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Duration (seconds)</label>
                            <input type="number" id="qos_duration" class="form-input" value="60">
                        </div>
                    </div>
                    <button class="btn btn-primary" onclick="window.startQoS()">▶ START QOS TEST</button>
                    <button class="btn btn-secondary" onclick="window.getQoSResults()">📊 GET RESULTS</button>
                    <div id="qos_results" style="margin-top: 15px;"></div>
                </div>
                
                <!-- Network Impairments -->
                <div class="card" style="margin-bottom: 20px;">
                    <h3>⚠️ Network Impairments</h3>
                    <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 15px;">
                        Simulate degraded network conditions: latency, jitter, packet loss, reordering.
                    </p>
                    <div class="form-grid">
                        <div class="form-group">
                            <label class="form-label">Latency (ms)</label>
                            <input type="number" id="imp_latency" class="form-input" value="0" min="0" max="5000">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Jitter (ms)</label>
                            <input type="number" id="imp_jitter" class="form-input" value="0" min="0" max="1000">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Packet Loss (%)</label>
                            <input type="number" id="imp_loss" class="form-input" value="0" min="0" max="100" step="0.1">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Burst Loss (%)</label>
                            <input type="number" id="imp_burst" class="form-input" value="0" min="0" max="100" step="0.1">
                        </div>
                    </div>
                    <button class="btn btn-primary" onclick="window.enableImpairments()">▶ ENABLE IMPAIRMENTS</button>
                    <button class="btn btn-danger" onclick="window.disableImpairments()">⏹ DISABLE</button>
                    <div id="imp_status" style="margin-top: 15px; padding: 10px; border-radius: 6px;"></div>
                </div>
            </div>
        `;
        
        const rfc2544Tab = document.querySelector('[data-tab="rfc2544"]');
        if (rfc2544Tab) {
            rfc2544Tab.parentNode.insertBefore(advBtn, rfc2544Tab.nextSibling);
        }
        
        container.appendChild(advTab);
        
        // Add tab switching
        advBtn.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            advBtn.classList.add('active');
            advTab.classList.add('active');
            checkFeatureAvailability();
        });
        
        console.log('✅ Advanced Features tab added');
    }
    
    // ========================================================================
    // DDOS TESTING TAB
    // ========================================================================
    
    function addDDoSTab() {
        const tabsDiv = document.querySelector('.tabs');
        if (!tabsDiv) return;
        
        const ddosBtn = document.createElement('button');
        ddosBtn.className = 'tab';
        ddosBtn.setAttribute('data-tab', 'ddos');
        ddosBtn.innerHTML = '🔥 DDoS';
        tabsDiv.appendChild(ddosBtn);
        
        const container = document.querySelector('.container');
        const ddosTab = document.createElement('div');
        ddosTab.id = 'ddos';
        ddosTab.className = 'tab-content';
        ddosTab.innerHTML = `
            <div class="section">
                <div class="section-title">🔥 DDoS Attack Simulation</div>
                <div class="card" style="background: var(--accent-red); color: white; margin-bottom: 20px; padding: 15px;">
                    <h3 style="margin: 0;">⚠️ WARNING</h3>
                    <p style="margin: 10px 0 0 0;">
                        Only use on isolated test networks or with explicit written permission.
                        Unauthorized DDoS attacks are illegal and can result in criminal prosecution.
                    </p>
                </div>
                
                <div class="card">
                    <h3>Attack Configuration</h3>
                    <div class="form-grid">
                        <div class="form-group">
                            <label class="form-label">Attack Type</label>
                            <select id="ddos_type" class="form-select">
                                <option value="udp_flood">UDP Flood (Volumetric)</option>
                                <option value="syn_flood">SYN Flood (TCP Half-Open)</option>
                                <option value="http_flood">HTTP Flood (Layer 7)</option>
                                <option value="dns_amp">DNS Amplification</option>
                                <option value="distributed">Distributed Multi-Source</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Target IP Address</label>
                            <input type="text" id="ddos_target_ip" class="form-input" placeholder="24.1.1.139">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Target Port</label>
                            <input type="number" id="ddos_target_port" class="form-input" value="80">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Attack Intensity</label>
                            <select id="ddos_rate" class="form-select">
                                <option value="low">Low (100 Mbps / 10K PPS)</option>
                                <option value="medium">Medium (500 Mbps / 50K PPS)</option>
                                <option value="high">High (1 Gbps / 100K PPS)</option>
                                <option value="extreme">Extreme (Line Rate)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Duration (seconds)</label>
                            <input type="number" id="ddos_duration" class="form-input" value="30" min="1" max="300">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Source Interface</label>
                            <select id="ddos_src_iface" class="form-select">
                                <option value="eno2">eno2</option>
                                <option value="eno3">eno3</option>
                                <option value="eno4">eno4</option>
                                <option value="eno5">eno5</option>
                                <option value="eno6">eno6</option>
                                <option value="all">All Interfaces (Distributed)</option>
                            </select>
                        </div>
                    </div>
                    
                    <div style="margin-top: 20px; display: flex; gap: 10px;">
                        <button class="btn btn-danger" style="font-size: 18px; flex: 1;" onclick="window.launchDDoS()">
                            🔥 LAUNCH ATTACK
                        </button>
                        <button class="btn btn-secondary" style="flex: 1;" onclick="window.stopDDoS()">
                            ⏹ STOP ALL ATTACKS
                        </button>
                    </div>
                    
                    <div id="ddos_status" style="margin-top: 20px; padding: 15px; border-radius: 6px;"></div>
                </div>
                
                <div class="card" style="margin-top: 20px;">
                    <h3>📊 Real-Time Attack Metrics</h3>
                    <div id="ddos_metrics">
                        <p style="color: var(--text-secondary);">No active attack</p>
                    </div>
                </div>
            </div>
        `;
        
        container.appendChild(ddosTab);
        
        ddosBtn.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            ddosBtn.classList.add('active');
            ddosTab.classList.add('active');
        });
        
        console.log('✅ DDoS Testing tab added');
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
    
    console.log('✅ Enhanced Features loaded successfully');
})();
