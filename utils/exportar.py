"""Exportar: el libro de gerencia en Excel, listo para la junta.

Un director de operaciones no vive en el panel. Vive en el correo y en Loggro,
y cuando tiene junta el martes necesita **llevarse los números**, no un enlace.
Un panel del que no se puede sacar nada obliga a rehacer las tablas a mano en
Excel, y ahí es donde muere: no porque sea feo, sino porque no sirve para el
siguiente paso del trabajo.

Dos decisiones que importan:

  · **`XlsxWriter`, no `weasyprint` ni nada que pida librerías del sistema.**
    Es Python puro, se instala con pip y no necesita `packages.txt`. En
    Streamlit Cloud eso es la diferencia entre que despliegue y que no.
  · **El archivo se genera al pulsar, no al cargar la pantalla.**
    `st.download_button` acepta un invocable en `data`: sin eso, cada vez que
    alguien abre el módulo se arman veinte hojas de Excel que nadie pidió.

Y el libro no es un volcado: cada hoja lleva encabezado congelado, filtro
automático, formatos de moneda y porcentaje, y escala de color donde ayuda.
Un volcado de CSV lo hace cualquiera; lo que convence en una junta es abrir el
archivo y que ya esté ordenado.
"""
import io
from datetime import datetime, timedelta, timezone

import pandas as pd

COLOMBIA = timezone(timedelta(hours=-5))

# Ancho y formato por nombre de columna. Se declara una vez para que las veinte
# hojas salgan iguales; sin esto cada hoja hereda el ancho por defecto y las
# cifras aparecen como «#######».
FORMATOS = {
    "moneda": {"num_format": '"$"#,##0', "align": "right"},
    "moneda_m": {"num_format": '"$"#,##0.0,, "M"', "align": "right"},
    "pct": {"num_format": "0.0%", "align": "right"},
    "entero": {"num_format": "#,##0", "align": "right"},
    "fecha": {"num_format": "dd/mm/yyyy", "align": "center"},
}

# Qué formato lleva cada columna, por lo que dice su nombre. Es heurístico a
# propósito: mantener un mapa columna por columna de veinte hojas se
# desactualiza en la primera semana.
def _formato_de(col: str) -> str:
    c = str(col).lower()
    if any(k in c for k in ("%", "pct", "porcentaje", "cumplimiento", "margen %")):
        return "pct"
    if any(k in c for k in ("valor", "venta", "neto", "bruto", "costo", "saldo",
                            "margen", "precio", "comisión", "comision", "rebate",
                            "cupo", "inversión", "presupuesto", "plata")):
        return "moneda"
    if any(k in c for k in ("fecha", "vence", "emitida", "alta", "creado")):
        return "fecha"
    if any(k in c for k in ("unidades", "cuentas", "entregas", "facturas",
                            "referencias", "días", "dias")):
        return "entero"
    return ""


def libro(hojas: dict, titulo: str = "KYVA · Libro de gerencia") -> bytes:
    """Arma el .xlsx. `hojas` es {nombre: DataFrame}.

    Devuelve bytes para pasárselos a `st.download_button`. Se llama como
    invocable —`data=lambda: libro(...)`— para que el trabajo ocurra al pulsar.
    """
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as xw:
        wb = xw.book
        f_cab = wb.add_format({
            "bold": True, "font_size": 9, "font_color": "#FFFFFF",
            "bg_color": "#0E113A", "align": "left", "valign": "vcenter",
            "border": 0, "text_wrap": True})
        f_tit = wb.add_format({"bold": True, "font_size": 13,
                               "font_color": "#0E113A"})
        f_sub = wb.add_format({"font_size": 9, "font_color": "#9193A1"})
        fmts = {k: wb.add_format(v) for k, v in FORMATOS.items()}

        # Portada: de dónde salen los números y con qué corte. Sin esto, a la
        # semana nadie recuerda si el archivo era de agosto o de septiembre, y
        # un número sin fecha en una junta no se puede defender.
        port = wb.add_worksheet("Portada")
        port.hide_gridlines(2)
        port.set_column("A:A", 3)
        port.set_column("B:B", 78)
        port.write("B2", titulo, f_tit)
        port.write("B4", f"Generado el {datetime.now(COLOMBIA):%d de %B de %Y, %H:%M} "
                         f"(hora de Colombia)", f_sub)
        port.write("B5", "Corte de los datos: 31 de agosto de 2026", f_sub)
        port.write("B6", "Panel construido por Calybrat · datos simulados "
                         "anclados a cifras públicas", f_sub)
        port.write("B8", "Hojas de este libro:", f_cab)
        for i, nombre in enumerate(hojas, start=9):
            port.write(f"B{i}", f"   {nombre}")

        for nombre, df in hojas.items():
            if df is None or len(df) == 0:
                continue
            hoja = nombre[:31]
            df.to_excel(xw, sheet_name=hoja, index=False, startrow=1, header=False)
            ws = xw.sheets[hoja]
            for j, col in enumerate(df.columns):
                ws.write(0, j, str(col), f_cab)
                f = _formato_de(col)
                # El ancho sale del contenido real, no de un número fijo: una
                # columna de nombres de bar necesita el doble que una de días.
                largo = max([len(str(col))] +
                            [len(str(v)) for v in df[col].head(200)])
                ws.set_column(j, j, min(max(largo + 3, 10), 42),
                              fmts.get(f) if f else None)
            ws.freeze_panes(1, 1)
            ws.autofilter(0, 0, len(df), len(df.columns) - 1)
            ws.set_row(0, 30)
    return buf.getvalue()


def hojas_de_gerencia() -> dict:
    """El libro que se lleva a la junta del martes.

    No es todo lo que hay: es lo que se defiende en una reunión. Un archivo con
    treinta hojas no se abre; uno con siete, sí.
    """
    from utils import b2b, gerencia

    r = b2b.rentabilidad()
    f = gerencia.facturas()
    ab = f[~f["pagada"]]

    cuentas = r[["nombre", "canal", "ciudad", "zona", "vendedor", "neto",
                 "margen", "logistica", "servido", "servido_pct", "entregas",
                 "descuento_pct", "plazo_pago", "salud"]].copy()
    cuentas.columns = ["Cuenta", "Canal", "Ciudad", "Zona", "Vendedor",
                       "Venta neta", "Margen bruto", "Costo de servir",
                       "Margen servido", "Margen servido %", "Entregas",
                       "Descuento %", "Plazo de pago", "Estado"]
    cuentas["Margen servido %"] = cuentas["Margen servido %"] / 100
    cuentas["Descuento %"] = cuentas["Descuento %"] / 100

    cartera = ab[["factura", "nombre", "canal", "ciudad", "vendedor", "emitida",
                  "vence", "saldo", "dias_vencida", "tramo"]].copy()
    cartera.columns = ["Factura", "Cuenta", "Canal", "Ciudad", "Vendedor",
                       "Emitida", "Vence", "Saldo", "Días vencida", "Tramo"]

    reb = gerencia.rebates()
    marcas = reb[["trimestre", "marca", "cuota", "unidades", "cumplimiento",
                  "tasa_rebate", "rebate", "faltan_para_siguiente"]].copy()
    marcas.columns = ["Trimestre", "Marca", "Cuota", "Vendidas", "Cumplimiento %",
                      "Tasa de rebate", "Rebate", "Faltaron para el tramo"]
    marcas["Cumplimiento %"] = marcas["Cumplimiento %"] / 100

    return {
        "Cuentas": cuentas.sort_values("Margen servido"),
        "Cartera abierta": cartera.sort_values("Días vencida", ascending=False),
        "Marcas y rebate": marcas,
        "Presupuesto": gerencia.presupuesto(),
        "Compromisos": gerencia.compromisos_base(),
        "Quiebres": gerencia.quiebres(),
        "Lotes por vencer": gerencia.lotes()[
            gerencia.lotes()["estado"].isin(["Vencido", "Crítico", "Vigilar"])],
    }


def boton(st, etiqueta="Descargar el libro de gerencia (.xlsx)",
          hojas=None, clave="dl_libro"):
    """El botón. `data` recibe un invocable: el Excel se arma al pulsar.

    Sin esto, abrir el módulo montaría siete hojas de Excel cada vez, y con
    ochenta mil pedidos eso se siente.
    """
    def armar():
        return libro(hojas if hojas is not None else hojas_de_gerencia())

    return st.download_button(
        etiqueta, data=armar,
        file_name=f"kyva_gerencia_{datetime.now(COLOMBIA):%Y%m%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=clave, width="stretch", on_click="ignore")
