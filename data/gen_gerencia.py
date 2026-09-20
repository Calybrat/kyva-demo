#!/usr/bin/env python3
"""Lo que faltaba para que esto sea gerencia y no diagnóstico.

Escrito contra una revisión adversaria hecha por un COO de distribuidora con 15
años en el sector. Su veredicto fue: *«el mejor diagnóstico que he visto de mi
negocio, y sigue siendo un diagnóstico. Yo no pago por que me expliquen mi
empresa; pago por dejar de perder plata los martes.»*

Los cinco huecos que señaló, y que esta capa llena:

1. **Cartera de verdad.** Lo que había era `venta_mensual × plazo/30`, que asume
   que todo el mundo paga en el plazo pactado. En este negocio el plazo pactado
   y el real se llevan tres semanas. Aquí hay facturas, con fecha, edad y saldo.

2. **Cumplimiento con las marcas.** KYVA es distribuidor exclusivo de Mil
   Demonios. Eso trae una cuota de sell-in firmada y un rebate de fin de año
   que, en muchos meses, **es toda la utilidad**. No estaba en ninguna parte. Y
   la bonificación —las botellas que se regalan para cerrar un pedido— es el
   descuento oculto que se come el margen sin aparecer en ningún informe.

3. **Lo que NO se vendió.** Todo el panel medía ventas. La plata que se pierde
   no está ahí: está en el martes que el bar le compró el aguardiente a otro
   porque no había, y no vuelve a pedirlo en tres meses.

4. **Vencimientos.** Venden cerveza, que dura cuatro a seis meses. El módulo de
   reposición razonaba solo hacia adelante.

5. **El punto de venta.** El panel sabía todo lo que sale de la bodega y nada de
   lo que pasa en el bar: qué rota, a qué precio lo pone en carta, qué marca de
   la competencia está en la barra, qué material POP tiene.

Y dos cosas que no son datos sino estructura, y que son la diferencia entre un
tablero y un sistema: **presupuesto** contra el cual medir, y **compromisos**
con dueño y fecha que sobreviven al lunes siguiente.

    python3 data/gen_gerencia.py
"""
import numpy as np
import pandas as pd
from pathlib import Path

AQUI = Path(__file__).parent
RNG = np.random.default_rng(20260921)
CORTE = pd.Timestamp("2026-08-31")
MESES = pd.date_range("2024-09-01", "2026-08-01", freq="MS")

# ── Las marcas con contrato ──────────────────────────────────────────────────
# El rebate es escalonado, como en la vida real: no se gana por vender un poco
# más, se gana por cruzar un umbral. Por eso el último mes del trimestre se
# decide si conviene empujar o no — y esa decisión hoy la toma nadie.
MARCAS_CONTRATO = [
    # marca, exclusiva, cuota trimestral (unidades), rebate por tramo
    ("Mil Demonios",  True,  1200, [(0.85, 0.02), (1.00, 0.055), (1.15, 0.085)]),
    ("Ron Defensor",  True,   800, [(0.85, 0.02), (1.00, 0.050), (1.20, 0.080)]),
    ("Marcel Thorel", True,   450, [(0.90, 0.03), (1.00, 0.060), (1.25, 0.095)]),
    ("Pernod Ricard", False, 2600, [(0.90, 0.015), (1.00, 0.035), (1.10, 0.055)]),
    ("Diageo",        False, 2200, [(0.90, 0.015), (1.00, 0.040), (1.15, 0.060)]),
    ("Bacardí",       False, 1500, [(0.92, 0.012), (1.00, 0.030), (1.12, 0.050)]),
]

MOTIVO_DEVOLUCION = {
    "Producto vencido": 0.18, "Avería en transporte": 0.31,
    "Pedido equivocado": 0.24, "No rotó en el punto": 0.19,
    "Diferencia de precio": 0.08,
}
MOTIVO_QUIEBRE = {
    "Sin stock en bodega": 0.44, "Importación atrasada": 0.21,
    "Comprometido en otro pedido": 0.19, "Lote vencido retirado": 0.09,
    "Error de inventario": 0.07,
}
POP = ["Nevera exhibidora", "Habladores de barra", "Cenefa", "Menú de coctelería",
       "Backbar iluminado", "Copas de marca", "Ninguno"]
COMPETENCIA = ["Dislicores", "La Licorera", "Quality Brands", "Distrisegovia",
               "Compra directa importador", "Ninguna"]


# ── 1. Facturas y cartera real ───────────────────────────────────────────────
def gen_facturas(ventas, cuentas):
    """Cada entrega es una factura, con su fecha real de pago.

    Lo importante no es que existan las facturas: es que **el plazo pactado y el
    real son distintos**. Un bar a 15 días paga a 31 de media; un club social a
    45 paga a 52 pero nunca deja de pagar. Esa diferencia es toda la gestión de
    cartera, y con el cálculo teórico anterior era invisible.
    """
    # Cuánto se estira cada canal sobre su plazo, y qué tan errático es.
    ATRASO = {"Discotecas": (18, 16), "Bares": (14, 12), "Restaurantes": (9, 8),
              "Clubes sociales": (7, 5), "Empresas": (11, 9)}
    c = cuentas.set_index("cuenta_id")
    filas, n = [], 1
    for _, v in ventas.iterrows():
        mes = pd.Timestamp(v["mes"] + "-01")
        if mes < CORTE - pd.Timedelta(days=200):      # solo lo reciente importa
            continue
        cta = c.loc[v["cuenta_id"]]
        por_factura = max(int(v["entregas"]), 1)
        for i in range(por_factura):
            dia = int(RNG.integers(1, 28))
            emitida = mes + pd.Timedelta(days=dia)
            if emitida > CORTE:
                continue
            media, disp = ATRASO.get(v["canal"], (10, 9))
            atraso = max(0, int(RNG.normal(media, disp)))
            vence = emitida + pd.Timedelta(days=int(cta["plazo_pago"]))
            pagada_el = vence + pd.Timedelta(days=atraso)
            filas.append({
                "factura": f"FV-{n:05d}", "cuenta_id": v["cuenta_id"],
                "nombre": cta["nombre"], "canal": v["canal"], "ciudad": v["ciudad"],
                "zona": v["zona"], "vendedor": v["vendedor"],
                "emitida": emitida.date(), "vence": vence.date(),
                "valor": round(v["neto"] / por_factura),
                "plazo": int(cta["plazo_pago"]),
                "pagada": pagada_el <= CORTE,
                "pagada_el": pagada_el.date() if pagada_el <= CORTE else "",
                "dias_atraso_real": atraso if pagada_el <= CORTE else
                                    max(0, (CORTE - vence).days),
            })
            n += 1
    f = pd.DataFrame(filas)
    abierta = ~f["pagada"]
    f["saldo"] = np.where(abierta, f["valor"], 0)
    dias = (CORTE - pd.to_datetime(f["vence"])).dt.days
    f["dias_vencida"] = np.where(abierta, dias.clip(lower=0), 0)
    f["tramo"] = pd.cut(f["dias_vencida"], [-1, 0, 30, 60, 90, 9999],
                        labels=["Corriente", "1 a 30", "31 a 60", "61 a 90", "Más de 90"])
    return f


# ── 2. Cuotas de marca, bonificación y rebate ────────────────────────────────
def gen_marcas(ventas, catalogo):
    """El compromiso con el proveedor, que para un distribuidor ES la utilidad.

    La mecánica del rebate escalonado es la que hace interesante el módulo: no
    se gana por vender más, se gana por **cruzar un umbral**. Estar en 97% de la
    cuota a quince días del cierre y no darse cuenta cuesta el tramo entero —y
    normalmente vale más que el margen de esas unidades—.
    """
    cat = catalogo.groupby("marca")["costo_unit"].mean().to_dict()
    filas = []
    for m in MESES:
        trimestre = f"{m.year}-T{(m.month - 1)//3 + 1}"
        for marca, excl, cuota_t, tramos in MARCAS_CONTRATO:
            costo = cat.get(marca, 95_000)
            base = cuota_t / 3
            est = {1: .72, 2: .78, 3: .88, 4: .92, 5: .97, 6: 1.02,
                   7: .99, 8: .95, 9: 1.04, 10: 1.18, 11: 1.74, 12: 2.45}[m.month]
            u = int(base * est * RNG.uniform(0.74, 1.24))
            # La bonificación: botellas regaladas para cerrar. Es descuento que
            # no aparece en ninguna lista de precios y nadie lo suma al año.
            bonif = int(u * RNG.uniform(0.015, 0.075))
            filas.append({
                "mes": m.strftime("%Y-%m"), "trimestre": trimestre,
                "marca": marca, "exclusiva": excl,
                "unidades": u, "bonificadas": bonif,
                "cuota_mes": round(cuota_t / 3),
                "costo_unit": costo,
                "compra": round(u * costo),
                "costo_bonificacion": round(bonif * costo),
            })
    d = pd.DataFrame(filas)

    # Rebate por trimestre: se mira el cumplimiento y se busca el tramo.
    reb = []
    for (tri, marca), g in d.groupby(["trimestre", "marca"]):
        cfg = next(x for x in MARCAS_CONTRATO if x[0] == marca)
        cuota, tramos = cfg[2], cfg[3]
        u = int(g["unidades"].sum())
        cumpl = u / cuota
        tasa = 0.0
        for umbral, t in tramos:
            if cumpl >= umbral:
                tasa = t
        siguiente = next((umbral for umbral, _ in tramos if cumpl < umbral), None)
        reb.append({
            "trimestre": tri, "marca": marca, "exclusiva": cfg[1],
            "cuota": cuota, "unidades": u, "cumplimiento": round(cumpl * 100, 1),
            "tasa_rebate": tasa, "compra": float(g["compra"].sum()),
            "rebate": round(float(g["compra"].sum()) * tasa),
            "faltan_para_siguiente": int(max(0, (siguiente or cumpl) * cuota - u)),
            "siguiente_tramo": (next((t for umbral, t in tramos if cumpl < umbral), None)),
            "bonificadas": int(g["bonificadas"].sum()),
            "costo_bonificacion": float(g["costo_bonificacion"].sum()),
        })
    return d, pd.DataFrame(reb)


# ── 3. Lo que no se vendió ───────────────────────────────────────────────────
def gen_quiebres(ventas, catalogo, cuentas):
    """Pedidos que llegaron y no se pudieron servir completos.

    Es la cifra que ningún ERP muestra bien porque el pedido se corrige antes de
    grabarse: el vendedor llama, dice «de ese no hay», y el bar pide otra cosa o
    no pide. La venta perdida nunca queda registrada, y por eso nadie sabe
    cuánto cuesta un quiebre.
    """
    cat = catalogo.sample(160, random_state=3)
    c = cuentas.sample(min(len(cuentas), 45), random_state=5)
    filas = []
    for _, v in ventas[ventas["mes"] >= "2026-03"].iterrows():
        if RNG.random() > 0.30:
            continue
        cta = c[c["cuenta_id"] == v["cuenta_id"]]
        if cta.empty:
            continue
        for _ in range(int(RNG.integers(1, 4))):
            sku = cat.sample(1).iloc[0]
            pedidas = int(RNG.integers(3, 30))
            servidas = int(pedidas * RNG.uniform(0, 0.75))
            if servidas >= pedidas:
                continue
            motivo = str(RNG.choice(list(MOTIVO_QUIEBRE), p=list(MOTIVO_QUIEBRE.values())))
            filas.append({
                "mes": v["mes"], "cuenta_id": v["cuenta_id"],
                "nombre": cta.iloc[0]["nombre"], "canal": v["canal"],
                "ciudad": v["ciudad"], "vendedor": v["vendedor"],
                "sku": sku["sku"], "producto": sku["nombre"],
                "categoria": sku["categoria"], "marca": sku["marca"],
                "pedidas": pedidas, "servidas": servidas,
                "faltantes": pedidas - servidas,
                "valor_perdido": round((pedidas - servidas) * sku["precio_classic"] * 0.76),
                "motivo": motivo,
            })
    return pd.DataFrame(filas)


def gen_devoluciones(ventas, catalogo, cuentas):
    """Devoluciones con motivo, SKU y responsable.

    Antes era un número agregado por cuenta. Una devolución por avería en
    transporte, una por vencido y una por «pedí mal» son tres problemas de tres
    áreas distintas; sumarlas en una cifra impide actuar sobre cualquiera.
    """
    cat = catalogo.sample(200, random_state=7)
    c = cuentas.set_index("cuenta_id")
    filas = []
    for _, v in ventas[ventas["mes"] >= "2026-01"].iterrows():
        if v["devoluciones"] <= 0 or RNG.random() > 0.5:
            continue
        sku = cat.sample(1).iloc[0]
        motivo = str(RNG.choice(list(MOTIVO_DEVOLUCION), p=list(MOTIVO_DEVOLUCION.values())))
        u = max(1, int(v["devoluciones"] / max(sku["precio_classic"], 1)))
        filas.append({
            "mes": v["mes"], "cuenta_id": v["cuenta_id"],
            "nombre": c.loc[v["cuenta_id"], "nombre"], "canal": v["canal"],
            "ciudad": v["ciudad"], "vendedor": v["vendedor"],
            "sku": sku["sku"], "producto": sku["nombre"], "categoria": sku["categoria"],
            "unidades": u, "valor": round(v["devoluciones"]), "motivo": motivo,
            "responsable": {"Producto vencido": "Compras",
                            "Avería en transporte": "Logística",
                            "Pedido equivocado": "Comercial",
                            "No rotó en el punto": "Comercial",
                            "Diferencia de precio": "Administración"}[motivo],
        })
    return pd.DataFrame(filas)


# ── 4. Lotes y vencimientos ──────────────────────────────────────────────────
def gen_lotes(inventario, catalogo):
    """Qué hay en bodega y cuándo se vence.

    La vida útil por categoría es la real: la cerveza son meses, el destilado no
    se vence. Por eso el riesgo se concentra en pocas categorías y el módulo
    puede ser específico en vez de dar una alerta genérica sobre todo.
    """
    VIDA = {"Cerveza": (120, 180), "Mixers y aguas": (240, 420),
            "Vino": (900, 3000), "Champaña y espumosos": (1200, 3600),
            "Accesorios gourmet": (300, 700)}
    filas = []
    inv = inventario[inventario["unidades"] > 0]
    for _, r in inv.iterrows():
        if r["categoria"] not in VIDA:
            continue                       # los destilados no vencen
        lo, hi = VIDA[r["categoria"]]
        n_lotes = int(RNG.integers(1, 4))
        restante = int(r["unidades"])
        for i in range(n_lotes):
            u = restante if i == n_lotes - 1 else int(restante * RNG.uniform(0.25, 0.6))
            restante -= u
            if u <= 0:
                continue
            vida = int(RNG.integers(lo, hi))
            # Cuánto de la vida útil ya se consumió al llegar a bodega
            consumido = RNG.uniform(0.18, 0.86)
            vence = CORTE + pd.Timedelta(days=int(vida * (1 - consumido)))
            filas.append({
                "lote": f"L-{r['sku'][-4:]}-{i+1}", "sku": r["sku"],
                "producto": r["nombre"], "categoria": r["categoria"],
                "marca": r["marca"], "bodega": r["bodega"],
                "unidades": u, "costo_unit": r["costo_unit"],
                "valor": round(u * r["costo_unit"]),
                "vence": vence.date(),
                "dias_para_vencer": int((vence - CORTE).days),
                "demanda_dia": r["demanda_dia"],
            })
    l = pd.DataFrame(filas)
    if l.empty:
        return l
    # Lo que no se va a alcanzar a vender antes de que se venza.
    l["vendible"] = (l["demanda_dia"] * l["dias_para_vencer"]).round(0)
    l["en_riesgo_u"] = (l["unidades"] - l["vendible"]).clip(lower=0).astype(int)
    l["en_riesgo"] = (l["en_riesgo_u"] * l["costo_unit"]).round(0)
    l["estado"] = pd.cut(l["dias_para_vencer"], [-9999, 0, 45, 90, 99999],
                         labels=["Vencido", "Crítico", "Vigilar", "Normal"])
    return l.sort_values("dias_para_vencer")


# ── 5. El punto de venta ─────────────────────────────────────────────────────
def gen_punto_venta(cuentas, catalogo):
    """Lo que pasa DENTRO del bar, que es donde se gana o se pierde la marca.

    Tres cosas que el ERP no puede saber y el vendedor sí, si se le pregunta en
    la visita: a qué precio lo pone en carta, qué competencia está en la barra y
    qué material nuestro tiene. Con eso se explica por qué dos cuentas parecidas
    rotan distinto — y hoy esa explicación no existe.
    """
    top = catalogo.nlargest(40, "unidades_90d")
    filas = []
    for _, c in cuentas.iterrows():
        for _, p in top.sample(int(RNG.integers(3, 9))).iterrows():
            sugerido = p["pvp_mercado"]
            # El precio en carta de un bar va con un margen enorme sobre el PVP
            carta = sugerido * RNG.uniform(1.8, 3.6)
            rota = max(0, RNG.normal(p["unidades_90d"] / 90 * 0.6, 3))
            filas.append({
                "cuenta_id": c["cuenta_id"], "nombre": c["nombre"],
                "canal": c["canal"], "ciudad": c["ciudad"], "zona": c["zona"],
                "vendedor": c["vendedor"], "sku": p["sku"], "producto": p["nombre"],
                "marca": p["marca"], "categoria": p["categoria"],
                "pvp_sugerido": round(sugerido),
                "precio_carta": round(carta),
                "sobreprecio_pct": round((carta / sugerido - 1) * 100, 0),
                "rotacion_mes": round(rota * 30, 1),
                "pop": str(RNG.choice(POP, p=[.09, .17, .14, .11, .06, .13, .30])),
                "competencia": str(RNG.choice(COMPETENCIA,
                                              p=[.19, .16, .11, .09, .07, .38])),
                "visitada_hace_dias": int(RNG.integers(2, 75)),
            })
    return pd.DataFrame(filas)


# ── 6. Presupuesto ───────────────────────────────────────────────────────────
def gen_presupuesto(ventas, finanzas):
    """El compromiso contra el que se mide todo.

    Sin esto el panel entero es descriptivo: proyecta cuatro mil millones, ¿y
    eso es bueno o malo? Nadie sabe. La pregunta de un gerente no es «cuánto
    vendí» sino «cuánto me falta y quién lo debe».

    El presupuesto se arma como se arma en la vida real: sobre el año anterior
    más una ambición, no sobre lo que realmente pasó. Por eso algunos meses se
    cumplen holgados y otros no se alcanzan — y esa desviación es el módulo.
    """
    filas = []
    for canal in ventas["canal"].unique():
        for ciudad in ventas["ciudad"].unique():
            d = ventas[(ventas["canal"] == canal) & (ventas["ciudad"] == ciudad)]
            if d.empty:
                continue
            for m in MESES:
                mm = m.strftime("%Y-%m")
                ant = d[d["mes"] == (m - pd.DateOffset(years=1)).strftime("%Y-%m")]["neto"].sum()
                base = ant if ant > 0 else d[d["mes"] <= mm]["neto"].tail(3).mean()
                if not base or np.isnan(base):
                    base = d["neto"].mean()
                filas.append({
                    "mes": mm, "canal": canal, "ciudad": ciudad,
                    "presupuesto": round(float(base) * RNG.uniform(1.12, 1.34)),
                })
    p = pd.DataFrame(filas)
    real = ventas.groupby(["mes", "canal", "ciudad"])["neto"].sum().rename("real")
    p = p.merge(real, on=["mes", "canal", "ciudad"], how="left")
    p["real"] = p["real"].fillna(0)
    p["cumplimiento"] = (p["real"] / p["presupuesto"] * 100).round(1)
    p["brecha"] = p["real"] - p["presupuesto"]
    return p


# ── 7. Compromisos del comité ────────────────────────────────────────────────
def gen_compromisos(cuentas):
    """Lo que alguien dijo que iba a hacer, con fecha.

    Es la pieza que hace que una herramienta sobreviva al tercer mes: el comité
    del lunes abre con el cumplimiento de los compromisos del lunes anterior, en
    rojo los vencidos. Deja de ser una pantalla que se mira y se vuelve el sitio
    donde se pasa lista.
    """
    PERSONAS = ["Javier", "Andrea Restrepo", "Julián Mora", "Paola Cárdenas",
                "Santiago Ospina", "Valentina Ríos", "Diana (compras)"]
    TEXTOS = [
        ("Renegociar el descuento de {cuenta} de {d1}% a {d2}%", "Comercial"),
        ("Pasar {cuenta} a entrega quincenal", "Logística"),
        ("Visitar {cuenta}: lleva 3 semanas sin pedir", "Comercial"),
        ("Cobrar la cartera vencida de {cuenta}", "Cartera"),
        ("Subir el pedido mínimo en la zona {zona}", "Logística"),
        ("Emitir la orden de compra de whisky para diciembre", "Compras"),
        ("Revisar por qué {cuenta} devolvió producto dos veces seguidas", "Calidad"),
        ("Cerrar el trimestre de Mil Demonios: faltan unidades para el tramo", "Compras"),
        ("Instalar nevera exhibidora en {cuenta}", "Mercadeo"),
        ("Bajar el precio de la referencia que está 9% sobre el competidor", "Comercial"),
    ]
    filas = []
    for i in range(22):
        c = cuentas.sample(1).iloc[0]
        txt, area = TEXTOS[i % len(TEXTOS)]
        creado = CORTE - pd.Timedelta(days=int(RNG.integers(3, 52)))
        vence = creado + pd.Timedelta(days=int(RNG.choice([7, 14, 21, 30])))
        cerrado = RNG.random() < 0.52
        filas.append({
            "id": f"CM-{i+1:03d}",
            "compromiso": txt.format(cuenta=c["nombre"], zona=c["zona"],
                                     d1=int(c["descuento_pct"]),
                                     d2=max(int(c["descuento_pct"]) - 5, 8)),
            "area": area, "dueno": str(RNG.choice(PERSONAS)),
            "creado": creado.date(), "vence": vence.date(),
            "estado": "Cumplido" if cerrado else ("Vencido" if vence < CORTE else "En curso"),
            "cerrado_el": (vence - pd.Timedelta(days=int(RNG.integers(0, 6)))).date()
                          if cerrado else "",
            "valor": int(RNG.choice([0, 0, 2_400_000, 5_800_000, 11_000_000, 18_500_000])),
            "cuenta": c["nombre"],
        })
    return pd.DataFrame(filas)


def main():
    cat = pd.read_csv(AQUI / "catalogo.csv")
    cuentas = pd.read_csv(AQUI / "cuentas.csv")
    ventas = pd.read_csv(AQUI / "ventas_cuenta_mes.csv.gz")
    inv = pd.read_csv(AQUI / "inventario_bodega.csv.gz")
    fin = pd.read_csv(AQUI / "finanzas.csv")

    fac = gen_facturas(ventas, cuentas)
    marcas_mes, rebates = gen_marcas(ventas, cat)
    qb = gen_quiebres(ventas, cat, cuentas)
    dev = gen_devoluciones(ventas, cat, cuentas)
    lotes = gen_lotes(inv, cat)
    pdv = gen_punto_venta(cuentas, cat)
    pres = gen_presupuesto(ventas, fin)
    comp = gen_compromisos(cuentas)

    for df, nombre, comprimir in [
            (fac, "facturas.csv", True), (marcas_mes, "marcas_mes.csv", False),
            (rebates, "rebates.csv", False), (qb, "quiebres.csv", True),
            (dev, "devoluciones.csv", True), (lotes, "lotes.csv", True),
            (pdv, "punto_venta.csv", True), (pres, "presupuesto.csv", False),
            (comp, "compromisos.csv", False)]:
        ruta = AQUI / (nombre + (".gz" if comprimir else ""))
        df.to_csv(ruta, index=False, compression="gzip" if comprimir else None)
        print(f"  {nombre:24} {len(df):>7,} filas")

    ab = fac[~fac["pagada"]]
    print(f"\n  Cartera abierta: {ab['saldo'].sum()/1e6:,.0f} M · "
          f"vencida {ab[ab['dias_vencida']>0]['saldo'].sum()/1e6:,.0f} M")
    print(f"  Atraso real promedio: {fac[fac['pagada']]['dias_atraso_real'].mean():.0f} días "
          f"sobre el plazo pactado")
    ult = rebates[rebates["trimestre"] == "2026-T3"]
    print(f"  Rebate del trimestre en curso: {ult['rebate'].sum()/1e6:,.0f} M · "
          f"{(ult['cumplimiento']<100).sum()} marcas por debajo de cuota")
    print(f"  Bonificación 12m: {marcas_mes.tail(72)['costo_bonificacion'].sum()/1e6:,.0f} M "
          f"(descuento que no aparece en ninguna lista)")
    print(f"  Venta perdida por quiebre: {qb['valor_perdido'].sum()/1e6:,.0f} M")
    if not lotes.empty:
        print(f"  Inventario en riesgo de vencer: {lotes['en_riesgo'].sum()/1e6:,.0f} M")
    print(f"  Compromisos vencidos sin cerrar: {(comp['estado']=='Vencido').sum()}")


if __name__ == "__main__":
    main()
