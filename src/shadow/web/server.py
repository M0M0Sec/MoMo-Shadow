"""
Web UI Server

FastAPI-based web interface for buttonless control.
Mobile-friendly dark theme UI.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

if TYPE_CHECKING:
    from shadow.main import ShadowOrchestrator

logger = logging.getLogger(__name__)

# Global reference to orchestrator
_orchestrator: "ShadowOrchestrator | None" = None


class StatusResponse(BaseModel):
    """Status response model."""

    state: str
    mode: str
    uptime: int
    ap_count: int
    client_count: int
    probe_count: int
    handshake_count: int
    battery_percent: int
    target_ssid: str | None = None


class TargetRequest(BaseModel):
    """Target selection request."""

    bssid: str
    ssid: str


class ModeRequest(BaseModel):
    """Mode change request."""

    mode: str  # passive, capture, drop


class ConfigUpdate(BaseModel):
    """Configuration update."""

    key: str
    value: str | int | bool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan."""
    logger.info("Web server starting")
    yield
    logger.info("Web server stopping")


def create_app(orchestrator: "ShadowOrchestrator | None" = None) -> FastAPI:
    """
    Create FastAPI application.

    Args:
        orchestrator: Shadow orchestrator instance

    Returns:
        FastAPI application
    """
    global _orchestrator
    _orchestrator = orchestrator

    app = FastAPI(
        title="MoMo-Shadow",
        description="Stealth Recon Device Control",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Static files and templates
    static_dir = Path(__file__).parent / "static"
    templates_dir = Path(__file__).parent / "templates"

    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    templates = Jinja2Templates(directory=str(templates_dir)) if templates_dir.exists() else None

    def get_orchestrator() -> "ShadowOrchestrator":
        """Get orchestrator dependency."""
        if _orchestrator is None:
            raise HTTPException(status_code=503, detail="Service not ready")
        return _orchestrator

    # Routes
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Main page."""
        if templates:
            return templates.TemplateResponse("index.html", {"request": request})
        return HTMLResponse(content=get_embedded_html(), status_code=200)

    @app.get("/api/status", response_model=StatusResponse)
    async def get_status(orch: "ShadowOrchestrator" = Depends(get_orchestrator)):
        """Get current status."""
        return StatusResponse(
            state=orch.state.value,
            mode=orch.mode,
            uptime=orch.uptime,
            ap_count=len(orch.scanner.access_points) if orch.scanner else 0,
            client_count=len(orch.scanner.clients) if orch.scanner else 0,
            probe_count=len(orch.scanner.probes) if orch.scanner else 0,
            handshake_count=orch.handshake_count,
            battery_percent=orch.battery_percent,
            target_ssid=orch.target_ssid,
        )

    @app.get("/api/aps")
    async def get_access_points(orch: "ShadowOrchestrator" = Depends(get_orchestrator)):
        """Get discovered access points."""
        if not orch.scanner:
            return []

        return [
            {
                "bssid": ap.bssid,
                "ssid": ap.ssid,
                "channel": ap.channel,
                "signal_dbm": ap.signal_dbm,
                "security": ap.security.value,
                "clients": len(ap.clients),
                "hidden": ap.hidden,
            }
            for ap in orch.scanner.access_points
        ]

    @app.get("/api/clients")
    async def get_clients(orch: "ShadowOrchestrator" = Depends(get_orchestrator)):
        """Get discovered clients."""
        if not orch.scanner:
            return []

        return [
            {
                "mac": client.mac,
                "bssid": client.bssid,
                "signal_dbm": client.signal_dbm,
                "probes": client.probes,
            }
            for client in orch.scanner.clients
        ]

    @app.get("/api/probes")
    async def get_probes(orch: "ShadowOrchestrator" = Depends(get_orchestrator)):
        """Get captured probe requests."""
        if not orch.scanner:
            return []

        return [
            {
                "client_mac": probe.client_mac,
                "ssid": probe.ssid,
                "signal_dbm": probe.signal_dbm,
                "timestamp": probe.timestamp.isoformat(),
            }
            for probe in orch.scanner.probes[-100:]  # Last 100
        ]

    @app.get("/api/handshakes")
    async def get_handshakes(orch: "ShadowOrchestrator" = Depends(get_orchestrator)):
        """Get captured handshakes."""
        return [
            {
                "bssid": hs.bssid,
                "ssid": hs.ssid,
                "client_mac": hs.client_mac,
                "capture_type": hs.capture_type.value,
                "timestamp": hs.timestamp.isoformat(),
                "complete": hs.is_complete,
                "pcap_path": hs.pcap_path,
            }
            for hs in orch.handshakes
        ]

    @app.post("/api/mode")
    async def set_mode(
        request: ModeRequest,
        orch: "ShadowOrchestrator" = Depends(get_orchestrator),
    ):
        """Change operation mode."""
        if request.mode not in ("passive", "capture", "drop"):
            raise HTTPException(status_code=400, detail="Invalid mode")

        await orch.set_mode(request.mode)
        return {"status": "ok", "mode": request.mode}

    @app.post("/api/target")
    async def set_target(
        request: TargetRequest,
        orch: "ShadowOrchestrator" = Depends(get_orchestrator),
    ):
        """Set capture target."""
        await orch.set_target(request.bssid, request.ssid)
        return {"status": "ok", "target": request.ssid}

    @app.post("/api/capture/start")
    async def start_capture(orch: "ShadowOrchestrator" = Depends(get_orchestrator)):
        """Start handshake capture."""
        if not orch.target_ssid:
            raise HTTPException(status_code=400, detail="No target selected")

        await orch.start_capture()
        return {"status": "ok"}

    @app.post("/api/capture/stop")
    async def stop_capture(orch: "ShadowOrchestrator" = Depends(get_orchestrator)):
        """Stop handshake capture."""
        await orch.stop_capture()
        return {"status": "ok"}

    @app.post("/api/deauth")
    async def send_deauth(
        request: TargetRequest,
        orch: "ShadowOrchestrator" = Depends(get_orchestrator),
    ):
        """Send deauth packets."""
        await orch.send_deauth(request.bssid)
        return {"status": "ok"}

    @app.get("/api/config")
    async def get_config(orch: "ShadowOrchestrator" = Depends(get_orchestrator)):
        """Get current configuration."""
        return orch.config.model_dump()

    @app.post("/api/shutdown")
    async def shutdown(orch: "ShadowOrchestrator" = Depends(get_orchestrator)):
        """Shutdown device."""
        await orch.shutdown()
        return {"status": "shutting_down"}

    @app.post("/api/reboot")
    async def reboot(orch: "ShadowOrchestrator" = Depends(get_orchestrator)):
        """Reboot device."""
        await orch.reboot()
        return {"status": "rebooting"}

    @app.post("/api/scan/start")
    async def start_scanning(orch: "ShadowOrchestrator" = Depends(get_orchestrator)):
        """Start scanning (exits setup mode)."""
        await orch.start_scanning()
        return {"status": "ok", "mode": "scanning"}

    @app.post("/api/setup")
    async def return_to_setup(orch: "ShadowOrchestrator" = Depends(get_orchestrator)):
        """Return to setup mode (AP mode)."""
        await orch.return_to_setup()
        return {"status": "ok", "mode": "setup"}

    return app


def get_embedded_html() -> str:
    """Get embedded HTML when templates not available."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MoMo-Shadow</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-tertiary: #1a1a2e;
            --accent-primary: #00ff88;
            --accent-secondary: #00d4ff;
            --accent-danger: #ff4444;
            --text-primary: #e0e0e0;
            --text-secondary: #888;
            --border-color: #2a2a3a;
        }
        
        body {
            font-family: 'JetBrains Mono', 'SF Mono', monospace;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
        }
        
        .container { max-width: 480px; margin: 0 auto; padding: 1rem; }
        
        header {
            text-align: center;
            padding: 1.5rem 0;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 1rem;
        }
        
        h1 {
            font-size: 1.5rem;
            color: var(--accent-primary);
            text-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
        }
        
        .status-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 999px;
            font-size: 0.75rem;
            margin-top: 0.5rem;
        }
        
        .status-badge.active {
            background: rgba(0, 255, 136, 0.2);
            color: var(--accent-primary);
            border: 1px solid var(--accent-primary);
        }
        
        .card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        
        .card h2 {
            font-size: 0.875rem;
            color: var(--accent-secondary);
            margin-bottom: 0.75rem;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.75rem;
        }
        
        .stat {
            text-align: center;
            padding: 0.75rem;
            background: var(--bg-tertiary);
            border-radius: 6px;
        }
        
        .stat-value {
            font-size: 1.5rem;
            font-weight: bold;
            color: var(--accent-primary);
        }
        
        .stat-label {
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-top: 0.25rem;
        }
        
        .ap-list {
            max-height: 200px;
            overflow-y: auto;
        }
        
        .ap-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem;
            border-bottom: 1px solid var(--border-color);
            cursor: pointer;
        }
        
        .ap-item:hover { background: var(--bg-tertiary); }
        .ap-item:last-child { border-bottom: none; }
        
        .ap-ssid {
            font-weight: 500;
            max-width: 180px;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .ap-signal {
            font-size: 0.75rem;
            color: var(--text-secondary);
        }
        
        .btn {
            display: block;
            width: 100%;
            padding: 0.75rem;
            border: none;
            border-radius: 6px;
            font-family: inherit;
            font-size: 0.875rem;
            font-weight: 600;
            cursor: pointer;
            margin-bottom: 0.5rem;
            transition: all 0.2s;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: #000;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
        }
        
        .btn-danger {
            background: var(--accent-danger);
            color: #fff;
        }
        
        .btn-secondary {
            background: var(--bg-tertiary);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
        }
        
        .mode-selector {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1rem;
        }
        
        .mode-btn {
            flex: 1;
            padding: 0.5rem;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            color: var(--text-primary);
            cursor: pointer;
            font-family: inherit;
            font-size: 0.75rem;
        }
        
        .mode-btn.active {
            background: var(--accent-primary);
            color: #000;
            border-color: var(--accent-primary);
        }
        
        #target-display {
            padding: 0.5rem;
            background: var(--bg-tertiary);
            border-radius: 6px;
            margin-bottom: 0.5rem;
            font-size: 0.875rem;
        }
        
        .loading {
            text-align: center;
            padding: 2rem;
            color: var(--text-secondary);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🥷 MoMo-Shadow</h1>
            <div class="status-badge active" id="status-badge">SCANNING</div>
        </header>
        
        <div class="card">
            <h2>📊 Statistics</h2>
            <div class="stats-grid">
                <div class="stat">
                    <div class="stat-value" id="ap-count">0</div>
                    <div class="stat-label">Access Points</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="client-count">0</div>
                    <div class="stat-label">Clients</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="probe-count">0</div>
                    <div class="stat-label">Probes</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="hs-count">0</div>
                    <div class="stat-label">Handshakes</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>📶 Access Points</h2>
            <div class="ap-list" id="ap-list">
                <div class="loading">Loading...</div>
            </div>
        </div>
        
        <div class="card">
            <h2>🎯 Capture</h2>
            <div class="mode-selector">
                <button class="mode-btn active" data-mode="passive">Passive</button>
                <button class="mode-btn" data-mode="capture">Capture</button>
                <button class="mode-btn" data-mode="drop">Drop</button>
            </div>
            <div id="target-display">Target: None selected</div>
            <button class="btn btn-primary" id="btn-capture">Start Capture</button>
            <button class="btn btn-secondary" id="btn-deauth">Send Deauth</button>
        </div>
        
        <div class="card">
            <h2>⚙️ System</h2>
            <button class="btn btn-secondary" onclick="location.reload()">Refresh</button>
            <button class="btn btn-danger" id="btn-shutdown">Shutdown</button>
        </div>
    </div>
    
    <script>
        let selectedTarget = null;
        let currentMode = 'passive';
        
        async function fetchStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                
                document.getElementById('status-badge').textContent = data.state.toUpperCase();
                document.getElementById('ap-count').textContent = data.ap_count;
                document.getElementById('client-count').textContent = data.client_count;
                document.getElementById('probe-count').textContent = data.probe_count;
                document.getElementById('hs-count').textContent = data.handshake_count;
            } catch (e) {
                console.error('Status fetch error:', e);
            }
        }
        
        async function fetchAPs() {
            try {
                const res = await fetch('/api/aps');
                const aps = await res.json();
                
                const list = document.getElementById('ap-list');
                if (aps.length === 0) {
                    list.innerHTML = '<div class="loading">No access points found</div>';
                    return;
                }
                
                list.innerHTML = aps.map(ap => `
                    <div class="ap-item" data-bssid="${ap.bssid}" data-ssid="${ap.ssid}">
                        <div>
                            <div class="ap-ssid">${ap.ssid || '&lt;hidden&gt;'}</div>
                            <div class="ap-signal">CH${ap.channel} • ${ap.security} • ${ap.clients} clients</div>
                        </div>
                        <div class="ap-signal">${ap.signal_dbm}dBm</div>
                    </div>
                `).join('');
                
                // Add click handlers
                list.querySelectorAll('.ap-item').forEach(item => {
                    item.addEventListener('click', () => selectTarget(item.dataset.bssid, item.dataset.ssid));
                });
            } catch (e) {
                console.error('AP fetch error:', e);
            }
        }
        
        function selectTarget(bssid, ssid) {
            selectedTarget = { bssid, ssid };
            document.getElementById('target-display').textContent = `Target: ${ssid}`;
            
            // Highlight selected
            document.querySelectorAll('.ap-item').forEach(item => {
                item.style.background = item.dataset.bssid === bssid ? 'var(--bg-tertiary)' : '';
            });
        }
        
        async function setMode(mode) {
            try {
                await fetch('/api/mode', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ mode })
                });
                
                currentMode = mode;
                document.querySelectorAll('.mode-btn').forEach(btn => {
                    btn.classList.toggle('active', btn.dataset.mode === mode);
                });
            } catch (e) {
                console.error('Mode change error:', e);
            }
        }
        
        async function startCapture() {
            if (!selectedTarget) {
                alert('Please select a target first');
                return;
            }
            
            try {
                await fetch('/api/target', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(selectedTarget)
                });
                
                await fetch('/api/capture/start', { method: 'POST' });
                alert('Capture started!');
            } catch (e) {
                console.error('Capture error:', e);
            }
        }
        
        async function sendDeauth() {
            if (!selectedTarget) {
                alert('Please select a target first');
                return;
            }
            
            try {
                await fetch('/api/deauth', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(selectedTarget)
                });
                alert('Deauth sent!');
            } catch (e) {
                console.error('Deauth error:', e);
            }
        }
        
        async function shutdown() {
            if (confirm('Are you sure you want to shutdown?')) {
                await fetch('/api/shutdown', { method: 'POST' });
            }
        }
        
        // Event listeners
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', () => setMode(btn.dataset.mode));
        });
        
        document.getElementById('btn-capture').addEventListener('click', startCapture);
        document.getElementById('btn-deauth').addEventListener('click', sendDeauth);
        document.getElementById('btn-shutdown').addEventListener('click', shutdown);
        
        // Initial load
        fetchStatus();
        fetchAPs();
        
        // Auto-refresh
        setInterval(fetchStatus, 5000);
        setInterval(fetchAPs, 10000);
    </script>
</body>
</html>"""

