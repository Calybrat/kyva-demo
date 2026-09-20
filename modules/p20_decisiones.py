"""Centro de decisiones: lo único que de verdad necesita a un gerente hoy.

**Este es el módulo que separa un panel de una herramienta de gerencia.**

Un tablero dice «esta cuenta deja -2%». Eso no es una decisión: es un dato que
alguien tiene que interpretar, convertir en opciones, estimar y ejecutar. Aquí
eso ya viene hecho. Cada fila trae cuatro cosas y por eso se puede resolver en
veinte segundos:

  1. **El número que la justifica**, no una alerta genérica.
  2. **Las opciones concretas**, redactadas como se dirían en una reunión.
  3. **Lo que cuesta no hacer nada**, y —esto es lo que hace que el orden
     signifique algo— en la MISMA unidad para todas: utilidad en riesgo a doce
     meses. Sumar venta anual de una cuenta apagada con margen negativo de otra
     y con el costo de una mercancía que falta da un número que no quiere decir
     nada, y es la primera objeción que hace cualquiera que sepa de finanzas.
     Aquí cada fila se traduce antes de entrar.
  4. **Quién decide.** Una decisión sin dueño vuelve a aparecer el lunes.

La bandeja junta lo que hoy vive en ocho lugares distintos: el ERP, el informe
del operador logístico, el Excel de cartera, el contador de cuotas del
proveedor, el inventario de lotes, el presupuesto del año, el WhatsApp del
vendedor y la cabeza de quien compra. Ese reparto es la razón por la que nada
se decide: cada pieza sola no alcanza para actuar.

**Decidir aquí no es marcar un check.** La revisión adversaria fue lapidaria
con la versión anterior:

    «Tiene un botón que dice "Decidir" y le voy a decir qué hace: guarda en la
    memoria de mi navegador. Refresco la página y se borró. Eso no es un
    sistema de gerencia, eso es una demo.»

Tenía razón, y el arreglo no es técnico sino de concepto. Decidir exige elegir
**dueño y plazo**: toda decisión genera un compromiso con nombre y fecha, y se
guarda en disco, fuera de la sesión del navegador. Lo que queda es el registro
—quién decidió qué, cuándo y con qué número a la vista— que es exactamente lo
que permite contestar en enero por qué se le bajó el descuento a una cuenta en
septiembre.

**Nada de aquí se ejecuta solo.** Decidir deja registro y dispara el flujo; la
acción la confirma una persona. Es la misma regla del módulo de
automatizaciones y es lo que permite que un director de operaciones diga que sí.
"""
import hashlib
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import b2b, operacion, datos, gerencia, filtros, estado

TONO = {"Alta": "#8B1E1E", "Media": "#B5762F", "Baja": CLARO}
ICONO = {"Condiciones comerciales": "🤝", "Cuenta apagada": "🔌",
         "Riesgo de crédito": "🏦", "Compra": "📦", "Excepción": "⚠️",
         "Precio": "🏷️", "Cartera": "🏦", "Marcas": "🎁",
         "Vencimientos": "⏳", "Presupuesto": "🎯"}

# Las tres situaciones en que puede estar una fila. Aplazada tiene color
# propio: no es verde porque no está resuelta.
ESTADOS = (("Sin decidir", ACENTO), ("Aplazada", "#B5762F"), ("Con dueño", "#2f7a48"))

# Plazos que se pueden pactar. No hay "sin fecha": un compromiso sin fecha es
# una intención, y las intenciones son las que vuelven a la bandeja el lunes.
PLAZOS = {"Esta semana": 7, "Quince días": 15, "Este mes": 30,
          "Antes del cierre del trimestre": 45}

# A quién le cae por defecto lo que no tiene un vendedor detrás. Son las áreas
# que la propia bandeja declara en la columna «decide».
DUENO_POR_AREA = {
    "Dirección comercial": "Javier", "Compras": "Diana (compras)",
    "Operaciones": "Javier", "Cartera": "Andrea Restrepo",
    "Dirección": "Javier",
}

# ── La unidad en que se mide la bandeja ──────────────────────────────────────
#
# Todas las filas se valoran en UTILIDAD EN RIESGO A DOCE MESES. Sin una unidad
# común el orden es una ilusión: $43 M de venta que se apaga no pesan lo mismo
# que $43 M de margen, y un KPI que los suma no significa nada. La regla es:
# lo que se pierde de una vez —una factura que no se recupera, producto que se
# vence, un rebate que no se devenga— entra completo; lo que se repite mes a
# mes entra por los meses que faltan hasta cerrar el año; y lo que está
# denominado en VENTA se convierte a margen antes de entrar.

# Quedan cuatro meses hasta el cierre del año (el corte del panel es agosto).
# Una brecha de presupuesto que nadie corrige se repite los meses que faltan:
# por eso se anualiza así y no se reporta el número del mes a secas.
MESES_AL_CIERRE = 4

# Costo de financiar capital de trabajo en Colombia. Es lo que cuesta al año
# sostener la exposición de un cliente por encima del cupo que respalda.
COSTO_CAPITAL = 0.18

# Costo cargado de la hora de quien destraba un pedido a mano. Un auxiliar de
# operaciones sale en ~$3,0 M al mes con prestaciones y parafiscales (básico de
# ~$1,9 M por un factor prestacional de 1,55) y trabaja unas 160 horas al mes.
# La versión anterior usaba $60.000, que es el costo de una persona de $12 M al
# mes: triplicaba el valor de estas filas.
COSTO_HORA = 18_750

# Desde cuántos días de mora una factura deja de ser gestión de rutina y pasa a
# ser una decisión. Son los mismos 15 días que la pantalla de cartera declara
# como política de bloqueo de despacho —el punto donde la probabilidad de cobro
# empieza a caer rápido y todavía alcanza una llamada—. Con los 30 que usaba
# esta bandeja quedaban fuera 38 de las 42 facturas vencidas y la cartera
# aparecía como el problema más pequeño de la compañía.
MORA_MINIMA = 15

# Por debajo de qué cumplimiento una brecha de presupuesto es una decisión. Un
# mes que cierra en 96% de la meta es ruido de un mes, y publicarlo como
# prioridad de la compañía gasta la credibilidad de toda la bandeja. Si ninguna
# línea baja del umbral este bloque no aporta filas, y eso está bien: no hay
# nada que decidir.
CUMPLIMIENTO_MINIMO = 90

# Cuántas filas caben y cuántas tiene asegurada cada fuente.
#
# La versión anterior recortaba DENTRO de cada bloque —cinco de cartera, cuatro
# de compras— antes del orden final, así que la composición de la bandeja la
# fijaba una cuota arbitraria por sistema y no el dinero: cartera se llevaba
# cinco cupos por $1,7 M mientras compras entraba con cuatro por $227 M. Aquí
# cada fuente tiene aseguradas sus dos filas más caras —eso es lo que sostiene
# la promesa de «los ocho sistemas en una sola cola»— y el resto de los cupos
# se reparte por plata entre todas.
CUPO_BANDEJA = 25
MINIMO_POR_FUENTE = 2


class _Cap:
    """Recoge una tarjeta en vez de pintarla.

    Existe para no reescribir las cuatro llamadas a `kpi()` que ya están bien
    redactadas: solo cambia DÓNDE se pintan. La primera pasa a ser el titular
    en navy y las otras tres, apoyos más pequeños a su derecha.
    """

    def __init__(self, destino):
        self.destino = destino

    def markdown(self, html, **_):
        self.destino.append(html)


# ── Construcción de la bandeja ───────────────────────────────────────────────
def _clave(tipo: str, ident: str) -> str:
    """Identificador estable de una fila, para poder recordarla en disco.

    La versión anterior usaba el índice del DataFrame. Bastaba con cambiar un
    filtro o con que entrara una factura nueva para que la decisión guardada
    apareciera pegada a otra fila. La clave tiene que salir del negocio
    —cuenta, marca, proveedor— y no de la posición en una tabla.
    """
    base = re.sub(r"[^a-z0-9]+", "-", f"{tipo}-{ident}".lower()).strip("-")
    if len(base) <= 64:
        return base
    # Truncar a secas hacía colisionar dos motivos de excepción que comparten
    # los primeros 64 caracteres: `drop_duplicates` habría borrado uno en
    # silencio y con él la decisión que ya estaba guardada en disco. El sufijo
    # los separa sin alargar la clave.
    return f"{base[:57]}-{hashlib.md5(base.encode()).hexdigest()[:6]}"


def _corto(txt, n: int = 26) -> str:
    """Recorta con puntos suspensivos. Un corte seco se lee como un dato malo."""
    t = str(txt)
    return t if len(t) <= n else t[:n - 1].rstrip() + "…"


def _dia(fecha) -> str:
    return f"{fecha.day} de {MESES_ES[fecha.month - 1]}"


def _a_pesos(txt: str) -> float:
    """«14 M al año» → 14.000.000. Sirve para ordenar por plata, no por texto."""
    m = re.search(r"(-?[\d.,]+)\s*M", str(txt))
    if not m:
        return 0.0
    try:
        return float(m.group(1).replace(".", "").replace(",", ".")) * 1e6
    except ValueError:
        return 0.0


def _riesgo_de_esperar(saldo: float, tramo: str) -> float:
    """Lo que cuesta dejar que una factura vencida pase al siguiente tramo.

    No es el saldo entero —ese se cobra o no se cobra igual— sino el deterioro:
    una factura en «31 a 60» se recupera al 82%; si nadie la llama y cruza a
    «61 a 90», al 58%. Esos veinticuatro puntos son el precio exacto de la
    semana que se dejó pasar, y es el número que hace comparable una gestión de
    cobro con una orden de compra.
    """
    t = gerencia.TRAMOS
    if tramo not in t:
        return saldo * 0.10
    sig = t[min(t.index(tramo) + 1, len(t) - 1)]
    # En «Más de 90» ya no hay tramo siguiente, pero seguir sin tocarla tampoco
    # es gratis: el piso del 5% evita que la mora más vieja quede de última.
    return saldo * max(gerencia.COBRO[tramo] - gerencia.COBRO[sig], 0.05)


def _en_utilidad(tipo: str, plata: float, margen: float) -> tuple:
    """Traduce a utilidad en riesgo lo que trae el análisis de cuentas.

    Los tres tipos vienen en unidades distintas y hay que decirlo: «cuenta
    apagada» está en VENTA anual, «condiciones comerciales» ya está en MARGEN
    anual y «riesgo de crédito» no es ni lo uno ni lo otro sino capital
    expuesto sin respaldo. Apilarlos como venían era lo que hacía que el número
    de arriba no significara nada.
    """
    v = abs(float(plata))
    if tipo == "Cuenta apagada":
        u = v * margen
        return u, f"{cop(u, 0)} de margen al año si no vuelve"
    if tipo == "Riesgo de crédito":
        u = v * COSTO_CAPITAL
        return u, f"{cop(u, 0)} al año de financiar lo que no respalda"
    if tipo == "Condiciones comerciales":
        return v, f"{cop(v, 0)} al año de margen en rojo"
    return v, cop(v, 0)


def _recortar(b: pd.DataFrame) -> pd.DataFrame:
    """Elige qué cabe en la bandeja por plata, no por cuota de cada fuente.

    Cada sistema tiene aseguradas sus filas más caras —sin eso la bandeja deja
    de ser «los ocho sistemas en una sola cola» en cuanto uno de ellos tiene
    cifras grandes— y los cupos restantes se reparten por dinero entre todas.
    """
    b = b.sort_values("costo_inaccion", ascending=False)
    fijas = b.groupby("origen", sort=False).head(MINIMO_POR_FUENTE)
    resto = b.drop(fijas.index)
    sel = pd.concat([fijas, resto.head(max(CUPO_BANDEJA - len(fijas), 0))])
    return sel.sort_values("costo_inaccion", ascending=False).reset_index(drop=True)


def _bandeja() -> pd.DataFrame:
    """Reúne en una sola cola lo que hoy vive repartido en ocho sistemas.

    El orden lo fija la PLATA EN JUEGO, no la gravedad que declare cada fuente.
    Una alerta «alta» de 400 mil pesos no puede ir encima de una «media» de
    catorce millones — y en los sistemas que las producen por separado eso pasa
    todos los días, que es por lo que nadie las lee.

    Para que ese orden signifique algo, todas las filas entran en la misma
    unidad: utilidad en riesgo a doce meses. Lo que llega denominado en venta o
    en costo de mercancía se convierte antes, y se dice con qué supuesto.
    """
    filas = []
    # El margen de la compañía sale del resumen del negocio, no de un supuesto
    # escrito aquí: si cambia el mix o el costo, la bandeja se reordena sola.
    margen = b2b.resumen_b2b()["margen_12m_pct"] / 100

    # 1. Lo que sale del análisis de cuentas (gen_b2b lo calcula con su costo real)
    d = filtros.aplicar(b2b.decisiones(), col_mes=None)
    for _, r in d.iterrows():
        plata, texto = _en_utilidad(
            r["tipo"], _a_pesos(r.get("si_nadie_hace_nada", "")), margen)
        filas.append({
            "clave": _clave(r["tipo"], r.get("cuenta") or r["titulo"]),
            "tipo": r["tipo"], "urgencia": r["urgencia"], "titulo": r["titulo"],
            "dato": r["dato"], "opciones": r["accion"],
            "costo_inaccion": plata, "costo_txt": texto,
            "decide": r["decide"], "quien": r.get("cuenta", ""),
            "sugerido": r.get("vendedor", ""), "origen": "Análisis de cuentas",
            "ambito": "Por ciudad y vendedor",
        })

    # 2. Cartera: lo vencido por encima del umbral de bloqueo, por cuenta
    #
    # Se agrupa por cuenta y no por factura a propósito: nadie llama a una
    # factura, se llama al dueño del bar, y si tiene tres vencidas la
    # conversación es una sola.
    #
    # El filtro de PERIODO no se aplica, igual que en la pantalla de cartera:
    # el «mes» de una factura es el de emisión, así que filtrar por periodo
    # esconde justamente la factura vieja que sigue abierta. Con el periodo en
    # «Mes» este bloque entero desaparecía de la bandeja sin decir nada.
    f = filtros.aplicar(gerencia.facturas(), col_mes=None)
    venc = f[(~f["pagada"]) & (f["dias_vencida"] >= MORA_MINIMA)].copy()
    if len(venc):
        venc["riesgo"] = [_riesgo_de_esperar(s, t)
                          for s, t in zip(venc["saldo"], venc["tramo"])]
        # Ordenar por mora antes de agrupar hace que «last» sea el tramo de la
        # factura más vieja, que es la que manda en la conversación de cobro.
        por_cuenta = venc.sort_values("dias_vencida").groupby(
            ["cuenta_id", "nombre", "canal", "ciudad", "vendedor"]).agg(
            saldo=("saldo", "sum"), riesgo=("riesgo", "sum"),
            n=("factura", "size"), dias=("dias_vencida", "max"),
            tramo=("tramo", "last")).reset_index()
        for _, r in por_cuenta.nlargest(12, "riesgo").iterrows():
            filas.append({
                "clave": _clave("cartera", r["cuenta_id"]),
                "tipo": "Cartera",
                "urgencia": "Alta" if r["dias"] > 30 else "Media",
                "titulo": f"{r['nombre']} debe {cop(r['saldo'])} con {int(r['dias'])} días de mora",
                "dato": f"{int(r['n'])} factura(s) en el tramo «{r['tramo']}» · "
                        f"{r['canal']} · {r['ciudad']} · vende {r['vendedor']}",
                "opciones": "Llamar hoy y pactar fecha de pago · suspender despachos "
                            "hasta que se ponga al día · pasar a acuerdo de pago con cuotas",
                "costo_inaccion": float(r["riesgo"]),
                "costo_txt": f"{cop(r['riesgo'], 0)} que se dejan de recobrar",
                "decide": "Cartera", "quien": r["nombre"],
                "sugerido": r["vendedor"], "origen": "Cartera",
                "ambito": "",
            })

    # 3. Marcas: cuotas de trimestre que no llegan al ritmo actual
    #
    # El compromiso con la marca es de la compañía entera, no de una ciudad ni
    # de un vendedor: por eso este bloque NO pasa por los filtros globales, y
    # por eso cada fila lo dice en la tarjeta.
    reb = gerencia.rebates()
    act = reb[reb["trimestre"] == "2026-T3"].copy()
    if len(act):
        # Van dos meses de tres: el cierre se proyecta al ritmo que lleva.
        act["proyectado"] = act["unidades"] / 2 * 3
        act["cumpl_proy"] = act["proyectado"] / act["cuota"] * 100
        act["faltan"] = (act["cuota"] - act["proyectado"]).clip(lower=0)
        act["vale_el_tramo"] = act["compra"] / 2 * 3 * act["siguiente_tramo"]
        cortas = act[(act["cumpl_proy"] < 100) & (act["vale_el_tramo"] > 0)]
        for _, r in cortas.nlargest(8, "vale_el_tramo").iterrows():
            excl = " (exclusiva)" if r["exclusiva"] else ""
            filas.append({
                "clave": _clave("marca", f"{r['marca']}-2026t3"),
                "tipo": "Marcas",
                "urgencia": "Alta" if r["cumpl_proy"] < 92 else "Media",
                "titulo": f"{r['marca']}{excl} cierra el trimestre en "
                          f"{r['cumpl_proy']:.0f}% al ritmo de hoy",
                "dato": f"{miles(r['unidades'])} de {miles(r['cuota'])} unidades · "
                        f"faltan {miles(r['faltan'])} u · quedan 30 días",
                "opciones": "Comprar las unidades que faltan antes del cierre · "
                            "empujar la marca en la promoción del mes · "
                            "renegociar la cuota con el proveedor para el próximo trimestre",
                "costo_inaccion": float(r["vale_el_tramo"]),
                "costo_txt": f"{cop(r['vale_el_tramo'], 0)} del tramo que se pierde",
                "decide": "Compras", "quien": r["marca"],
                "sugerido": "", "origen": "Marcas y rebate",
                "ambito": "Toda la compañía",
            })

    # 4. Compras cuya ventana de importación se cierra
    #
    # El faltante se toma NETO de lo que ya viene en camino, que es el mismo
    # número que muestra la pantalla de reposición. Con el bruto la bandeja
    # pide comprar mercancía que ya está en el barco, y comprar dos veces lo
    # mismo es el error caro de un MRP mal hecho.
    falt = operacion.resumen_operacion()["faltantes"].copy()
    falt = filtros.aplicar(falt.rename(columns={"bodega": "ciudad"}), col_mes=None)
    urge = falt[(falt["urgencia"].isin(["Ventana cerrada", "Pedir esta semana"])) &
                (falt["faltante_neto"] > 0)]
    if len(urge):
        por_prov = urge.groupby("proveedor").agg(
            refs=("sku", "nunique"), plata=("valor_neto", "sum"),
            bruto=("valor_faltante", "sum"),
            primera=("fecha_limite_pedido", "min"),
            ultima=("fecha_limite_pedido", "max"),
            cerradas=("urgencia", lambda s: int((s == "Ventana cerrada").sum())),
        ).reset_index()
        for _, r in por_prov.nlargest(8, "plata").iterrows():
            ini, fin = r["primera"], r["ultima"]
            # La fecha y el dinero tienen que describir el mismo conjunto. El
            # titular anterior ponía el límite de UNA referencia sobre la plata
            # de las dieciocho: era una fecha que no correspondía a esa cifra.
            cuando = (f"se pide antes del {_dia(ini)}" if ini == fin else
                      f"se piden entre el {_dia(ini)} y el {_dia(fin)}")
            vencida = ini <= datos.CORTE
            en_camino = float(r["bruto"]) - float(r["plata"])
            # El faltante está valorado AL COSTO. Lo que se pierde por no
            # tenerlo no es ese costo ni la venta entera: es el margen de la
            # venta que no va a ocurrir.
            perdido = float(r["plata"]) * margen / (1 - margen)
            filas.append({
                "clave": _clave("compra", r["proveedor"]),
                "tipo": "Compra",
                "urgencia": "Alta" if (vencida or r["cerradas"]) else "Media",
                "titulo": f"Orden a {r['proveedor']}: {int(r['refs'])} "
                          f"referencia{'s' if r['refs'] != 1 else ''} {cuando}",
                "dato": f"{cop(r['plata'], 0)} de faltante para la temporada, neto de "
                        f"lo que viene en camino"
                        + (f" ({cop(en_camino, 0)} ya está pedido)" if en_camino > 0 else "")
                        + (" · la primera fecha ya se pasó" if vencida else ""),
                "opciones": "Emitir la orden sugerida · pedir solo el top 10 · "
                            "asumir el quiebre y comprar a un mayorista local en diciembre",
                "costo_inaccion": perdido,
                "costo_txt": f"{cop(perdido, 0)} de margen que no se alcanza a hacer",
                "decide": "Compras", "quien": r["proveedor"],
                "sugerido": "", "origen": "Reposición",
                "ambito": "Solo por ciudad",
            })

    # 5. Vencimientos: lotes críticos en bodega
    lot = gerencia.lotes().rename(columns={"bodega": "ciudad"})
    lot = filtros.aplicar(lot, col_mes=None)
    cri = lot[(lot["estado"].isin(["Crítico", "Vencido"])) & (lot["en_riesgo"] > 0)]
    if len(cri):
        por_marca = cri.groupby(["marca", "ciudad"]).agg(
            plata=("en_riesgo", "sum"), u=("en_riesgo_u", "sum"),
            lotes=("lote", "size"), dias=("dias_para_vencer", "min")).reset_index()
        for _, r in por_marca.nlargest(8, "plata").iterrows():
            filas.append({
                "clave": _clave("lote", f"{r['marca']}-{r['ciudad']}"),
                "tipo": "Vencimientos",
                "urgencia": "Alta" if r["dias"] <= 21 else "Media",
                "titulo": f"{r['marca']} en {r['ciudad']}: {int(r['u'])} unidades "
                          f"no se alcanzan a vender",
                "dato": f"{int(r['lotes'])} lote(s) · vence el primero en "
                        f"{int(r['dias'])} días · a la rotación de hoy sobra producto",
                "opciones": "Sacarlo en promoción esta semana · moverlo a la otra bodega · "
                            "ofrecerlo al canal de distribución con descuento · "
                            "negociar devolución con el proveedor",
                "costo_inaccion": float(r["plata"]),
                "costo_txt": f"{cop(r['plata'], 0)} que se van a la basura",
                "decide": "Operaciones", "quien": r["marca"],
                "sugerido": "", "origen": "Vencimientos",
                "ambito": "Solo por ciudad",
            })

    # 6. Presupuesto: el mes cerrado contra la meta, por canal y ciudad
    #
    # Se mira el ÚLTIMO MES CERRADO y no el acumulado a propósito: un acumulado
    # bueno esconde justo el mes en que se empezó a caer, que es el único que
    # todavía se puede corregir. Y se descartan los meses con real en cero
    # —Medellín antes de marzo— porque sumarlos inventa una brecha de cuarenta
    # millones en una ciudad que todavía no existía.
    #
    # Se exige además que la brecha sea MATERIAL. Una línea que cierra en 96%
    # de su meta, en un mes en que la compañía entera está por encima, no es una
    # decisión de gerencia: publicarla como prioridad de la casa es lo que hace
    # que nadie vuelva a creerle a la bandeja.
    pre = filtros.aplicar(gerencia.presupuesto())
    pre = pre[pre["real"] > 0]
    if len(pre):
        ult = pre[pre["mes"] == pre["mes"].max()]
        cortos = ult[(ult["brecha"] < 0) & (ult["cumplimiento"] < CUMPLIMIENTO_MINIMO)]
        for _, r in cortos.nsmallest(6, "brecha").iterrows():
            # La brecha está en VENTA. Lo que se deja de ganar es su margen.
            perdido = abs(float(r["brecha"])) * MESES_AL_CIERRE * margen
            filas.append({
                "clave": _clave("presupuesto", f"{r['canal']}-{r['ciudad']}-{r['mes']}"),
                "tipo": "Presupuesto",
                "urgencia": "Alta" if r["cumplimiento"] < 80 else "Media",
                "titulo": f"{r['canal']} en {r['ciudad']} cerró {mes_es(r['mes'])} en "
                          f"{r['cumplimiento']:.0f}% del presupuesto",
                "dato": f"Meta {cop(r['presupuesto'], 0)} · real {cop(r['real'], 0)} · "
                        f"faltaron {cop(abs(r['brecha']), 0)} de venta",
                "opciones": "Revisar la cuota del vendedor de ese canal · "
                            "reasignar el presupuesto del canal al que sí está tirando · "
                            "montar una acción comercial para el trimestre",
                "costo_inaccion": perdido,
                "costo_txt": f"{cop(perdido, 0)} de margen hasta cerrar el año",
                "decide": "Dirección comercial", "quien": f"{r['canal']} · {r['ciudad']}",
                "sugerido": "", "origen": "Presupuesto",
                "ambito": "Por canal y ciudad",
            })

    # 7. Lo que la automatización no pudo resolver sola
    #
    # Los minutos salen de la bitácora —lo que cada corrida se ahorra cuando
    # sale bien es exactamente lo que cuesta hacerla a mano cuando falla— y no
    # de un número escrito aquí, que es imposible de contrastar.
    eje = operacion.ejecuciones()
    fallas = eje[eje["resultado"] != "ok"]
    if len(fallas):
        por_motivo = fallas.groupby("motivo").agg(
            n=("resultado", "size"), minutos=("minutos_ahorrados", "mean")).reset_index()
        for _, r in por_motivo.nlargest(5, "n").iterrows():
            n, minutos = int(r["n"]), float(r["minutos"])
            horas = n * 12 * minutos / 60
            plata = horas * COSTO_HORA
            filas.append({
                "clave": _clave("excepcion", r["motivo"]),
                "tipo": "Excepción", "urgencia": "Media",
                "titulo": f"{n} pedidos detenidos: {str(r['motivo']).lower()}",
                "dato": f"{n} corridas en 30 días se pararon por lo mismo · "
                        f"≈{num(horas)} horas al año a {cop(COSTO_HORA, 0)} la hora",
                "opciones": "Corregir el dato de origen una vez · dejar la regla como está "
                            "y seguir revisando a mano",
                "costo_inaccion": plata,
                "costo_txt": f"{cop(plata, 0)} al año de revisión manual",
                "decide": "Operaciones", "quien": "",
                "sugerido": "", "origen": "Automatizaciones",
                "ambito": "Toda la compañía",
            })

    # 8. Precio contra competencia
    #
    # Es la única fila SIN cifra, y se dice: los precios publicados no traen
    # volumen atado, así que poner un número aquí sería inventarlo. Queda de
    # última en el orden y no suma al total de arriba. Antes comparaba los
    # precios en bruto; la comparación buena es por litro —la misma que usa la
    # pantalla de precios— porque un litro contra 700 ml no se comparan.
    pc = datos.precios_competencia()
    caras = pc[pc["dif_classic_pct"] > 6]
    if len(caras):
        n = int(len(caras))
        filas.append({
            "clave": _clave("precio", "competencia"),
            "tipo": "Precio", "urgencia": "Media",
            "titulo": f"{n} referencia{'s' if n != 1 else ''} por encima del "
                      f"competidor, por litro",
            "dato": "  ·  ".join(f"{_corto(r['producto'])} +{r['dif_classic_pct']:.0f}% "
                                 f"vs {r['competidor']}"
                                 for _, r in caras.nlargest(3, "dif_classic_pct").iterrows())
                    + " · sin volumen atado, no se puede cifrar el riesgo",
            "opciones": "Igualar el precio · sostenerlo y argumentar servicio · "
                        "bajar solo en las cuentas donde compiten de frente",
            "costo_inaccion": 0.0,
            "costo_txt": "Sin cifrar",
            "decide": "Dirección comercial", "quien": "",
            "sugerido": "", "origen": "Precios",
            "ambito": "Toda la compañía",
        })

    b = pd.DataFrame(filas)
    if b.empty:
        return b
    b = b.drop_duplicates(subset="clave", keep="first")
    return _recortar(b)


def _duenos() -> list:
    """Quién puede quedar de dueño.

    La lista sale de quien YA responde por compromisos en la casa, más el
    equipo comercial. No es un catálogo aparte que se desincroniza: si entra un
    vendedor nuevo, aparece aquí sin tocar nada.
    """
    base = gerencia.compromisos_base()["dueno"].dropna().astype(str)
    vend = b2b.vendedores()["vendedor"].dropna().astype(str)
    gente = {x.strip() for x in list(base) + list(vend) if x.strip()}
    return sorted(gente)


# ── Presentación ─────────────────────────────────────────────────────────────
def _tarjeta(r, dec):
    """La fila completa: el número, las opciones, lo que cuesta y quién decide."""
    color = TONO.get(r["urgencia"], CLARO)
    opciones = "".join(
        f'<li style="margin-bottom:3px">{o.strip()}</li>'
        for o in str(r["opciones"]).split("·"))
    apagado = "opacity:.5;" if dec else ""
    sello = pie = ""
    if dec:
        # Aplazada no lleva el verde de resuelta: no lo está.
        aplazada = dec["accion"] == "Aplazada"
        fondo, letra, marca = (("#FBF0E6", "#8A5A1B", "⏸") if aplazada
                               else ("#E3F0E8", "#2f7a48", "✓"))
        sello = (f'<span style="background:{fondo};color:{letra};font-size:10px;'
                 f'font-weight:800;padding:2px 8px;border-radius:3px;'
                 f'white-space:nowrap">{marca} {dec["accion"].upper()}'
                 + ("" if aplazada else f' · {dec["quien"]}') + '</span>')
        # Aplazar no tiene autor en el registro —nadie se identifica al entrar
        # al demo— y el nombre que se guardó es el dueño PROPUESTO. Decir
        # «aplazada por Andrea» sería atribuirle algo que no hizo.
        pie = (f'Aplazada el {dec["cuando"]} · vuelve a la bandeja · '
               f'queda propuesta para <b style="color:{TINTA}">{dec["quien"]}</b>'
               if aplazada else
               f'{dec["accion"]} el {dec["cuando"]} por '
               f'<b style="color:{TINTA}">{dec["quien"]}</b>')
        if dec.get("nota"):
            pie += f' &nbsp;·&nbsp; {dec["nota"]}'
    else:
        pie = (f'Decide: <b style="color:{TINTA}">{r["decide"]}</b>' +
               (f' &nbsp;·&nbsp; {r["quien"]}' if r["quien"] else ""))
    # Hasta dónde llega el filtro global en esta fila. Va junto al origen y no
    # en una nota al pie: una fila de cuota de marca sigue siendo de la
    # compañía entera aunque la cinta de arriba diga «Medellín», y quien lee
    # tiene que saberlo en la misma línea donde lee de dónde salió. Sin filtro
    # puesto no se pinta: ahí no hay nada que advertir y sería ruido.
    ambito = (f' &nbsp;·&nbsp; <span style="color:{ACENTO}">{r["ambito"]}</span>'
              if r.get("ambito") and filtros.activo() else "")
    return f"""
    <div style="{apagado}border:1px solid {PALIDO};border-left:4px solid {color};
         border-radius:5px;padding:15px 18px;margin-bottom:6px;background:#fff">
      <div style="display:flex;justify-content:space-between;gap:14px;align-items:flex-start">
        <div style="flex:1">
          <div style="font-size:9.5px;font-weight:800;letter-spacing:.13em;
               text-transform:uppercase;color:{CLARO}">
            {ICONO.get(r['tipo'],'•')} &nbsp;{r['tipo']} &nbsp;·&nbsp; {r['origen']}{ambito}</div>
          <div style="font-size:15.5px;font-weight:800;color:{TINTA};margin:4px 0 6px">
            {r['titulo']} {sello}</div>
          <div style="font-size:12px;color:{CLARO};margin-bottom:9px">{r['dato']}</div>
        </div>
        <div style="text-align:right;white-space:nowrap;padding-left:10px">
          <div style="font-size:9px;font-weight:800;letter-spacing:.1em;
               text-transform:uppercase;color:{CLARO}">Si nadie hace nada</div>
          <div style="font-size:17px;font-weight:800;color:{color};line-height:1.2">
            {r['costo_txt']}</div>
        </div>
      </div>
      <div style="font-size:11.5px;color:{TINTA};background:{FONDO_SUAVE};
           border-radius:4px;padding:9px 14px 9px 26px;margin-bottom:8px">
        <b style="margin-left:-12px">Opciones:</b>
        <ul style="margin:4px 0 0;padding-left:14px">{opciones}</ul></div>
      <div style="font-size:11px;color:{CLARO}">{pie}</div>
    </div>"""


def _grafico_plata(b, comprometidas, aplazadas):
    """Dónde está la plata en juego y cuánta ya tiene dueño.

    Contesta la pregunta previa a la bandeja: «¿de qué es el problema este
    mes?». Cartera y compras se ven distintas cuando una barra vale seis veces
    la otra, y eso no se percibe leyendo tarjetas una por una.

    Aplazada va en su propia franja y NO cuenta como resuelta: aplazar es
    precisamente no comprometerse, y la plata sigue exactamente donde estaba.
    """
    t = b.copy()
    t["situacion"] = np.where(t["clave"].isin(comprometidas), "Con dueño",
                              np.where(t["clave"].isin(aplazadas), "Aplazada",
                                       "Sin decidir"))
    g = (t.groupby(["tipo", "situacion"])["costo_inaccion"].sum()
         .unstack(fill_value=0).reindex(columns=[e[0] for e in ESTADOS],
                                        fill_value=0))
    g = g.loc[g.sum(axis=1).sort_values().index]

    fig = go.Figure()
    for estado_, color in ESTADOS:
        fig.add_trace(go.Bar(
            y=g.index, x=g[estado_] / 1e6, orientation="h", name=estado_,
            marker_color=color,
            hovertemplate="%{y} · " + estado_ + "<br>$%{x:,.1f} M<extra></extra>"))
    fig.update_layout(barmode="stack")
    # El eje va en millones a mano: con `moneda=True` el formateo solo toca el
    # eje Y, y en barras horizontales la plata está en el X.
    fig.update_xaxes(title="Utilidad en riesgo a doce meses", tickprefix="$",
                     ticksuffix=" M", tickformat=",.0f")
    return fig


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Centro de decisiones",
        "Lo que espera que alguien decida, ordenado por la plata que cuesta no decidirlo",
        "El lunes a las 7"), unsafe_allow_html=True)
    filtros.encabezado_filtro()
    if filtros.activo():
        # La cinta de arriba afirma un filtro que no todas las fuentes pueden
        # aplicar: el inventario está por bodega y no tiene canal, y la cuota
        # con una marca no tiene geografía. Decirlo aquí —y en cada tarjeta—
        # es la diferencia entre una vista filtrada y una vista que miente.
        st.caption(md(
            "Hasta dónde llega el filtro: **cartera** lo aplica entero; "
            "**cuentas** por ciudad y vendedor; **compras y vencimientos** solo "
            "por ciudad, porque el inventario está por bodega; **presupuesto** "
            "por canal y ciudad; y **marcas, excepciones y precios** no se "
            "filtran —una cuota con el proveedor o una regla de automatización "
            "son de la compañía entera—. Cada fila lo dice al lado de su origen."))

    b = _bandeja()
    if b.empty:
        st.success("No hay nada esperando decisión con estos filtros. La bandeja "
                   "en cero es el objetivo, no la excepción.")
        return

    dec = estado.decisiones()
    # Aplazar no resuelve: por eso va en su propio conjunto y la plata de esas
    # filas se sigue contando como abierta.
    comprometidas = {c for c, v in dec.items()
                     if v.get("accion") in ("Decidida", "Delegada")}
    aplazadas = {c for c, v in dec.items() if v.get("accion") == "Aplazada"}
    pendientes = b[~b["clave"].isin(set(dec))]

    total = float(b["costo_inaccion"].sum())
    # `cerrado` sale de la bandeja que se está viendo, no del archivo. Antes el
    # KPI contaba todo lo guardado en disco y el pie del gráfico solo lo que
    # estaba a la vista: los dos números divergían en cuanto un filtro sacaba
    # de la pantalla una fila ya decidida.
    en_vista = comprometidas & set(b["clave"])
    cerrado = float(b.loc[b["clave"].isin(en_vista), "costo_inaccion"].sum())
    abierto = total - cerrado
    altas = int((pendientes["urgencia"] == "Alta").sum())

    pospuestas = int(b["clave"].isin(aplazadas).sum())
    fuentes = sorted(b["origen"].unique())

    apoyos = [
        kpi("Esperando decisión", num(len(pendientes)),
            f"{altas} no pueden esperar a la otra semana"
            + (f" · {pospuestas} aplazadas" if pospuestas else ""),
            altas == 0, "",
            "Cada una trae el número, las opciones y quién decide."),
    ]
    k = [None, None, _Cap(apoyos), _Cap(apoyos)]
    k[2].markdown(kpi(
        "Con dueño y fecha", num(len(en_vista)),
        cop(cerrado, 0) + " comprometidos", len(en_vista) > 0, "✍️",
        "De las que están a la vista. Guardadas en disco, no en el navegador: "
        "siguen aquí el lunes aunque se cierre la pestaña.",
        "Cada una generó un compromiso con nombre y plazo"), unsafe_allow_html=True)
    # El número y el texto salen de la misma lista: antes el KPI era dinámico
    # —con un filtro de ciudad bajaba a cinco— y la ayuda seguía enumerando
    # ocho sistemas fijos. Un número que se desmiente al pasar el mouse.
    k[3].markdown(kpi(
        "Sistemas que se consultan", num(len(fuentes)),
        "con algo que decidir, en una sola bandeja", True, "🔗",
        "Hoy cada uno es una pestaña distinta y por eso nada se decide. En "
        "esta vista aportan filas: " + ", ".join(f.lower() for f in fuentes)
        + ". Los que no aparecen se consultaron y no tenían nada."),
        unsafe_allow_html=True)

    fila_kpi(
        kpi_hero("En juego si nadie decide hoy", cop(abierto, 0),
                 f"{len(pendientes)} decisiones esperando",
                 False,
                 "Utilidad en riesgo a doce meses. Todas las filas están en la "
                 "misma unidad: la venta de una cuenta que se apagó y el costo "
                 "de una mercancía que falta se convierten a margen antes de "
                 "sumarse. Lo aplazado sigue contando — aplazar no mueve la "
                 "plata de sitio."),
        apoyos)

    st.markdown(espacio(18), unsafe_allow_html=True)

    # ── Dónde está la plata ─────────────────────────────────────────────────
    st.markdown('<div class="ky-sub">De qué es el problema este mes</div>',
                unsafe_allow_html=True)
    st.plotly_chart(light(_grafico_plata(b, comprometidas, aplazadas), 300),
                    width="stretch")
    st.caption(md(
        f"Verde es lo que ya tiene dueño y fecha. De **{cop(total, 0)}** en "
        f"juego, **{cop(cerrado, 0)}** están asignados y **{cop(abierto, 0)}** "
        f"siguen sin que nadie responda por ellos."))

    st.markdown(espacio(10), unsafe_allow_html=True)

    st.markdown(panel(
        "Por qué esto no es una lista de alertas",
        "Una alerta dice que algo pasó. Una decisión trae <b>el número que la "
        "justifica, las opciones redactadas como se dirían en una reunión, lo que "
        "cuesta no hacer nada, y quién decide</b>. La diferencia se nota en el "
        "orden: aquí manda la plata en juego, no la gravedad que declare cada "
        "sistema. Una alerta «alta» de cuatrocientos mil pesos no puede ir encima "
        "de una «media» de catorce millones — y en sistemas separados eso pasa "
        "todos los días, que es exactamente por lo que nadie las lee.<br><br>"
        "Para que ese orden signifique algo, todas las filas están en la misma "
        "unidad: <b>utilidad en riesgo a doce meses</b>. La venta anual de una "
        "cuenta que se apagó entra a margen; el faltante de una compra, que está "
        "valorado al costo, entra por el margen de la venta que no va a ocurrir. "
        "Sumar venta con margen y con costo de mercancía da un número grande que "
        "no quiere decir nada.",
        "📋", "azul"), unsafe_allow_html=True)

    st.markdown(panel(
        "Decidir aquí crea un compromiso, no un check",
        "Para cerrar una fila hay que poner <b>dueño y plazo</b>. No es fricción "
        "de formulario: una decisión sin alguien que responda por ella y sin "
        "fecha vuelve a aparecer en la bandeja el lunes siguiente, y eso es "
        "exactamente lo que mata estas herramientas. El área que <i>decide</i> y "
        "la persona que <i>responde</i> no son lo mismo — Dirección comercial "
        "decide bajar un descuento, pero alguien con nombre tiene que llamar al "
        "cliente antes del viernes.<br><br>"
        "Lo que se guarda queda en disco, no en la memoria del navegador: se "
        "puede refrescar, cerrar la pestaña o volver el lunes y el registro "
        "sigue ahí.",
        "✍️", "ok"), unsafe_allow_html=True)

    st.markdown(espacio(6), unsafe_allow_html=True)

    # ── La bandeja ──────────────────────────────────────────────────────────
    c = st.columns([1, 1, 1, 2])
    tipos = ["Todos"] + sorted(b["tipo"].unique().tolist())
    tipo = c[0].selectbox("Tipo", tipos, key="dc_tipo")
    quien = c[1].selectbox("Decide", ["Todos"] + sorted(b["decide"].unique().tolist()),
                           key="dc_quien")
    ver = c[2].selectbox("Mostrar", ["Pendientes", "Aplazadas", "Todas"],
                         key="dc_ver")

    # Lo aplazado sale de la vista por defecto —para eso se aplaza— pero tiene
    # su propia pestaña: una fila que se aplaza tres lunes seguidos es una
    # decisión que nadie quiere tomar, y eso hay que poder verlo.
    if ver == "Todas":
        sel = b
    elif ver == "Aplazadas":
        sel = b[b["clave"].isin(aplazadas)]
    else:
        sel = pendientes
    if tipo != "Todos":
        sel = sel[sel["tipo"] == tipo]
    if quien != "Todos":
        sel = sel[sel["decide"] == quien]

    gente = _duenos() or ["Dirección"]
    plazos = list(PLAZOS)

    if sel.empty:
        st.success("Nada pendiente con ese filtro. Vale la pena revisar los otros "
                   "tipos antes de cerrar la pantalla.")

    for _, r in sel.iterrows():
        clave = r["clave"]
        d = dec.get(clave)
        st.markdown(_tarjeta(r, d), unsafe_allow_html=True)

        if d:
            fin = st.columns([1, 5])
            if fin[0].button("Reabrir", key=f"re_{clave}", width="stretch"):
                estado.olvidar(clave)
                st.rerun()
            st.markdown(espacio(6), unsafe_allow_html=True)
            continue

        with st.expander("Decidir — hay que poner dueño y plazo"):
            sug = r["sugerido"] if r["sugerido"] in gente else \
                DUENO_POR_AREA.get(r["decide"], gente[0] if gente else "")
            idx = gente.index(sug) if sug in gente else 0
            f1 = st.columns([1.3, 1.2, 2.5])
            dueno = f1[0].selectbox("Dueño", gente, index=idx, key=f"du_{clave}")
            plazo = f1[1].selectbox("Plazo", plazos, index=1, key=f"pl_{clave}")
            nota = f1[2].text_input(
                "Qué se acordó", key=f"nt_{clave}",
                placeholder=r["opciones"].split("·")[0].strip())

            f2 = st.columns([1, 1, 1, 3])
            texto = nota.strip() or r["titulo"]
            if f2[0].button("Decidir", key=f"ok_{clave}", width="stretch",
                            type="primary"):
                estado.decidir(clave, "Decidida", dueno, texto,
                               float(r["costo_inaccion"]), PLAZOS[plazo])
                st.rerun()
            if f2[1].button("Delegar", key=f"dl_{clave}", width="stretch"):
                estado.decidir(clave, "Delegada", dueno, texto,
                               float(r["costo_inaccion"]), PLAZOS[plazo])
                st.rerun()
            if f2[2].button("Aplazar", key=f"ap_{clave}", width="stretch"):
                # Aplazar también se registra: si una fila se aplaza tres veces
                # seguidas eso es información, no ruido. Pero NO crea
                # compromiso — `estado.decidir` solo lo hace con Decidida y
                # Delegada, y aplazar es justamente no comprometerse.
                estado.decidir(clave, "Aplazada", dueno,
                               texto, float(r["costo_inaccion"]), PLAZOS[plazo])
                st.rerun()

        st.markdown(espacio(8), unsafe_allow_html=True)

    st.markdown(espacio(14), unsafe_allow_html=True)

    # ── El registro ─────────────────────────────────────────────────────────
    #
    # Esta tabla es el módulo entero. Sin ella lo de arriba es un tablero con
    # botones; con ella se puede contestar en enero por qué se le bajó el
    # descuento a una cuenta en septiembre, quién lo decidió y con qué número a
    # la vista.
    st.markdown('<div class="ky-sub">El registro: quién decidió qué y cuándo</div>',
                unsafe_allow_html=True)

    if not dec:
        st.caption("Todavía no hay decisiones registradas. Cada una que se tome "
                   "aquí queda con dueño, fecha y el número que la justificaba.")
    else:
        # Lo que se muestra es lo que se registró ENTONCES, no el titular de
        # hoy. La versión anterior prefería el título recalculado de la
        # bandeja: si Gótica pasaba de 31 a 45 días de mora, la tabla decía que
        # en septiembre se había decidido sobre 45 días. Una tabla que sirve
        # para contestar en enero por qué se bajó un descuento en septiembre no
        # puede reescribir septiembre con los datos de enero.
        reg = pd.DataFrame([{
            "Cuándo": v.get("cuando", ""),
            "Qué se decidió": v.get("nota", "") or c,
            "Acción": v.get("accion", ""),
            "Dueño": v.get("quien", ""),
            "Plata que estaba en juego": cop(v.get("valor", 0), 0),
        } for c, v in dec.items()])
        reg = reg.sort_values("Cuándo", ascending=False)
        st.dataframe(reg, hide_index=True, width="stretch")

        comp = {k: v for k, v in estado.compromisos().items() if k.startswith("D-")}
        if comp:
            st.caption(
                f"Las {len(comp)} decisiones con acción «Decidida» o «Delegada» "
                f"generaron su compromiso con dueño y fecha de vencimiento. "
                f"Cerrar un compromiso exige escribir **qué pasó**, que es lo que "
                f"permite mirar dentro de tres meses si la decisión sirvió.")

    st.markdown(espacio(14), unsafe_allow_html=True)
    st.markdown(panel(
        "Qué pasa al pulsar «Decidir»",
        "Queda el registro de quién decidió, cuándo y con qué número a la vista, "
        "y se crea el compromiso con dueño y fecha de vencimiento. Eso es lo que "
        "permite revisar en enero por qué se le bajó el descuento a una cuenta en "
        "septiembre. Conectado de verdad, además se dispara el flujo "
        "correspondiente en Loggro o Salesforce, que <b>prepara la acción y "
        "espera confirmación</b>. El sistema nunca ejecuta solo lo que mueve "
        "plata.",
        "✓", "alerta"), unsafe_allow_html=True)

    with st.expander("Para la demostración"):
        st.caption(
            f"Las decisiones y los compromisos se guardan en `{estado.donde()}`, "
            f"fuera del árbol del proyecto —escribirlos dentro hace que Streamlit "
            f"los lea como código cambiado y recargue en bucle—. Este botón deja "
            f"el demo como recién instalado.")
        if st.button("Reiniciar el demo", key="dc_reset"):
            estado.reiniciar()
            st.rerun()
