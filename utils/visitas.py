"""
Registro de visitas al demo.

El demo es de acceso libre (sin usuario ni clave) para que el cliente pueda
abrirlo de una. Aun así se deja constancia de cada visita —fecha, IP y ciudad
aproximada— para saber cuándo y desde dónde lo abrieron.

El panel con esas visitas no se muestra a nadie: solo aparece si se entra con
`?accesos=calybrat` en la URL.
"""
import datetime
import json
import urllib.request
from pathlib import Path

import streamlit as st

_LOG = Path(__file__).parent.parent / "visit_log.json"
CLAVE_PANEL = "calybrat"


def _ip() -> str:
    try:
        headers = st.context.headers
        for k in ("X-Forwarded-For", "x-forwarded-for", "X-Real-Ip", "x-real-ip"):
            v = headers.get(k, "")
            if v:
                return v.split(",")[0].strip()
    except Exception:
        pass
    try:
        with urllib.request.urlopen("https://api.ipify.org?format=json", timeout=3) as r:
            return json.loads(r.read()).get("ip", "desconocida")
    except Exception:
        return "desconocida"


def _ubicacion(ip: str) -> dict:
    if not ip or ip in ("desconocida", "127.0.0.1", "::1"):
        return {"ciudad": "local", "region": "—", "pais": "—"}
    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,country,city,regionName"
        with urllib.request.urlopen(url, timeout=3) as r:
            d = json.loads(r.read())
        if d.get("status") == "success":
            return {"ciudad": d.get("city", "—"), "region": d.get("regionName", "—"),
                    "pais": d.get("country", "—")}
    except Exception:
        pass
    return {"ciudad": "—", "region": "—", "pais": "—"}


def registrar_visita():
    """Deja constancia de la visita una sola vez por sesión."""
    if st.session_state.get("_visita_registrada"):
        return
    st.session_state["_visita_registrada"] = True
    try:
        ip = _ip()
        loc = _ubicacion(ip)
        registro = []
        if _LOG.exists():
            try:
                registro = json.loads(_LOG.read_text(encoding="utf-8"))
            except Exception:
                registro = []
        registro.append({
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "ip": ip, **loc,
        })
        _LOG.write_text(json.dumps(registro, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        # Nunca dejar que el registro rompa la experiencia del demo
        pass


def panel_solicitado() -> bool:
    try:
        return st.query_params.get("accesos") == CLAVE_PANEL
    except Exception:
        return False


def render_panel_visitas():
    import pandas as pd
    st.subheader("Registro de accesos al demo")
    if not _LOG.exists():
        st.info("Todavía no hay visitas registradas.")
        return
    try:
        registro = json.loads(_LOG.read_text(encoding="utf-8"))
    except Exception:
        st.warning("No se pudo leer el registro.")
        return
    if not registro:
        st.info("Todavía no hay visitas registradas.")
        return

    filas = []
    for e in registro[::-1]:
        ubic = ", ".join(x for x in (e.get("ciudad"), e.get("region"), e.get("pais"))
                         if x and x != "—") or "—"
        filas.append({"Fecha / Hora": e.get("timestamp", ""), "Ubicación": ubic,
                      "IP": e.get("ip", "—")})
    st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)
    st.caption(f"{len(registro)} visita(s) registrada(s). "
               "En Streamlit Cloud el registro se reinicia con cada despliegue.")
