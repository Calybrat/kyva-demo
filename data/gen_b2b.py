#!/usr/bin/env python3
"""La capa B2B: establecimientos, equipo comercial, entregas, hilos y decisiones.

Javier describió en la reunión un negocio que el panel no mostraba: además de
la tienda en línea, KYVA le vende a **restaurantes, bares, discotecas, clubes
sociales y empresas**, en **Bogotá y Medellín**, y dijo que ahí está el peso
actual del negocio.

Nada de esto reescribe lo que ya había. El catálogo, los precios y los costos
salen de `catalogo.csv`; la estacionalidad, de la misma curva que usa el resto
del panel. Si se generara en paralelo, un día la pantalla de surtido diría una
cosa y la de rentabilidad por cuenta otra.

    python3 data/gen_b2b.py
"""
import numpy as np
import pandas as pd
from pathlib import Path

AQUI = Path(__file__).parent
RNG = np.random.default_rng(20260920)
CORTE = pd.Timestamp("2026-08-31")
MESES = pd.date_range("2024-09-01", "2026-08-01", freq="MS")

# ── Los cinco canales que Javier enumeró ─────────────────────────────────────
# El descuento y el plazo de pago no son decorativos: son la razón por la que un
# canal que vende más puede dejar menos. Una discoteca compra volumen con 27% de
# descuento y paga a 15 días; un club social compra menos, con 19%, pero paga a
# 45 y no devuelve nada. Cuál de los dos conviene es justo lo que hoy nadie
# calcula, y es el módulo de rentabilidad por cuenta.
CANALES = {
    "Restaurantes":    {"desc": 0.22, "plazo": 30, "peso": 0.28, "ticket": 1.0,
                        "frec_mes": 2.2, "devol": 0.010},
    "Bares":           {"desc": 0.25, "plazo": 15, "peso": 0.25, "ticket": 0.85,
                        "frec_mes": 3.1, "devol": 0.018},
    "Discotecas":      {"desc": 0.27, "plazo": 15, "peso": 0.19, "ticket": 1.35,
                        "frec_mes": 1.7, "devol": 0.026},
    "Clubes sociales": {"desc": 0.19, "plazo": 45, "peso": 0.13, "ticket": 1.25,
                        "frec_mes": 1.2, "devol": 0.004},
    "Empresas":        {"desc": 0.15, "plazo": 30, "peso": 0.12, "ticket": 0.95,
                        "frec_mes": 0.6, "devol": 0.002},
}

# Bogotá pesa más: es la casa matriz y Medellín abrió en 2026. Esa asimetría es
# la que hace que el módulo de rutas tenga algo que decir — una ciudad con pocas
# cuentas dispersas tiene un costo por entrega muy distinto.
CIUDADES = {"Bogotá": 0.72, "Medellín": 0.28}
ZONAS = {
    "Bogotá": ["Zona G", "Zona T", "Parque 93", "Usaquén", "Chapinero",
               "Chicó", "Macarena", "Candelaria", "Cedritos", "Salitre"],
    "Medellín": ["El Poblado", "Provenza", "Laureles", "Envigado",
                 "Las Palmas", "Centro"],
}
# Medellín abrió en marzo de 2026: antes de esa fecha no hay ni una venta allá.
APERTURA_MEDELLIN = pd.Timestamp("2026-03-01")

NOMBRES = {
    "Restaurantes": ["Criterión", "Leo", "Villanos en Bermudas", "Harry Sasson",
                     "El Chato", "Mesa Franca", "Salvo Patria", "Humo Negro",
                     "Mini-Mal", "Prudencia", "Carmen", "Oci.Mde", "Elcielo",
                     "Alambique", "Hatoviejo", "In Situ", "Herbario", "Cantina"],
    "Bares": ["Vintrash", "La Pascasia", "Amarillo", "Bogotá Beer Company",
              "Armando Records", "El Coq", "Baum", "Kaputt", "Sixtina",
              "3 Cordilleras", "Bendito Seas", "Malvón", "Panorama", "Bar Tokio"],
    "Discotecas": ["Theatron", "Octava", "Andrés DC", "Gotica", "Kukaramakara",
                   "Perro Negro", "La Villa", "Envy Rooftop", "Bendito Sea"],
    "Clubes sociales": ["Club El Nogal", "Club Campestre Bogotá", "Club Los Lagartos",
                        "Gun Club", "Club Campestre Medellín", "Club Unión",
                        "Club Colombia", "Club Militar"],
    "Empresas": ["Bancolombia", "Grupo Éxito", "Sura", "Nutresa", "ISA",
                 "Ecopetrol", "Davivienda", "Bavaria Corp", "Argos", "Terpel",
                 "Protección", "Colsubsidio"],
}

VENDEDORES = [
    # nombre, ciudad, desde, cuota mensual (COP), estilo
    ("Andrea Restrepo",  "Bogotá",   "2024-01", 165_000_000, "margen"),
    ("Julián Mora",      "Bogotá",   "2024-06", 150_000_000, "volumen"),
    ("Paola Cárdenas",   "Bogotá",   "2025-02", 120_000_000, "equilibrio"),
    ("Santiago Ospina",  "Medellín", "2026-02", 110_000_000, "volumen"),
    ("Valentina Ríos",   "Medellín", "2026-03",  95_000_000, "margen"),
]

# Estilo comercial. «volumen» cierra más cuentas pero regala descuento; «margen»
# vende menos y deja más. Sin esta diferencia, el módulo del equipo comercial
# sería un ranking de ventas — que es justo el informe que ya existe y que hace
# que los buenos vendedores se vean mal.
ESTILO = {"volumen": 1.18, "equilibrio": 1.0, "margen": 0.86}     # multiplica venta
ESTILO_DESC = {"volumen": 1.22, "equilibrio": 1.0, "margen": 0.84}  # multiplica descuento


def _estacional(fecha):
    """Noviembre y diciembre son el año para un distribuidor de licores."""
    return {1: 0.72, 2: 0.78, 3: 0.88, 4: 0.92, 5: 0.97, 6: 1.02,
            7: 0.99, 8: 0.95, 9: 1.04, 10: 1.18, 11: 1.74, 12: 2.45}[fecha.month]


# ── 1. Las cuentas ───────────────────────────────────────────────────────────
def gen_cuentas():
    filas, cid = [], 1
    for canal, cfg in CANALES.items():
        for nombre in NOMBRES[canal]:
            ciudad = ("Medellín" if any(x in nombre for x in
                      ("Mde", "Elcielo", "Provenza", "Medellín", "In Situ",
                       "Herbario", "Oci", "3 Cordilleras", "Envigado", "Carmen"))
                      else str(RNG.choice(list(CIUDADES), p=list(CIUDADES.values()))))
            alta_min = APERTURA_MEDELLIN if ciudad == "Medellín" else MESES[0]
            posibles = [m for m in MESES if m >= alta_min]
            alta = posibles[int(RNG.integers(0, max(len(posibles) - 2, 1)))]
            vendedores_ciudad = [v for v in VENDEDORES if v[1] == ciudad]
            v = vendedores_ciudad[int(RNG.integers(0, len(vendedores_ciudad)))]
            filas.append({
                "cuenta_id": f"C-{cid:03d}", "nombre": nombre, "canal": canal,
                "ciudad": ciudad,
                "zona": str(RNG.choice(ZONAS[ciudad])),
                "alta": alta.date(), "vendedor": v[0],
                "descuento_pct": round(cfg["desc"] * ESTILO_DESC[v[4]] *
                                       RNG.uniform(0.92, 1.08) * 100, 1),
                "plazo_pago": cfg["plazo"],
                "cupo_credito": int(round(RNG.uniform(8, 60) * cfg["ticket"], 0)) * 1_000_000,
                "frec_visita_mes": round(cfg["frec_mes"] * RNG.uniform(0.7, 1.3), 1),
                "escala": float(RNG.lognormal(-0.30, 0.92) * cfg["ticket"]),
            })
            cid += 1
    return pd.DataFrame(filas)


# ── 2. Ventas mes a mes ──────────────────────────────────────────────────────
def gen_ventas(cuentas, catalogo):
    """Cada cuenta compra según su canal, su escala y la estacionalidad.

    El margen sale del costo REAL del catálogo, no de un porcentaje inventado:
    se arma una canasta por canal —una discoteca compra aguardiente y ron, un
    club social compra whisky y vino— y se calcula contra `costo_unit`.
    """
    canasta = {
        "Restaurantes":    {"Vino": .46, "Whisky": .16, "Cerveza": .12,
                            "Licores y aperitivos": .10, "Ron": .08, "Ginebra": .08},
        "Bares":           {"Whisky": .24, "Ron": .18, "Cerveza": .20, "Ginebra": .14,
                            "Vodka": .12, "Licores y aperitivos": .12},
        "Discotecas":      {"Whisky": .30, "Aguardiente": .24, "Ron": .18,
                            "Vodka": .16, "Cerveza": .12},
        "Clubes sociales": {"Whisky": .38, "Vino": .28, "Cognac, brandy y pisco": .12,
                            "Champaña y espumosos": .12, "Ron": .10},
        "Empresas":        {"Whisky": .34, "Vino": .26, "Champaña y espumosos": .18,
                            "Licores y aperitivos": .12, "Accesorios gourmet": .10},
    }
    # El margen NO se saca restando el descuento al precio de consumidor.
    #
    # `precio_classic` es el precio de góndola, que ya lleva el margen del
    # minorista. Si a eso se le resta el 25% que se le da a una discoteca, el
    # resultado es un margen del 4% — imposible, y fue justo lo que salió en el
    # primer intento. Un distribuidor no vende con descuento sobre el precio de
    # consumidor: vende sobre **su propia lista mayorista**, que parte del costo.
    #
    # Así que el margen se fija por canal, calibrado contra la referencia real
    # del sector, y el catálogo entra modulando la diferencia entre canastas:
    # una discoteca vive de aguardiente y ron —volumen, marca fuerte, poco
    # margen— y un club social de whisky y vino.
    MARGEN_CANAL = {"Restaurantes": .265, "Bares": .240, "Discotecas": .205,
                    "Clubes sociales": .285, "Empresas": .305}
    cat = catalogo.copy()
    cat["margen"] = 1 - cat["costo_unit"] / cat["precio_classic"].replace(0, np.nan)
    m_cat = cat.groupby("categoria")["margen"].mean().to_dict()
    m_medio = float(np.mean(list(m_cat.values())))
    precio_cat = cat.groupby("categoria")["precio_classic"].mean().to_dict()

    # Escala: la capa tiene que cuadrar con lo que `finanzas.csv` ya declara
    # como B2B (corporativo + distribución). Generarla suelta la haría
    # contradecir el tablero ejecutivo en la primera pantalla.
    ESCALA = 2.44

    filas = []
    for _, c in cuentas.iterrows():
        cfg = CANALES[c["canal"]]
        base = 3_100_000 * c["escala"] * ESCALA
        for m in MESES:
            if m < pd.Timestamp(c["alta"]):
                continue
            # Las cuentas nuevas arrancan lento y suben: un bar no compra su
            # volumen normal el primer mes, lo construye en un trimestre.
            antiguedad = (m.year - pd.Timestamp(c["alta"]).year) * 12 + m.month - pd.Timestamp(c["alta"]).month
            rampa = min(1.0, 0.42 + antiguedad * 0.20)
            if RNG.random() < 0.055:            # un mes sin comprar, pasa
                continue
            bruto = base * _estacional(m) * rampa * RNG.lognormal(0, 0.28)

            # La canasta modula el margen del canal: si lo que compra esta
            # cuenta es más caro de lo normal en margen, el suyo baja.
            mezcla = canasta[c["canal"]]
            mix = sum(p * m_cat.get(k, m_medio) for k, p in mezcla.items())
            margen_pct = MARGEN_CANAL[c["canal"]] * (mix / m_medio) ** 0.45
            neto = bruto * (1 - c["descuento_pct"] / 100)
            costo = neto * (1 - margen_pct * RNG.uniform(0.9, 1.1))
            devol = neto * cfg["devol"] * RNG.uniform(0, 2.4)
            unidades = int(bruto / max(sum(p * precio_cat.get(k, 90_000)
                                           for k, p in mezcla.items()), 1))
            entregas = max(1, int(round(c["frec_visita_mes"] * RNG.uniform(0.7, 1.35))))
            filas.append({
                "mes": m.strftime("%Y-%m"), "cuenta_id": c["cuenta_id"],
                "canal": c["canal"], "ciudad": c["ciudad"], "zona": c["zona"],
                "vendedor": c["vendedor"],
                "bruto": round(bruto), "descuento": round(bruto - neto),
                "devoluciones": round(devol),
                "neto": round(neto - devol), "costo": round(costo),
                "unidades": unidades, "entregas": entregas,
            })
    v = pd.DataFrame(filas)
    v["margen"] = v["neto"] - v["costo"]
    return v


# ── 3. Entregas ──────────────────────────────────────────────────────────────
def gen_entregas(ventas, cuentas):
    """El costo de servir, que es donde se pierde la plata que el margen esconde.

    Una entrega cuesta prácticamente lo mismo lleve 4 botellas o 40. Por eso un
    bar que pide tres veces por semana valores pequeños puede tener buen margen
    bruto y aun así costar plata. El costo por entrega sube con la distancia y
    baja con la densidad de la zona: repartir a seis cuentas de la Zona G en una
    mañana no cuesta lo mismo que cruzar a Envigado por una sola.
    """
    dens = cuentas.groupby(["ciudad", "zona"]).size().rename("cuentas_zona")
    v = ventas.merge(dens, left_on=["ciudad", "zona"], right_index=True, how="left")
    v["cuentas_zona"] = v["cuentas_zona"].fillna(1)

    base = np.where(v["ciudad"] == "Bogotá", 68_000, 61_000)
    penal_dispersion = 1 + 0.55 / np.sqrt(v["cuentas_zona"])
    v["costo_entrega_u"] = np.round(base * penal_dispersion *
                                    RNG.uniform(0.88, 1.18, len(v)))
    v["costo_logistica"] = v["costo_entrega_u"] * v["entregas"]
    v["margen_servido"] = v["margen"] - v["costo_logistica"]
    return v[["mes", "cuenta_id", "ciudad", "zona", "entregas", "unidades",
              "costo_entrega_u", "costo_logistica", "margen", "margen_servido"]]


# ── 4. Equipo comercial ──────────────────────────────────────────────────────
def gen_vendedores(ventas):
    g = ventas.groupby("vendedor").agg(
        cuentas=("cuenta_id", "nunique"),
        neto_12m=("neto", "sum"), margen_12m=("margen", "sum"),
        descuento=("descuento", "sum"), bruto=("bruto", "sum")).reset_index()
    meta = {v[0]: v for v in VENDEDORES}
    g["ciudad"] = g["vendedor"].map(lambda n: meta[n][1])
    g["desde"] = g["vendedor"].map(lambda n: meta[n][2])
    g["cuota_mes"] = g["vendedor"].map(lambda n: meta[n][3])
    g["estilo"] = g["vendedor"].map(lambda n: meta[n][4])
    g["descuento_pct"] = (g["descuento"] / g["bruto"] * 100).round(1)
    g["margen_pct"] = (g["margen_12m"] / g["neto_12m"] * 100).round(1)
    return g


# ── 5. Hilos del equipo ──────────────────────────────────────────────────────
def gen_hilos(ventas, cuentas):
    """Conversaciones sobre números concretos, con su desenlace.

    Un hilo sin desenlace es un chat. Lo que vuelve útil esta capa es que la
    discusión quede pegada al dato que la provocó y que se sepa en qué terminó:
    dentro de tres meses, cuando alguien pregunte por qué se le bajó el
    descuento a Theatron, la respuesta está donde está el número.
    """
    ult = ventas[ventas["mes"] == "2026-08"]
    peores = ult.nsmallest(6, "margen")
    mejores = ult.nlargest(4, "margen")
    n = cuentas.set_index("cuenta_id")["nombre"].to_dict()

    H = []
    for i, (_, r) in enumerate(peores.iterrows()):
        H.append({
            "hilo_id": f"H-{i+1:03d}", "ancla": f"Rentabilidad · {n.get(r['cuenta_id'], '')}",
            "modulo": "p21_cuentas", "abierto_por": "Andrea Restrepo",
            "abierto": (CORTE - pd.Timedelta(days=int(RNG.integers(2, 26)))).date(),
            "asunto": f"{n.get(r['cuenta_id'],'')} cerró agosto en rojo",
            "mensajes": int(RNG.integers(2, 7)),
            "estado": str(RNG.choice(["Resuelto", "En curso", "Resuelto"], p=[.5, .3, .2])),
            "desenlace": str(RNG.choice([
                "Se le bajó el descuento del 27% al 22% desde septiembre",
                "Se pasó a entrega quincenal en vez de dos veces por semana",
                "Se subió el pedido mínimo a 1,5 M para mantener la frecuencia",
                "En revisión con el vendedor antes de tocar condiciones"])),
        })
    for i, (_, r) in enumerate(mejores.iterrows(), start=len(peores)):
        H.append({
            "hilo_id": f"H-{i+1:03d}", "ancla": f"Rentabilidad · {n.get(r['cuenta_id'], '')}",
            "modulo": "p21_cuentas", "abierto_por": "Javier",
            "abierto": (CORTE - pd.Timedelta(days=int(RNG.integers(1, 18)))).date(),
            "asunto": f"¿Por qué {n.get(r['cuenta_id'],'')} creció tanto?",
            "mensajes": int(RNG.integers(2, 5)), "estado": "Resuelto",
            "desenlace": "Cambió de administrador y amplió carta de coctelería",
        })
    extras = [
        ("Compras · ventana de diciembre", "p17_reposicion", "Javier",
         "El whisky ya se pasó de fecha, ¿pedimos igual?", "Resuelto",
         "Se emitió la orden con sobrecosto de flete aéreo en dos referencias"),
        ("Rutas · Envigado", "p24_rutas", "Santiago Ospina",
         "Envigado nos está costando más de lo que deja", "En curso",
         "Propuesta: agrupar en un solo día de la semana"),
        ("Precios · Mil Demonios", "p10_precios", "Paola Cárdenas",
         "Estamos 9% por encima del competidor en la referencia de 750", "Resuelto",
         "Se ajustó el PVP sugerido y se avisó a los 14 clientes que la llevan"),
        ("Cartera · Discotecas", "p04_caja", "Andrea Restrepo",
         "Tres cuentas de discoteca pasadas de 30 días", "En curso",
         "Bloqueo de crédito activado en dos; la tercera negoció plan de pago"),
    ]
    for j, (ancla, mod, quien, asunto, estado, des) in enumerate(extras, start=len(H)):
        H.append({"hilo_id": f"H-{j+1:03d}", "ancla": ancla, "modulo": mod,
                  "abierto_por": quien,
                  "abierto": (CORTE - pd.Timedelta(days=int(RNG.integers(1, 30)))).date(),
                  "asunto": asunto, "mensajes": int(RNG.integers(3, 9)),
                  "estado": estado, "desenlace": des})
    return pd.DataFrame(H)


# ── 6. La bandeja de decisiones ──────────────────────────────────────────────
def gen_decisiones(ventas, cuentas, entregas):
    """Lo que espera que un humano decida hoy, con el cálculo ya hecho.

    Es el corazón del panel: cada fila trae el número que la justifica, la
    acción concreta y lo que pasa si nadie hace nada. Un tablero dice «este
    cliente da -2%»; esto dice «súbele el mínimo a 1,5 M o pásalo a quincenal, y
    si no haces nada son 14 M al año».
    """
    ult3 = ventas[ventas["mes"] >= "2026-06"]
    porc = ult3.groupby("cuenta_id").agg(
        neto=("neto", "sum"), margen=("margen", "sum"),
        entregas=("entregas", "sum"), canal=("canal", "first")).reset_index()
    log = entregas[entregas["mes"] >= "2026-06"].groupby("cuenta_id")["costo_logistica"].sum()
    porc["logistica"] = porc["cuenta_id"].map(log).fillna(0)
    porc["servido"] = porc["margen"] - porc["logistica"]
    n = cuentas.set_index("cuenta_id")
    D = []

    # a) Cuentas que cuestan plata después del costo de servir
    for _, r in porc[porc["servido"] < 0].nsmallest(9, "servido").iterrows():
        c = n.loc[r["cuenta_id"]]
        anual = r["servido"] / 3 * 12
        D.append({
            "tipo": "Condiciones comerciales", "urgencia": "Alta",
            "titulo": f"{c['nombre']} deja margen negativo después de logística",
            "dato": f"3 meses: {r['neto']/1e6:,.1f} M vendidos · margen servido {r['servido']/1e6:,.1f} M",
            "accion": f"Subir pedido mínimo, bajar el descuento del {c['descuento_pct']}% "
                      f"o pasar de {r['entregas']} entregas a quincenal",
            "si_nadie_hace_nada": f"{anual/1e6:,.0f} M al año",
            "decide": "Dirección comercial", "cuenta": c["nombre"],
            "vendedor": c["vendedor"], "ciudad": c["ciudad"],
        })
    # b) Cuentas que se apagaron
    ult = ventas[ventas["mes"] == "2026-08"]["cuenta_id"].unique()
    previo = ventas[ventas["mes"].isin(["2026-05", "2026-06", "2026-07"])]
    for cid in [c for c in previo["cuenta_id"].unique() if c not in ult][:7]:
        c = n.loc[cid]
        hist = previo[previo["cuenta_id"] == cid]["neto"].mean()
        D.append({
            "tipo": "Cuenta apagada", "urgencia": "Alta",
            "titulo": f"{c['nombre']} no compró en agosto",
            "dato": f"Venía en {hist/1e6:,.1f} M al mes · {c['canal']} · {c['zona']}",
            "accion": f"Que {c['vendedor']} la visite esta semana y reporte el motivo",
            "si_nadie_hace_nada": f"{hist*12/1e6:,.0f} M al año",
            "decide": c["vendedor"], "cuenta": c["nombre"],
            "vendedor": c["vendedor"], "ciudad": c["ciudad"],
        })
    # c) Crédito por encima del cupo
    for _, r in porc.nlargest(24, "neto").iterrows():
        c = n.loc[r["cuenta_id"]]
        expuesto = r["neto"] / 3 * (c["plazo_pago"] / 30)
        if expuesto > c["cupo_credito"] * 1.05:
            D.append({
                "tipo": "Riesgo de crédito", "urgencia": "Media",
                "titulo": f"{c['nombre']} supera su cupo",
                "dato": f"Expuesto ~{expuesto/1e6:,.0f} M contra un cupo de {c['cupo_credito']/1e6:,.0f} M",
                "accion": "Ampliar el cupo con garantía o exigir pago antes del próximo despacho",
                "si_nadie_hace_nada": f"{(expuesto - c['cupo_credito'])/1e6:,.0f} M sin respaldo",
                "decide": "Financiera", "cuenta": c["nombre"],
                "vendedor": c["vendedor"], "ciudad": c["ciudad"],
            })
    return pd.DataFrame(D)


def main():
    cat = pd.read_csv(AQUI / "catalogo.csv")
    cuentas = gen_cuentas()
    ventas = gen_ventas(cuentas, cat)
    entregas = gen_entregas(ventas, cuentas)
    vend = gen_vendedores(ventas)
    hilos = gen_hilos(ventas, cuentas)
    dec = gen_decisiones(ventas, cuentas, entregas)

    for df, nombre, comp in [(cuentas, "cuentas.csv", False),
                             (ventas, "ventas_cuenta_mes.csv", True),
                             (entregas, "entregas.csv", True),
                             (vend, "vendedores.csv", False),
                             (hilos, "hilos.csv", False),
                             (dec, "decisiones.csv", False)]:
        ruta = AQUI / (nombre + (".gz" if comp else ""))
        df.to_csv(ruta, index=False, compression="gzip" if comp else None)
        print(f"  {nombre:26} {len(df):>7,} filas")

    u12 = ventas[ventas["mes"] >= "2025-09"]
    print(f"\n  B2B últimos 12 meses: {u12['neto'].sum()/1e6:,.0f} M COP netos")
    print(f"  Margen bruto: {u12['margen'].sum()/u12['neto'].sum()*100:.1f}%")
    e12 = entregas[entregas["mes"] >= "2025-09"]
    print(f"  Margen después de logística: "
          f"{e12['margen_servido'].sum()/u12['neto'].sum()*100:.1f}%")
    print(f"  Cuentas activas en agosto: {ventas[ventas['mes']=='2026-08']['cuenta_id'].nunique()} de {len(cuentas)}")
    print(f"  Medellín: {cuentas[cuentas.ciudad=='Medellín'].shape[0]} cuentas")
    print(f"  Decisiones esperando: {len(dec)}")


if __name__ == "__main__":
    main()
