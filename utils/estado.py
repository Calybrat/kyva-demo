"""Estado que sobrevive al refresco: decisiones, compromisos y asignaciones.

Nace de una objeción concreta de la revisión adversaria:

    «Hoy tiene un botón que dice "Decidir" y le voy a decir qué hace: guarda en
    la memoria de mi navegador. Refresco la página y se borró. Eso no es un
    sistema de gerencia, eso es una demo.»

Tenía razón. `st.session_state` vive lo que vive la pestaña. Una decisión de
gerencia tiene que seguir ahí el lunes siguiente, con quién la tomó, cuándo, y
—esto es lo que casi nadie hace— **qué pasó después**. Sin ese cierre de ciclo
el sistema nunca aprende y nadie sabe si las decisiones sirvieron.

El archivo vive FUERA del árbol del repositorio a propósito: escribirlo dentro
hace que el vigilante de Streamlit lo lea como código cambiado y recargue en
bucle. Ya pasó en este mismo proyecto y costó un despliegue roto.
"""
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st

COLOMBIA = timezone(timedelta(hours=-5))
_ARCHIVO = Path(os.environ.get("KYVA_ESTADO_DIR", tempfile.gettempdir())) / "kyva_estado.json"

VACIO = {"decisiones": {}, "compromisos": {}, "hilos": [], "notas": {}}


def _leer() -> dict:
    if not _ARCHIVO.exists():
        return json.loads(json.dumps(VACIO))
    try:
        d = json.loads(_ARCHIVO.read_text(encoding="utf-8"))
        for k, v in VACIO.items():
            d.setdefault(k, json.loads(json.dumps(v)))
        return d
    except (json.JSONDecodeError, OSError):
        return json.loads(json.dumps(VACIO))


def _escribir(d: dict) -> None:
    try:
        _ARCHIVO.write_text(json.dumps(d, ensure_ascii=False, indent=1),
                            encoding="utf-8")
    except OSError:
        pass          # en un entorno de solo lectura el demo sigue funcionando


def ahora() -> str:
    return datetime.now(COLOMBIA).strftime("%Y-%m-%d %H:%M")


# ── Decisiones ───────────────────────────────────────────────────────────────
def decidir(clave: str, accion: str, quien: str, nota: str = "",
            valor: float = 0.0, vence_dias: int = 14) -> None:
    """Registra una decisión y el compromiso que se deriva de ella.

    Toda decisión genera un compromiso con dueño y fecha. Es deliberado: una
    decisión sin alguien que responda por ella vuelve a aparecer en la bandeja
    el lunes siguiente, y eso es exactamente lo que mata estas herramientas.
    """
    d = _leer()
    d["decisiones"][clave] = {
        "accion": accion, "quien": quien, "nota": nota,
        "cuando": ahora(), "valor": valor,
    }
    if accion in ("Decidida", "Delegada"):
        d["compromisos"][f"D-{clave}"] = {
            "compromiso": nota or accion, "dueno": quien, "origen": "Decisión",
            "creado": ahora()[:10], "valor": valor,
            "vence": (datetime.now(COLOMBIA) + timedelta(days=vence_dias)).strftime("%Y-%m-%d"),
            "estado": "En curso", "resultado": "",
        }
    _escribir(d)


def decisiones() -> dict:
    return _leer()["decisiones"]


def olvidar(clave: str) -> None:
    d = _leer()
    d["decisiones"].pop(clave, None)
    d["compromisos"].pop(f"D-{clave}", None)
    _escribir(d)


# ── Compromisos ──────────────────────────────────────────────────────────────
def compromisos() -> dict:
    return _leer()["compromisos"]


def cerrar_compromiso(cid: str, resultado: str) -> None:
    """Cerrar un compromiso exige decir QUÉ PASÓ, no solo marcarlo.

    Es la diferencia entre una lista de tareas y una herramienta que aprende:
    dentro de tres meses se puede mirar si bajarle el descuento a esa cuenta
    sirvió, y eso solo se puede si alguien escribió el resultado.
    """
    d = _leer()
    if cid in d["compromisos"]:
        d["compromisos"][cid]["estado"] = "Cumplido"
        d["compromisos"][cid]["resultado"] = resultado
        d["compromisos"][cid]["cerrado_el"] = ahora()
        _escribir(d)


def nuevo_compromiso(texto: str, dueno: str, dias: int = 14,
                     valor: float = 0.0, origen: str = "Manual") -> str:
    # El id salía de contar los compromisos, y contar no sirve cuando algo se
    # borra: `olvidar()` quita el `D-clave` de una decisión, el contador baja y
    # el siguiente compromiso nace con un id que YA existe y sobrescribe al
    # anterior, sin error y sin aviso. Con el comité del lunes escribiendo un
    # registro por cada cierre dejó de ser una rareza teórica: la colisión se
    # llevaría por delante un resultado ya escrito y el compromiso volvería a
    # aparecer en rojo como si nunca se hubiera cerrado.
    d = _leer()
    n = len(d["compromisos"]) + 1
    while f"M-{n:03d}" in d["compromisos"]:
        n += 1
    cid = f"M-{n:03d}"
    d["compromisos"][cid] = {
        "compromiso": texto, "dueno": dueno, "origen": origen,
        "creado": ahora()[:10], "valor": valor,
        "vence": (datetime.now(COLOMBIA) + timedelta(days=dias)).strftime("%Y-%m-%d"),
        "estado": "En curso", "resultado": "",
    }
    _escribir(d)
    return cid


# ── Hilos ────────────────────────────────────────────────────────────────────
def abrir_hilo(asunto: str, ancla: str, quien: str, nota: str = "") -> None:
    d = _leer()
    d["hilos"].append({"asunto": asunto, "ancla": ancla, "abierto_por": quien,
                       "nota": nota, "cuando": ahora(), "estado": "En curso"})
    _escribir(d)


def hilos_nuevos() -> list:
    return _leer()["hilos"]


def reiniciar() -> None:
    """Deja el demo como recién instalado. Solo para la demostración."""
    _escribir(json.loads(json.dumps(VACIO)))


def donde() -> str:
    return str(_ARCHIVO)
