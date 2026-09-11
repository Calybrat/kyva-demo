#!/usr/bin/env python3
"""
Prueba headless del panel: abre cada módulo y falla si alguno lanza una excepción.

Usa el runner de pruebas de Streamlit, así que ejercita el código igual que el
navegador: carga los datos, arma las figuras y renderiza los widgets. Es la
forma barata de no descubrir un `KeyError` en una demostración con el cliente.

Uso:  python3 pruebas.py
"""
import sys
import time
from pathlib import Path

from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).parent
sys.path.insert(0, str(RAIZ))

from app import PAGES  # noqa: E402


def main() -> int:
    fallos = []
    print(f"\nProbando {len(PAGES)} módulo(s) del panel…\n")
    for etiqueta in PAGES:
        t0 = time.time()
        at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=180)
        at.session_state["page"] = etiqueta
        at.run()
        dur = time.time() - t0
        if at.exception:
            fallos.append((etiqueta, at.exception[0].message))
            print(f"  ✗ {etiqueta:<38} {dur:5.1f}s  {at.exception[0].message[:90]}")
        else:
            # `st.error` no levanta excepción, pero el app.py la usa para
            # reportar módulos que no cargaron: hay que mirarla también.
            errores = [e.value for e in at.error]
            if errores:
                fallos.append((etiqueta, errores[0]))
                print(f"  ✗ {etiqueta:<38} {dur:5.1f}s  {errores[0][:90]}")
            else:
                print(f"  ✓ {etiqueta:<38} {dur:5.1f}s")

    print()
    if fallos:
        print(f"{len(fallos)} módulo(s) con problemas:\n")
        for etiqueta, msg in fallos:
            print(f"── {etiqueta} ───────────────────────────")
            print(msg[:2000])
            print()
        return 1
    print("Todos los módulos cargan correctamente.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
