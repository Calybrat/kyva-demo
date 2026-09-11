#!/usr/bin/env python3
"""
Generador del set de datos del panel de KYVA.

CÓMO ES EL NEGOCIO QUE SE MODELA
────────────────────────────────
KYVA SAS (Bogotá, 2019) vende licores, vinos y cervezas premium por internet con
entrega en Bogotá y la Sabana. Gana plata por cuatro vías, y cada una tiene un
margen muy distinto:

  · The Store      tienda abierta al público, precio Classic.
  · The Lounge     miembros Elite, precio Elite (más bajo). La membresía llega
                   casi siempre gratis, a través de una marca aliada (Porsche,
                   BoConcept, Argento & Bourbon…) — el modelo B2B2C.
  · Corporativo    regalos de fin de año, eventos, bodas y catas.
  · Distribución   marcas que KYVA distribuye (Mil Demonios en exclusiva desde
                   2026, Ron Defensor, Marcel Thorel) vendidas a restaurantes,
                   bares, hoteles y otras tiendas.

LAS DOS REGLAS QUE NO SE NEGOCIAN
─────────────────────────────────
· **Simular, luego derivar.** Se simula cada cliente, cada pedido y cada línea
  de producto; los ingresos, márgenes, cohortes, la rotación del surtido y el
  estado de resultados se DERIVAN de esa simulación. Por eso cierran siempre.
· **Un solo cálculo por indicador.** Lo que sale en más de una pantalla se
  calcula en `utils/datos.py`.

LO QUE ESTÁ CALIBRADO CONTRA DATOS PÚBLICOS
───────────────────────────────────────────
Crecimiento de ingresos 2024 y 2025, margen operacional 2025, equipo en 2026,
tamaño del catálogo, reglas de envío y horario de despacho, precios reales de
catálogo, stock de Mil Demonios. Ver ANCLAS abajo y la tabla del README.

Uso:  python3 data/generate_data.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path

OUT = Path(__file__).parent
RNG = np.random.default_rng(20260910)     # semilla fija: datos reproducibles

# ── Ventana de tiempo ────────────────────────────────────────────────────────
CORTE = pd.Timestamp("2026-08-31 23:59")
INICIO_SIM = pd.Timestamp("2022-01-01")   # se simula desde antes: la base ya existe
INICIO = pd.Timestamp("2023-01-01")       # desde aquí se guarda
MESES_SIM = pd.period_range("2022-01", "2026-08", freq="M")
MESES = pd.period_range("2023-01", "2026-08", freq="M").strftime("%Y-%m").tolist()

# ═════════════════════════════════════════════════════════════════════════════
# ANCLAS PÚBLICAS  (cada una con su fuente; también en el README con enlace)
# ═════════════════════════════════════════════════════════════════════════════
ANCLAS = {
    "constitucion": 2019,                  # 13-ago-2019 — EMIS
    "ventas_2021_min_mm": 1_000,           # ventas 2021 entre $1.000M y $2.000M — einforma
    "ventas_2021_max_mm": 2_000,
    "crec_ingresos_2024_pct": 120.03,      # ingresos netos 2024 — EMIS
    "crec_ingresos_2025_pct": 130.46,      # ingresos netos 2025 — EMIS
    "margen_operacional_2025_pct": 0.08,   # EMIS
    "crec_ebit_2025_pct": 135.71,          # ganancia operativa 2025 vs 2024 — EMIS
    "empleados_2026": 13,                  # EMIS
    "referencias_min": 300,                # "más de 300 referencias" — kyva.co
    "whiskies_en_catalogo": 85,            # categoría Whisky — kyva.co/tienda
    "envio_costo": 18_000,                 # pedidos bajo $300.000 — kyva.co/faq
    "envio_gratis_desde": 300_000,         # kyva.co/faq
    "descuento_lounge_max_pct": 25,        # "-25% permanente sobre el precio sugerido" — COPU 2023
    "stock_mil_demonios_u": 1_200,         # ficha de producto en kyva.co, vista el 10-sep-2026
    "asistentes_lanzamiento_elite": 250,   # Porsche Center Bogotá, sep-2025 — Produ
}

# ── Reglas de operación públicas (kyva.co/faq) ───────────────────────────────
ENVIO_COSTO = 18_000
ENVIO_GRATIS = 300_000
CORTE_MISMO_DIA = 12          # "pide AM y recibe PM"
CIERRE = {0: 17, 1: 17, 2: 17, 3: 17, 4: 16}   # lun–jue 8–5, vie 8–4; sin fin de semana

# Festivos de Colombia (Ley Emiliani: muchos caen en lunes)
FESTIVOS = set(pd.to_datetime([
    "2022-01-01", "2022-01-10", "2022-03-21", "2022-04-14", "2022-04-15", "2022-05-01",
    "2022-05-30", "2022-06-20", "2022-06-27", "2022-07-04", "2022-07-20", "2022-08-07",
    "2022-08-15", "2022-10-17", "2022-11-07", "2022-11-14", "2022-12-08", "2022-12-25",
    "2023-01-01", "2023-01-09", "2023-03-20", "2023-04-06", "2023-04-07", "2023-05-01",
    "2023-05-22", "2023-06-12", "2023-06-19", "2023-07-03", "2023-07-20", "2023-08-07",
    "2023-08-21", "2023-10-16", "2023-11-06", "2023-11-13", "2023-12-08", "2023-12-25",
    "2024-01-01", "2024-01-08", "2024-03-25", "2024-03-28", "2024-03-29", "2024-05-01",
    "2024-05-13", "2024-06-03", "2024-06-10", "2024-07-01", "2024-07-20", "2024-08-07",
    "2024-08-19", "2024-10-14", "2024-11-04", "2024-11-11", "2024-12-08", "2024-12-25",
    "2025-01-01", "2025-01-06", "2025-03-24", "2025-04-17", "2025-04-18", "2025-05-01",
    "2025-06-02", "2025-06-23", "2025-06-30", "2025-07-20", "2025-08-07", "2025-08-18",
    "2025-10-13", "2025-11-03", "2025-11-17", "2025-12-08", "2025-12-25",
    "2026-01-01", "2026-01-12", "2026-03-23", "2026-04-02", "2026-04-03", "2026-05-01",
    "2026-05-18", "2026-06-08", "2026-06-15", "2026-06-29", "2026-07-20", "2026-08-07",
    "2026-08-17", "2026-10-12", "2026-11-02", "2026-11-16", "2026-12-08", "2026-12-25",
]).date)

# IVA del 19% a licores (Decreto 1474 de 2025): rigió desde el 1 de enero hasta
# la suspensión provisional de la Corte, el 29 de enero de 2026.
IVA19_DESDE, IVA19_HASTA = pd.Timestamp("2026-01-01"), pd.Timestamp("2026-01-29 23:59")

# ── Estacionalidad del consumo ───────────────────────────────────────────────
# Diciembre manda (primas, regalos, fiestas); junio trae Día del Padre y prima;
# septiembre, Amor y Amistad. Enero y febrero son la resaca.
ESTACION = {1: .74, 2: .84, 3: .93, 4: .95, 5: 1.0, 6: 1.13, 7: .96, 8: .97,
            9: 1.12, 10: 1.0, 11: 1.10, 12: 1.42}
DOW = np.array([.11, .11, .12, .16, .21, .18, .11])       # lun → dom
HORA = np.array([.4, .2, .1, .05, .05, .1, .3, .8, 1.6, 2.6, 3.4, 3.6, 3.0, 2.6,
                 2.6, 2.8, 3.2, 3.8, 4.4, 4.8, 4.6, 3.8, 2.4, 1.2])
HORA = HORA / HORA.sum()

ZONAS = [("Usaquén", 21, False), ("Chapinero", 17, False), ("Suba", 13, False),
         ("Teusaquillo", 6, False), ("Barrios Unidos", 5, False), ("Engativá", 5, False),
         ("Fontibón", 4, False), ("Kennedy", 3, False), ("Puente Aranda", 2, False),
         ("Santa Fe y Candelaria", 2, False), ("Otras localidades", 8, False),
         ("Chía", 5, True), ("Cajicá", 3, True), ("Cota", 2, True),
         ("La Calera", 2, True), ("Sopó", 1, True), ("Funza y Mosquera", 1, True)]
SABANA = {z for z, _, s in ZONAS if s}

# Aliados del modelo B2B2C. Los nombres son públicos (prensa y sitio de KYVA);
# el peso y la activación de cada uno son SUPUESTOS del modelo.
ALIADOS = [("Porsche Center Bogotá", .14, .46), ("Foro de Presidentes", .10, .52),
           ("BoConcept", .09, .33), ("Argento & Bourbon", .08, .41),
           ("EO Colombia", .08, .49), ("Carmiña Villegas", .07, .36),
           ("Café San Alberto", .06, .29), ("Weber", .06, .31), ("Bauer", .05, .27),
           ("Convenios de nómina", .27, .24)]


def _pick(opciones, n, rng=RNG):
    vals = [o[0] for o in opciones]
    p = np.array([o[1] for o in opciones], dtype=float)
    return rng.choice(vals, size=n, p=p / p.sum())


def _curva(puntos: dict) -> np.ndarray:
    """Interpolación lineal por mes sobre MESES_SIM a partir de {'AAAA-MM': valor}."""
    idx = {str(m): i for i, m in enumerate(MESES_SIM)}
    xs = [idx[k] for k in puntos]
    return np.interp(np.arange(len(MESES_SIM)), xs, list(puntos.values()))


def _deflactor(fechas) -> np.ndarray:
    """Los precios del catálogo son de ago-2026; hacia atrás, ~5,5% anual."""
    dias = np.asarray((CORTE - pd.DatetimeIndex(pd.to_datetime(fechas))).days)
    return (1.055) ** (-dias / 365)


def _guardar(df: pd.DataFrame, nombre: str, comprimir=False):
    ruta = OUT / (f"{nombre}.csv.gz" if comprimir else f"{nombre}.csv")
    df.to_csv(ruta, index=False, compression="gzip" if comprimir else None)
    mb = ruta.stat().st_size / 1_048_576
    print(f"  ✓ {ruta.name:<30} {len(df):>9,} filas   {mb:>6.2f} MB")


# ═════════════════════════════════════════════════════════════════════════════
# 1. CATÁLOGO
# ═════════════════════════════════════════════════════════════════════════════
# (categoría, cuántas referencias, precio Classic mediano, margen sobre el
#  precio Classic neto, IVA). El margen es un SUPUESTO de retail de licores;
#  el número de whiskies (85) es público.
CATEGORIAS = [
    ("Whisky", 85, 190_000, .19, .05), ("Vino", 140, 78_000, .27, .05),
    ("Ron", 34, 95_000, .21, .05), ("Ginebra", 16, 150_000, .22, .05),
    ("Tequila y mezcal", 28, 175_000, .21, .05), ("Vodka", 18, 115_000, .20, .05),
    ("Aguardiente", 12, 48_000, .15, .05), ("Champaña y espumosos", 22, 240_000, .21, .05),
    ("Cognac, brandy y pisco", 14, 230_000, .22, .05),
    ("Licores y aperitivos", 40, 92_000, .24, .05), ("Cerveza", 22, 26_000, .12, .19),
    ("Mixers y aguas", 18, 19_000, .25, .19), ("Accesorios gourmet", 11, 65_000, .38, .19),
]
IVA_CAT = {c[0]: c[4] for c in CATEGORIAS}

# Precios reales vistos en kyva.co el 10-sep-2026: (nombre, cat, marca, proveedor,
# ml, Classic, Elite). Elite en None = no se vio; se deriva.
REALES = [
    ("Whisky Chivas Regal 12 años", "Whisky", "Chivas Regal", "Pernod Ricard", 1000, 184_800, 155_600),
    ("Whisky Chivas Regal Extra", "Whisky", "Chivas Regal", "Pernod Ricard", 1000, 210_600, 177_300),
    ("Whisky The Glenlivet Founders Reserve", "Whisky", "The Glenlivet", "Pernod Ricard", 700, 166_100, 139_800),
    ("Whisky The Glenlivet 12 años", "Whisky", "The Glenlivet", "Pernod Ricard", 700, 195_800, None),
    ("Whisky Buchanan's Deluxe 12 años + 200 ml", "Whisky", "Buchanan's", "Diageo", 950, 165_000, 158_100),
    ("Whisky Jack Daniel's Old No. 7", "Whisky", "Jack Daniel's", "Otros importadores", 1000, 183_300, 173_100),
    ("Whisky Jack Daniel's Old No. 7 200 ml", "Whisky", "Jack Daniel's", "Otros importadores", 200, 39_900, 37_300),
    ("Whisky Old Parr 12 años", "Whisky", "Old Parr", "Diageo", 500, 110_200, 104_400),
    ("Whisky Glenfiddich 12 años 50 ml", "Whisky", "Glenfiddich", "Otros importadores", 50, 26_000, 25_200),
    ("Ginebra Beefeater London Dry", "Ginebra", "Beefeater", "Pernod Ricard", 700, 140_600, 118_400),
    ("Ron Defensor 12 años", "Ron", "Defensor", "Distribución KYVA", 700, 265_900, None),
    ("Ron Medellín Dorado 750 ml", "Ron", "Ron Medellín", "Otros importadores", 750, 49_200, 48_400),
    ("Ron Medellín Dorado 375 ml", "Ron", "Ron Medellín", "Otros importadores", 375, 27_000, 26_500),
    ("Aguardiente Antioqueño Real 375 ml", "Aguardiente", "Antioqueño", "Otros importadores", 375, 24_500, 24_500),
    ("Aguardiente Mil Demonios 700 ml", "Aguardiente", "Mil Demonios", "Distribución KYVA", 700, 111_000, 99_300),
    ("Aguardiente Mil Demonios 375 ml", "Aguardiente", "Mil Demonios", "Distribución KYVA", 375, 59_700, 53_400),
    ("Cerveza Club Colombia x6", "Cerveza", "Club Colombia", "Bavaria", 1980, 23_400, 20_600),
    ("Cerveza Stella Artois lata x6", "Cerveza", "Stella Artois", "Bavaria", 1614, 25_000, 23_900),
    ("Cerveza Heineken 0,0 x6", "Cerveza", "Heineken", "Otros importadores", 1500, 23_200, 21_500),
    ("Red Bull Sin Azúcar x4", "Mixers y aguas", "Red Bull", "Otros importadores", 1000, 36_200, 32_700),
    ("Agua Hatsu con gas x6", "Mixers y aguas", "Hatsu", "Otros importadores", 1800, 18_000, 16_200),
    ("Agua Hatsu sin gas x6", "Mixers y aguas", "Hatsu", "Otros importadores", 3000, 23_600, 21_300),
]

MARCAS = {
    "Whisky": [("Johnnie Walker", "Diageo", ["Red Label", "Black Label", "Double Black", "Gold Reserve", "18 años", "Blue Label"]),
               ("Buchanan's", "Diageo", ["Master", "18 años", "Two Souls"]),
               ("Chivas Regal", "Pernod Ricard", ["18 años", "Mizunara"]),
               ("Royal Salute", "Pernod Ricard", ["21 años", "21 años Polo"]),
               ("The Glenlivet", "Pernod Ricard", ["15 años", "18 años", "Caribbean Reserve"]),
               ("Macallan", "Otros importadores", ["12 Double Cask", "15 Double Cask", "18 Sherry Oak"]),
               ("Glenfiddich", "Otros importadores", ["12 años", "15 años", "18 años"]),
               ("Old Parr", "Diageo", ["Silver", "18 años"]), ("Monkey Shoulder", "Otros importadores", [""]),
               ("Jameson", "Pernod Ricard", ["", "Black Barrel"]), ("Ballantine's", "Pernod Ricard", ["Finest", "12 años"]),
               ("Dewar's", "Bacardí", ["White Label", "12 años", "15 años"]), ("Black & White", "Diageo", [""]),
               ("Something Special", "Pernod Ricard", [""]), ("Jack Daniel's", "Otros importadores", ["Honey", "Fire", "Gentleman Jack", "Single Barrel"]),
               ("Woodford Reserve", "Otros importadores", [""]), ("Maker's Mark", "Otros importadores", [""]),
               ("Bulleit", "Diageo", ["Bourbon"]), ("Aberlour", "Pernod Ricard", ["12 años"]),
               ("Talisker", "Diageo", ["10 años"]), ("Lagavulin", "Diageo", ["16 años"]),
               ("The Singleton", "Diageo", ["12 años"]), ("Glenmorangie", "Otros importadores", ["10 años"])],
    "Vino": [(m, p, ["Cabernet Sauvignon", "Malbec", "Merlot", "Carménère", "Chardonnay", "Sauvignon Blanc", "Rosé", "Tempranillo"])
             for m, p in [("Casillero del Diablo", "Otros importadores"), ("Marqués de Casa Concha", "Otros importadores"),
                          ("Santa Rita 120", "Global Wine & Spirits"), ("Trapiche", "Marpico"), ("Norton", "Global Wine & Spirits"),
                          ("Catena", "Marpico"), ("Alamos", "Marpico"), ("Luigi Bosca", "Global Wine & Spirits"),
                          ("Rutini", "Marpico"), ("Montes", "Global Wine & Spirits"), ("Castillo de Molina", "Otros importadores"),
                          ("Undurraga", "Global Wine & Spirits"), ("Campo Viejo", "Pernod Ricard"), ("Marqués de Riscal", "Marpico"),
                          ("Ramón Bilbao", "Global Wine & Spirits"), ("Mouton Cadet", "Otros importadores"),
                          ("Emiliana", "Marpico"), ("Santa Carolina", "Global Wine & Spirits"), ("Protos", "Marpico"),
                          ("Beronia", "Global Wine & Spirits")]],
    "Ron": [("Havana Club", "Pernod Ricard", ["Añejo Especial", "7 años", "Selección de Maestros"]),
            ("Bacardí", "Bacardí", ["Superior", "Añejo 4", "8 años", "Reserva Ocho"]),
            ("Zacapa", "Diageo", ["23", "XO", "Edición Negra"]), ("Dictador", "Otros importadores", ["12 años", "20 años", "XO"]),
            ("Ron Viejo de Caldas", "Otros importadores", ["Tradicional", "Esencial", "Gran Reserva"]),
            ("Diplomático", "Otros importadores", ["Reserva Exclusiva", "Mantuano"]), ("Parce", "Otros importadores", ["8 años", "12 años"]),
            ("Defensor", "Distribución KYVA", ["18 años"]), ("La Hechicera", "Otros importadores", [""]),
            ("Kraken", "Otros importadores", [""]), ("Captain Morgan", "Diageo", ["Spiced"])],
    "Ginebra": [("Plymouth", "Pernod Ricard", ["", "Navy Strength"]), ("Monkey 47", "Pernod Ricard", [""]),
                ("Beefeater", "Pernod Ricard", ["Pink", "24"]), ("Hendrick's", "Otros importadores", [""]),
                ("Tanqueray", "Diageo", ["London Dry", "Ten"]), ("Bombay Sapphire", "Bacardí", [""]),
                ("Gin Mare", "Otros importadores", [""]), ("Roku", "Otros importadores", [""]), ("Malfy", "Pernod Ricard", ["Rosa", "Limone"])],
    "Tequila y mezcal": [("Patrón", "Bacardí", ["Silver", "Reposado", "Añejo"]), ("Avión", "Pernod Ricard", ["Cristalino", "Silver", "Reposado"]),
                         ("Don Julio", "Diageo", ["Blanco", "Reposado", "70", "1942"]), ("José Cuervo", "Otros importadores", ["Especial", "Tradicional", "Reserva de la Familia"]),
                         ("1800", "Otros importadores", ["Cristalino", "Añejo"]), ("Casamigos", "Diageo", ["Blanco", "Reposado"]),
                         ("400 Conejos", "Otros importadores", ["Mezcal"]), ("Montelobos", "Otros importadores", ["Mezcal Espadín"]),
                         ("Casa Dragones", "Otros importadores", ["Blanco"]), ("Herradura", "Otros importadores", ["Reposado"])],
    "Vodka": [("Absolut", "Pernod Ricard", ["", "Citron", "Raspberri", "Elyx"]), ("Grey Goose", "Bacardí", ["", "La Poire"]),
              ("Smirnoff", "Diageo", ["", "Green Apple"]), ("Belvedere", "Otros importadores", [""]),
              ("Ketel One", "Diageo", [""]), ("Cîroc", "Diageo", ["", "Red Berry"]), ("Stolichnaya", "Otros importadores", [""]),
              ("Tito's", "Otros importadores", [""])],
    "Aguardiente": [("Antioqueño", "Otros importadores", ["Verde", "Sin Azúcar", "Real 700 ml"]),
                    ("Amarillo de Manzanares", "Otros importadores", [""]), ("Néctar", "Otros importadores", ["Club", "Verde"]),
                    ("Blanco del Valle", "Otros importadores", [""]), ("Mil Demonios", "Distribución KYVA", ["50 ml"])],
    "Champaña y espumosos": [("Moët & Chandon", "Otros importadores", ["Impérial", "Rosé Impérial", "Nectar Impérial"]),
                             ("Veuve Clicquot", "Otros importadores", ["Brut", "Rosé"]), ("Mumm", "Pernod Ricard", ["Cordon Rouge", "Rosé"]),
                             ("Perrier-Jouët", "Pernod Ricard", ["Grand Brut", "Belle Époque"]), ("Dom Pérignon", "Otros importadores", ["Vintage"]),
                             ("Freixenet", "Otros importadores", ["Cordon Negro", "Prosecco"]), ("Chandon", "Otros importadores", ["Brut", "Garden Spritz"]),
                             ("Martini", "Bacardí", ["Asti", "Prosecco"]), ("Codorníu", "Otros importadores", ["Clásico", "Rosé"])],
    "Cognac, brandy y pisco": [("Martell", "Pernod Ricard", ["VS", "VSOP", "Blue Swift"]), ("Hennessy", "Otros importadores", ["VS", "VSOP", "XO"]),
                               ("Rémy Martin", "Otros importadores", ["VSOP", "1738"]), ("Demonio de los Andes", "Otros importadores", ["Quebranta", "Acholado"]),
                               ("Torres", "Otros importadores", ["10", "20"]), ("Carlos I", "Otros importadores", [""])],
    "Licores y aperitivos": [("Aperol", "Otros importadores", [""]), ("Campari", "Otros importadores", [""]), ("Baileys", "Diageo", ["", "Salted Caramel"]),
                             ("Jägermeister", "Otros importadores", [""]), ("Licor 43", "Otros importadores", ["", "Baristo"]),
                             ("Cointreau", "Otros importadores", [""]), ("Kahlúa", "Pernod Ricard", [""]), ("Malibu", "Pernod Ricard", [""]),
                             ("Amaretto Disaronno", "Otros importadores", [""]), ("Frangelico", "Otros importadores", [""]),
                             ("Lillet", "Pernod Ricard", ["Blanc", "Rosé"]), ("Martini", "Bacardí", ["Rosso", "Bianco", "Extra Dry"]),
                             ("St-Germain", "Bacardí", [""]), ("Chambord", "Otros importadores", [""]), ("Sheridan's", "Otros importadores", [""]),
                             ("Limoncello Villa Massa", "Otros importadores", [""]), ("Ricard", "Pernod Ricard", ["Pastis"]),
                             ("Pernod", "Pernod Ricard", ["Absinthe"]), ("Fernet-Branca", "Otros importadores", [""]),
                             ("Grand Marnier", "Otros importadores", [""])],
    "Cerveza": [(m, p, ["x6", "x12"]) for m, p in [("Corona", "Bavaria"), ("BBC", "Bavaria"), ("Heineken", "Otros importadores"),
                                                   ("Peroni", "Otros importadores"), ("3 Cordilleras", "Otros importadores"),
                                                   ("Coronita", "Bavaria"), ("Budweiser", "Bavaria"), ("Erdinger", "Otros importadores"),
                                                   ("Miller", "Otros importadores"), ("Club Colombia Negra", "Bavaria")]],
    "Mixers y aguas": [("Fever-Tree", "Otros importadores", ["Tónica x4", "Ginger Beer x4", "Mediterránea x4"]),
                       ("Schweppes", "Otros importadores", ["Tónica x6", "Ginger Ale x6"]), ("Red Bull", "Otros importadores", ["x4", "Tropical x4"]),
                       ("San Pellegrino", "Otros importadores", ["x6"]), ("Perrier", "Otros importadores", ["x6"]),
                       ("Coca-Cola", "Otros importadores", ["Original x6", "Sin Azúcar x6"]), ("Hielo en cubos", "Otros importadores", ["5 kg"])],
    "Accesorios gourmet": [("Copas Riedel", "Otros importadores", ["Vino x2", "Whisky x2"]), ("Set de cata KYVA", "Otros importadores", [""]),
                           ("Decantador", "Otros importadores", [""]), ("Sacacorchos Laguiole", "Otros importadores", [""]),
                           ("Tabla de quesos", "Otros importadores", [""]), ("Chocolates Cacao Hunters", "Otros importadores", ["Caja x12"]),
                           ("Hielera", "Otros importadores", [""]), ("Caja de regalo KYVA", "Otros importadores", ["Premium"])],
}
# Nivel de precio de cada marca frente a la mediana de su categoría. Sin esto,
# un Martini Asti salía a $290.000 y un Black & White al precio de un Macallan:
# errores que cualquier persona del negocio de licores ve en dos segundos.
PRECIO_MARCA = {
    # whisky
    "Black & White": .33, "Something Special": .36, "Ballantine's": .45, "Dewar's": .48,
    "Johnnie Walker": .55, "Jameson": .62, "Old Parr": .8, "Jack Daniel's": .85,
    "Monkey Shoulder": .85, "Bulleit": .85, "Maker's Mark": .9, "Buchanan's": 1.0,
    "Woodford Reserve": 1.05, "The Singleton": .95, "Glenfiddich": 1.0, "The Glenlivet": 1.0,
    "Aberlour": 1.05, "Glenmorangie": 1.05, "Chivas Regal": 1.0, "Talisker": 1.2,
    "Lagavulin": 1.9, "Macallan": 1.9, "Royal Salute": 1.3,
    # vino
    "Santa Rita 120": .45, "Undurraga": .5, "Santa Carolina": .5, "Trapiche": .5,
    "Casillero del Diablo": .55, "Castillo de Molina": .62, "Norton": .6, "Alamos": .7,
    "Emiliana": .7, "Campo Viejo": .7, "Mouton Cadet": .9, "Montes": 1.0, "Beronia": 1.0,
    "Marqués de Casa Concha": 1.1, "Ramón Bilbao": 1.1, "Luigi Bosca": 1.2, "Catena": 1.2,
    "Marqués de Riscal": 1.3, "Rutini": 1.5, "Protos": 1.5,
    # ron
    "Ron Viejo de Caldas": .38, "Bacardí": .5, "Captain Morgan": .55, "Havana Club": .75,
    "Kraken": .85, "La Hechicera": 1.2, "Parce": 1.1, "Dictador": 1.1, "Diplomático": 1.3,
    "Zacapa": 2.3, "Defensor": 2.4,
    # ginebra, tequila, vodka
    "Tanqueray": .75, "Bombay Sapphire": .8, "Malfy": .8, "Plymouth": .9, "Roku": .9,
    "Beefeater": 1.0, "Hendrick's": 1.1, "Gin Mare": 1.15, "Monkey 47": 1.5,
    "José Cuervo": .45, "400 Conejos": .7, "Herradura": .8, "Montelobos": .85, "1800": .85,
    "Avión": 1.0, "Don Julio": 1.0, "Patrón": 1.1, "Casamigos": 1.2, "Casa Dragones": 2.4,
    "Smirnoff": .42, "Stolichnaya": .55, "Absolut": .68, "Tito's": .8, "Ketel One": .9,
    "Cîroc": 1.15, "Grey Goose": 1.3, "Belvedere": 1.3,
    # aguardiente, espumosos, destilados, licores
    "Antioqueño": .8, "Néctar": .7, "Blanco del Valle": .7, "Amarillo de Manzanares": .85,
    "Mil Demonios": 1.6,
    "Martini": .22, "Freixenet": .3, "Codorníu": .3, "Chandon": .5, "Mumm": .85,
    "Moët & Chandon": 1.0, "Veuve Clicquot": 1.15, "Perrier-Jouët": 1.2, "Dom Pérignon": 3.0,
    "Demonio de los Andes": .42, "Carlos I": .6, "Torres": .55, "Martell": .8,
    "Hennessy": .85, "Rémy Martin": 1.1,
    "Ricard": .6, "Pernod": .8, "Campari": .6, "Aperol": .62, "Malibu": .6, "Kahlúa": .65,
    "Sheridan's": .75, "Baileys": .8, "Fernet-Branca": .8, "Jägermeister": .9, "Lillet": .8,
    "Licor 43": .95, "Amaretto Disaronno": .9, "Frangelico": .9, "Cointreau": 1.1,
    "St-Germain": 1.2, "Chambord": 1.1, "Grand Marnier": 1.2, "Limoncello Villa Massa": .7,
}
VARIANTE = {   # nivel frente a la mediana de la categoría, por etiqueta
    "Blue Label": 5.0, "18 años": 2.8, "21 años": 4.6, "21 años Polo": 5.2, "Mizunara": 2.6,
    "15 años": 1.6, "Gold Reserve": 1.3, "Double Black": 1.0, "Black Label": .85,
    "Red Label": .5, "Master": 1.25, "Two Souls": 1.4, "12 Double Cask": 1.9,
    "15 Double Cask": 2.7, "18 Sherry Oak": 5.5, "Caribbean Reserve": .95,
    "XO": 3.8, "1942": 4.3, "70": 1.0, "Reserva de la Familia": 2.6, "Belle Époque": 3.5,
    "Vintage": 7.0, "23": 2.3, "Edición Negra": 2.0, "Selección de Maestros": 1.3,
    "20 años": 2.2, "Gran Reserva": .9, "Reserva Ocho": .75,
}
PRESENTACION = {"Whisky": [700, 750, 1000, 375], "Vino": [750], "Ron": [700, 750, 1000],
                "Ginebra": [700, 1000], "Tequila y mezcal": [700, 750], "Vodka": [700, 750, 1000],
                "Aguardiente": [375, 750, 1000], "Champaña y espumosos": [750, 375],
                "Cognac, brandy y pisco": [700], "Licores y aperitivos": [700, 750, 1000],
                "Cerveza": [0], "Mixers y aguas": [0], "Accesorios gourmet": [0]}


def gen_catalogo() -> pd.DataFrame:
    filas = []
    for nombre, cat, marca, prov, ml, classic, elite in REALES:
        filas.append(dict(nombre=nombre, categoria=cat, marca=marca, proveedor=prov,
                          ml=ml, precio_classic=classic, precio_elite=elite,
                          precio_observado=True))
    usados = {f["nombre"] for f in filas}
    for cat, n, mediana, _, _ in CATEGORIAS:
        faltan = n - sum(1 for f in filas if f["categoria"] == cat)
        pool = []
        for marca, prov, variantes in MARCAS[cat]:
            for v in variantes:
                for ml in PRESENTACION[cat]:
                    pool.append((marca, prov, v, ml))
        RNG.shuffle(pool)
        # Primero una presentación por variante, luego las demás
        pool.sort(key=lambda x: PRESENTACION[cat].index(x[3]))
        for marca, prov, v, ml in pool:
            if faltan <= 0:
                break
            pref = {"Vino": "Vino", "Cerveza": "Cerveza", "Whisky": "Whisky", "Ron": "Ron",
                    "Ginebra": "Ginebra", "Vodka": "Vodka", "Aguardiente": "Aguardiente"}.get(cat, "")
            base = " ".join(x for x in (pref, marca, v) if x)
            nombre = base + (f" {ml} ml" if ml and ml not in (700, 750) else "")
            if nombre in usados:
                continue
            usados.add(nombre)
            factor_ml = (ml / 750) ** .85 if ml else 1
            # Las etiquetas icónicas tienen su propio precio: un Blue Label no
            # cuesta "Johnnie Walker × algo", cuesta lo que cuesta un Blue Label.
            nivel = VARIANTE.get(v, PRECIO_MARCA.get(marca, 1.0))
            precio = mediana * factor_ml * nivel * RNG.lognormal(0, .16)
            precio = float(np.clip(round(precio, -2), 12_000, 2_400_000))
            filas.append(dict(nombre=nombre, categoria=cat, marca=marca, proveedor=prov,
                              ml=ml, precio_classic=precio, precio_elite=None,
                              precio_observado=False))
            faltan -= 1
    df = pd.DataFrame(filas)
    df["sku"] = [f"KY-{i:04d}" for i in range(1, len(df) + 1)]

    # Precio Elite: donde no se vio, descuento sorteado. Pernod y Diageo dan más
    # espacio (el fundador viene de Pernod Ricard Colombia).
    prof = np.where(df["proveedor"].isin(["Pernod Ricard", "Diageo"]), .10, .06)
    d = np.clip(RNG.normal(prof, .035), .02, .19)
    df["precio_elite"] = df["precio_elite"].fillna(
        (df["precio_classic"] * (1 - d)).round(-2))

    # Precio sugerido de mercado (PVP): Classic queda ~4% debajo.
    df["pvp_mercado"] = (df["precio_classic"] * RNG.uniform(1.0, 1.09, len(df))).round(-2)

    # Costo: margen sobre el precio Classic sin IVA, por categoría. Las marcas en
    # distribución propia se compran directo y dejan más.
    margen = df["categoria"].map({c[0]: c[3] for c in CATEGORIAS}).values
    margen = np.where(df["proveedor"] == "Distribución KYVA", .31, margen)
    margen = np.clip(margen + RNG.normal(0, .03, len(df)), .06, .5)
    iva = df["categoria"].map(IVA_CAT).values
    df["costo_unit"] = (df["precio_classic"] / (1 + iva) * (1 - margen)).round(-1)
    df["exclusiva"] = df["proveedor"] == "Distribución KYVA"

    # Popularidad: las referencias reales arriba, y una cola larga de verdad —
    # ~150 referencias que casi no se mueven (la "mercancía que no rota").
    n = len(df)
    rango = RNG.permutation(n) + 1
    peso = 1 / rango ** .95
    # Lo que más rota es el rango medio: una botella de $800.000 no puede ser la
    # referencia más vendida. Las caras pierden peso según su precio.
    precio = df["precio_classic"].values
    caros = precio > 350_000
    peso[caros] *= (350_000 / precio[caros]) ** 1.6
    peso[df["precio_observado"].values] *= 6
    peso[df["categoria"].isin(["Mixers y aguas", "Cerveza"]).values] *= 1.6
    muertas = RNG.choice(np.where(~df["precio_observado"].values)[0], 150, replace=False)
    peso[muertas] *= .015
    df["popularidad"] = peso / peso.sum()
    df = df[["sku", "nombre", "categoria", "marca", "proveedor", "ml", "precio_classic",
             "precio_elite", "pvp_mercado", "costo_unit", "exclusiva", "precio_observado",
             "popularidad"]]
    return df


# ═════════════════════════════════════════════════════════════════════════════
# 2. CLIENTES Y PEDIDOS DE E-COMMERCE (The Store y The Lounge)
# ═════════════════════════════════════════════════════════════════════════════
# Clientes nuevos (primera compra) por mes. The Store abrió en oct-2023: antes
# KYVA era 100% privado. Calibrado contra el crecimiento público de 2024 y 2025.
NUEVOS_STORE = _curva({"2022-01": 0, "2023-09": 0, "2023-10": 70, "2024-06": 215,
                       "2024-12": 400, "2025-06": 620, "2025-12": 840, "2026-08": 700})
NUEVOS_ELITE = _curva({"2022-01": 114, "2023-01": 129, "2023-12": 149, "2024-12": 225,
                       "2025-12": 330, "2026-08": 285})

# Un solo multiplicador de volumen para las dos curvas: la forma la dan las
# curvas, el nivel se ajusta aquí contra el tamaño de la empresa.
ESCALA_CLIENTES = 1.38

ORIGEN_STORE = [("Google y SEO", .44), ("Instagram y Meta", .25), ("Mi Círculo (referido)", .19),
                ("Directo y WhatsApp", .12)]
ORIGEN_ELITE = [("Alianza", .62), ("Referido Elite", .23), ("Compra de membresía", .15)]

# (prob. de 2.ª compra, prob. de las siguientes, días medianos entre compras)
RECOMPRA = {"Google y SEO": (.34, .60, 64), "Instagram y Meta": (.30, .57, 68),
            "Mi Círculo (referido)": (.43, .64, 56), "Directo y WhatsApp": (.46, .66, 52),
            "Alianza": (.44, .66, 58), "Referido Elite": (.52, .70, 50),
            "Compra de membresía": (.70, .80, 38)}


def _fechas_en_mes(periodos, rng=RNG) -> pd.DatetimeIndex:
    """Un día por elemento dentro de su mes, pesado por día de la semana y quincena."""
    salida = np.empty(len(periodos), dtype="datetime64[ns]")
    for p in np.unique(periodos):
        idx = np.where(periodos == p)[0]
        dias = pd.date_range(p.start_time, p.end_time.normalize(), freq="D")
        w = DOW[dias.dayofweek] * np.where(dias.day.isin([14, 15, 16, 29, 30, 31, 1]), 1.25, 1)
        salida[idx] = rng.choice(dias.values, size=len(idx), p=w / w.sum())
    return pd.DatetimeIndex(salida)


def _reubicar_semana(fechas: pd.DatetimeIndex, rng=RNG) -> pd.DatetimeIndex:
    """Mueve cada fecha a un día de su misma semana según el patrón de consumo."""
    lunes = fechas.normalize() - pd.to_timedelta(fechas.dayofweek, unit="D")
    dow = rng.choice(7, size=len(fechas), p=DOW / DOW.sum())
    return lunes + pd.to_timedelta(dow, unit="D")


def simular_clientes():
    filas = []
    for i, per in enumerate(MESES_SIM):
        est = ESTACION[per.month] ** .8
        # El lanzamiento de la membresía Élite en el Porsche Center (sep-2025)
        extra_elite = 60 if str(per) == "2025-09" else 0
        for tipo, curva, origenes in (("Classic", NUEVOS_STORE, ORIGEN_STORE),
                                      ("Elite", NUEVOS_ELITE, ORIGEN_ELITE)):
            n = RNG.poisson(curva[i] * est * ESCALA_CLIENTES + (extra_elite if tipo == "Elite" else 0))
            if n == 0:
                continue
            org = _pick(origenes, n)
            filas.append(pd.DataFrame({"tipo": tipo, "origen": org, "periodo": per}))
    cli = pd.concat(filas, ignore_index=True)
    cli["cliente_id"] = [f"C{i:06d}" for i in range(1, len(cli) + 1)]
    cli["fecha_alta"] = _fechas_en_mes(cli["periodo"].values)
    cli["zona"] = _pick([(z, w) for z, w, _ in ZONAS], len(cli))
    es_al = cli["origen"] == "Alianza"
    cli["aliado"] = ""
    cli.loc[es_al, "aliado"] = _pick([(a, w * act) for a, w, act in ALIADOS], int(es_al.sum()))
    sep25 = es_al & (cli["periodo"].astype(str) == "2025-09")
    cli.loc[sep25 & (RNG.random(len(cli)) < .5), "aliado"] = "Porsche Center Bogotá"

    # ── Pedidos por proceso de recompra, generación por generación ────────────
    p1 = cli["origen"].map(lambda o: RECOMPRA[o][0]).values
    pn = cli["origen"].map(lambda o: RECOMPRA[o][1]).values
    gap = cli["origen"].map(lambda o: RECOMPRA[o][2]).values
    ped_c, ped_f = [cli.index.values], [cli["fecha_alta"].values]
    vivos = np.ones(len(cli), bool)
    actual = cli["fecha_alta"].values.copy()
    for g in range(40):
        p = p1 if g == 0 else pn
        sigue = vivos & (RNG.random(len(cli)) < p)
        dias = RNG.lognormal(np.log(gap), .62)
        nueva = actual + (dias * 86_400e9).astype("timedelta64[ns]")
        nueva = _reubicar_semana(pd.DatetimeIndex(nueva)).values
        nueva = np.maximum(nueva, actual + np.timedelta64(1, "D"))
        sigue &= nueva <= CORTE.to_datetime64()
        if not sigue.any():
            break
        ped_c.append(cli.index.values[sigue])
        ped_f.append(nueva[sigue])
        actual = np.where(sigue, nueva, actual)
        vivos = sigue
    ped = pd.DataFrame({"ci": np.concatenate(ped_c),
                        "fecha": pd.DatetimeIndex(np.concatenate(ped_f))})

    # ── Compras de temporada que el proceso no captura ────────────────────────
    extra = []
    temporada = {12: .15, 6: .06, 9: .07, 11: .04}
    for per in MESES_SIM:
        tasa = temporada.get(per.month)
        if not tasa:
            continue
        ini, fin = per.start_time, per.end_time
        ult = ped[(ped["fecha"] < ini) & (ped["fecha"] >= ini - pd.Timedelta(days=365))]
        base = ult["ci"].unique()
        sel = base[RNG.random(len(base)) < tasa]
        if len(sel):
            f = _fechas_en_mes(np.array([per] * len(sel), dtype=object))
            if per.month == 12:   # se concentra antes de Navidad
                f = pd.DatetimeIndex([min(x, pd.Timestamp(per.year, 12, RNG.integers(5, 24)))
                                      if RNG.random() < .7 else x for x in f])
            extra.append(pd.DataFrame({"ci": sel, "fecha": f}))
    ped = pd.concat([ped] + extra, ignore_index=True)

    # ── El choque del IVA del 19% (enero de 2026) ─────────────────────────────
    ene = (ped["fecha"] >= IVA19_DESDE) & (ped["fecha"] <= IVA19_HASTA)
    u = RNG.random(len(ped))
    adelanto = ene & (u < .13)                  # compraron antes, a fin de diciembre
    ped.loc[adelanto, "fecha"] = pd.to_datetime("2025-12-26") + pd.to_timedelta(
        RNG.integers(0, 6, int(adelanto.sum())), unit="D")
    ped = ped[~(ene & (u >= .13) & (u < .27))]  # demanda que no volvió

    ped = ped[(ped["fecha"] <= CORTE)].copy()
    ped["fecha"] = ped["fecha"].dt.normalize() + pd.to_timedelta(
        RNG.choice(24, len(ped), p=HORA) * 60 + RNG.integers(0, 60, len(ped)), unit="m")
    ped = ped.sort_values("fecha").reset_index(drop=True)
    return cli, ped


# ═════════════════════════════════════════════════════════════════════════════
# 3. LÍNEAS DE PRODUCTO → valor de cada pedido y rotación del surtido
# ═════════════════════════════════════════════════════════════════════════════
MULT_MES = {12: {"Champaña y espumosos": 2.3, "Whisky": 1.3, "Aguardiente": 1.9, "Accesorios gourmet": 1.8},
            6: {"Whisky": 1.45, "Cognac, brandy y pisco": 1.3},
            9: {"Vino": 1.35, "Champaña y espumosos": 1.3, "Licores y aperitivos": 1.2},
            1: {"Cerveza": 1.3, "Mixers y aguas": 1.3}}


def gen_lineas(ped: pd.DataFrame, cli: pd.DataFrame, cat: pd.DataFrame) -> pd.DataFrame:
    tipo = cli["tipo"].values[ped["ci"].values]
    lam = np.where(tipo == "Elite", 1.45, 1.05)
    n_items = 1 + RNG.poisson(lam)
    lin = pd.DataFrame({"pi": np.repeat(ped.index.values, n_items)})
    lin["mes"] = np.repeat(ped["fecha"].dt.month.values, n_items)
    lin["sku_i"] = 0
    cat_arr = cat["categoria"].values
    for m in range(1, 13):
        idx = np.where(lin["mes"].values == m)[0]
        if not len(idx):
            continue
        w = cat["popularidad"].values.copy()
        for c, f in MULT_MES.get(m, {}).items():
            w[cat_arr == c] *= f
        lin.iloc[idx, lin.columns.get_loc("sku_i")] = RNG.choice(len(cat), len(idx), p=w / w.sum())
    c_lin = cat_arr[lin["sku_i"].values]
    multi = np.isin(c_lin, ["Cerveza", "Mixers y aguas"])
    lin["unidades"] = np.where(multi, RNG.integers(1, 4, len(lin)),
                               np.where(RNG.random(len(lin)) < .12, 2, 1))
    fechas = ped["fecha"].values[lin["pi"].values]
    defl = _deflactor(fechas)
    es_elite = tipo[lin["pi"].values] == "Elite"
    classic = cat["precio_classic"].values[lin["sku_i"].values] * defl
    elite = cat["precio_elite"].values[lin["sku_i"].values] * defl
    # Los descuentos se profundizaron con el tiempo: la brecha Elite llega a la
    # de hoy tras el relanzamiento de la membresía en sep-2025, y The Store pasó
    # de promociones ocasionales a una de cada ocho líneas. SUPUESTO del modelo.
    t = pd.DatetimeIndex(fechas).asi8
    f_el = np.interp(t, pd.to_datetime(["2022-01-01", "2024-06-01", "2025-06-01", "2025-10-01"]).asi8,
                     [.5, .6, .8, 1.0])
    p_promo = np.interp(t, pd.to_datetime(["2023-10-01", "2025-01-01", "2026-01-01"]).asi8,
                        [.05, .08, .12])
    elite = classic - (classic - elite) * f_el
    promo = (~es_elite) & (RNG.random(len(lin)) < p_promo)
    desc_promo = np.where(promo, RNG.uniform(.08, .26, len(lin)), 0)
    precio = np.where(es_elite, elite, classic * (1 - desc_promo))
    iva = pd.Series(c_lin).map(IVA_CAT).values
    ts = pd.DatetimeIndex(fechas)
    en_iva19 = (ts >= IVA19_DESDE) & (ts <= IVA19_HASTA) & (iva == .05)
    bruto = precio * lin["unidades"].values * np.where(en_iva19, 1.19 / 1.05, 1)
    lin["valor_bruto"] = bruto.round(-1)
    lin["descuento"] = ((classic - precio) * lin["unidades"].values).round(-1)
    lin["ingreso_neto"] = (bruto / (1 + np.where(en_iva19, .19, iva))).round(-1)
    lin["costo"] = (cat["costo_unit"].values[lin["sku_i"].values] * defl *
                    lin["unidades"].values).round(-1)
    lin["pvp"] = cat["pvp_mercado"].values[lin["sku_i"].values] * defl * lin["unidades"].values
    lin["sku"] = cat["sku"].values[lin["sku_i"].values]
    lin["categoria"] = c_lin
    return lin


def _habil(d) -> bool:
    return d.weekday() < 5 and d.date() not in FESTIVOS


def _siguiente_habil(d):
    d = d + pd.Timedelta(days=1)
    while not _habil(d):
        d += pd.Timedelta(days=1)
    return d


def entregas(ped: pd.DataFrame) -> pd.DataFrame:
    """Aplica el horario público de despacho a cada pedido."""
    disp, vent = [], []
    for ts in ped["fecha"]:
        d = ts.normalize()
        h = ts.hour + ts.minute / 60
        if _habil(d) and h < CORTE_MISMO_DIA:
            disp.append(d); vent.append("Pide AM · recibe PM")
        elif _habil(d) and h < CIERRE[d.weekday()]:
            disp.append(_siguiente_habil(d)); vent.append("Día hábil siguiente")
        else:
            s = _siguiente_habil(d)
            disp.append(s)
            vent.append("Espera fin de semana o festivo" if (s - d).days >= 2 or not _habil(d)
                        else "Día hábil siguiente")
    disp = pd.DatetimeIndex(disp)
    ped["ventana"] = vent
    # Resbalones: en la segunda quincena de diciembre se pierde uno de cada cinco.
    pico = (disp.month == 12) & (disp.day.isin(range(10, 25)))
    resbala = RNG.random(len(ped)) < np.where(pico, .21, .045)
    disp = pd.DatetimeIndex([_siguiente_habil(x) if r else x for x, r in zip(disp, resbala)])
    mismo = np.array(vent) == "Pide AM · recibe PM"
    hora = np.where(mismo & ~resbala, RNG.uniform(13.5, 18, len(ped)), RNG.uniform(10, 17.5, len(ped)))
    ped["fecha_entrega"] = disp + pd.to_timedelta(hora * 60, unit="m").round("min")
    ped["horas_espera"] = ((ped["fecha_entrega"] - ped["fecha"]).dt.total_seconds() / 3600).round(1)
    ped["en_promesa"] = ~resbala
    p_cancel = .011 + .048 * (ped["horas_espera"] > 40) + .02 * resbala
    ped["cancelado"] = RNG.random(len(ped)) < p_cancel
    return ped


def armar_pedidos(cli, ped, lin, cat) -> pd.DataFrame:
    agg = lin.groupby("pi").agg(items=("sku", "size"), unidades=("unidades", "sum"),
                                valor_bruto=("valor_bruto", "sum"), descuento=("descuento", "sum"),
                                ingreso_prod=("ingreso_neto", "sum"), costo_mercancia=("costo", "sum"),
                                pvp=("pvp", "sum"))
    principal = (lin.sort_values("valor_bruto").groupby("pi")["categoria"].last())
    exclusiva = lin.assign(e=lin["sku"].isin(cat.loc[cat["exclusiva"], "sku"])).groupby("pi")["e"].any()
    ped = ped.join(agg).join(principal.rename("categoria_principal")).join(exclusiva.rename("lleva_exclusiva"))
    c = cli.iloc[ped["ci"].values]
    ped["cliente_id"] = c["cliente_id"].values
    ped["canal"] = np.where(c["tipo"].values == "Elite", "The Lounge", "The Store")
    ped["origen"] = c["origen"].values
    ped["zona"] = c["zona"].values
    ped["n_compra"] = ped.groupby("cliente_id").cumcount() + 1
    ped["mes"] = ped["fecha"].dt.strftime("%Y-%m")
    ped["dia_semana"] = ped["fecha"].dt.dayofweek
    ped["hora"] = ped["fecha"].dt.hour

    defl = _deflactor(ped["fecha"])
    ped["envio_cobrado"] = np.where(ped["valor_bruto"] < ENVIO_GRATIS, ENVIO_COSTO, 0)
    sab = ped["zona"].isin(SABANA).values
    ped["costo_envio"] = (np.where(sab, 21_500, 14_800) * defl).round(-1)
    # Cupones de Mi Círculo ($25.000, supuesto): el referido en su primera compra
    # y quien lo invitó en la siguiente compra que haga.
    ped["cupon"] = np.where((ped["origen"] == "Mi Círculo (referido)") & (ped["n_compra"] == 1), 25_000, 0)
    ped.loc[(ped["n_compra"] > 1) & (RNG.random(len(ped)) < .07), "cupon"] = 25_000
    pagado = ped["valor_bruto"] + ped["envio_cobrado"] - ped["cupon"]
    ped["comision_pasarela"] = (pagado * .0299 + 900).round(-1)
    ped["empaque"] = (3_200 * defl).round(-1)
    ped["ingreso_neto"] = (ped["ingreso_prod"] + ped["envio_cobrado"] / 1.19 - ped["cupon"] / 1.05).round(-1)
    ped["margen_bruto"] = ped["ingreso_prod"] - ped["costo_mercancia"]
    ped["contribucion"] = (ped["ingreso_neto"] - ped["costo_mercancia"] - ped["costo_envio"]
                           - ped["comision_pasarela"] - ped["empaque"])
    # Cancelado: no hay venta, pero sí el pedido perdido
    montos = ["ingreso_prod", "ingreso_neto", "costo_mercancia", "costo_envio",
              "comision_pasarela", "empaque", "margen_bruto", "contribucion", "cupon", "envio_cobrado"]
    ped.loc[ped["cancelado"], montos] = 0
    ped["estado"] = np.where(ped["cancelado"], "Cancelado", "Entregado")
    ped["pedido_id"] = [f"P{i:07d}" for i in range(1, len(ped) + 1)]
    cols = ["pedido_id", "cliente_id", "fecha", "mes", "dia_semana", "hora", "canal", "origen",
            "zona", "n_compra", "items", "unidades", "categoria_principal", "lleva_exclusiva",
            "pvp", "valor_bruto", "descuento", "cupon", "envio_cobrado", "ingreso_neto",
            "costo_mercancia", "margen_bruto", "costo_envio", "comision_pasarela", "empaque",
            "contribucion", "ventana", "fecha_entrega", "horas_espera", "en_promesa", "estado"]
    for m in ["pvp", "valor_bruto", "descuento", "margen_bruto", "contribucion"]:
        ped[m] = ped[m].round(-1)
    return ped[cols]


def resumir_clientes(cli: pd.DataFrame, ped: pd.DataFrame) -> pd.DataFrame:
    ok = ped[ped["estado"] == "Entregado"]
    g = ok.groupby("cliente_id").agg(pedidos=("pedido_id", "size"), ingreso_neto=("ingreso_neto", "sum"),
                                     contribucion=("contribucion", "sum"), primer_pedido=("fecha", "min"),
                                     ultimo_pedido=("fecha", "max"))
    out = cli.drop(columns=["periodo"]).set_index("cliente_id").join(g).reset_index()
    out = out[out["pedidos"].notna()].copy()
    out["pedidos"] = out["pedidos"].astype(int)
    out["dias_sin_comprar"] = (CORTE - out["ultimo_pedido"]).dt.days
    out["estado"] = np.select([out["dias_sin_comprar"] <= 90, out["dias_sin_comprar"] <= 180],
                              ["Activo", "En riesgo"], "Dormido")
    out["cohorte"] = out["primer_pedido"].dt.strftime("%Y-%m")
    # Quién refirió a quién (Mi Círculo y Referido Elite): un cliente que ya existía.
    refer = out["origen"].isin(["Mi Círculo (referido)", "Referido Elite"]).values
    out["referido_por"] = ""
    orden = out.sort_values("primer_pedido")
    fechas = orden["primer_pedido"].values
    ids = orden["cliente_id"].values
    peso_base = np.where(orden["tipo"].values == "Elite", 3.0, 1.0) * np.sqrt(orden["pedidos"].values)
    for i in np.where(refer)[0]:
        f = out["primer_pedido"].values[i]
        k = np.searchsorted(fechas, f)
        if k < 5:
            continue
        w = peso_base[:k]
        out.iat[i, out.columns.get_loc("referido_por")] = ids[:k][RNG.choice(k, p=w / w.sum())]
    for c in ["primer_pedido", "ultimo_pedido"]:
        out[c] = out[c].dt.strftime("%Y-%m-%d")
    out["fecha_alta"] = out["fecha_alta"].dt.strftime("%Y-%m-%d")
    return out


# ═════════════════════════════════════════════════════════════════════════════
# 4. MEMBRESÍA ELITE: los miembros que compran y los que nunca estrenaron
# ═════════════════════════════════════════════════════════════════════════════
def gen_miembros(clientes: pd.DataFrame) -> pd.DataFrame:
    elite = clientes[clientes["tipo"] == "Elite"]
    act = {"Referido Elite": .64, "Compra de membresía": .93}
    filas = [pd.DataFrame({"cliente_id": elite["cliente_id"], "origen": elite["origen"],
                           "aliado": elite["aliado"], "fecha_alta": elite["fecha_alta"],
                           "compro": True})]
    # Los que recibieron la membresía y nunca compraron
    for (org, aliado), grupo in elite.groupby(["origen", "aliado"]):
        tasa = act.get(org) or dict((a, x) for a, _, x in ALIADOS).get(aliado, .35)
        if aliado == "Porsche Center Bogotá":
            tasa = .46
        n_no = int(round(len(grupo) * (1 / tasa - 1)))
        if n_no <= 0:
            continue
        altas = pd.to_datetime(grupo["fecha_alta"]).sample(n_no, replace=True, random_state=int(RNG.integers(1e9)))
        altas = altas + pd.to_timedelta(RNG.integers(-20, 20, n_no), unit="D")
        filas.append(pd.DataFrame({"cliente_id": "", "origen": org, "aliado": aliado,
                                   "fecha_alta": altas.clip(upper=CORTE).dt.strftime("%Y-%m-%d").values,
                                   "compro": False}))
    m = pd.concat(filas, ignore_index=True).sort_values("fecha_alta").reset_index(drop=True)
    m["miembro_id"] = [f"M{i:06d}" for i in range(1, len(m) + 1)]
    return m[["miembro_id", "fecha_alta", "origen", "aliado", "compro", "cliente_id"]]


# ═════════════════════════════════════════════════════════════════════════════
# 5. MI CÍRCULO: invitaciones mensuales (agregado)
# ═════════════════════════════════════════════════════════════════════════════
def gen_referidos(clientes: pd.DataFrame, ped: pd.DataFrame) -> pd.DataFrame:
    ref = clientes[clientes["origen"].isin(["Mi Círculo (referido)", "Referido Elite"])]
    compraron = ref.groupby(ref["primer_pedido"].str[:7]).size()
    filas = []
    for m in MESES:
        c = int(compraron.get(m, 0))
        reg = int(round(c / RNG.uniform(.50, .58)))
        inv = int(round(reg / RNG.uniform(.20, .25)))
        cup_emit = c * 2
        cup_usados = int(round(c + c * RNG.uniform(.55, .68)))
        filas.append(dict(mes=m, invitaciones=inv, registrados=reg, primera_compra=c,
                          cupones_emitidos=cup_emit, cupones_usados=cup_usados,
                          costo_cupones=cup_usados * 25_000))
    return pd.DataFrame(filas)


# ═════════════════════════════════════════════════════════════════════════════
# 6. CORPORATIVO: regalos, eventos, bodas, catas
# ═════════════════════════════════════════════════════════════════════════════
CORP_ANUAL = {2022: .18e9, 2023: .35e9, 2024: .58e9, 2025: 1.45e9, 2026: 2.2e9}   # neto, entregado
CORP_MES = np.array([.025, .03, .04, .045, .055, .08, .04, .045, .085, .065, .16, .33])
SECTORES = [("Financiero", 20), ("Tecnología", 15), ("Inmobiliario y construcción", 11),
            ("Automotriz", 8), ("Salud", 9), ("Consultoría y legal", 12), ("Energía y minería", 7),
            ("Consumo masivo", 8), ("Educación", 4), ("Gremios y asociaciones", 6)]
TIPOS_CORP = [("Regalos de fin de año", 46), ("Obsequios a clientes", 18), ("Evento corporativo", 16),
              ("Boda o celebración privada", 12), ("Cata privada", 8)]


def gen_corporativo() -> pd.DataFrame:
    filas = []
    n_emp = 0
    for anio, total in CORP_ANUAL.items():
        for mes in range(1, 13):
            entrega_ini = pd.Timestamp(anio, mes, 1)
            if entrega_ini < INICIO_SIM:
                continue
            objetivo = total * CORP_MES[mes - 1]
            ganado = 0
            while ganado < objetivo:
                bruto = float(np.clip(RNG.lognormal(np.log(3.6e6), .95), 6e5, 9e7))
                gana = RNG.random() < .43
                dia = int(RNG.integers(1, 21 if mes == 12 else 28))
                entrega = pd.Timestamp(anio, mes, dia)
                # Los regalos de fin de año se cotizan desde julio; lo demás, con
                # dos a seis semanas de anticipación.
                lead = RNG.integers(25, 150) if mes in (11, 12) else RNG.integers(10, 45)
                cotiza = entrega - pd.Timedelta(days=int(lead))
                filas.append(dict(fecha_cotizacion=cotiza, fecha_entrega=entrega,
                                  valor_cotizado=round(bruto, -3), gana=gana))
                if gana:
                    ganado += bruto / 1.05
    df = pd.DataFrame(filas)
    df = df[df["fecha_cotizacion"] <= CORTE].reset_index(drop=True)
    n = len(df)
    empresas = [f"Empresa C-{i:04d}" for i in range(1, 700)]
    peso_emp = 1 / np.arange(1, 700) ** .7          # hay clientes corporativos que repiten
    df["empresa"] = RNG.choice(empresas, n, p=peso_emp / peso_emp.sum())
    df["sector"] = _pick(SECTORES, n)
    df["tipo"] = _pick(TIPOS_CORP, n)
    df.loc[df["fecha_entrega"].dt.month.isin([11, 12]) & (RNG.random(n) < .7), "tipo"] = "Regalos de fin de año"
    abierta = df["fecha_entrega"] > CORTE
    df["estado"] = np.where(abierta, "Abierta", np.where(df["gana"], "Ganada", "Perdida"))
    df["motivo_perdida"] = np.where(df["estado"] == "Perdida",
                                    _pick([("Precio", 38), ("Tiempo de entrega", 21), ("Se fue con el proveedor de siempre", 19),
                                           ("Sin respuesta del cliente", 15), ("Cobertura fuera de Bogotá", 7)], n), "")
    df["unidades"] = (df["valor_cotizado"] / RNG.uniform(120_000, 210_000, n)).round().astype(int).clip(lower=4)
    df["ingreso_neto"] = np.where(df["estado"] == "Ganada", (df["valor_cotizado"] / 1.05).round(-3), 0)
    df["costo_mercancia"] = (df["ingreso_neto"] * RNG.uniform(.74, .81, n)).round(-3)
    df["empaque_personalizado"] = (df["ingreso_neto"] * RNG.uniform(.025, .05, n)).round(-3)
    df["dias_pago"] = RNG.choice([30, 45, 60, 90], n, p=[.25, .35, .3, .1])
    df["probabilidad"] = np.where(abierta, RNG.choice([.2, .4, .6, .8], n), np.nan)
    df = df.sort_values("fecha_cotizacion").reset_index(drop=True)
    df["cotizacion_id"] = [f"Q-{i:05d}" for i in range(1, len(df) + 1)]
    for c in ["fecha_cotizacion", "fecha_entrega"]:
        df[c] = df[c].dt.strftime("%Y-%m-%d")
    return df[["cotizacion_id", "empresa", "sector", "tipo", "fecha_cotizacion", "fecha_entrega",
               "valor_cotizado", "unidades", "estado", "motivo_perdida", "probabilidad",
               "ingreso_neto", "costo_mercancia", "empaque_personalizado", "dias_pago"]]


# ═════════════════════════════════════════════════════════════════════════════
# 7. DISTRIBUCIÓN DE MARCAS: cuentas, sell-in e inventario de exclusivas
# ═════════════════════════════════════════════════════════════════════════════
MARCAS_DIST = {   # desde, precio sell-in por unidad (ago-26, sin IVA), costo, unidades medianas por pedido
    "Ron Defensor": ("2024-07-01", 168_000, 118_000, 11),
    "Marcel Thorel": ("2025-03-01", 96_000, 69_000, 13),
    "Mil Demonios": ("2026-02-01", 71_000, 49_500, 9),
}
TIPOS_CUENTA = [("Restaurante", 34), ("Bar y coctelería", 24), ("Hotel", 12),
                ("Licorera o tienda", 20), ("Club social", 10)]


def gen_distribucion(lin: pd.DataFrame, cat: pd.DataFrame):
    cuentas = []
    altas = _curva({"2022-01": 0, "2024-06": 0, "2024-07": 1.4, "2025-06": 2.2,
                    "2026-01": 3.0, "2026-02": 5.0, "2026-08": 3.5})
    for i, per in enumerate(MESES_SIM):
        for _ in range(RNG.poisson(altas[i])):
            cuentas.append(dict(alta=per.start_time + pd.Timedelta(days=int(RNG.integers(0, 27)))))
    cu = pd.DataFrame(cuentas)
    cu["cuenta_id"] = [f"D-{i:03d}" for i in range(1, len(cu) + 1)]
    cu["tipo"] = _pick(TIPOS_CUENTA, len(cu))
    cu["zona"] = _pick([(z, w) for z, w, _ in ZONAS if z not in ("Otras localidades",)], len(cu))
    cu["tamano"] = RNG.lognormal(0, .55, len(cu))
    # Algunas se apagan
    cu["baja"] = pd.NaT
    apaga = RNG.random(len(cu)) < .18
    cu.loc[apaga, "baja"] = cu.loc[apaga, "alta"] + pd.to_timedelta(RNG.integers(90, 420, int(apaga.sum())), unit="D")

    ventas = []
    for per in pd.period_range("2024-07", "2026-08", freq="M"):
        ini = per.start_time
        activas = cu[(cu["alta"] <= per.end_time) & (cu["baja"].isna() | (cu["baja"] > ini))]
        for marca, (desde, precio, costo, u_med) in MARCAS_DIST.items():
            if ini < pd.Timestamp(desde):
                continue
            prob = .52 if marca != "Mil Demonios" else .66
            for _, c in activas.iterrows():
                if RNG.random() > prob * min(1.4, c["tamano"]):
                    continue
                u = max(1, int(RNG.lognormal(np.log(u_med * c["tamano"]), .45) * ESTACION[per.month] ** 1.1))
                defl = _deflactor([ini])[0]
                ventas.append(dict(mes=str(per), cuenta_id=c["cuenta_id"], marca=marca, unidades=u,
                                   ingreso_neto=round(u * precio * defl, -2),
                                   costo_mercancia=round(u * costo * defl, -2)))
    ve = pd.DataFrame(ventas)
    cu["alta"] = cu["alta"].dt.strftime("%Y-%m-%d")
    cu["baja"] = pd.to_datetime(cu["baja"]).dt.strftime("%Y-%m-%d").fillna("")

    # Inventario de Mil Demonios: compras al productor contra ventas totales (sell-in
    # + e-commerce). Se calibra para cerrar agosto con el stock que muestra kyva.co.
    md_sku = cat.loc[cat["marca"] == "Mil Demonios", "sku"]
    md_ecom = (lin[lin["sku"].isin(md_sku)].assign(mes=lambda x: pd.DatetimeIndex(x["fecha"]).strftime("%Y-%m"))
               .groupby("mes")["unidades"].sum())
    md_dist = ve[ve["marca"] == "Mil Demonios"].groupby("mes")["unidades"].sum()
    meses_md = [str(p) for p in pd.period_range("2026-02", "2026-08", freq="M")]
    vend = np.array([md_dist.get(m, 0) + md_ecom.get(m, 0) for m in meses_md], dtype=float)
    compras = np.zeros(len(meses_md))
    compras[0] = 4_800                                  # compra inicial de la exclusiva
    stock = 0.0
    for i in range(len(meses_md)):
        disponible = stock + compras[i] - vend[i]
        if i < len(meses_md) - 1 and disponible < 1_400:
            compras[i] += 2_400
        stock = stock + compras[i] - vend[i]
    compras[-1] += ANCLAS["stock_mil_demonios_u"] - stock    # cierre = stock observado
    stock_serie = np.cumsum(compras - vend)
    inv = pd.DataFrame({"mes": meses_md, "marca": "Mil Demonios", "compras_u": compras.round(),
                        "ventas_distribucion_u": [md_dist.get(m, 0) for m in meses_md],
                        "ventas_ecommerce_u": [md_ecom.get(m, 0) for m in meses_md],
                        "stock_final_u": stock_serie.round(), "costo_unit": MARCAS_DIST["Mil Demonios"][2]})
    return cu[["cuenta_id", "tipo", "zona", "alta", "baja"]], ve, inv


# ═════════════════════════════════════════════════════════════════════════════
# 8. MERCADEO, EQUIPO Y FINANZAS
# ═════════════════════════════════════════════════════════════════════════════
def gen_marketing() -> pd.DataFrame:
    g = _curva({"2022-01": 0, "2023-09": 1.2e6, "2023-10": 2.6e6, "2024-12": 4.5e6, "2025-06": 14e6, "2025-12": 19e6, "2026-08": 17.0e6})
    m = _curva({"2022-01": 1.0e6, "2023-09": 1.6e6, "2023-10": 2.2e6, "2024-12": 3.3e6, "2025-06": 9e6, "2025-12": 12.5e6, "2026-08": 11.0e6})
    ev = _curva({"2022-01": 3.0e6, "2024-12": 5.0e6, "2026-08": 7.5e6})
    inf = _curva({"2022-01": .5e6, "2024-12": 2.0e6, "2026-08": 3.5e6})
    filas = []
    for i, per in enumerate(MESES_SIM):
        e = ESTACION[per.month]
        evento = ev[i] * (1 + (per.month == 12) * .8) + (24e6 if str(per) == "2025-09" else 0)
        for canal, v in (("Google y SEO", g[i] * e), ("Instagram y Meta", m[i] * e),
                         ("Eventos y experiencias", evento), ("Contenido e influenciadores", inf[i]),
                         ("Beneficios de Mi Círculo", 0)):
            filas.append(dict(mes=str(per), canal=canal, inversion=round(v * RNG.uniform(.9, 1.1), -3)))
    return pd.DataFrame(filas)


ROLES = [("CEO y fundador", "2019-08"), ("CMO y socio", "2019-08"), ("Operaciones y bodega", "2019-10"),
         ("Servicio al cliente", "2020-03"), ("Contabilidad y administración", "2021-01"),
         ("Compras y catálogo", "2022-06"), ("Bodega y alistamiento", "2023-10"),
         ("Mercadeo digital", "2024-02"), ("Servicio al cliente", "2024-09"),
         ("Ventas corporativas", "2025-02"), ("Bodega y alistamiento", "2025-07"),
         ("Distribución y cuentas clave", "2025-11"), ("Analista de operaciones", "2026-03")]


def gen_equipo() -> pd.DataFrame:
    filas = []
    for per in MESES_SIM:
        n = sum(1 for _, d in ROLES if pd.Period(d, "M") <= per)
        filas.append(dict(mes=str(per), personas=n))
    return pd.DataFrame(filas)


def gen_finanzas(ped, corp, dist, mkt, equipo) -> pd.DataFrame:
    ok = ped[ped["estado"] == "Entregado"]
    b2c = ok.groupby(["mes", "canal"]).agg(ing=("ingreso_neto", "sum"), costo=("costo_mercancia", "sum"),
                                           envio=("costo_envio", "sum"), pas=("comision_pasarela", "sum"),
                                           emp=("empaque", "sum")).unstack("canal").fillna(0)
    co = corp[corp["estado"] == "Ganada"].assign(mes=lambda x: x["fecha_entrega"].str[:7])
    co = co.groupby("mes")[["ingreso_neto", "costo_mercancia", "empaque_personalizado"]].sum()
    di = dist.groupby("mes")[["ingreso_neto", "costo_mercancia"]].sum()
    mk = mkt.groupby("mes")["inversion"].sum()
    eq = equipo.set_index("mes")["personas"]
    filas = []
    for per in MESES_SIM:
        m = str(per)
        defl = _deflactor([per.start_time])[0]
        g = lambda col, canal: float(b2c[(col, canal)].get(m, 0)) if (col, canal) in b2c.columns else 0.0
        f = dict(mes=m,
                 ingreso_store=g("ing", "The Store"), ingreso_lounge=g("ing", "The Lounge"),
                 ingreso_corporativo=float(co["ingreso_neto"].get(m, 0)),
                 ingreso_distribucion=float(di["ingreso_neto"].get(m, 0)))
        f["ingresos"] = f["ingreso_store"] + f["ingreso_lounge"] + f["ingreso_corporativo"] + f["ingreso_distribucion"]
        f["costo_mercancia"] = (g("costo", "The Store") + g("costo", "The Lounge") +
                                float(co["costo_mercancia"].get(m, 0)) + float(di["costo_mercancia"].get(m, 0)))
        f["margen_bruto"] = f["ingresos"] - f["costo_mercancia"]
        f["logistica"] = g("envio", "The Store") + g("envio", "The Lounge") + float(di["ingreso_neto"].get(m, 0)) * .02
        f["pasarela_y_empaque"] = (g("pas", "The Store") + g("pas", "The Lounge") + g("emp", "The Store")
                                   + g("emp", "The Lounge") + float(co["empaque_personalizado"].get(m, 0)))
        f["mercadeo"] = float(mk.get(m, 0))
        f["personas"] = int(eq.get(m, 0))
        # Costo por persona (con prestaciones). Sube con los años: al principio
        # los fundadores se pagan poco y el equipo es junior.
        sueldo = {2022: 2.5e6, 2023: 2.6e6, 2024: 2.7e6, 2025: 4.8e6, 2026: 5.2e6}[per.year]
        f["nomina"] = f["personas"] * sueldo
        f["arriendo_y_bodega"] = (4.0e6 if per < pd.Period("2025-01", "M") else 9.8e6) * defl
        f["tecnologia"] = (2.0e6 if per.year < 2025 else 3.9e6) * defl
        filas.append(f)
    fin = pd.DataFrame(filas)
    # "Otros gastos" (servicios, seguros, bancarios, mermas, bonificaciones):
    # un fijo mensual más una parte proporcional a los ingresos. Esos DOS
    # parámetros se calibran una vez contra las DOS cifras públicas de utilidad
    # operacional — margen de 0,08% en 2025 y crecimiento de +135,71% sobre
    # 2024 — y se aplican iguales a todos los meses.
    antes = (fin["margen_bruto"] - fin["logistica"] - fin["pasarela_y_empaque"] - fin["mercadeo"]
             - fin["nomina"] - fin["arriendo_y_bodega"] - fin["tecnologia"])
    anio = fin["mes"].str[:4]
    A = {a: antes[anio == a].sum() for a in ("2024", "2025")}
    I = {a: fin.loc[anio == a, "ingresos"].sum() for a in ("2024", "2025")}
    ebit25 = I["2025"] * ANCLAS["margen_operacional_2025_pct"] / 100
    ebit24 = ebit25 / (1 + ANCLAS["crec_ebit_2025_pct"] / 100)
    # A_y − 12·fijo − tasa·I_y = EBIT_y   (dos ecuaciones, dos incógnitas)
    tasa = ((A["2025"] - ebit25) - (A["2024"] - ebit24)) / (I["2025"] - I["2024"])
    fijo = ((A["2024"] - ebit24) - tasa * I["2024"]) / 12
    fin["otros_gastos"] = fijo + fin["ingresos"] * tasa
    print(f"  (otros gastos calibrados: fijo ${fijo/1e6:,.1f}M/mes + {tasa*100:.2f}% de ingresos)")
    fin["ebitda"] = (fin["margen_bruto"] - fin["logistica"] - fin["pasarela_y_empaque"] - fin["mercadeo"]
                     - fin["nomina"] - fin["arriendo_y_bodega"] - fin["tecnologia"] - fin["otros_gastos"])
    fin["depreciacion"] = 0.0
    fin["utilidad_operacional"] = fin["ebitda"] - fin["depreciacion"]

    # Capital de trabajo: inventario (días de costo, sube antes de diciembre),
    # cartera corporativa y de distribución, y proveedores.
    costo_dia = fin["costo_mercancia"].rolling(3, min_periods=1).mean() / 30
    dias_inv = fin["mes"].str[5:].map({"10": 52, "11": 58}).fillna(36).astype(float)
    fin["inventario"] = costo_dia * dias_inv
    fin.loc[fin["mes"] >= "2026-02", "inventario"] += 1.2e8     # la exclusiva de Mil Demonios
    fin["cartera"] = (fin["ingreso_corporativo"] * 1.6 + fin["ingreso_distribucion"] * 1.9) * .6
    fin["proveedores"] = costo_dia * 30 * 42 / 30
    fin["capital_trabajo"] = fin["inventario"] + fin["cartera"] - fin["proveedores"]
    caja, deuda = 1.1e8, 0.0
    cajas, deudas = [], []
    delta = fin["capital_trabajo"].diff().fillna(0)
    for i in range(len(fin)):
        caja += fin["utilidad_operacional"].iat[i] - delta.iat[i] - deuda * .0165
        if caja < 6e7:
            deuda += 6e7 - caja
            caja = 6e7
        elif caja > 1.6e8 and deuda > 0:
            pago = min(deuda, caja - 1.6e8)
            deuda -= pago
            caja -= pago
        cajas.append(caja)
        deudas.append(deuda)
    fin["caja"] = cajas
    fin["deuda"] = deudas
    num = [c for c in fin.columns if c not in ("mes", "personas")]
    fin[num] = fin[num].round(-3)
    return fin[fin["mes"] >= "2023-01"].reset_index(drop=True)


# ═════════════════════════════════════════════════════════════════════════════
# 9. PRECIOS DE LA COMPETENCIA (reales, observados)
# ═════════════════════════════════════════════════════════════════════════════
def gen_precios_competencia() -> pd.DataFrame:
    """Precios públicos vistos el 10-sep-2026. Donde la presentación no es la
    misma, se compara por litro y se dice."""
    f = [
        ("Aguardiente Mil Demonios 700 ml", 111_000, 99_300, "La Licorera", 100_990, 700, 700, "https://lalicorera.com/productos/aguardiente/mil-demonios"),
        ("Aguardiente Mil Demonios 700 ml", 111_000, 99_300, "Dislicores", 114_990, 700, 700, "https://www.dislicores.com/aguardiente-mil-demonios/p"),
        ("Whisky Old Parr 12 años 500 ml", 110_200, 104_400, "Dislicores", 105_990, 500, 500, "https://www.dislicores.com/old-parr"),
        ("Whisky Chivas Regal 12 años 1 L", 184_800, 155_600, "Éxito", 186_700, 1000, 1000, "https://www.exito.com/whisky-chivas-regal-12-a-os-x-1000-ml-327638/p"),
        ("Whisky Buchanan's 12 años (con estuche)", 165_000, 158_100, "La Licorera", 172_990, 950, 750, "https://lalicorera.com/productos/whisky/buchanans-12-anos"),
        ("Whisky Jack Daniel's Old No. 7 (por litro)", 183_300, 173_100, "Dislicores", 132_500, 1000, 700, "https://www.dislicores.com/jack-daniels"),
        ("Whisky The Glenlivet 12 años 700 ml", 146_850, 146_850, "Dislicores", 146_925, 700, 700, "https://www.dislicores.com/whisky-glenlivet-12-anos--ref304037/p"),
    ]
    df = pd.DataFrame(f, columns=["producto", "kyva_classic", "kyva_elite", "competidor",
                                  "precio_competidor", "ml_kyva", "ml_competidor", "fuente"])
    df["fecha_observacion"] = "2026-09-10"
    return df


# ═════════════════════════════════════════════════════════════════════════════
def main():
    print("\nGenerando datos del panel de KYVA…")
    print(f"  Simulación: {MESES_SIM[0]} → {MESES_SIM[-1]} · se guarda desde {MESES[0]} · "
          f"corte {CORTE:%d/%m/%Y}\n")

    cat = gen_catalogo()
    cli, ped = simular_clientes()
    lin = gen_lineas(ped, cli, cat)
    ped = entregas(ped)
    pedidos = armar_pedidos(cli, ped, lin, cat)
    lin["fecha"] = ped["fecha"].values[lin["pi"].values]
    lin["estado"] = pedidos["estado"].values[lin["pi"].values]
    clientes = resumir_clientes(cli, pedidos)
    miembros = gen_miembros(clientes)
    referidos = gen_referidos(clientes, pedidos)
    corp = gen_corporativo()
    cuentas, dist, inv = gen_distribucion(lin[lin["estado"] == "Entregado"], cat)
    mkt = gen_marketing()
    equipo = gen_equipo()
    fin = gen_finanzas(pedidos, corp, dist, mkt, equipo)

    # Rotación del surtido por mes (derivada de las líneas)
    lv = lin[lin["estado"] == "Entregado"].copy()
    lv["mes"] = pd.DatetimeIndex(lv["fecha"]).strftime("%Y-%m")
    sku_mes = (lv[lv["mes"] >= "2023-01"].groupby(["mes", "sku"])
               .agg(unidades=("unidades", "sum"), ingreso_neto=("ingreso_neto", "sum"),
                    costo=("costo", "sum"), descuento=("descuento", "sum")).reset_index())
    for c in ["ingreso_neto", "costo", "descuento"]:
        sku_mes[c] = sku_mes[c].round(-1)
    # Stock actual por referencia: cobertura objetivo sobre la venta de 90 días;
    # las que no rotan tienen stock igual.
    u90 = lv[lv["fecha"] > CORTE - pd.Timedelta(days=90)].groupby("sku")["unidades"].sum()
    cat["unidades_90d"] = cat["sku"].map(u90).fillna(0).astype(int)
    cat["stock_u"] = np.where(cat["unidades_90d"] > 0,
                              np.ceil(cat["unidades_90d"] / 90 * RNG.uniform(35, 75, len(cat))),
                              RNG.integers(3, 24, len(cat))).astype(int)
    cat.loc[cat["marca"] == "Mil Demonios", "stock_u"] = 0
    cat.loc[cat["nombre"] == "Aguardiente Mil Demonios 700 ml", "stock_u"] = ANCLAS["stock_mil_demonios_u"]
    cat = cat.drop(columns=["popularidad"])

    guardar = pedidos[pedidos["fecha"] >= INICIO].copy()
    guardar["fecha"] = guardar["fecha"].dt.strftime("%Y-%m-%d %H:%M")
    guardar["fecha_entrega"] = guardar["fecha_entrega"].dt.strftime("%Y-%m-%d %H:%M")

    _guardar(cat, "catalogo")
    _guardar(clientes, "clientes", comprimir=True)
    _guardar(guardar, "pedidos", comprimir=True)
    _guardar(sku_mes, "ventas_sku_mes", comprimir=True)
    _guardar(miembros, "miembros", comprimir=True)
    _guardar(referidos, "mi_circulo")
    _guardar(corp, "corporativo")
    _guardar(cuentas, "cuentas_distribucion")
    _guardar(dist, "distribucion")
    _guardar(inv, "inventario_exclusivas")
    _guardar(mkt[mkt["mes"] >= "2023-01"], "mercadeo")
    _guardar(fin, "finanzas")
    _guardar(gen_precios_competencia(), "precios_competencia")

    # ── VERIFICACIÓN contra las anclas ───────────────────────────────────────
    anual = fin.groupby(fin["mes"].str[:4])[["ingresos", "utilidad_operacional"]].sum()
    i23, i24, i25 = (anual.loc[a, "ingresos"] for a in ("2023", "2024", "2025"))
    c24, c25 = (i24 / i23 - 1) * 100, (i25 / i24 - 1) * 100
    mo25 = anual.loc["2025", "utilidad_operacional"] / i25 * 100
    ytd = fin[fin["mes"].between("2026-01", "2026-08")]["ingresos"].sum()
    ytd_a = fin[fin["mes"].between("2025-01", "2025-08")]["ingresos"].sum()
    dic = fin[fin["mes"] == "2025-12"]["ingresos"].sum() / i25 * 100
    refs_90 = int((cat["unidades_90d"] > 0).sum())
    ok90 = pedidos[(pedidos["estado"] == "Entregado") & (pedidos["fecha"] > CORTE - pd.Timedelta(days=365))]

    def fila(nombre, modelo, ancla, ok):
        print(f"  {'✓' if ok else '✗'} {nombre:<34} modelo {modelo:>14}   ancla {ancla}")

    print("\nVerificación contra anclas públicas:")
    fila("Crecimiento ingresos 2024", f"{c24:.1f}%", "120,03%", abs(c24 - 120.03) < 6)
    fila("Crecimiento ingresos 2025", f"{c25:.1f}%", "130,46%", abs(c25 - 130.46) < 6)
    fila("Margen operacional 2025", f"{mo25:.2f}%", "0,08%", abs(mo25 - .08) < .05)
    e24, e25 = anual.loc["2024", "utilidad_operacional"], anual.loc["2025", "utilidad_operacional"]
    ce = (e25 / e24 - 1) * 100 if e24 > 0 else float("nan")
    fila("Crecimiento utilidad operac. 2025", f"{ce:.1f}%", "135,71%", abs(ce - 135.71) < 8)
    fila("Personas en el equipo (ago-26)", f"{int(equipo.iloc[-1]['personas'])}", "13", int(equipo.iloc[-1]['personas']) == 13)
    fila("Referencias con venta en 90 días", f"{refs_90}", "más de 300", refs_90 >= 300)
    fila("Whiskies en catálogo", f"{int((cat['categoria'] == 'Whisky').sum())}", "85", (cat['categoria'] == 'Whisky').sum() == 85)
    fila("Stock Mil Demonios 700 ml", f"{int(inv['stock_final_u'].iloc[-1]):,}", "1.200", abs(inv['stock_final_u'].iloc[-1] - 1200) < 1)
    print("\nOrden de magnitud (sin ancla exacta):")
    print(f"  Ingresos 2023 / 2024 / 2025        ${i23/1e6:,.0f}M · ${i24/1e6:,.0f}M · ${i25/1e6:,.0f}M")
    print(f"  Ingresos ene–ago 2026              ${ytd/1e6:,.0f}M ({(ytd/ytd_a-1)*100:+.1f}% vs ene–ago 2025)")
    print(f"  Diciembre 2025 sobre el año        {dic:.1f}%")
    print(f"  Pedidos entregados (12 meses)      {len(ok90):,} · ticket bruto ${ok90['valor_bruto'].median():,.0f} (mediana)")
    print(f"  Mezcla 2025                        " + " · ".join(
        f"{k} {fin[fin['mes'].str[:4]=='2025'][c].sum()/i25*100:.0f}%"
        for k, c in [("Store", "ingreso_store"), ("Lounge", "ingreso_lounge"),
                     ("Corp", "ingreso_corporativo"), ("Dist", "ingreso_distribucion")]))
    mb = fin[fin["mes"].str[:4] == "2025"]
    print(f"  Margen bruto 2025                  {mb['margen_bruto'].sum()/mb['ingresos'].sum()*100:.1f}%")
    print(f"  Caja / deuda al corte              ${fin['caja'].iloc[-1]/1e6:,.0f}M · ${fin['deuda'].iloc[-1]/1e6:,.0f}M")
    print(f"  Miembros Elite / que compraron     {len(miembros):,} · {int(miembros['compro'].sum()):,}")
    print("\nListo.\n")


if __name__ == "__main__":
    main()
