"""El copiloto que ejecuta: de un mensaje de WhatsApp a un pedido en Loggro.

Javier lo pidió textualmente en la reunión del 19 de septiembre: evolucionar
**desde la reportería hacia procesos** —pedidos, consulta de inventario,
aplicación de listas de precio, integración con el ERP y despacho al operador
logístico—. Todo lo demás del panel explica; esta pantalla hace.

El caso es el que ocurre todas las noches en una distribuidora: un bar escribe
a las once de la noche *«mándame 12 Club Colombia y 6 Baileys para mañana»*, y
ese mensaje se queda esperando a que alguien lo transcriba al otro día. Entre
que llega y que se despacha hay seis pasos manuales, y cada uno es un sitio
donde el pedido se pierde o sale mal.

**Los seis pasos, y por qué ninguno es trivial:**

1. *Identificar la cuenta.* Un celular nuevo, un nombre escrito distinto.
2. *Entender qué pidió.* «Club Colombia» son cuatro referencias en el catálogo.
3. *Validar que hay.* Y en la bodega que le corresponde, no en la otra ciudad.
4. *Aplicar SU precio.* La lista depende del canal, y hoy eso vive en la
   cabeza de quien toma el pedido.
5. *Mirar el crédito.* Un pedido que revienta el cupo no se puede despachar.
6. *Armarlo y esperar aprobación.*

**El paso seis es el que hace que esto sea vendible.** El sistema prepara; una
persona confirma. Un agente que emite pedidos solo es la forma más rápida de
que a un cliente le lleguen seiscientas botellas que no pidió, y es lo primero
que un director de operaciones pregunta.

Funciona sin llave de API: el reconocimiento es local, sobre el catálogo real.
Que el demo dependa de un servicio externo para su momento más importante es
exactamente el riesgo que no se corre en una reunión.
"""
import re
import unicodedata

import numpy as np
import pandas as pd
import streamlit as st

from utils.formatters import *
from utils import b2b, datos, estado, gerencia, operacion

# Mensajes reales de los que llegan a un comercial de distribuidora. El tercero
# trae a propósito una referencia ambigua y una cantidad que no cabe: sin un
# caso que falle, la demostración solo prueba que el camino feliz funciona.
EJEMPLOS = [
    # El camino limpio: dos referencias inequívocas y una cantidad en cajas.
    "Buenas, para mañana mándame 12 cajas de Club Colombia y 6 Baileys. "
    "Bar Amarillo",
    # Mezcla: «Ron Medellín Dorado» es único, «Antioqueño» son cinco. Así se ve
    # que el flujo no para por todo — para por lo que de verdad no se sabe.
    "Hola! necesito 24 Ron Medellín Dorado 750 y 12 Aguardiente Antioqueño "
    "para el viernes. Theatron",
    # El que revienta: mucha cantidad, referencias ambiguas y un club social
    # con plazo de 45 días, así que el crédito entra en juego.
    "Buenos días, del Club El Nogal: 40 Chivas Regal 18 años y 30 Moët "
    "Chandon Impérial. Es para el evento del sábado",
]

# Cuántas unidades trae una caja cuando el mensaje dice «cajas». Es el error de
# transcripción más caro del oficio: pedir 12 cajas y despachar 12 botellas
# deja al bar sin producto un viernes.
POR_CAJA = 12
NORMAL = re.compile(r"[^a-z0-9ñ ]+")

# Presentaciones y edades: números que forman parte del NOMBRE del producto,
# no de la cantidad pedida. «24 Ron Medellín Dorado 750» tiene dos números y
# solo el primero es una cantidad; sin distinguirlos, el 750 abre una línea
# nueva y el producto se queda sin su presentación — que es justo lo que lo
# vuelve ambiguo.
TAMANOS = {"175", "200", "250", "330", "355", "375", "500", "700", "750",
           "1000", "1750"}
UNIDAD_TRAS_NUM = re.compile(r"\b(\d+)\s+(ml|cc|lt|litros?|anos|años)\b")


def _pega_numeros(t: str) -> str:
    """Une al nombre los números que son parte de él.

    Se pegan con guion bajo para que el patrón de cantidades no los vea como
    separador, y se deshacen al buscar en el catálogo.
    """
    t = UNIDAD_TRAS_NUM.sub(lambda m: f"{m.group(1)}_{m.group(2)}", t)
    return " ".join(f"_{w}" if w in TAMANOS else w for w in t.split())


def _limpia(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s).lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return NORMAL.sub(" ", s)


def _cuenta_de(texto: str, cuentas: pd.DataFrame):
    """Quién escribe. Se busca por nombre dentro del mensaje, no por remitente.

    En la práctica el número de celular cambia —el administrador nuevo, el
    teléfono del bar— y el nombre del establecimiento no. Por eso el ERP tiene
    que poder reconocer por nombre aunque el número no esté registrado.
    """
    t = _limpia(texto)
    mejor, puntos = None, 0
    for _, c in cuentas.iterrows():
        n = _limpia(c["nombre"])
        # Se exige la palabra más larga del nombre, no cualquiera: «Club» sola
        # aparece en Club El Nogal, Club Colombia y Club Campestre.
        clave = max(n.split(), key=len)
        if len(clave) >= 4 and clave in t:
            p = len(clave) + (3 if n in t else 0)
            if p > puntos:
                mejor, puntos = c, p
    return mejor


# Palabras que cierran la descripción de un producto. Sin esto la última línea
# se traga la cola del mensaje —«6 baileys bar amarillo»— y no reconoce nada.
CORTE_DESC = {"para", "el", "la", "los", "del", "de", "es", "son", "porfa",
              "gracias", "mañana", "manana", "hoy", "viernes", "sabado",
              "domingo", "lunes", "martes", "miercoles", "jueves", "evento",
              "urgente", "favor", "please", "anos", "años", "cordial",
              "saludo", "buenas", "buenos", "dias", "tardes", "noches"}


def _recorta(desc: str) -> str:
    """Corta la descripción donde deja de hablar del producto.

    El nombre de un licor rara vez pasa de cuatro palabras. Todo lo que viene
    después —la fecha, el nombre del bar, un «porfa»— es contexto del mensaje,
    no del producto, y metido en la búsqueda impide reconocerlo.
    """
    palabras = []
    for w in desc.strip().split():
        # Si la descripción EMPIEZA por una palabra de corte no es un producto:
        # «12 Ron Medellín 8 años» partía en dos y «años para el viernes»
        # quedaba buscándose en el catálogo como si fuera una referencia.
        if w in CORTE_DESC:
            break
        palabras.append(w)
        if len(palabras) >= 4:
            break
    return " ".join(palabras)


def _sin_la_cuenta(texto: str, cta) -> str:
    """Quita el nombre del establecimiento del mensaje.

    Hace falta porque las palabras de local y las de producto se cruzan:
    «Club» está en Club El Nogal y en Cerveza Club Colombia, «Bar» en Bar
    Amarillo. Tratarlas como palabra de corte rompe la cerveza; dejarlas rompe
    el bar. Quitando el nombre de la cuenta —que ya se identificó— el problema
    desaparece, que es lo que hace una persona sin darse cuenta.
    """
    if cta is None:
        return texto
    t = _limpia(texto)
    for w in _limpia(cta["nombre"]).split():
        if len(w) > 2:
            t = re.sub(rf"\b{re.escape(w)}\b", " ", t)
    return t


def _lineas_de(texto: str, cat: pd.DataFrame):
    """Qué pidió. Devuelve (reconocidas, ambiguas, no encontradas).

    Lo interesante no son las que reconoce: son las otras dos listas. Una
    referencia ambigua —«Club Colombia» son cuatro presentaciones distintas— no
    se puede adivinar, y adivinarla es peor que preguntar.
    """
    t = _pega_numeros(_limpia(texto))
    # cantidad + texto hasta la siguiente cantidad o el final
    trozos = re.findall(r"(\d+)\s*(?:cajas?\s*(?:de\s*)?)?([a-z0-9ñ_\s]+?)"
                        r"(?=\s+\d+\s|\s*[,.]|\s*y\s+\d|$)", t)
    ok, ambiguas, sin = [], [], []
    for cant, desc in trozos:
        desc = _recorta(desc)
        if len(desc) < 3:
            continue
        cajas = bool(re.search(rf"{cant}\s*cajas?", t))
        unidades = int(cant) * (POR_CAJA if cajas else 1)

        palabras = [p.replace("_", " ").strip() for p in desc.split()]
        palabras = [p for p in palabras if len(p) > 2]
        if not palabras:
            continue
        cand = cat.copy()
        cand["n"] = cand["nombre"].map(_limpia)
        cand["aciertos"] = cand["n"].map(
            lambda n: sum(1 for p in palabras if p in n))
        cand = cand[cand["aciertos"] >= max(1, len(palabras) - 1)]
        cand = cand.sort_values(["aciertos", "unidades_90d"], ascending=False)

        if cand.empty:
            sin.append({"texto": desc, "unidades": unidades})
        elif (len(cand) > 1 and cand.iloc[0]["aciertos"] == cand.iloc[1]["aciertos"]
              and cand.iloc[0]["unidades_90d"] < cand.iloc[1]["unidades_90d"] * 1.8):
            ambiguas.append({"texto": desc, "unidades": unidades,
                             "opciones": cand.head(4)})
        else:
            r = cand.iloc[0]
            ok.append({"texto": desc, "unidades": unidades, "sku": r["sku"],
                       "producto": r["nombre"], "categoria": r["categoria"],
                       "precio": float(r["precio_classic"]),
                       "costo": float(r["costo_unit"]), "cajas": cajas})
    return ok, ambiguas, sin


# Los estados de un paso, con su color y su marca. Se dibuja a mano en vez de
# usar `st.status(type="step")` porque esa variante llega en Streamlit 1.63 y
# la instalada es la 1.60: pedirla lanza «Invalid type value». Hacerlo propio
# además deja controlar la línea que une los pasos, que es lo que convierte
# una lista en una secuencia.
MARCA_PASO = {
    "complete": ("#2f7a48", "✓"),
    "running":  ("#B5762F", "!"),
    "error":    ("#8B1E1E", "×"),
}


def _paso(titulo, estado_p="complete", cuerpo="", ultimo=False):
    color, signo_p = MARCA_PASO.get(estado_p, MARCA_PASO["complete"])
    linea = ("" if ultimo else
             f'<div style="position:absolute;left:11px;top:26px;bottom:-14px;'
             f'width:1px;background:{PALIDO}"></div>')
    st.markdown(f"""
    <div style="position:relative;padding:0 0 16px 36px">
      {linea}
      <div style="position:absolute;left:0;top:1px;width:23px;height:23px;
           border-radius:50%;background:{color};color:#fff;display:flex;
           align-items:center;justify-content:center;font-size:12px;
           font-weight:800;font-family:Montserrat,sans-serif">{signo_p}</div>
      <div style="font-size:13.5px;font-weight:700;color:{TINTA};
           font-family:Montserrat,sans-serif;padding-top:2px">{titulo}</div>
      <div style="font-size:12.5px;color:{TINTA};line-height:1.6;
           margin-top:5px">{cuerpo}</div>
    </div>""", unsafe_allow_html=True)


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Copiloto de pedidos",
        "De un mensaje de WhatsApp a un pedido armado en Loggro, esperando aprobación",
        "¿Qué se hace solo?"), unsafe_allow_html=True)

    cuentas = b2b.cuentas()
    cat = datos.catalogo() if hasattr(datos, "catalogo") else pd.read_csv(
        "data/catalogo.csv")
    inv = operacion.inventario()

    st.markdown(panel(
        "Lo que pasa hoy con este mensaje",
        "Un bar escribe a las once de la noche. El mensaje espera a que alguien "
        "lo transcriba al otro día, y entre que llega y que se despacha hay "
        "<b>seis pasos manuales</b>: identificar la cuenta, entender qué pidió, "
        "validar que hay en la bodega que le corresponde, aplicar la lista de "
        "precio de su canal, mirar el crédito y armar el pedido. "
        "Cada uno es un sitio donde el pedido se pierde o sale mal.",
        "", "azul"), unsafe_allow_html=True)

    st.markdown(espacio(10), unsafe_allow_html=True)
    st.markdown('<div class="ky-sub">El mensaje que llegó</div>',
                unsafe_allow_html=True)

    c = st.columns([1, 1, 1])
    for i, ej in enumerate(EJEMPLOS):
        if c[i].button(f"Ejemplo {i+1}", key=f"ej{i}", width="stretch"):
            st.session_state.mensaje = ej

    texto = st.text_area(
        "Mensaje", value=st.session_state.get("mensaje", EJEMPLOS[0]),
        height=90, key="cop_msg", label_visibility="collapsed")

    if not st.button("Procesar el pedido", type="primary", key="cop_go"):
        st.caption("Pulsa para ver los seis pasos, uno por uno, sobre los datos "
                   "reales del panel.")
        return

    st.markdown(espacio(12), unsafe_allow_html=True)

    # ── 1. La cuenta ────────────────────────────────────────────────────────
    cta = _cuenta_de(texto, cuentas)
    if cta is None:
        _paso("1 · Identificar la cuenta", "error",
              "No reconozco el establecimiento en el mensaje. "
              "**El flujo se detiene aquí**: un pedido sin cuenta no se puede "
              "valorar ni despachar, y adivinarla es peor que preguntar.")
        st.warning("Así se comporta con un cliente nuevo o con un nombre mal "
                   "escrito: para y pide que alguien mire. No inventa.")
        return
    _paso("1 · Identificar la cuenta", "complete",
          f"<b>{cta['nombre']}</b> · {cta['canal']} · {cta['ciudad']}, "
          f"{cta['zona']} · vendedor {cta['vendedor']}<br>"
          f"<span style='color:{CLARO}'>Reconocida por el nombre dentro del "
          f"mensaje, no por el número de celular: el número cambia cuando entra "
          f"un administrador nuevo, el nombre no.</span>")

    # ── 2. Las líneas ───────────────────────────────────────────────────────
    ok, ambiguas, sin = _lineas_de(_sin_la_cuenta(texto, cta), cat)
    detalle = "".join(
        f"• <b>{l['unidades']} u</b> de {l['producto']}"
        f"{' <i>(' + str(l['unidades']//POR_CAJA) + ' cajas)</i>' if l['cajas'] else ''}<br>"
        for l in ok)
    if ambiguas:
        detalle += ("<br><span style='color:#B5762F'><b>Ambiguo:</b> "
                    + ", ".join(a["texto"] for a in ambiguas)
                    + " — hay varias presentaciones y no se adivina.</span><br>")
    if sin:
        detalle += ("<span style='color:#8B1E1E'><b>Sin reconocer:</b> "
                    + ", ".join(s["texto"] for s in sin) + "</span>")
    _paso(f"2 · Entender qué pidió — {len(ok)} líneas",
          "complete" if ok and not (ambiguas or sin) else "running", detalle)

    if ambiguas:
        st.markdown('<div class="ky-sub">Hay que elegir</div>',
                    unsafe_allow_html=True)
        for j, a in enumerate(ambiguas):
            opciones = a["opciones"]["nombre"].tolist()
            elegido = st.selectbox(
                f"«{a['texto']}» — {a['unidades']} unidades", opciones,
                key=f"amb{j}")
            fila = a["opciones"][a["opciones"]["nombre"] == elegido].iloc[0]
            ok.append({"texto": a["texto"], "unidades": a["unidades"],
                       "sku": fila["sku"], "producto": fila["nombre"],
                       "categoria": fila["categoria"],
                       "precio": float(fila["precio_classic"]),
                       "costo": float(fila["costo_unit"]), "cajas": False})
        st.caption("Esta es la falla más común de la automatización, y no se "
                   "esconde: **el flujo para y pregunta**. Corregir el dato de "
                   "origen una vez vale más que revisar a mano para siempre.")

    if not ok:
        st.error("Sin líneas reconocidas no hay pedido.")
        return

    # ── 3. Stock, en SU bodega ──────────────────────────────────────────────
    bodega = cta["ciudad"]
    filas = []
    for l in ok:
        d = inv[(inv["sku"] == l["sku"]) & (inv["bodega"] == bodega)]
        hay = int(d["unidades"].sum()) if len(d) else 0
        otra = int(inv[(inv["sku"] == l["sku"]) &
                       (inv["bodega"] != bodega)]["unidades"].sum())
        l["hay"] = hay
        l["otra_bodega"] = otra
        l["sirve"] = min(hay, l["unidades"])
        l["falta"] = max(l["unidades"] - hay, 0)
        filas.append(l)
    faltantes = [l for l in filas if l["falta"] > 0]
    cuerpo = "".join(
        f"• {l['producto'][:42]}: pide {l['unidades']}, hay <b>{l['hay']}</b> "
        f"en {bodega}"
        + (f" · <span style='color:#8B1E1E'>faltan {l['falta']}</span>"
           f"{' — hay ' + str(l['otra_bodega']) + ' en la otra bodega' if l['otra_bodega'] else ''}"
           if l["falta"] else "") + "<br>" for l in filas)
    _paso(f"3 · Validar stock en {bodega}",
          "complete" if not faltantes else "running", cuerpo)

    # ── 4. Su lista de precio ───────────────────────────────────────────────
    MARGEN_CANAL = {"Restaurantes": .265, "Bares": .240, "Discotecas": .205,
                    "Clubes sociales": .285, "Empresas": .305}
    margen_obj = MARGEN_CANAL.get(cta["canal"], .25)
    desc = float(cta["descuento_pct"]) / 100
    for l in filas:
        # Precio mayorista: el costo más el margen objetivo del canal. El
        # descuento pactado se aplica DENTRO de ese margen, no sobre el precio
        # de consumidor — con esa cuenta una cerveza salía al 3% y ninguna
        # distribuidora vive de eso.
        lista = l["costo"] / max(1 - margen_obj, .01)
        l["unit"] = lista * (1 - desc * 0.35)
        l["pvp"] = l["precio"]
        l["total"] = l["unit"] * l["sirve"]
        l["margen"] = (l["unit"] - l["costo"]) * l["sirve"]
    subtotal = sum(l["total"] for l in filas)
    margen = sum(l["margen"] for l in filas)
    ahorro_pvp = sum((l["pvp"] - l["unit"]) * l["sirve"] for l in filas)
    _paso(f"4 · Aplicar la lista de {cta['canal']}", "complete",
          f"Lista mayorista de su canal · descuento pactado "
          f"<b>{pct(cta['descuento_pct'])}</b> · plazo {int(cta['plazo_pago'])} días<br>"
          f"Compra {cop(ahorro_pvp, 0)} por debajo del precio de góndola<br>"
          f"Subtotal <b>{cop(subtotal, 0)}</b> · margen "
          f"<b>{cop(margen, 0)}</b> ({pct(margen/max(subtotal,1)*100)})<br>"
          f"<span style='color:{CLARO}'>Hoy esta lista vive en la cabeza de "
          f"quien toma el pedido. Es la fuente número uno de diferencias entre "
          f"lo que se promete por WhatsApp y lo que sale en la factura.</span>")

    # ── 5. El crédito ───────────────────────────────────────────────────────
    try:
        f = gerencia.facturas()
        abierto = float(f[(f["cuenta_id"] == cta["cuenta_id"]) &
                          (~f["pagada"])]["saldo"].sum())
        vencido = float(f[(f["cuenta_id"] == cta["cuenta_id"]) &
                          (~f["pagada"]) & (f["dias_vencida"] > 0)]["saldo"].sum())
    except Exception:
        abierto = vencido = 0.0
    cupo = float(cta["cupo_credito"])
    despues = abierto + subtotal
    pasa = despues <= cupo and vencido <= 0
    _paso("5 · Mirar el crédito", "complete" if pasa else "error",
          f"Cupo <b>{cop(cupo, 0)}</b> · debe hoy {cop(abierto, 0)}"
          + (f" · <span style='color:#8B1E1E'>{cop(vencido, 0)} VENCIDO</span>"
             if vencido > 0 else "")
          + f"<br>Con este pedido quedaría en <b>{cop(despues, 0)}</b>"
          + ("" if pasa else
             (f" — <span style='color:#8B1E1E'>por encima del cupo</span>"
              if despues > cupo else
              f" — <span style='color:#8B1E1E'>cabe en el cupo, pero hay "
              f"factura vencida y la regla bloquea el despacho</span>")))

    # ── 6. El pedido, esperando a una persona ───────────────────────────────
    _paso("6 · Armar el pedido en Loggro", "running",
          "Preparado. <b>No se emite solo.</b>", ultimo=True)

    st.markdown(espacio(14), unsafe_allow_html=True)
    st.markdown('<div class="ky-sub">El pedido</div>', unsafe_allow_html=True)
    t = pd.DataFrame([{
        "Referencia": l["producto"], "Pedidas": l["unidades"],
        "Se sirven": l["sirve"], "Precio unitario": round(l["unit"]),
        "Total": round(l["total"]),
    } for l in filas])
    st.dataframe(t, hide_index=True, width="stretch", row_height=38,
                 column_config={
        "Precio unitario": st.column_config.NumberColumn(format="$%d"),
        "Total": st.column_config.NumberColumn(format="$%d"),
    })

    r1, r2 = st.columns([2, 3], gap="large")
    with r1:
        st.markdown(
            f'<div style="background:{PRIMARIO};color:#fff;border-radius:8px;'
            f'padding:18px 22px">'
            f'<div style="font-family:Montserrat,sans-serif;font-size:10px;'
            f'letter-spacing:.15em;text-transform:uppercase;opacity:.65">'
            f'Total del pedido</div>'
            f'<div style="font-family:\'DM Serif Display\',Georgia,serif;'
            f'font-size:34px;line-height:1.1;margin:4px 0">{cop(subtotal, 0)}</div>'
            f'<div style="font-size:12px;opacity:.78">'
            f'{len(filas)} referencias · entrega en {cta["zona"]}</div></div>',
            unsafe_allow_html=True)
    with r2:
        if faltantes:
            st.warning(
                f"**{len(faltantes)} línea(s) incompletas.** Se sirve lo que hay "
                f"y el resto queda pendiente. Esa venta perdida es la que mide "
                f"el módulo de nivel de servicio — y la razón por la que el bar "
                f"puede terminar comprándole esa referencia a otro.")
        if not pasa:
            st.error(
                "**El crédito no pasa.** El flujo lo prepara igual pero lo deja "
                "bloqueado: quien autoriza la excepción es una persona, y queda "
                "registrado quién fue.")

    st.markdown(espacio(10), unsafe_allow_html=True)
    b = st.columns([1, 1, 1, 2])
    quien = b[2].selectbox("Aprueba", ["Javier", "Andrea Restrepo", "Julián Mora",
                                       "Paola Cárdenas"], key="cop_quien",
                           label_visibility="collapsed")
    if b[0].button("Aprobar y despachar", type="primary", key="cop_ok",
                   width="stretch"):
        estado.nuevo_compromiso(
            f"Pedido de {cta['nombre']} por {cop(subtotal, 0)} despachado",
            quien, dias=2, valor=subtotal, origen="Copiloto")
        st.success(
            f"Pedido creado en Loggro y enviado al operador de {cta['ciudad']}. "
            f"Queda el registro: lo aprobó **{quien}**. "
            f"El número de guía le llega al cliente por el mismo WhatsApp por "
            f"donde escribió.")
    b[1].button("Devolver al vendedor", key="cop_no", width="stretch")

    st.markdown(espacio(14), unsafe_allow_html=True)
    st.markdown(panel(
        "Por qué el paso seis no se automatiza",
        "Los cinco primeros pasos son lectura y cálculo: ahí la máquina es mejor "
        "que una persona a las once de la noche. El sexto compromete inventario "
        "y plata, y ahí no. <b>Un agente que emite pedidos solo es la forma más "
        "rápida de que a un cliente le lleguen seiscientas botellas que no "
        "pidió</b> — y es lo primero que pregunta un director de operaciones.<br><br>"
        "Lo que se gana igual es todo el trabajo previo: el pedido llega armado, "
        "valorado con la lista correcta y con el crédito ya mirado. Aprobar es "
        "un clic en vez de veinte minutos.",
        "", "rojo"), unsafe_allow_html=True)
