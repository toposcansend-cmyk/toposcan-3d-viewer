"""Envia notificacao por email com link grande + QR code para abrir no celular."""
import json, urllib.request, ssl, urllib.parse

WEBHOOK = "https://script.google.com/macros/s/AKfycbz_EE5M_grgoMdkjs7OJHHlDPSQB8qH-oJ4T6Pqg-0qDZYWq1qTZv_sZeJ6mXU-5-Gt3A/exec"
SECRET = "toposcan-agent-2026"
TO = "toposcan.send@gmail.com"
SITE_URL = "https://toposcansend-cmyk.github.io/toposcan-3d-viewer/"
REPO_URL = "https://github.com/toposcansend-cmyk/toposcan-3d-viewer"

# QR code gerado por URL publica (qrserver.com) - Gmail carrega imagens HTTPS normais
qr_url = "https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=" + urllib.parse.quote(SITE_URL) + "&color=2670a8&bgcolor=ffffff&margin=10"

html = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#f0f4f8;font-family:-apple-system,Segoe UI,Roboto,sans-serif;">
<div style="max-width:520px;margin:0 auto;padding:20px;">

  <div style="background:linear-gradient(135deg,#0d2b40 0%,#1a4a72 50%,#2670a8 100%);color:white;padding:24px;border-radius:14px;text-align:center;margin-bottom:18px;box-shadow:0 8px 24px rgba(13,43,64,0.25);">
    <div style="font-size:11px;letter-spacing:3px;opacity:0.85;margin-bottom:6px;">TOPOSCAN</div>
    <h1 style="margin:0;font-size:24px;font-weight:700;">Visualizador 3D ONLINE</h1>
    <div style="font-size:13px;opacity:0.92;margin-top:8px;">Torre Radar Banda C · SIMEPAR</div>
  </div>

  <div style="background:white;border-radius:14px;padding:24px;text-align:center;box-shadow:0 4px 16px rgba(0,0,0,0.06);margin-bottom:14px;">
    <div style="color:#5a6878;font-size:13px;margin-bottom:14px;">Toque para abrir no celular:</div>
    <a href="{SITE_URL}" style="display:inline-block;background:#2670a8;color:white;padding:16px 32px;border-radius:10px;text-decoration:none;font-weight:700;font-size:15px;box-shadow:0 4px 12px rgba(38,112,168,0.3);">
      🌐 Abrir Visualizador 3D
    </a>
    <div style="margin-top:18px;font-size:11px;color:#8898a8;word-break:break-all;font-family:monospace;">
      {SITE_URL}
    </div>
  </div>

  <div style="background:white;border-radius:14px;padding:24px;text-align:center;box-shadow:0 4px 16px rgba(0,0,0,0.06);margin-bottom:14px;">
    <div style="color:#5a6878;font-size:13px;margin-bottom:14px;font-weight:600;">📱 Ou escaneie com a câmera</div>
    <img src="{qr_url}" alt="QR code" style="max-width:280px;width:100%;height:auto;border-radius:8px;border:1px solid #e0e8f0;"/>
    <div style="margin-top:12px;color:#8898a8;font-size:11px;">Abra a câmera do celular e aponte para o QR</div>
  </div>

  <div style="background:#fff8e8;border-radius:10px;padding:16px;border-left:4px solid #f0a050;margin-bottom:14px;font-size:13px;color:#5a4830;line-height:1.5;">
    <b>O que voce vai ver:</b><br>
    • Torre Radar 3D interativa (girar, zoom, vistas)<br>
    • Logo TopoScan branco oficial no header<br>
    • 401 peças do modelo com dimensões EXATAS do PDF<br>
    • Toggle: "Só Torre" ou "Com Terreno"<br>
    • Dimensões, componentes, downloads, atalhos<br>
    • Funciona perfeito em mobile (touch para girar)
  </div>

  <div style="background:white;border-radius:10px;padding:16px;font-size:12px;color:#5a6878;line-height:1.6;">
    <div style="font-size:11px;color:#8898a8;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">REPO GITHUB</div>
    <a href="{REPO_URL}" style="color:#2670a8;text-decoration:none;word-break:break-all;font-family:monospace;font-size:11px;">
      {REPO_URL}
    </a>
  </div>

  <div style="text-align:center;font-size:10px;color:#a0aebc;padding:14px;letter-spacing:1px;">
    TOPOSCAN · TORRE RADAR BANDA C · SIMEPAR
  </div>

</div>
</body></html>"""

# Validar tamanho
size = len(html.encode('utf-8'))
print(f"HTML size: {size/1024:.0f} KB")

payload = {
    "secret": SECRET, "action": "sendEmail", "to": TO,
    "subject": "📱 TopoScan Visualizador 3D ONLINE - clique para abrir no celular",
    "htmlBody": html,
    "body": f"Visualizador 3D online! Abra: {SITE_URL}"
}
req = urllib.request.Request(WEBHOOK, data=json.dumps(payload).encode('utf-8'),
                             headers={"Content-Type": "text/plain"})
try:
    resp = urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=60)
    body = resp.read().decode("utf-8")
    print(f"Status: {resp.status}")
    print(f"Response: {body[:300]}")
except Exception as e:
    print(f"ERRO: {e}")
