import csv
import json
import http.server
import socketserver
import webbrowser
import base64
from pathlib import Path

def run_visualizer():
    csv_file = 'data.csv'
    base_path = Path.cwd()
    sets_data = {}

    print("Encoding images into a single file... please wait.")

    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)
            set_counters = {}
            for row in reader:
                if len(row) < 4: continue
                name = row[0].strip()
                if name not in sets_data:
                    sets_data[name] = []
                    set_counters[name] = 1
                
                # PATH TO IMAGE
                img_path = base_path / name / f"{name} — {set_counters[name]}.png"
                
                # Convert Image to Base64 string
                img_base64 = ""
                if img_path.exists():
                    with open(img_path, "rb") as img_f:
                        encoded_string = base64.b64encode(img_f.read()).decode('utf-8')
                        img_base64 = f"data:image/png;base64,{encoded_string}"
                else:
                    print(f"⚠️ Warning: Image not found: {img_path}")
                
                sets_data[name].append({
                    "src": img_base64, # Now contains the actual image data
                    "url": row[1].strip(),
                    "a": float(row[2]), 
                    "b": float(row[3])
                })
                set_counters[name] += 1
    except Exception as e:
        print(f"Error reading CSV or images: {e}")
        return

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>IRT Analysis - Portable Edition</title>
        <style>
            * { box-sizing: border-box; }
            :root {
                --bg-grey: #2c2c2c;
                --stage-grey: #353535;
                --pastel-mint: #b2d8b2;
                --text-muted: #d1d1d1;
                --border-dim: #4a4a4a;
            }
            body { background: var(--bg-grey); color: var(--pastel-mint); font-family: 'Segoe UI', sans-serif; margin: 0; display: flex; width: 100vw; height: 100vh; overflow: hidden; }
            #sidebar { width: 280px; background: #222; border-right: 1px solid var(--border-dim); overflow-y: auto; padding: 20px; height: 100%; z-index: 100; flex-shrink: 0; }
            h3 { color: var(--pastel-mint); text-transform: uppercase; letter-spacing: 2px; font-size: 12px; border-bottom: 1px solid var(--border-dim); padding-bottom: 10px; margin-top: 0; }
            #searchBar { width: 100%; background: #2c2c2c; border: 1px solid var(--border-dim); color: var(--pastel-mint); padding: 8px; margin-bottom: 15px; outline: none; border-radius: 4px; }
            .set-link { display: block; padding: 12px; color: #999; text-decoration: none; cursor: pointer; border-bottom: 1px solid #2a2a2a; font-size: 13px; }
            .set-link:hover { background: #333; color: var(--pastel-mint); }
            .set-link.active { background: var(--pastel-mint); color: #222; font-weight: bold; border-radius: 4px; }
            .controls { margin: 10px 0 20px 0; display: flex; flex-direction: column; gap: 10px; }
            .zoom-label { font-size: 11px; display: flex; justify-content: space-between; opacity: 0.8; }
            #zoomSlider { width: 100%; cursor: pointer; accent-color: var(--pastel-mint); }
            .btn { background: #333; color: var(--pastel-mint); border: 1px solid var(--pastel-mint); padding: 8px; cursor: pointer; font-size: 11px; text-align: center; border-radius: 4px; }
            .btn:hover { background: var(--pastel-mint); color: #222; }
            #viewport { flex-grow: 1; height: 100%; overflow: auto; background: var(--bg-grey); position: relative; }
            #stage { position: relative; width: 500vw; height: 500vh; background: var(--stage-grey); transform-origin: 0 0; }
            #canvas-container { position: absolute; top: 100vh; left: 100vw; width: 300vw; height: 300vh; }
            #canvas { width: 100%; height: 100%; position: absolute; top: 0; left: 0; }
            .axis { position: absolute; background: var(--pastel-mint); opacity: 0.45; z-index: 1; pointer-events: none; }
            .axis-title { position: absolute; color: var(--pastel-mint); font-size: 14px; font-weight: bold; text-transform: uppercase; z-index: 5; opacity: 1; pointer-events: none; background: #222; padding: 5px 12px; border-radius: 20px; border: 1px solid var(--border-dim); }
            .quadrant-label { position: absolute; color: rgba(178, 216, 178, 0.25); font-size: 28px; font-weight: 900; text-transform: uppercase; pointer-events: none; text-align: center; width: 1000px; display: flex; align-items: center; justify-content: center; z-index: 0; }
            .item-link { position: absolute; text-decoration: none; z-index: 10; transition: transform 0.1s ease-out; display: block; }
            .item { width: 180px; border: 1px solid var(--border-dim); background: #222; border-radius: 4px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.4); }
            .item-link:hover { transform: scale(2.8); z-index: 9999 !important; }
            .item-link:hover .item { border-color: var(--pastel-mint); box-shadow: 0 15px 50px rgba(0,0,0,0.6); }
            .item img { width: 100%; display: block; opacity: 0.85; transition: 0.2s; }
            .item-link:hover img { opacity: 1; }
            .info { font-size: 10px; text-align: center; color: var(--text-muted); background: #1a1a1a; padding: 8px; border-top: 1px solid var(--border-dim); }
            #viewport::-webkit-scrollbar { width: 14px; height: 14px; }
            #viewport::-webkit-scrollbar-track { background: var(--bg-grey); }
            #viewport::-webkit-scrollbar-thumb { background: #4a4a4a; border-radius: 7px; border: 3px solid var(--bg-grey); }
            #viewport::-webkit-scrollbar-thumb:hover { background: var(--pastel-mint); }
        </style>
    </head>
    <body>
        <div id="sidebar">
            <h3>IRT Dataset Explorer</h3>
            <input type="text" id="searchBar" placeholder="Search sets..." onkeyup="filterMenu()">
            <div class="controls">
                <div class="zoom-label"><span>Zoom Level</span><span id="zoomVal">100%</span></div>
                <input type="range" id="zoomSlider" min="0.1" max="1.5" step="0.01" value="1" oninput="handleZoom(this.value)">
                <div class="btn" onclick="centerView()">Recenter Intersect</div>
            </div>
            <div id="menu"></div>
        </div>
        <div id="viewport">
            <div id="stage">
                <div id="canvas-container">
                    <div id="label-ul" class="quadrant-label">Low Discrimination / High Difficulty</div>
                    <div id="label-ur" class="quadrant-label">High Discrimination / High Difficulty</div>
                    <div id="label-ll" class="quadrant-label">Low Discrimination / Low Difficulty</div>
                    <div id="label-lr" class="quadrant-label">High Discrimination / Low Difficulty</div>
                    <div id="y-axis" class="axis" style="width:2px; height:100%;"></div>
                    <div id="x-axis" class="axis" style="height:2px; width:100%;"></div>
                    <div id="y-title" class="axis-title" style="top: 100px; transform: translateX(-50%); white-space: nowrap;">Difficulty (b = 0.00)</div>
                    <div id="x-title" class="axis-title" style="right: 100px; transform: translateY(-50%); white-space: nowrap;">Discrimination (a = 1.00)</div>
                    <div id="canvas"></div>
                </div>
            </div>
        </div>
        <script>
            const allData = {DATA_JSON};
            const canvas = document.getElementById('canvas');
            const viewport = document.getElementById('viewport');
            const stage = document.getElementById('stage');
            const zoomVal = document.getElementById('zoomVal');
            let currentSet = null;
            let currentZoom = 1;

            function handleZoom(val) {
                const newZoom = parseFloat(val);
                const centerX = (viewport.scrollLeft + viewport.clientWidth / 2) / currentZoom;
                const centerY = (viewport.scrollTop + viewport.clientHeight / 2) / currentZoom;
                currentZoom = newZoom;
                zoomVal.innerText = Math.round(currentZoom * 100) + "%";
                stage.style.transform = `scale(${currentZoom})`;
                viewport.scrollLeft = (centerX * currentZoom) - (viewport.clientWidth / 2);
                viewport.scrollTop = (centerY * currentZoom) - (viewport.clientHeight / 2);
            }

            function centerView() {
                const w = canvas.offsetWidth;
                const h = canvas.offsetHeight;
                const aMax = 4.0;
                const xIntGlobal = ((1.0 / aMax) * w) + window.innerWidth; 
                const yIntGlobal = (h / 2) + window.innerHeight;
                viewport.scrollLeft = (xIntGlobal * currentZoom) - (viewport.clientWidth / 2);
                viewport.scrollTop = (yIntGlobal * currentZoom) - (viewport.clientHeight / 2);
            }

            function filterMenu() {
                const input = document.getElementById('searchBar').value.toLowerCase();
                document.querySelectorAll('.set-link').forEach(link => {
                    link.style.display = link.innerText.toLowerCase().includes(input) ? '' : 'none';
                });
            }

            function render() {
                if (!currentSet) return;
                canvas.innerHTML = '';
                const w = canvas.offsetWidth, h = canvas.offsetHeight;
                const aMax = 4.0, bRange = 8.0;
                const xInt = (1.0 / aMax) * w, yInt = h / 2;

                document.getElementById('y-axis').style.left = xInt + 'px';
                document.getElementById('x-axis').style.top = yInt + 'px';
                document.getElementById('y-title').style.left = xInt + 'px';
                document.getElementById('x-title').style.top = yInt + 'px';

                document.getElementById('label-ul').style.left = (xInt / 2 - 500) + 'px';
                document.getElementById('label-ul').style.top = (yInt / 2) + 'px';
                document.getElementById('label-ur').style.left = (xInt + (w - xInt)/2 - 500) + 'px';
                document.getElementById('label-ur').style.top = (yInt / 2) + 'px';
                document.getElementById('label-ll').style.left = (xInt / 2 - 500) + 'px';
                document.getElementById('label-ll').style.top = (yInt + (h - yInt)/2) + 'px';
                document.getElementById('label-lr').style.left = (xInt + (w - xInt)/2 - 500) + 'px';
                document.getElementById('label-lr').style.top = (yInt + (h - yInt)/2) + 'px';

                allData[currentSet].forEach((d, i) => {
                    const link = document.createElement('a');
                    link.className = 'item-link';
                    link.href = d.url;
                    link.target = '_blank';
                    let xBase = (d.a / aMax) * w;
                    let yBase = h - (((d.b + 4) / bRange) * h);
                    const stagger = 18;
                    link.style.left = (xBase - 90 + ((i % 8) * stagger)) + 'px';
                    link.style.top = (yBase - 65 + ((Math.floor(i / 8) % 5) * stagger)) + 'px';
                    link.style.zIndex = 10 + i;
                    link.innerHTML = `
                        <div class="item">
                            <img src="${d.src}">
                            <div class="info">a: ` + d.a.toFixed(2) + ` | b: ` + d.b.toFixed(2) + `</div>
                        </div>`;
                    canvas.appendChild(link);
                });
                centerView();
            }

            const menu = document.getElementById('menu');
            Object.keys(allData).forEach(name => {
                const lnk = document.createElement('a');
                lnk.className = 'set-link';
                lnk.innerText = name;
                lnk.onclick = () => {
                    document.querySelectorAll('.set-link').forEach(l => l.classList.remove('active'));
                    lnk.classList.add('active');
                    currentSet = name;
                    render();
                };
                menu.appendChild(lnk);
            });
            window.addEventListener('resize', centerView);
            window.onload = () => { setTimeout(() => { if(menu.firstChild) menu.firstChild.click(); }, 100); };
        </script>
    </body>
    </html>
    """.replace("{DATA_JSON}", json.dumps(sets_data))

    with open("irt_visualizer_portable.html", "w") as f:
        f.write(html_content)

    print(f"✅ Success! Created 'irt_visualizer_portable.html' ({len(html_content)/1024/1024:.2f} MB)")
    webbrowser.open(f"file://{base_path}/irt_visualizer_portable.html")

if __name__ == "__main__":
    run_visualizer()