"""El comité del lunes: se pasa lista antes de mirar un solo número nuevo.

Esta es la pantalla que decide si la herramienta sigue abierta en el tercer mes.
Un panel se mira; un comité se cumple. La diferencia está en el orden del día:

    «El comité del lunes siguiente abre con el cumplimiento de los compromisos
    anteriores, en rojo los vencidos. Ese bucle es lo que hace que un software
    de gerencia se use, porque se vuelve el sitio donde se pasa lista.»

Por eso lo primero que aparece —antes de las tarjetas, antes de cualquier
gráfico— son los compromisos vencidos con nombre propio y días de retraso. No
es un adorno de severidad: es la única forma conocida de que la lista de la
semana pasada no se evapore. Cuando lo vencido está arriba y con dueño, la
reunión empieza explicando; cuando está al final, la reunión empieza con una
diapositiva de ventas y nadie vuelve a hablar de lo de la semana pasada.

Tres reglas de negocio que la pantalla impone y que parecen detalles:

**1. Cerrar exige escribir qué pasó.** No hay casilla de «hecho». Un compromiso
se cierra con el resultado en texto, porque en enero la pregunta no va a ser si
se hizo: va a ser si sirvió bajarle el descuento a esa cuenta en julio.

**2. Cerrar tarde no es cumplir.** Un vencido que se cierra hoy queda como
«cerrado tarde», en ámbar. Si cerrarlo tarde contara igual que cumplir, el
indicador se limpia solo el lunes por la mañana y deja de medir nada.

**3. El orden del día se arma desde aquí, no en un Word.** Vencidos, luego lo
que espera decisión, luego los números. Quien arma la agenda decide de qué se
habla, y esa es exactamente la palanca que hace que el comité no se convierta
otra vez en un informe de ventas leído en voz alta.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import *
from utils import b2b, datos, estado, filtros, gerencia

# El panel entero está cortado al 31 de agosto. El comité tiene que usar ese
# mismo «hoy»: si midiera contra la fecha real del computador, los compromisos
# de septiembre se verían vencidos aquí y en curso en el resto del panel.
HOY = datos.CORTE.normalize()

VERDE = "#2f7a48"
AMBAR = "#B5762F"
ROJO = "#8B1E1E"

# Marca con la que se guarda el cierre de un compromiso que vive en el CSV.
# utils/estado solo puede cerrar lo que él mismo creó, y los 22 del histórico no
# están ahí. En vez de escribir sobre el CSV —que se regenera con los datos— se
# guarda un registro de cierre en el estado y la pantalla lo superpone. Lo que
# importa, el resultado escrito, queda persistido igual.
MARCA_CIERRE = "Cierre de "

# `MESES_ES` de formatters son abreviaturas para ejes de gráfico. Esta pantalla
# imprime un documento que se reparte en una sala: «se pactó el 28 de jul» se
# lee a medio terminar al lado del resto del texto.
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre")

# Los mismos cortes que usa p28, que es la dueña del fill rate, y utils/gerencia:
# `quiebres.csv` arranca en marzo de 2026 y una entrega a un bar lleva del orden
# de once referencias. El comité imprime la cifra de p28, no una propia: si allá
# se mueven, hay que moverlas aquí o las dos pantallas dejan de cuadrar.
QUIEBRES_DESDE = "2026-03"
LINEAS_POR_ENTREGA = 11


def _desfase() -> pd.Timedelta:
    """Corrimiento entre el reloj real y la fecha del panel.

    utils/estado sella con la hora de Colombia de verdad. Sin corregirlo, un
    compromiso creado durante la demostración nace venciendo dentro de un mes y
    no aparece nunca en «vence esta semana», que es justo lo que hay que
    enseñar. Se mueve lo que se crea en vivo, nunca las fechas del corte.
    """
    return HOY - pd.Timestamp(estado.ahora()[:10])


def _estado_real(cerrado, vence) -> str:
    """El estado se recalcula; no se le cree al que viene en el archivo.

    El histórico trae dos compromisos marcados «Cumplido» con fecha de cierre
    posterior al corte —se generaron sin mirar el calendario—. Mostrarlos como
    cumplidos pondría en pantalla un cierre del 21 de septiembre en un panel que
    dice 31 de agosto, y eso es lo primero que un gerente señala con el dedo.
    """
    if pd.notna(cerrado) and cerrado <= HOY:
        return "Cumplido"
    if pd.notna(vence) and vence < HOY:
        return "Vencido"
    return "En curso"


@st.cache_data(show_spinner=False)
def _cuentas_mapa() -> pd.DataFrame:
    return b2b.cuentas()[["nombre", "ciudad", "canal"]].drop_duplicates("nombre")


def _compromisos() -> pd.DataFrame:
    """El histórico del CSV más lo que se creó en vivo, en una sola lista.

    No se le pone columna `mes` a propósito: con el filtro de periodo en «Mes»
    desaparecerían justo los compromisos vencidos más viejos, que son los únicos
    que de verdad hay que mirar el lunes.
    """
    desf = _desfase()
    guardados = estado.compromisos()

    # Primero los cierres que se escribieron desde esta pantalla sobre el
    # histórico: se aplican encima, no se listan como compromisos aparte.
    cierres = {}
    for cid, c in guardados.items():
        org = str(c.get("origen", ""))
        if org.startswith(MARCA_CIERRE):
            cierres[org[len(MARCA_CIERRE):].strip()] = c

    base = gerencia.compromisos_base().copy()
    base["cerrado"] = pd.to_datetime(base["cerrado_el"], errors="coerce").dt.normalize()
    base["resultado"] = ""
    base["origen"] = "Comité"
    base["vivo"] = False
    for cid, c in cierres.items():
        m = base["id"] == cid
        if m.any():
            cer = pd.to_datetime(c.get("cerrado_el") or estado.ahora(),
                                 errors="coerce")
            base.loc[m, "cerrado"] = (cer.normalize() + desf) if pd.notna(cer) else HOY
            base.loc[m, "resultado"] = c.get("resultado", "")

    filas = []
    for cid, c in guardados.items():
        if str(c.get("origen", "")).startswith(MARCA_CIERRE):
            continue
        cerrado = pd.to_datetime(c.get("cerrado_el"), errors="coerce")
        filas.append({
            "id": cid,
            "compromiso": c.get("compromiso", ""),
            # utils/estado no guarda área: lo que sirve en el comité de un
            # compromiso nacido en vivo es de dónde salió, no a qué área toca.
            "area": c.get("origen", "Manual"),
            "dueno": c.get("dueno", ""),
            "creado": pd.to_datetime(c.get("creado"), errors="coerce") + desf,
            "vence": pd.to_datetime(c.get("vence"), errors="coerce") + desf,
            "cerrado": (cerrado.normalize() + desf) if pd.notna(cerrado) else pd.NaT,
            "resultado": c.get("resultado", ""),
            "valor": float(c.get("valor", 0) or 0),
            "cuenta": c.get("cuenta", ""),
            "origen": c.get("origen", "Manual"),
            "vivo": True,
        })

    vivos = pd.DataFrame(filas)
    cols = ["id", "compromiso", "area", "dueno", "creado", "vence", "cerrado",
            "resultado", "valor", "cuenta", "origen", "vivo"]
    c = pd.concat([base[cols], vivos[cols]], ignore_index=True) if len(vivos) else base[cols]

    c["estado_real"] = [_estado_real(a, b) for a, b in zip(c["cerrado"], c["vence"])]
    c["a_tiempo"] = (c["estado_real"] == "Cumplido") & (c["cerrado"] <= c["vence"])
    c["marca"] = np.where(c["estado_real"] != "Cumplido", c["estado_real"],
                          np.where(c["a_tiempo"], "A tiempo", "Cerrado tarde"))
    c["dias_retraso"] = (HOY - c["vence"]).dt.days
    c["dias_plazo"] = (c["vence"] - HOY).dt.days

    # El filtro de vendedor aquí significa el DUEÑO del compromiso, no el
    # vendedor de la cuenta: en el comité se le pasa lista a las personas.
    c = c.merge(_cuentas_mapa(), left_on="cuenta", right_on="nombre", how="left")
    c["vendedor"] = c["dueno"]
    return c.drop(columns=["nombre"])


def _fila_vencida(r) -> str:
    """Un vencido, con la cara visible: días, dueño y plata atada."""
    plata = (f'<div style="font-size:12px;font-weight:700;color:{ROJO};'
             f'white-space:nowrap">{cop(r["valor"], 0)}</div>') if r["valor"] > 0 else ""
    cuenta = r["cuenta"] if isinstance(r["cuenta"], str) and r["cuenta"] else "sin cuenta asociada"
    return f"""
    <div style="display:flex;align-items:center;gap:14px;padding:9px 0;
         border-top:1px solid #EFD9D9">
      <div style="min-width:74px;text-align:center;background:{ROJO};color:#fff;
           border-radius:4px;padding:4px 6px">
        <div style="font-size:17px;font-weight:800;line-height:1">{int(r['dias_retraso'])}</div>
        <div style="font-size:8.5px;font-weight:700;letter-spacing:.1em;
             text-transform:uppercase;opacity:.85">días tarde</div></div>
      <div style="flex:1">
        <div style="font-size:13.5px;font-weight:700;color:{TINTA};line-height:1.35">
          {r['compromiso']}</div>
        <div style="font-size:11px;color:{CLARO};margin-top:2px">
          {r['area']} &nbsp;·&nbsp; {cuenta}
          &nbsp;·&nbsp; se pactó el {r['creado'].day} de {MESES[r['creado'].month - 1]}</div>
      </div>
      <div style="text-align:right;white-space:nowrap">
        <div style="font-size:12.5px;font-weight:800;color:{TINTA}">{r['dueno']}</div>
        {plata}
      </div>
    </div>"""


def _cerrar(fila, resultado: str) -> None:
    """Deja el resultado escrito, venga el compromiso del histórico o de en vivo."""
    if fila["vivo"]:
        estado.cerrar_compromiso(fila["id"], resultado)
        return
    nid = estado.nuevo_compromiso(
        fila["compromiso"], fila["dueno"], dias=0, valor=float(fila["valor"]),
        origen=f"{MARCA_CIERRE}{fila['id']}")
    estado.cerrar_compromiso(nid, resultado)


def _ventana(meses) -> str:
    """«marzo a agosto de 2026», a partir de los meses que de verdad hay."""
    ms = sorted(str(m) for m in meses if str(m))
    if not ms:
        return "sin meses con registro"
    a, b = ms[0], ms[-1]
    fin = f"{MESES[int(b[5:7]) - 1]} de {b[:4]}"
    if a == b:
        return fin
    ini = MESES[int(a[5:7]) - 1]
    if a[:4] != b[:4]:
        ini = f"{ini} de {a[:4]}"
    return f"{ini} a {fin}"


def _cifras() -> dict:
    """Los números del periodo, con el filtro puesto y con la fórmula de su dueño.

    `gerencia.resumen_gerencia()` es el consolidado de toda la operación y no
    pasa por `filtros.aplicar`. Imprimirlo tal cual debajo de una lista de
    compromisos ya filtrada era el peor defecto de esta pantalla: el documento
    que salía de la sala mezclaba dos alcances en la misma hoja —los
    compromisos de Medellín encima de la cartera del país entero— y encima
    afirmaba que no lo hacía. Aquí cada cifra se recalcula con el filtro puesto
    y con la misma fórmula de la pantalla que la manda, para que el comité y el
    área discutan el mismo número:

      · cartera vencida, como p26: foto al corte, sin recortar por mes de
        emisión, porque una factura de abril que sigue abierta es el problema;
      · venta perdida y fill rate, como p28: el denominador son las líneas
        despachadas estimadas desde las entregas, nunca la tabla de quiebres;
      · plata en riesgo de vencerse, como p32: `en_riesgo`, que es la parte del
        lote que la demanda no alcanza a vender, no el valor del lote entero.

    Dos cifras no se pueden filtrar y se devuelven marcadas: el rebate se pacta
    por marca —no tiene ciudad ni vendedor— y el lote solo sabe de bodega.
    """
    f = filtros.aplicar(gerencia.facturas(), col_mes=None)
    ab = f[~f["pagada"]]
    venc = ab[ab["dias_vencida"] > 0]

    q = filtros.aplicar(gerencia.quiebres())
    q = q[q["mes"] >= QUIEBRES_DESDE]
    ve = filtros.aplicar(b2b.ventas())
    ve = ve[ve["mes"] >= QUIEBRES_DESDE]
    lineas = float(ve["entregas"].sum()) * LINEAS_POR_ENTREGA + len(q)

    lot = gerencia.lotes().copy()
    # Igual que en p32: el filtro global habla de ciudades y la tabla de lotes
    # habla de bodegas, que son la misma cosa.
    lot["ciudad"] = lot["bodega"]
    lot = filtros.aplicar(lot, col_mes=None)

    return {
        "vencida": float(venc["saldo"].sum()),
        "facturas_vencidas": int(len(venc)),
        "dias_prom": float(venc["dias_vencida"].mean()) if len(venc) else 0.0,
        "dias_max": int(venc["dias_vencida"].max()) if len(venc) else 0,
        "venta_perdida": float(q["valor_perdido"].sum()),
        "fill_rate": (1 - len(q) / lineas) * 100 if lineas else None,
        "ventana": _ventana(q["mes"].unique()),
        # Sin filtrar a propósito: `rebates.csv` no tiene ciudad, canal ni
        # vendedor. Va a la agenda dicho con todas las letras.
        "rebate_perdido": gerencia.resumen_gerencia()["rebate_perdido"],
        "en_riesgo": float(lot["en_riesgo"].sum()),
        "lotes_riesgo": int((lot["en_riesgo_u"] > 0).sum()),
    }


def _orden_del_dia(c: pd.DataFrame, dec: pd.DataFrame, res: dict) -> str:
    """La agenda en markdown, en el orden en que hay que hablar de las cosas.

    Vencidos primero. Es deliberado y es la mitad del valor de esta pantalla:
    una agenda que arranca con los números del mes hace que lo incumplido se
    discuta a las 8:55, con la gente ya parada.
    """
    venc = c[c["estado_real"] == "Vencido"].sort_values("dias_retraso", ascending=False)
    semana = c[(c["estado_real"] == "En curso") &
               (c["dias_plazo"].between(0, 7))].sort_values("vence")
    juz = c[c["estado_real"].isin(["Cumplido", "Vencido"])]
    cumplidos = int((juz["marca"] == "A tiempo").sum())
    cumpl_pct = cumplidos / max(len(juz), 1) * 100

    L = [f"# Comité KYVA — {datos.CORTE_TXT}",
         "",
         f"Alcance: {filtros.resumen()}. Preparado desde el panel, no a mano: "
         f"todo lo que sigue está calculado con ese mismo alcance y con la "
         f"fórmula de la pantalla que manda cada cifra, así que cuadra con lo "
         f"que ve cada área. Las dos excepciones van marcadas abajo.",
         "",
         f"## 1. Compromisos vencidos ({len(venc)}) — se pasa lista",
         ""]
    if venc.empty:
        L.append("_Ninguno. Es la primera vez; conviene decirlo en voz alta._")
    else:
        L.append("| Días | Dueño | Compromiso | Plata atada |")
        L.append("|---:|---|---|---:|")
        for _, r in venc.iterrows():
            L.append(f"| {int(r['dias_retraso'])} | {r['dueno']} | {r['compromiso']} "
                     f"| {cop(r['valor'], 0) if r['valor'] > 0 else '—'} |")
        L += ["", f"**{cop(float(venc['valor'].sum()), 0)}** dependen de esta lista. "
                  f"Cada uno se cierra con el resultado escrito o se vuelve a "
                  f"pactar con fecha nueva; dejarlo abierto sin decir nada no es "
                  f"una opción del comité."]

    L += ["", f"## 2. Decisiones que esperan ({len(dec)})", ""]
    if dec.empty:
        L.append("_Nada esperando decisión en esta vista._")
    for _, r in dec.iterrows():
        L += [f"**{r['titulo']}**",
              f"- Dato: {r['dato']}",
              f"- Opciones: {r['accion']}",
              f"- Si nadie hace nada: {r['si_nadie_hace_nada']}",
              f"- Decide: {r['decide']}", ""]

    # El denominador se dice siempre, y cuando es de uno o dos se dice que lo
    # es: «100% de cumplimiento» sobre un solo compromiso es una frase que en
    # un comité se repite en voz alta y no significa nada.
    aviso_n = (" — son muy pocos: el porcentaje se mueve entero con uno"
               if 0 < len(juz) <= 2 else "")
    fill_txt = pct(res["fill_rate"]) if res["fill_rate"] is not None else "—"
    # El atraso que se dice al lado de la cartera vencida es el de ESA cartera
    # —días vencidas de lo que sigue abierto—, no el `atraso_real` del resumen,
    # que es la media de las facturas YA PAGADAS. Los dos números quedaban
    # cerca por casualidad y la frase le atribuía a la cartera vencida un
    # indicador que no era suyo.
    cartera = (
        f"- **Cartera vencida:** {cop(res['vencida'], 0)} en "
        f"{res['facturas_vencidas']} facturas · {res['dias_prom']:.0f} días "
        f"vencidas en promedio, la más vieja {res['dias_max']}"
        if res["facturas_vencidas"] else
        "- **Cartera vencida:** ninguna factura vencida en esta vista")
    L += ["", "## 3. Los números del periodo", "",
          f"- **Cumplimiento de compromisos:** {pct(cumpl_pct)} "
          f"({cumplidos} a tiempo de {len(juz)} con plazo cumplido{aviso_n})",
          cartera,
          f"- **Venta perdida por quiebre ({res['ventana']}):** "
          f"{cop(res['venta_perdida'], 0)} · fill rate {fill_txt}",
          f"- **Rebate que se dejó ir:** {cop(res['rebate_perdido'], 0)} por "
          f"quedarse corto de tramo _(toda la operación: el rebate se pacta por "
          f"marca, no tiene ciudad ni vendedor)_",
          f"- **Plata en riesgo de vencerse:** {cop(res['en_riesgo'], 0)} en "
          f"{res['lotes_riesgo']} lotes _(por bodega: el lote no sabe de canal "
          f"ni de vendedor)_",
          ""]

    L += [f"## 4. Lo que vence esta semana ({len(semana)})", ""]
    if semana.empty:
        L.append("_Nada vence antes del próximo comité._")
    for _, r in semana.iterrows():
        L.append(f"- **{r['dueno']}** — {r['compromiso']} "
                 f"(vence el {r['vence'].day} de {MESES[r['vence'].month - 1]})")

    L += ["", "---",
          f"Generado por el panel KYVA · corte {datos.CORTE_TXT}. "
          f"El orden no es casual: primero lo que se debía y no se hizo."]
    return "\n".join(L)


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Comité del lunes",
        "Quién se comprometió a qué, qué se cumplió y qué lleva días vencido",
        "Se pasa lista"), unsafe_allow_html=True)
    filtros.encabezado_filtro()

    todos = _compromisos()
    c = filtros.aplicar(todos)

    venc = c[c["estado_real"] == "Vencido"].sort_values("dias_retraso", ascending=False)
    juz = c[c["estado_real"].isin(["Cumplido", "Vencido"])]
    a_tiempo = int((juz["marca"] == "A tiempo").sum())
    tarde = int((juz["marca"] == "Cerrado tarde").sum())
    cumpl_pct = a_tiempo / max(len(juz), 1) * 100
    semana = c[(c["estado_real"] == "En curso") &
               (c["dias_plazo"].between(0, 7))].sort_values("vence")

    # ── 1. Lo vencido, arriba de todo ───────────────────────────────────────
    if venc.empty:
        st.success("Ningún compromiso vencido. Con el filtro puesto no hay nada "
                   "que reclamar — conviene decirlo en voz alta, porque es lo "
                   "único que hace que la lista de la semana siguiente se tome "
                   "en serio.")
    else:
        filas = "".join(_fila_vencida(r) for _, r in venc.iterrows())
        st.markdown(f"""
        <div style="border:1px solid #E8B4B4;border-left:5px solid {ROJO};
             background:#FBF0F0;border-radius:6px;padding:15px 20px 8px">
          <div style="display:flex;justify-content:space-between;align-items:baseline">
            <div style="font-size:10px;font-weight:800;letter-spacing:.16em;
                 text-transform:uppercase;color:{ROJO};font-family:Montserrat,sans-serif">
              Se pasa lista · {len(venc)} compromisos vencidos sin cerrar</div>
            <div style="font-size:11.5px;color:{ROJO};font-weight:700">
              {cop(float(venc['valor'].sum()), 0)} atados a esta lista</div>
          </div>
          {filas}
        </div>""", unsafe_allow_html=True)
        st.caption(
            f"Ordenados por días de retraso, no por plata. El de arriba lleva "
            f"**{int(venc.iloc[0]['dias_retraso'])} días** y es de "
            f"**{venc.iloc[0]['dueno']}**: cuanto más viejo, menos probable es "
            f"que se haya vuelto a mirar y más barato es cerrarlo mal.")

    # El filtro de vendedor de la barra lateral se arma con `cuentas.csv` y aquí
    # muerde sobre el DUEÑO del compromiso. Hay dueños que no son vendedores de
    # cuenta —compras, calidad— y por eso no se pueden elegir en el selector:
    # sin este aviso sus compromisos desaparecen en silencio en cuanto alguien
    # toca el filtro, y son justamente a los que hay que pasarles lista. Una
    # lista de la que faltan nombres sin decirlo es peor que no tener filtro.
    fuera = sorted(set(todos["dueno"].dropna().astype(str)) -
                   set(c["dueno"].dropna().astype(str)))
    if filtros.activo() and fuera:
        om = todos[todos["dueno"].astype(str).isin(fuera)]
        om_venc = int((om["estado_real"] == "Vencido").sum())
        aviso = (f"⚠ Este filtro deja fuera **{len(om)} compromisos** "
                 f"({om_venc} vencidos, {cop(float(om['valor'].sum()), 0)} "
                 f"atados) de {', '.join(fuera)}.")
        # Y de esos, los que además no se pueden aislar con el filtro, porque
        # el selector no los ofrece.
        sin_opcion = [d for d in fuera
                      if d not in set(b2b.cuentas()["vendedor"].dropna().astype(str))]
        if sin_opcion:
            uno = len(sin_opcion) == 1
            aviso += (f" A {' y '.join(sin_opcion)} no se "
                      f"{'le' if uno else 'les'} puede pasar lista por separado: "
                      f"el selector de vendedor se arma con los vendedores de "
                      f"cuenta y ahí no {'aparece' if uno else 'aparecen'}, así "
                      f"que la única forma de ver{'lo' if uno else 'los'} es "
                      f"quitar el filtro.")
        st.caption(aviso)

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── Las cuatro cifras del comité ────────────────────────────────────────
    plata_venc = float(venc["valor"].sum())
    k = st.columns(4, gap="small")
    k[0].markdown(kpi(
        "Vencidos sin cerrar", num(len(venc)),
        f"de {len(juz)} con el plazo ya cumplido", len(venc) == 0, "🔴",
        "Lo que alguien dijo que haría, con fecha, y la fecha pasó."),
        unsafe_allow_html=True)
    k[1].markdown(kpi(
        "Cumplimiento del periodo", pct(cumpl_pct),
        # El denominador va en la tarjeta, no solo en la de al lado: un 100% de
        # uno sobre uno —pasa con el filtro puesto en una persona— y un 100% de
        # doce se leen igual si nadie dice cuántos son. Y «cerrados tarde» solo
        # se nombra cuando hay alguno: un cero mudo en la tarjeta que abre el
        # comité gasta una línea para no decir nada.
        f"{a_tiempo} a tiempo de {len(juz)}" +
        (f" · {tarde} cerrado{'s' if tarde > 1 else ''} tarde" if tarde else ""),
        cumpl_pct >= 70, "✓",
        "Cerrados dentro del plazo sobre los que ya se vencieron.",
        "El porcentaje es sobre muy pocos compromisos"
        if 0 < len(juz) <= 2 else "Un comité que funciona no baja del 70%"),
        unsafe_allow_html=True)
    k[2].markdown(kpi(
        "Plata comprometida vencida", cop(plata_venc, 0),
        "esperando a que alguien la ejecute" if plata_venc > 0
        else "ningún vencido tiene plata atada", plata_venc == 0, "💰",
        "Cartera por cobrar, descuentos por renegociar y cuotas por cerrar que "
        "ya tenían dueño y fecha."), unsafe_allow_html=True)
    # Un cero aquí NO es una buena noticia y pintarlo en verde era el semáforo
    # al revés: significa que la reunión anterior terminó sin que nadie se
    # comprometiera a nada antes del próximo comité, que es el peor resultado
    # posible de un comité. Lo sano es tener cosas en vuelo.
    k[3].markdown(kpi(
        "Vencen esta semana", num(len(semana)),
        "todavía se pueden cumplir" if not semana.empty
        else "nadie pactó nada para esta semana", not semana.empty, "📅",
        "Compromisos con fecha antes del próximo comité. Si se miran hoy "
        "todavía se pueden cumplir; el lunes ya no."), unsafe_allow_html=True)

    st.markdown(espacio(18), unsafe_allow_html=True)

    # ── 2. Quién cumple y quién no ──────────────────────────────────────────
    st.markdown('<div class="ky-sub">Quién cumple y quién no</div>',
                unsafe_allow_html=True)
    if juz.empty:
        st.info("Todavía no hay compromisos con el plazo cumplido en esta vista.")
    else:
        g = juz.pivot_table(index="dueno", columns="marca", values="id",
                            aggfunc="count", fill_value=0)
        for col in ("A tiempo", "Cerrado tarde", "Vencido"):
            if col not in g.columns:
                g[col] = 0
        g["total"] = g[["A tiempo", "Cerrado tarde", "Vencido"]].sum(axis=1)
        g["pct"] = g["A tiempo"] / g["total"] * 100
        g = g.sort_values(["pct", "total"])

        fig = go.Figure()
        for col, color in (("A tiempo", VERDE), ("Cerrado tarde", AMBAR),
                           ("Vencido", ROJO)):
            # Una serie que no tiene ninguna barra no dibuja nada y sí gasta una
            # entrada de leyenda. «Cerrado tarde» está en cero hasta que alguien
            # cierre un vencido —en vivo, durante la demostración— y hasta
            # entonces la leyenda prometía un color que no aparece por ninguna
            # parte. El concepto se sigue explicando en el texto de abajo.
            if int(g[col].sum()) == 0:
                continue
            fig.add_trace(go.Bar(
                y=g.index, x=g[col], orientation="h", name=col,
                marker_color=color,
                hovertemplate="%{y} · " + col + ": %{x:.0f}<extra></extra>"))
        fig.update_layout(barmode="stack")
        fig.update_xaxes(title="Compromisos con el plazo ya cumplido", dtick=1)
        for dueno, fila in g.iterrows():
            fig.add_annotation(
                x=fila["total"] + .12, y=dueno, text=f"<b>{fila['pct']:.0f}%</b>",
                showarrow=False, xanchor="left",
                font=dict(size=11, color=VERDE if fila["pct"] >= 70 else ROJO))
        f = light(fig, 60 + 34 * len(g))
        f.update_layout(hovermode="closest")
        st.plotly_chart(f, width="stretch", theme=None, config=PLOTLY_CONFIG)

        # La comparación dice los dos denominadores en vez de afirmar que son
        # parecidos sin haberlo comprobado: con un filtro puesto pueden ser uno
        # contra cuatro, y entonces la frase compara un porcentaje con una
        # anécdota.
        peor, mejor = g.index[0], g.index[-1]
        comparacion = (
            f"**{mejor}** va en {pct(g.loc[mejor, 'pct'])} sobre "
            f"{int(g.loc[mejor, 'total'])} compromisos y **{peor}** en "
            f"{pct(g.loc[peor, 'pct'])} sobre {int(g.loc[peor, 'total'])}."
            if peor != mejor else
            f"**{mejor}** va en {pct(g.loc[mejor, 'pct'])} sobre "
            f"{int(g.loc[mejor, 'total'])} compromisos con el plazo cumplido.")
        if int(g["total"].min()) <= 2:
            comparacion += (" Hay personas con uno o dos compromisos juzgados: "
                            "ahí el porcentaje no distingue a quien cumple de "
                            "quien tuvo suerte.")
        st.caption(
            f"El porcentaje es lo cerrado **dentro del plazo**. Cerrar tarde se "
            f"cuenta aparte —en ámbar, en cuanto haya alguno— a propósito: si "
            f"contara como cumplir, el indicador se limpia solo el lunes por la "
            f"mañana. " + comparacion)

        st.markdown(espacio(14), unsafe_allow_html=True)
        st.markdown('<div class="ky-sub">Por área</div>', unsafe_allow_html=True)
        ar = juz.groupby("area").agg(
            total=("id", "size"),
            a_tiempo=("marca", lambda s: int((s == "A tiempo").sum())),
            vencidos=("marca", lambda s: int((s == "Vencido").sum())),
            plata=("valor", "sum")).reset_index()
        ar["cumple"] = ar["a_tiempo"] / ar["total"] * 100
        ar = ar.sort_values("cumple")
        t = pd.DataFrame({
            "Área": ar["area"],
            "Compromisos": ar["total"],
            "A tiempo": ar["a_tiempo"],
            "Vencidos": ar["vencidos"],
            "Cumplimiento": ar["cumple"].map(lambda v: pct(v, 0)),
            "Plata atada": ar["plata"].map(lambda v: cop(v, 0)),
        })
        st.dataframe(t, hide_index=True, width="stretch")

        # El texto no reparte áreas a mano —«cartera depende de un tercero,
        # logística se ejecuta en casa»— porque con un filtro puesto nombraba
        # áreas que ni siquiera están en la tabla, y si el área más floja
        # resultaba ser la que ponía de contraejemplo, el párrafo se
        # contradecía solo. El criterio se dice sin nombres: es igual de útil y
        # es cierto en las seis combinaciones de filtro.
        floja = ar.iloc[0]
        st.markdown(panel(
            "Lo que dice el reparto por área",
            f"<b>{floja['area']}</b> cierra a tiempo {pct(floja['cumple'], 0)} de "
            f"lo que se compromete, sobre {int(floja['total'])} compromisos con "
            f"el plazo ya cumplido. Antes de sacar conclusiones sobre la persona "
            f"hay que mirar el tipo de compromiso: los que dependen de que "
            f"conteste un tercero —un cliente que paga, un proveedor que "
            f"responde— no se cumplen al mismo ritmo que los que se ejecutan "
            f"dentro de la casa. <b>Un área que nunca cumple no siempre tiene un "
            f"problema de disciplina; a veces tiene un problema de plazos que se "
            f"pactan sin preguntarle.</b> El comité que sirve es el que cambia "
            f"el plazo, no el que repite el reclamo.",
            "📐", "azul"), unsafe_allow_html=True)

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── 3. Lo que vence esta semana ─────────────────────────────────────────
    st.markdown('<div class="ky-sub">Vence antes del próximo comité</div>',
                unsafe_allow_html=True)
    if semana.empty:
        st.caption("Nada vence en los próximos siete días.")
    else:
        t = pd.DataFrame({
            "Vence": semana["vence"].dt.strftime("%d/%m"),
            "Faltan": semana["dias_plazo"].map(lambda d: f"{int(d)} días"),
            "Compromiso": semana["compromiso"],
            "Dueño": semana["dueno"],
            "Área": semana["area"],
            "Plata atada": semana["valor"].map(lambda v: cop(v, 0) if v > 0 else "—"),
        })
        st.dataframe(t, hide_index=True, width="stretch")
        st.caption("Esta es la lista que vale la pena leer en voz alta al final "
                   "de la reunión: son los que todavía se pueden cumplir.")

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── 4. Cerrar un compromiso, diciendo qué pasó ──────────────────────────
    st.markdown('<div class="ky-sub">Cerrar un compromiso</div>',
                unsafe_allow_html=True)
    # Los vencidos primero en el selector: son los que hay que cerrar hoy.
    abiertos = c[c["estado_real"] != "Cumplido"].sort_values(
        ["estado_real", "vence"], ascending=[False, True])
    if abiertos.empty:
        st.success("No queda nada abierto en esta vista.")
    else:
        etiquetas = [
            f"{'⚠ ' if r['estado_real'] == 'Vencido' else ''}{r['id']} · "
            f"{r['compromiso'][:72]} — {r['dueno']}"
            for _, r in abiertos.iterrows()]
        # `clear_on_submit` borraba el campo ANTES de que corriera la validación
        # de abajo: quien escribía un resultado de doce caracteres recibía «falta
        # el resultado» con el texto ya perdido y tenía que reescribirlo entero,
        # que en una demostración en vivo es justo donde se traba el que presenta.
        # Se limpia a mano y solo cuando el cierre se guardó de verdad; la bandera
        # se consume antes de crear el widget porque después Streamlit no deja
        # tocarle el estado.
        if st.session_state.pop("cm_limpiar_cierre", False):
            st.session_state["cm_resultado"] = ""
        with st.form("cerrar_compromiso", clear_on_submit=False):
            elegido = st.selectbox("Compromiso", etiquetas, key="cm_cerrar")
            resultado = st.text_area(
                "Qué pasó", height=90, key="cm_resultado",
                placeholder="Se bajó el descuento de 16% a 12%; aceptaron a cambio "
                            "de entrega quincenal. Efecto esperado: +1,4 M al mes.")
            enviado = st.form_submit_button("Cerrar con resultado", type="primary")
        if enviado:
            fila = abiertos.iloc[etiquetas.index(elegido)]
            if len(resultado.strip()) < 15:
                st.warning("Falta el resultado. «Listo» o «hecho» no sirve dentro "
                           "de tres meses, que es cuando alguien va a preguntar "
                           "si la decisión funcionó.")
            else:
                _cerrar(fila, resultado.strip())
                st.session_state["cm_limpiar_cierre"] = True
                # Toast y no st.success: el st.rerun() que refresca la lista de
                # arriba se lleva por delante cualquier mensaje de la página.
                st.toast(f"{fila['id']} cerrado con resultado.")
                st.rerun()

    st.markdown(panel(
        "Por qué no hay una casilla de «hecho»",
        "Marcar una casilla convierte esto en una lista de tareas, y una lista de "
        "tareas no le sirve a una gerencia: dice que algo se hizo, nunca si valió "
        "la pena. Exigir el resultado escrito cambia dos cosas. "
        "<b>Primero, en tres meses se puede mirar hacia atrás</b> y contestar si "
        "bajarle el descuento a esa cuenta la volvió rentable o solo la hizo "
        "comprar menos — con el número al lado de la decisión, no de memoria. "
        "<b>Segundo, obliga a que el compromiso sea concreto.</b> Nadie puede "
        "escribir el resultado de «mejorar la relación con el cliente», y eso se "
        "descubre al cerrarlo, no al pactarlo. "
        "Cerrar tarde queda registrado como tarde: el cumplimiento que se ve "
        "arriba no se puede limpiar cerrando el lunes por la mañana lo que "
        "venció hace tres semanas.",
        "✍️", "azul"), unsafe_allow_html=True)

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── 5. Pactar uno nuevo ─────────────────────────────────────────────────
    st.markdown('<div class="ky-sub">Pactar un compromiso nuevo</div>',
                unsafe_allow_html=True)
    # La lista de personas sale de TODOS los compromisos, no de los filtrados:
    # con un filtro de ciudad puesto no se puede dejar de asignarle a alguien.
    personas = sorted({str(d) for d in todos["dueno"].dropna() if str(d).strip()})
    # Mismo motivo que arriba: el texto sobrevive a la validación y se limpia
    # solo cuando el compromiso quedó anotado.
    if st.session_state.pop("cm_limpiar_nuevo", False):
        st.session_state["cm_texto"] = ""
        st.session_state["cm_valor"] = 0
    with st.form("nuevo_compromiso", clear_on_submit=False):
        f1 = st.columns([3, 1.3], gap="small")
        texto = f1[0].text_input(
            # El ejemplo no puede contradecir lo que se ve en la misma pantalla:
            # Envy Rooftop tiene 34,9% de descuento en `cuentas.csv` y su
            # renegociación ya está arriba, en rojo, como CM-021.
            "Compromiso", key="cm_texto",
            placeholder="Cobrar la factura vencida de Villanos en Bermudas antes del viernes")
        dueno = f1[1].selectbox("Dueño", personas, key="cm_dueno")
        f2 = st.columns([1.3, 1.3, 2], gap="small")
        fecha = f2[0].date_input("Vence", value=(HOY + pd.Timedelta(days=7)).date(),
                                 min_value=(HOY + pd.Timedelta(days=1)).date(),
                                 key="cm_fecha", format="DD/MM/YYYY")
        valor = f2[1].number_input("Plata en juego (COP)", min_value=0,
                                   step=500_000, value=0, key="cm_valor")
        nuevo = st.form_submit_button("Anotar el compromiso", type="primary")
    if nuevo:
        if len(texto.strip()) < 12:
            st.warning("El compromiso tiene que decir qué se hace y sobre qué. "
                       "«Revisar cuentas» no se puede cerrar ni se puede medir.")
        else:
            # `dias` y no una fecha: utils/estado calcula el vencimiento sobre el
            # reloj real y esta pantalla lo devuelve a la fecha del panel con el
            # mismo desfase con que lee todo lo demás.
            dias = max((fecha - HOY.date()).days, 1)
            estado.nuevo_compromiso(texto.strip(), dueno, dias=dias,
                                    valor=float(valor), origen="Comité")
            st.session_state["cm_limpiar_nuevo"] = True
            st.toast(f"Anotado para {dueno}: vence en {dias} días y sobrevive al "
                     f"cierre del navegador.")
            st.rerun()

    st.caption("Lo que se pacta aquí sobrevive al refresco y al cierre del "
               "navegador: se guarda fuera de la sesión, igual que lo que se "
               "decide en el Centro de decisiones. Un compromiso que no cuelga "
               "de una cuenta no tiene ciudad ni canal, así que con un filtro de "
               "ciudad puesto no aparece en esta vista.")

    st.markdown(espacio(16), unsafe_allow_html=True)

    # ── 6. El orden del día ─────────────────────────────────────────────────
    st.markdown('<div class="ky-sub">El orden del día del lunes</div>',
                unsafe_allow_html=True)
    dec = filtros.aplicar(b2b.decisiones())
    agenda = _orden_del_dia(c, dec, _cifras())

    d1, d2 = st.columns([1.4, 3], gap="small")
    d1.download_button("⬇️  Descargar el orden del día", agenda,
                       file_name=f"kyva_comite_{HOY:%Y%m%d}.md",
                       mime="text/markdown", width="stretch", type="primary")
    d2.markdown(
        f'<div style="padding-top:7px;font-size:12px;color:{CLARO}">'
        f'{len(venc)} vencidos · {len(dec)} decisiones esperando · '
        f'{len(semana)} vencen esta semana · alcance: {filtros.resumen().lower()}</div>',
        unsafe_allow_html=True)

    with st.expander("Ver el orden del día"):
        st.markdown(agenda)

    st.markdown(panel(
        "Por qué el orden del día sale de aquí y no de un Word",
        "Quien arma la agenda decide de qué se habla. Cuando la escribe alguien a "
        "mano el domingo, empieza por los números de venta —que son los que están "
        "a la mano— y lo incumplido se discute a las 8:55 con la gente ya parada. "
        "Armada desde el panel, el comité <b>abre reclamando lo de la semana "
        "pasada y cierra pactando lo de la siguiente</b>, y ese bucle es todo el "
        "invento: la herramienta deja de ser una pantalla que se mira y se vuelve "
        "el sitio donde se pasa lista. "
        "Es también la razón por la que esta pantalla se usa en el tercer mes, "
        "cuando la novedad de los gráficos ya pasó.",
        "📋", "azul"), unsafe_allow_html=True)
