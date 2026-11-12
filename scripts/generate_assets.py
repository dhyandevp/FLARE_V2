"""
Generate high-resolution visual assets and screenshots for FLARE V2 GitHub repository.
Uses headless Google Chrome to render pixel-perfect Retina (2x) PNG images.
"""
import os
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(HERE, "docs", "images")
os.makedirs(OUTPUT_DIR, exist_ok=True)

DASHBOARD_SRC = os.path.join(HERE, "4_Design", "dashboard.html")
with open(DASHBOARD_SRC, "r", encoding="utf-8") as f:
    dashboard_html = f.read()

def render_chrome(html_content, out_png, width=1200, height=860, scale=2):
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as tmp:
        tmp.write(html_content)
        tmp_path = tmp.name

    try:
        cmd = [
            "google-chrome",
            "--headless=new",
            "--disable-gpu",
            f"--force-device-scale-factor={scale}",
            f"--window-size={width},{height}",
            "--hide-scrollbars",
            f"--screenshot={out_png}",
            f"file://{tmp_path}"
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            print(f"Error rendering {out_png}: {res.stderr}")
        else:
            print(f"Generated: {os.path.basename(out_png)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

# Helper to inject synchronous simulation state into dashboard.html
def make_simulated_dashboard(state_type, is_mobile=False, active_tab="home"):
    html = dashboard_html
    if is_mobile:
        html = html.replace('<body data-tab="home">', f'<body data-tab="{active_tab}" style="margin:0 auto; max-width:412px;">')

    tab_code = f'setTab("{active_tab}");' if active_tab != "home" else ""

    sim_code = f"""
/* ---------- SYNCHRONOUS SIMULATION ({state_type}) ---------- */
var now = Date.now();
var sim_type = "{state_type}";

if (sim_type === "safe") {{
    st.water = 26; st.rain = 14; st.soil = 32; st.risk = 24;
    st.rssi = -58; st.up = 14420; st.ip = "192.168.4.1"; st.count = 42;
    levels = {{ water: "ok", rain: "ok", soil: "ok" }};
    connState = "live";
    alarm = {{ active: false, acked: false, manual: false }};
    alerts = [
        {{ k: "water", lvl: "ok", v: 26, m: "Water level is back to normal", t: now - 320000 }},
        {{ k: "soil", lvl: "ok", v: 32, m: "Soil moisture is back to normal", t: now - 680000 }}
    ];
    hist = [];
    for (var i = 29; i >= 0; i--) {{
        var w = Math.round(18 + 9 * Math.sin(i / 4));
        var r = Math.round(10 + 5 * Math.cos(i / 3));
        var s = Math.round(28 + 5 * Math.sin(i / 2));
        var rk = Math.round(w * 0.4 + s * 0.3 + r * 0.3);
        hist.push({{ t: now - i * 10000, water: w, rain: r, soil: s, risk: rk }});
    }}
}} else if (sim_type === "warning") {{
    st.water = 64; st.rain = 53; st.soil = 67; st.risk = 62;
    st.rssi = -62; st.up = 17200; st.ip = "192.168.4.1"; st.count = 89;
    levels = {{ water: "warn", rain: "warn", soil: "warn" }};
    connState = "live";
    alarm = {{ active: false, acked: false, manual: false }};
    alerts = [
        {{ k: "soil", lvl: "warn", v: 67, m: "Soil moisture is rising", t: now - 25000 }},
        {{ k: "rain", lvl: "warn", v: 53, m: "Rainfall is rising (rain starting)", t: now - 60000 }},
        {{ k: "water", lvl: "warn", v: 64, m: "Water level is rising toward alarm level", t: now - 95000 }}
    ];
    hist = [];
    for (var i = 29; i >= 0; i--) {{
        var p = (29 - i) / 29;
        var w = Math.round(28 + 36 * p);
        var r = Math.round(15 + 38 * p);
        var s = Math.round(35 + 32 * p);
        var rk = Math.round(w * 0.4 + s * 0.3 + r * 0.3);
        hist.push({{ t: now - i * 10000, water: w, rain: r, soil: s, risk: rk }});
    }}
}} else if (sim_type === "danger") {{
    st.water = 85; st.rain = 73; st.soil = 88; st.risk = 82;
    st.rssi = -59; st.up = 19800; st.ip = "192.168.4.1"; st.count = 145;
    levels = {{ water: "bad", rain: "bad", soil: "bad" }};
    connState = "live";
    alarm = {{ active: true, acked: false, manual: false }};
    alerts = [
        {{ k: "water", lvl: "bad", v: 85, m: "Water level went above the alarm level", t: now - 12000 }},
        {{ k: "soil", lvl: "bad", v: 88, m: "Soil moisture went above alarm level (landslide risk)", t: now - 28000 }},
        {{ k: "rain", lvl: "bad", v: 73, m: "Rainfall went above the alarm level (heavy rain)", t: now - 52000 }}
    ];
    hist = [];
    for (var i = 29; i >= 0; i--) {{
        var p = (29 - i) / 29;
        var w = Math.round(35 + 50 * p);
        var r = Math.round(20 + 53 * p);
        var s = Math.round(40 + 48 * p);
        var rk = Math.round(w * 0.4 + s * 0.3 + r * 0.3);
        hist.push({{ t: now - i * 10000, water: w, rain: r, soil: s, risk: rk }});
    }}
}}

lastMsgAt = now - 1000;
setConn("live", "Connected · " + st.ip);
$("ipIn").value = st.ip;
renderAlerts();
render();
drawChart();
{tab_code}
setTxt("upd", fmtTime(lastMsgAt, true) + " · just now");
if (sim_type === "danger") {{
    $("sos").classList.add("show");
}}
"""
    target = '/* ---------- start ---------- */\nrenderAlerts();render();drawChart();\nfunction needConnect(){setConn("off","Not connected");if(isPhone())setTab("device")}\nif(APP){\n  var saved="";try{saved=window.Android.savedIp()||""}catch(e){}\n  $("ipIn").value=saved;if(!saved)needConnect();\n}else if(/^https?:$/.test(location.protocol)&&location.hostname){\n  connectWeb(location.hostname);\n}else{\n  var last=load("flare-ip","");if(last)connectWeb(last);else needConnect();\n}'
    if target in html:
        html = html.replace(target, sim_code)
    else:
        html = html.replace('/* ---------- start ---------- */', sim_code + '/* ---------- original start disabled ---------- */\nif(false)')
    return html

# 1. Safe State Dashboard (Full page)
render_chrome(make_simulated_dashboard("safe"), os.path.join(OUTPUT_DIR, "dashboard-safe.png"), width=1200, height=1380)

# 2. Warning State Dashboard (Full page)
render_chrome(make_simulated_dashboard("warning"), os.path.join(OUTPUT_DIR, "dashboard-warning.png"), width=1200, height=1440)

# 3. Danger SOS State Dashboard (Full page)
render_chrome(make_simulated_dashboard("danger"), os.path.join(OUTPUT_DIR, "dashboard-danger.png"), width=1200, height=1440)

# 4. Mobile App Mockup (single frame)
render_chrome(make_simulated_dashboard("warning", is_mobile=True), os.path.join(OUTPUT_DIR, "mobile-app-mockup.png"), width=412, height=915)

# 4b. Triple-Device Mobile Showcase (Home, Danger Alarm, History)
triple_showcase_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@600;700;800&family=JetBrains+Mono:wght@500&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    width: 1200px;
    height: 840px;
    background: #140704;
    color: #FCF7F0;
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
    padding: 36px 48px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    overflow: hidden;
  }}
  .top-title {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    border-bottom: 1px solid rgba(252,247,240,0.12);
    padding-bottom: 14px;
  }}
  .top-title h2 {{ font-size: 22px; font-weight: 700; }}
  .top-title span {{ font-family: 'JetBrains Mono', monospace; font-size: 12.5px; color: #FF8F26; }}
  .devices-row {{
    display: flex;
    justify-content: center;
    align-items: flex-start;
    gap: 36px;
    margin: auto 0;
  }}
  .device-col {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 14px;
  }}
  .phone-card {{
    width: 325px;
    height: 650px;
    background: #000;
    border-radius: 44px;
    padding: 10px;
    box-shadow: 0 25px 60px rgba(0,0,0,0.85), 0 0 0 1px rgba(255,255,255,0.14);
    position: relative;
    overflow: hidden;
  }}
  .phone-label {{
    font-size: 12.5px;
    color: #E6D5C7;
    background: rgba(252,247,240,0.06);
    padding: 6px 16px;
    border-radius: 999px;
    border: 1px solid rgba(252,247,240,0.12);
    font-weight: 600;
  }}
  .phone-label.danger {{
    background: rgba(229, 72, 77, 0.2);
    border-color: rgba(229, 72, 77, 0.6);
    color: #FF888C;
  }}
  .screen {{
    width: 100%;
    height: 100%;
    border-radius: 34px;
    overflow: hidden;
    background: #22100B;
  }}
  iframe {{
    width: 100%;
    height: 100%;
    border: 0;
  }}
</style>
</head>
<body>
  <div class="top-title">
    <h2>FLARE V2 — Android Native Companion App</h2>
    <span>WebView + OkHttp WebSocket + Native Audio/Vibration Hardware Driver</span>
  </div>
  <div class="devices-row">
    <div class="device-col">
      <div class="phone-card">
        <div class="screen"><iframe srcdoc="{make_simulated_dashboard("safe", is_mobile=True, active_tab="home").replace('&', '&amp;').replace('"', '&quot;')}"></iframe></div>
      </div>
      <div class="phone-label">Home · Nominal Status</div>
    </div>
    <div class="device-col">
      <div class="phone-card" style="box-shadow: 0 35px 80px rgba(229,72,77,0.35), 0 0 0 2px #E5484D;">
        <div class="screen"><iframe srcdoc="{make_simulated_dashboard("danger", is_mobile=True, active_tab="home").replace('&', '&amp;').replace('"', '&quot;')}"></iframe></div>
      </div>
      <div class="phone-label danger">Critical SOS Alarm Active</div>
    </div>
    <div class="device-col">
      <div class="phone-card">
        <div class="screen"><iframe srcdoc="{make_simulated_dashboard("warning", is_mobile=True, active_tab="history").replace('&', '&amp;').replace('"', '&quot;')}"></iframe></div>
      </div>
      <div class="phone-label">History · 5-Min Telemetry</div>
    </div>
  </div>
</body>
</html>
"""
render_chrome(triple_showcase_html, os.path.join(OUTPUT_DIR, "mobile-showcase.png"), width=1200, height=840)




# 5. Hero Banner
hero_banner_html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    width: 1200px;
    height: 480px;
    background: #180905;
    background-image:
      radial-gradient(ellipse at 80% 20%, rgba(255, 122, 0, 0.18) 0%, transparent 60%),
      radial-gradient(ellipse at 20% 90%, rgba(229, 72, 77, 0.14) 0%, transparent 50%),
      linear-gradient(180deg, #1A0A06 0%, #110503 100%);
    color: #FCF7F0;
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
    padding: 56px 64px;
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }
  .grid-pattern {
    position: absolute;
    inset: 0;
    background-size: 32px 32px;
    background-image:
      linear-gradient(to right, rgba(252, 247, 240, 0.03) 1px, transparent 1px),
      linear-gradient(to bottom, rgba(252, 247, 240, 0.03) 1px, transparent 1px);
    pointer-events: none;
  }
  .header {
    display: flex;
    align-items: center;
    gap: 16px;
    z-index: 2;
  }
  .logo-box {
    width: 52px;
    height: 52px;
    border-radius: 16px;
    background: #FCF7F0;
    display: grid;
    place-items: center;
    box-shadow: 0 10px 30px rgba(255, 122, 0, 0.35);
  }
  .logo-box svg {
    width: 28px;
    height: 28px;
  }
  .badge-tag {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    letter-spacing: 0.06em;
    padding: 6px 14px;
    border-radius: 999px;
    background: rgba(255, 122, 0, 0.15);
    border: 1px solid rgba(255, 122, 0, 0.4);
    color: #FF8F26;
    font-weight: 600;
  }
  .main-content {
    z-index: 2;
  }
  h1 {
    font-size: 52px;
    font-weight: 800;
    letter-spacing: -0.03em;
    line-height: 1.08;
    background: linear-gradient(135deg, #FCF7F0 40%, #F8DEC0 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .tagline {
    font-size: 19px;
    color: #D3BEB0;
    margin-top: 14px;
    max-width: 820px;
    line-height: 1.5;
    font-weight: 400;
  }
  .footer-row {
    display: flex;
    align-items: center;
    gap: 12px;
    z-index: 2;
  }
  .feature-pill {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(252, 247, 240, 0.06);
    border: 1px solid rgba(252, 247, 240, 0.12);
    border-radius: 12px;
    padding: 8px 16px;
    font-size: 13.5px;
    color: #E6D5C7;
    font-weight: 500;
    backdrop-filter: blur(10px);
  }
  .feature-pill span {
    color: #3E9B57;
    font-size: 15px;
  }
</style>
</head>
<body>
  <div class="grid-pattern"></div>
  <div class="header">
    <div class="logo-box">
      <svg viewBox="0 0 16 16"><path d="M8 1.5S3.8 6 3.8 9a4.2 4.2 0 0 0 8.4 0C12.2 6 8 1.5 8 1.5z" fill="#FF7A00"/></svg>
    </div>
    <div class="badge-tag">FLARE V2 · OFFLINE-FIRST IOT</div>
  </div>
  <div class="main-content">
    <h1>Flood &amp; Landslide Early Warning System</h1>
    <p class="tagline">Decentralized, zero-cloud disaster telemetry on ESP32. Sub-second WebSocket broadcasts, multi-sensor risk score fusion, live browser dashboard &amp; native Android alert siren.</p>
  </div>
  <div class="footer-row">
    <div class="feature-pill"><span>●</span> ESP32 Edge Node</div>
    <div class="feature-pill"><span>●</span> WebSockets &amp; mDNS</div>
    <div class="feature-pill"><span>●</span> 100% Local Wi-Fi</div>
    <div class="feature-pill"><span>●</span> Dual-Alert Engine</div>
    <div class="feature-pill"><span>●</span> Android Native App</div>
  </div>
</body>
</html>
"""
render_chrome(hero_banner_html, os.path.join(OUTPUT_DIR, "hero-banner.png"), width=1200, height=480)

# 6. System Architecture Diagram
arch_html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    width: 1200px;
    height: 700px;
    background: #190B06;
    color: #FCF7F0;
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
    padding: 48px 56px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }
  .title-bar {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    border-bottom: 1px solid rgba(252,247,240,0.12);
    padding-bottom: 20px;
  }
  .title-bar h2 {
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -0.02em;
  }
  .title-bar span {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: #FF8F26;
  }
  .flow-container {
    display: grid;
    grid-template-columns: 280px 60px 420px 60px 280px;
    align-items: center;
    margin: auto 0;
  }
  .arrow {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #FF8F26;
    font-size: 22px;
  }
  .arrow-label {
    font-size: 11px;
    color: #B29684;
    margin-top: 4px;
    font-family: 'JetBrains Mono', monospace;
  }
  .column-box {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .card {
    background: #25120C;
    border: 1px solid rgba(252,247,240,0.15);
    border-radius: 16px;
    padding: 18px 20px;
    position: relative;
  }
  .card.highlight {
    background: #2C160F;
    border-color: rgba(255,122,0,0.45);
    box-shadow: 0 12px 35px rgba(255,122,0,0.12);
  }
  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }
  .card-title {
    font-size: 15.5px;
    font-weight: 700;
    color: #FCF7F0;
  }
  .pin-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    background: rgba(255,122,0,0.18);
    color: #FF8F26;
    padding: 3px 8px;
    border-radius: 6px;
    font-weight: 600;
  }
  .card-desc {
    font-size: 12.5px;
    color: #B9A190;
    line-height: 1.45;
  }
  .formula-box {
    background: #1C0C07;
    border: 1px dashed rgba(255,122,0,0.3);
    border-radius: 10px;
    padding: 10px 14px;
    margin-top: 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #FFB366;
  }
  .footer-note {
    font-size: 13px;
    color: #8C7364;
    text-align: center;
    border-top: 1px solid rgba(252,247,240,0.1);
    padding-top: 16px;
  }
</style>
</head>
<body>
  <div class="title-bar">
    <h2>FLARE V2 — System Architecture &amp; Data Pipeline</h2>
    <span>Zero Cloud Dependency · Real-Time WebSockets</span>
  </div>

  <div class="flow-container">
    <div class="column-box">
      <div class="card">
        <div class="card-header">
          <span class="card-title">HC-SR04 Ultrasonic</span>
          <span class="pin-badge">GPIO 5/18</span>
        </div>
        <p class="card-desc">Measures water channel depth via echo time-of-flight. Converted to 0–100% capacity.</p>
      </div>
      <div class="card">
        <div class="card-header">
          <span class="card-title">Precipitation Sensor</span>
          <span class="pin-badge">ADC 34</span>
        </div>
        <p class="card-desc">Analog rain intensity gauge with 10-sample moving average noise filter.</p>
      </div>
      <div class="card">
        <div class="card-header">
          <span class="card-title">Soil Moisture Sensor</span>
          <span class="pin-badge">ADC 35</span>
        </div>
        <p class="card-desc">Detects slope ground saturation to predict landslide and liquefaction danger.</p>
      </div>
    </div>

    <div class="arrow">➔<div class="arrow-label">GPIO/ADC</div></div>

    <div class="column-box">
      <div class="card highlight">
        <div class="card-header">
          <span class="card-title">ESP32 Dev Module (Edge)</span>
          <span class="pin-badge">240 MHz Dual-Core</span>
        </div>
        <p class="card-desc">Runs autonomously without external dependencies or cloud connectivity.</p>
        <div class="formula-box">
          Risk = (Water × 40%) + (Soil × 30%) + (Rain × 30%)
        </div>
        <div style="margin-top:12px; display:flex; flex-direction:column; gap:8px;">
          <div style="font-size:12px; color:#EADBC8;">• <b>WebServer (Port 80):</b> Serves PROGMEM dashboard HTML</div>
          <div style="font-size:12px; color:#EADBC8;">• <b>WebSocket (Port 81):</b> Broadcasts telemetry every 2s</div>
          <div style="font-size:12px; color:#EADBC8;">• <b>History Ring Buffer:</b> 30 samples (5-min rolling history)</div>
          <div style="font-size:12px; color:#EADBC8;">• <b>mDNS Daemon:</b> Resolves <code>flare.local</code> on LAN</div>
        </div>
      </div>
    </div>

    <div class="arrow">➔<div class="arrow-label">WS :81</div></div>

    <div class="column-box">
      <div class="card">
        <div class="card-header">
          <span class="card-title">Web Dashboard</span>
          <span class="pin-badge">Port 80 / mDNS</span>
        </div>
        <p class="card-desc">Zero-install browser app. Live gauges, interactive history charts, and Web Audio siren beep.</p>
      </div>
      <div class="card">
        <div class="card-header">
          <span class="card-title">Android Native App</span>
          <span class="pin-badge">Kotlin + WebView</span>
        </div>
        <p class="card-desc">Hardware ToneGenerator alarm, vibration motor pulse, and heads-up emergency notification.</p>
      </div>
    </div>
  </div>

  <div class="footer-note">
    Both Web and Android clients use identical shared UI compiled from <code>4_Design/dashboard.html</code> via <code>update_design.py</code>
  </div>
</body>
</html>
"""
render_chrome(arch_html, os.path.join(OUTPUT_DIR, "system-architecture.png"), width=1200, height=700)

# 7. Hardware Wiring & Pinout Diagram
pinout_html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    width: 1200px;
    height: 680px;
    background: #180905;
    color: #FCF7F0;
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
    padding: 44px 54px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }
  .title-bar {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    border-bottom: 1px solid rgba(252,247,240,0.12);
    padding-bottom: 16px;
  }
  .title-bar h2 { font-size: 24px; font-weight: 700; }
  .title-bar span { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #3E9B57; }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 24px 0;
    font-size: 14.5px;
  }
  th {
    background: #28140D;
    color: #FF8F26;
    text-align: left;
    padding: 14px 18px;
    font-weight: 700;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 2px solid rgba(255,122,0,0.3);
  }
  td {
    padding: 14px 18px;
    border-bottom: 1px solid rgba(252,247,240,0.08);
    color: #E6D5C7;
  }
  tr:hover td { background: rgba(255,122,0,0.05); }
  .pin {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    color: #FFB366;
    background: rgba(255,122,0,0.15);
    padding: 4px 8px;
    border-radius: 6px;
    display: inline-block;
  }
  .volt {
    font-family: 'JetBrains Mono', monospace;
    color: #55C37A;
    font-weight: 600;
  }
  .badge-sensor {
    font-weight: 600;
    color: #FCF7F0;
  }
  .info-cards {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
  }
  .info-box {
    background: #24110A;
    border: 1px solid rgba(252,247,240,0.1);
    border-radius: 12px;
    padding: 14px 18px;
  }
  .info-box h4 {
    font-size: 13px;
    text-transform: uppercase;
    color: #B29684;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
  }
  .info-box p {
    font-size: 13px;
    color: #EADBC8;
    line-height: 1.4;
  }
</style>
</head>
<body>
  <div class="title-bar">
    <h2>FLARE V2 — Hardware Wiring &amp; Pinout Specification</h2>
    <span>ESP32 38-Pin / 30-Pin NodeMCU Compatible</span>
  </div>

  <table>
    <thead>
      <tr>
        <th>Sensor / Peripheral</th>
        <th>Sensor Pin</th>
        <th>ESP32 GPIO Pin</th>
        <th>Operating Voltage</th>
        <th>Function / Notes</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><span class="badge-sensor">HC-SR04 Ultrasonic</span></td>
        <td>TRIG</td>
        <td><span class="pin">GPIO 5</span></td>
        <td><span class="volt">5.0V VCC</span></td>
        <td>10 µs trigger pulse initiates ultrasonic ping</td>
      </tr>
      <tr>
        <td><span class="badge-sensor">HC-SR04 Ultrasonic</span></td>
        <td>ECHO</td>
        <td><span class="pin">GPIO 18</span></td>
        <td><span class="volt">3.3V Safe</span></td>
        <td>Echo duration pulse (use voltage divider if 5V echo)</td>
      </tr>
      <tr>
        <td><span class="badge-sensor">Raindrop Sensor</span></td>
        <td>A0 (Analog Out)</td>
        <td><span class="pin">GPIO 34</span></td>
        <td><span class="volt">3.3V VCC</span></td>
        <td>ADC1 Channel 6 (dry: ~3500 raw, wet: ~1200 raw)</td>
      </tr>
      <tr>
        <td><span class="badge-sensor">Soil Moisture Sensor</span></td>
        <td>A0 (Analog Out)</td>
        <td><span class="pin">GPIO 35</span></td>
        <td><span class="volt">3.3V VCC</span></td>
        <td>ADC1 Channel 7 (dry: ~3000 raw, saturated: ~1400 raw)</td>
      </tr>
      <tr>
        <td><span class="badge-sensor">Power Distribution</span></td>
        <td>GND (All sensors)</td>
        <td><span class="pin">GND</span></td>
        <td><span class="volt">0V Common</span></td>
        <td>Shared common ground bus</td>
      </tr>
    </tbody>
  </table>

  <div class="info-cards">
    <div class="info-box">
      <h4>ADC Pin Selection</h4>
      <p>GPIO 34 and 35 belong to ADC1. They work simultaneously while Wi-Fi is active (ADC2 is reserved for Wi-Fi radio).</p>
    </div>
    <div class="info-box">
      <h4>Water Calibration</h4>
      <p><code>SENSOR_HEIGHT_CM = 20.0</code> sets reference distance. Water percent: <code>(20.0 - distance) / 20.0 × 100%</code>.</p>
    </div>
    <div class="info-box">
      <h4>Multi-Client Scalability</h4>
      <p>ESP32 dual-core handles simultaneous WebSocket broadcast to multiple mobile phones and laptops with sub-second latency.</p>
    </div>
  </div>
</body>
</html>
"""
render_chrome(pinout_html, os.path.join(OUTPUT_DIR, "hardware-pinout.png"), width=1200, height=680)

print("\nAll visual assets successfully generated in docs/images/")
