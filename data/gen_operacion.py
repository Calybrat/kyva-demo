#!/usr/bin/env python3
"""Datos de OPERACIÓN: inventario, proveedores, compras, automatizaciones y alertas.

Existe aparte de `generate_data.py` por una razón de diseño, no de comodidad:
**todo lo de aquí se DERIVA de lo que ya existe**, no se inventa al lado.

El inventario sale del `stock_u` del catálogo. La demanda sale de las líneas de
pedido reales. Los plazos de entrega salen del proveedor de cada referencia. Si
se generara en paralelo, un día el panel diría que hay 108 botellas de Chivas en
la pantalla de surtido y 74 en la de reposición, y el cliente lo vería antes que
nosotros. La consistencia se garantiza por construcción.

Lo que esto agrega al demo es lo que Javier pidió en la reunión del 19-sep:
pedidos, consulta de inventario, listas de precio por canal, integración con
Loggro, despacho automático al operador logístico, y forecasting/MRP para
planear compras. El panel dejaba ver; esto hace.

    python3 data/gen_operacion.py
"""
import numpy as np
import pandas as pd
from pathlib import Path

AQUI = Path(__file__).parent
RNG = np.random.default_rng(20260919)

CORTE = pd.Timestamp("2026-08-31")

# Las dos operaciones reales de KYVA. Bogotá es la casa matriz; Medellín abrió
# después y por eso mueve menos, tiene menos surtido y depende de traslados.
BODEGAS = {"Bogotá": 0.68, "Medellín": 0.32}

# Plazos de reposición. La diferencia entre importado y nacional es LA
# restricción del negocio: una cerveza nacional se repone en tres días, un
# whisky escocés tarda dos meses y medio entre orden y bodega. Planear compras
# de diciembre en noviembre es tarde para la mitad del catálogo, y esa es la
# conversación que el módulo de reposición tiene que provocar.
# Los plazos siguen la ruta real, no una media genérica: el vino chileno y
# argentino cruza en barco desde Valparaíso o Buenos Aires a Cartagena en
# tres a seis semanas, mientras el whisky escocés y la champaña francesa
# pasan de dos meses. Poner a todo lo importado en el mismo rango largo
# ponía medio catálogo en rojo por un supuesto, no por un hallazgo.
PLAZOS = {           # (días mínimo, días máximo, nacional?)
    "Cerveza":               (3, 8, True),
    "Aguardiente":           (5, 12, True),     # colombiano
    "Mixers y aguas":        (5, 14, True),
    "Ron":                   (12, 25, True),
    "Accesorios gourmet":    (20, 40, False),
    "Vino":                  (25, 45, False),   # Chile y Argentina
    "Tequila y mezcal":      (30, 55, False),   # México
    "Licores y aperitivos":  (35, 60, False),
    "Vodka":                 (35, 60, False),
    "Ginebra":               (38, 62, False),
    "Cognac, brandy y pisco":(40, 68, False),
    "Champaña y espumosos":  (45, 75, False),   # Francia
    "Whisky":                (55, 85, False),   # Escocia
}
PLAZO_DEF = (30, 55, False)

# El pico de diciembre. Un distribuidor de licores hace en noviembre y
# diciembre una parte desproporcionada del año, y el corte del demo es el
# 31 de agosto — o sea, en plena ventana de decisión de esa compra.
PICO = pd.Timestamp("2026-12-01")
FACTOR_PICO = 2.6          # cuánto se multiplica la demanda diaria en el pico

# Listas de precio por canal. KYVA no vende al mismo precio a un bar de
# Chapinero que a un club social con contrato anual, y hoy eso vive en la
# cabeza de quien toma el pedido. Ponerlo explícito es medio módulo de
# automatización: es la regla que el agente tiene que aplicar sin preguntar.
CANALES_B2B = {
    "Restaurantes":   {"desc": 0.22, "plazo_pago": 30, "peso": 0.29},
    "Bares":          {"desc": 0.25, "plazo_pago": 15, "peso": 0.24},
    "Discotecas":     {"desc": 0.27, "plazo_pago": 15, "peso": 0.16},
    "Clubes sociales":{"desc": 0.19, "plazo_pago": 45, "peso": 0.13},
    "Empresas":       {"desc": 0.15, "plazo_pago": 30, "peso": 0.18},
}


def _plazo(cat):
    lo, hi, nac = PLAZOS.get(cat, PLAZO_DEF)
    return int(RNG.integers(lo, hi + 1)), nac


# ── 1. Inventario por bodega ────────────────────────────────────────────────
def gen_inventario(cat: pd.DataFrame) -> pd.DataFrame:
    """El stock del catálogo, repartido entre las dos bodegas.

    No se reparte al 68/32 parejo: Medellín no trae todo el catálogo. Las
    referencias de baja rotación sencillamente no están allá, que es el caso
    real que hace interesante el módulo de traslados.
    """
    # Medellín no trae todo el catálogo: abrió después y solo surte lo que rota.
    # Esto se decide UNA vez por referencia y manda tanto el stock como la
    # demanda. Repartir la demanda al 32% en una referencia que Medellín no
    # surte inventa un faltante que no existe — y como el punto de reorden se
    # calcula sobre la demanda, marcaba media bodega en rojo.
    corte_rota = cat["unidades_90d"].quantile(0.45)

    filas = []
    for _, r in cat.iterrows():
        total = int(r["stock_u"])
        dias, nac = _plazo(r["categoria"])
        en_med = (r["unidades_90d"] > corte_rota) and RNG.random() > 0.22
        pesos = BODEGAS if en_med else {"Bogotá": 1.0, "Medellín": 0.0}

        for bodega, peso in pesos.items():
            # El reparto real nunca es exacto; lo que no se va a una bodega
            # queda en la otra, así que la suma sigue dando el stock del
            # catálogo y la pantalla de surtido no se contradice con esta.
            u = int(round(total * peso))
            filas.append({
                "sku": r["sku"], "nombre": r["nombre"], "categoria": r["categoria"],
                "marca": r["marca"], "proveedor": r["proveedor"], "bodega": bodega,
                "unidades": max(u, 0),
                "costo_unit": r["costo_unit"],
                "valor_inventario": max(u, 0) * r["costo_unit"],
                "dias_reposicion": dias,
                "nacional": nac,
                "surtida_aqui": peso > 0,
                "unidades_90d": r["unidades_90d"],
                "demanda_dia": round(r["unidades_90d"] / 90 * peso, 3),
            })
    inv = pd.DataFrame(filas)

    inv["dias_cobertura"] = np.where(
        inv["demanda_dia"] > 0,
        (inv["unidades"] / inv["demanda_dia"]).round(0), np.nan)

    # Punto de reorden = lo que se vende mientras llega el pedido, más un
    # colchón del 15%. Sin colchón, cualquier semana buena deja el quiebre
    # servido; con un colchón grande todo el catálogo aparece en rojo y el
    # módulo deja de ser accionable, que es el error que tenía antes.
    inv["punto_reorden"] = np.ceil(
        inv["demanda_dia"] * inv["dias_reposicion"] * 1.15).astype(int)
    inv["hay_que_pedir"] = (inv["unidades"] < inv["punto_reorden"]) & (inv["demanda_dia"] > 0)

    # ── La ventana de diciembre ──────────────────────────────────────────────
    # Esto es lo que vuelve el módulo accionable en vez de una lista de rojos.
    #
    # El corte del demo es el 31 de agosto. Un whisky escocés tarda 69 días en
    # promedio entre orden y bodega, así que la última fecha para pedirlo y
    # tenerlo antes del 1 de diciembre es a mediados de septiembre —dentro de
    # dos semanas—, mientras que una cerveza nacional se puede pedir el 20 de
    # noviembre y llega. No es que KYVA tenga poco inventario: es que la
    # ventana de decisión para la mitad del catálogo se está cerrando ahora y
    # no hay quién lo esté mirando referencia por referencia.
    inv["fecha_limite_pedido"] = (
        PICO - pd.to_timedelta(inv["dias_reposicion"] + 7, unit="D")).dt.date
    dias_para_limite = (pd.to_datetime(inv["fecha_limite_pedido"]) - CORTE).dt.days
    inv["dias_para_limite"] = dias_para_limite

    # Lo que hace falta para aguantar el pico, no el día normal.
    inv["necesidad_pico"] = np.ceil(
        inv["demanda_dia"] * FACTOR_PICO * 45).astype(int)      # seis semanas de pico
    inv["faltante_pico"] = np.maximum(
        inv["necesidad_pico"] - inv["unidades"], 0).astype(int)

    inv["urgencia"] = np.select(
        [dias_para_limite < 0, dias_para_limite <= 21, dias_para_limite <= 60],
        ["Ventana cerrada", "Pedir esta semana", "Pedir este mes"],
        default="Hay tiempo")
    inv.loc[inv["demanda_dia"] <= 0, "urgencia"] = "No rota"
    return inv


# ── 2. Proveedores ──────────────────────────────────────────────────────────
def gen_proveedores(inv: pd.DataFrame) -> pd.DataFrame:
    """Un proveedor por fila, con lo que decide una compra: plazo y mínimo.

    El pedido mínimo es la razón por la que no se compra «lo que falta»: si el
    importador exige 60 unidades y faltan 12, o se esperan tres meses o se
    compran 60 y se inmoviliza capital. Ese dilema es el módulo de compras.
    """
    g = inv.groupby("proveedor").agg(
        referencias=("sku", "nunique"),
        valor_inventario=("valor_inventario", "sum"),
        dias_reposicion=("dias_reposicion", "mean"),
        nacional=("nacional", "max"),
        demanda_dia=("demanda_dia", "sum"),
    ).reset_index()
    g["dias_reposicion"] = g["dias_reposicion"].round(0).astype(int)
    g["pedido_minimo_u"] = np.where(g["nacional"], 24, 60)
    g["moneda"] = np.where(g["nacional"], "COP", "USD")
    # Cumplimiento histórico: los nacionales entregan mejor, y esto es lo que
    # justifica pedirle antes al que falla más, no más cantidad.
    g["cumplimiento_pct"] = np.where(
        g["nacional"], RNG.uniform(88, 99, len(g)), RNG.uniform(68, 94, len(g))).round(1)
    return g.sort_values("valor_inventario", ascending=False)


# ── 3. Órdenes de compra en curso ───────────────────────────────────────────
def gen_ordenes(inv: pd.DataFrame, prov: pd.DataFrame) -> pd.DataFrame:
    """Lo que ya viene en camino. Restarlo es lo que separa un MRP de una lista.

    Sin esto el panel diría «pida 60 de Chivas» cuando hay 60 llegando el
    martes. Comprar dos veces lo mismo es el error clásico y caro.
    """
    faltantes = inv[inv["hay_que_pedir"]].copy()
    if faltantes.empty:
        return pd.DataFrame()
    muestra = faltantes.sample(min(len(faltantes), 46), random_state=7)
    filas = []
    for i, (_, r) in enumerate(muestra.iterrows(), 1):
        emitida = CORTE - pd.Timedelta(days=int(RNG.integers(3, 55)))
        eta = emitida + pd.Timedelta(days=int(r["dias_reposicion"]))
        # Un cuarto de las importadas va tarde. Es el dato que hace creíble el
        # cumplimiento del proveedor y el que dispara la alerta de riesgo.
        atraso = int(RNG.integers(4, 22)) if (not r["nacional"] and RNG.random() < 0.28) else 0
        u = int(max(r["punto_reorden"] - r["unidades"],
                    24 if r["nacional"] else 60))
        filas.append({
            "orden": f"OC-2026-{i:04d}",
            "sku": r["sku"], "nombre": r["nombre"], "proveedor": r["proveedor"],
            "bodega": r["bodega"], "unidades": u,
            "valor": round(u * r["costo_unit"]),
            "emitida": emitida.date(), "eta": eta.date(),
            "eta_real": (eta + pd.Timedelta(days=atraso)).date(),
            "dias_atraso": atraso,
            "estado": "En tránsito" if eta > CORTE else ("Atrasada" if atraso else "Recibida"),
        })
    return pd.DataFrame(filas)


# ── 4. Catálogo de automatizaciones ─────────────────────────────────────────
def gen_automatizaciones() -> pd.DataFrame:
    """Los flujos. Cada uno dice qué lo dispara, qué toca y dónde para.

    `aprueba` es la columna más importante del archivo y es la que hay que
    defender en la reunión: **ningún flujo que mueva plata o comprometa
    inventario se ejecuta solo.** El sistema prepara y un humano confirma. Un
    agente que emite órdenes de compra sin que nadie mire es la forma más
    rápida de que a un cliente le lleguen 600 botellas que no pidió.
    """
    F = [
        ("AUT-01", "Pedido B2B por WhatsApp o correo", "Pedidos",
         "Llega un mensaje de un cliente B2B",
         "Lee el mensaje · identifica cliente y referencias · valida stock en la bodega que "
         "le corresponde · aplica la lista de precio de su canal · arma el pedido en Loggro",
         "Loggro · Salesforce", True, 14, 0.94,
         "Un bar escribe «mándame 12 Club Colombia y 6 Baileys» a las 11 de la noche. "
         "Hoy alguien lo transcribe al otro día."),
        ("AUT-02", "Consulta de inventario en lenguaje natural", "Inventario",
         "Alguien pregunta por disponibilidad",
         "Consulta las dos bodegas · descuenta lo comprometido en pedidos abiertos · "
         "suma lo que viene en tránsito con su fecha",
         "Loggro", False, 3, 0.99,
         "«¿Cuánto Don Julio tengo en Medellín?» se responde sin abrir el ERP, y "
         "cuenta lo que llega el jueves."),
        ("AUT-03", "Despacho al operador logístico", "Logística",
         "Un pedido queda confirmado y pagado o aprobado a crédito",
         "Arma la guía · la manda al operador que cubre esa zona · devuelve el número "
         "de rastreo al cliente por su canal",
         "Operador logístico · WooCommerce", True, 9, 0.97,
         "Entre confirmar y despachar hoy hay una persona copiando direcciones."),
        ("AUT-04", "Sincronía de precios y stock con la tienda", "Precios",
         "Cambia un costo en Loggro o se agota una referencia",
         "Recalcula el precio de venta según el margen objetivo · actualiza WooCommerce · "
         "oculta lo agotado · avisa qué cambió",
         "Loggro · WooCommerce", False, 6, 0.98,
         "Vender en línea a precio viejo después de que sube el dólar es margen "
         "regalado, y se nota un mes después."),
        ("AUT-05", "Sugerencia de orden de compra", "Compras",
         "Diario, 6:00 a. m.",
         "Proyecta demanda por referencia y bodega · descuenta tránsito · respeta el "
         "pedido mínimo del proveedor · arma la orden sugerida",
         "Loggro", True, 22, 0.91,
         "Con plazos de 60 a 85 días en importados, decidir en noviembre la compra "
         "de diciembre es decidir tarde."),
        ("AUT-06", "Cobro de cartera vencida", "Cartera",
         "Una factura pasa de su plazo",
         "Manda el recordatorio con la factura adjunta · escala al comercial a los "
         "5 días · bloquea nuevos pedidos a crédito a los 15",
         "Loggro · Salesforce", False, 11, 0.96,
         "Las discotecas pagan a 15 días y nadie lleva la cuenta a mano."),
        ("AUT-07", "Traslado entre bodegas", "Inventario",
         "Una referencia se agota en una ciudad y sobra en la otra",
         "Detecta el desbalance · calcula si sale más barato trasladar que comprar · "
         "propone el traslado con su costo",
         "Loggro", True, 4, 0.93,
         "Medellín no trae todo el catálogo; hoy el faltante se resuelve llamando."),
        ("AUT-08", "Reporte de cierre a dirección", "Reportes",
         "Lunes, 7:00 a. m.",
         "Arma el cierre de la semana por canal y ciudad · señala lo que se salió "
         "de lo normal · lo manda por correo",
         "Google Workspace", False, 2, 1.00,
         "El reporte que hoy alguien arma el lunes en la mañana."),
    ]
    return pd.DataFrame(F, columns=[
        "id", "nombre", "area", "disparador", "pasos", "sistemas",
        "aprueba", "veces_dia", "acierto", "porque"])


# ── 5. Bitácora de ejecuciones ──────────────────────────────────────────────
def gen_ejecuciones(aut: pd.DataFrame, inv: pd.DataFrame) -> pd.DataFrame:
    """Treinta días de corridas reales, con sus fallas.

    Que haya fallas es deliberado. Javier preguntó explícitamente por el nivel
    de error y por alucinaciones — un panel que reporta 100% de acierto
    contesta esa pregunta con una mentira, y él lo va a notar. Lo que da
    confianza no es no fallar: es que las fallas queden registradas, digan por
    qué y muestren quién las atendió.
    """
    clientes = ["Bar Amarillo", "Club Colombia Bogotá", "Andrés Carne de Res",
                "Discoteca Theatron", "Club El Nogal", "Restaurante Criterión",
                "Gaira Café", "Hotel Estelar", "Bar Vintrash", "Club Campestre",
                "Grupo Takami", "Mesa Franca", "Sierra Nevada Bar", "El Cielo"]
    filas = []
    for _, a in aut.iterrows():
        for d in range(30):
            dia = CORTE - pd.Timedelta(days=29 - d)
            if dia.weekday() == 6 and a["area"] not in ("Pedidos", "Inventario"):
                continue
            n = max(0, int(RNG.poisson(a["veces_dia"])))
            for _ in range(n):
                ok = RNG.random() < a["acierto"]
                h = int(RNG.integers(6, 23))
                fila = {
                    "id": a["id"], "flujo": a["nombre"], "area": a["area"],
                    "momento": dia + pd.Timedelta(hours=h, minutes=int(RNG.integers(0, 60))),
                    "resultado": "ok" if ok else "revisar",
                    "cliente": RNG.choice(clientes) if a["area"] in ("Pedidos", "Logística", "Cartera") else "",
                    "segundos": round(float(RNG.uniform(2.5, 14)), 1),
                    "minutos_ahorrados": round(float(RNG.uniform(4, 18)), 1),
                    "motivo": "" if ok else str(RNG.choice([
                        "Referencia ambigua: dos productos con el mismo nombre corto",
                        "Cliente nuevo sin lista de precio asignada",
                        "Cantidad por encima del stock disponible en esa bodega",
                        "Dirección de entrega fuera de la zona del operador",
                        "El mensaje no traía cantidad para una de las referencias",
                    ])),
                }
                filas.append(fila)
    e = pd.DataFrame(filas)
    return e.sort_values("momento", ascending=False)


# ── 6. Alertas ──────────────────────────────────────────────────────────────
def gen_alertas(inv: pd.DataFrame, oc: pd.DataFrame) -> pd.DataFrame:
    """Alertas que se DISPARARON, con lo que pasó después.

    Una lista de reglas no impresiona a nadie: cualquiera escribe reglas. Lo
    que vale es la columna `desenlace` — qué cambió porque alguien se enteró a
    tiempo. Sin eso, el módulo de alertas es otro informe.
    """
    filas = []
    criticas = inv[inv["hay_que_pedir"] & (inv["unidades"] == 0)].head(9)
    for _, r in criticas.iterrows():
        filas.append({
            "tipo": "Quiebre de stock", "gravedad": "Alta",
            "que": f"{r['nombre'][:42]} en cero · {r['bodega']}",
            "cuando": (CORTE - pd.Timedelta(days=int(RNG.integers(1, 21)))).date(),
            "regla": "Unidades en cero con venta en los últimos 90 días",
            "aviso": "Compras + comercial de la ciudad",
            "desenlace": str(RNG.choice([
                "Orden emitida el mismo día",
                "Se trasladó desde la otra bodega",
                "Se ofreció la referencia equivalente al cliente",
                "Sin atender — se perdió el pedido"], p=[.45, .25, .2, .1])),
        })
    for _, r in oc[oc["dias_atraso"] > 0].head(7).iterrows():
        filas.append({
            "tipo": "Importación atrasada", "gravedad": "Alta",
            "que": f"{r['orden']} · {r['proveedor']} · {r['dias_atraso']} días tarde",
            "cuando": r["emitida"], "regla": "ETA vencida sin recepción",
            "aviso": "Compras", "desenlace": "Se avisó a los comerciales que la venden",
        })
    quietas = inv[(inv["unidades_90d"] == 0) & (inv["valor_inventario"] > 2_500_000)].head(8)
    for _, r in quietas.iterrows():
        filas.append({
            "tipo": "Capital quieto", "gravedad": "Media",
            "que": f"{r['nombre'][:42]} · {r['valor_inventario']/1e6:.1f} M sin rotar 90 días",
            "cuando": (CORTE - pd.Timedelta(days=int(RNG.integers(2, 40)))).date(),
            "regla": "Más de 2,5 M inmovilizados sin una sola venta en 90 días",
            "aviso": "Compras + dirección",
            "desenlace": str(RNG.choice([
                "Entró a promoción del mes", "Se ofreció al canal corporativo",
                "Pendiente de decisión"], p=[.4, .35, .25])),
        })
    return pd.DataFrame(filas).sort_values("cuando", ascending=False)


def main():
    cat = pd.read_csv(AQUI / "catalogo.csv")
    inv = gen_inventario(cat)
    prov = gen_proveedores(inv)
    oc = gen_ordenes(inv, prov)
    aut = gen_automatizaciones()
    eje = gen_ejecuciones(aut, inv)
    ale = gen_alertas(inv, oc)

    for df, nombre, comp in [(inv, "inventario_bodega.csv", True),
                             (prov, "proveedores.csv", False),
                             (oc, "ordenes_compra.csv", False),
                             (aut, "automatizaciones.csv", False),
                             (eje, "ejecuciones.csv", True),
                             (ale, "alertas.csv", False)]:
        ruta = AQUI / (nombre + (".gz" if comp else ""))
        df.to_csv(ruta, index=False, compression="gzip" if comp else None)
        print(f"  {nombre:26} {len(df):>7,} filas")

    print(f"\n  Inventario: {inv['valor_inventario'].sum()/1e6:,.0f} M COP en dos bodegas")
    print(f"  Hay que pedir: {int(inv['hay_que_pedir'].sum())} referencias")
    print(f"  En tránsito: {len(oc)} órdenes · {oc['valor'].sum()/1e6:,.0f} M")
    print(f"  Automatizaciones: {len(aut)} flujos · {len(eje):,} corridas en 30 días")
    print(f"  Acierto global: {(eje['resultado'] == 'ok').mean()*100:.1f}%")
    print(f"  Horas al mes que devuelven: {eje['minutos_ahorrados'].sum()/60:,.0f}")


if __name__ == "__main__":
    main()
