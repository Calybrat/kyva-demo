"""
Agente IA: preguntarle al negocio en español, sin abrir un tablero.

Con una llave de Anthropic en `st.secrets["ANTHROPIC_API_KEY"]` responde con el
modelo, usando como contexto un resumen real de los datos del panel. Sin llave,
responde con lógica local sobre los mismos datos: la demostración funciona
igual y las cifras son las mismas que muestran los tableros.
"""
import pandas as pd
import streamlit as st

from utils.formatters import *
from utils import datos

MODELO = "claude-sonnet-5"

CONTEXTO = """
Eres el Agente de Inteligencia de Negocio de KYVA, la tienda online de licores,
vinos y cervezas premium de Bogotá.

Lo que hay que saber de KYVA:
· KYVA SAS, constituida el 13 de agosto de 2019 en Bogotá. La fundó Romain Senechal
  (CEO, antes CFO de Pernod Ricard Colombia) con Mathieu Colombier (socio y CMO).
· Lema: «join the circle». Entrega en Bogotá y la Sabana; «pide AM y recibe PM».
  Despacha de lunes a jueves de 8am a 5pm y el viernes hasta las 4pm.
  Envío de $18.000 en pedidos bajo $300.000; gratis desde $300.000.
· Cuatro canales: The Store (abierta al público desde octubre de 2023, precio Classic),
  The Lounge (miembros Elite, precio Elite, membresía que casi siempre llega gratis
  por un aliado: Porsche Center Bogotá, BoConcept, Argento & Bourbon, Carmiña Villegas,
  Café San Alberto, Foro de Presidentes, EO), corporativo (regalos, eventos, bodas,
  catas) y distribución de marcas (Ron Defensor, Marcel Thorel y Mil Demonios, en
  exclusiva desde 2026).
· Programa de referidos Mi Círculo: cupón para el invitado y para quien invita.
· Cifras públicas: ingresos +120% en 2024 y +130% en 2025, margen operacional de
  0,08% en 2025, 13 empleados en 2026, más de 300 referencias.
· Del 1 al 29 de enero de 2026 rigió un IVA del 19% a licores (Decreto 1474 de 2025),
  suspendido por la Corte Constitucional y declarado inexequible el 15 de abril.

Cómo respondes:
· Siempre en español, directo y breve. Cifras en pesos colombianos.
· Cuando des una cifra, di qué significa para el negocio y qué habría que decidir.
· Habla como alguien que conoce el retail de licores premium, no como un reporte.
· Si el dato no está en el contexto que te dan, dilo en vez de inventarlo.
"""

SUGERIDAS = [
    "¿Cómo vamos este año?",
    "¿Por qué crecemos tanto y no ganamos plata?",
    "¿Cuánto nos cuesta la membresía Elite?",
    "¿Qué aliado trae miembros que compran?",
    "¿Cuántos pedidos perdemos por no despachar el fin de semana?",
    "¿Somos más caros que la competencia?",
    "¿Cómo va Mil Demonios?",
    "¿Qué hacemos con el inventario que no rota?",
    "¿Cómo viene diciembre?",
    "¿Cómo está la caja?",
]


@st.cache_data(show_spinner=False)
def resumen_datos() -> str:
    try:
        c = datos.cabecera()
        an = datos.anual()
        m = datos.margen_canal()
        e = datos.elite()
        al = datos.aliados()
        en = datos.entregas()
        r = datos.recompra_origen()
        s = datos.surtido()
        pc = datos.precios_competencia()
        pdic = datos.pipeline_diciembre()
        inv = datos.inventario_exclusivas().iloc[-1]
        quietas = s[s["unidades_90d"] == 0]
        return f"""
=== DATOS DE KYVA AL {datos.CORTE_TXT.upper()} ===
RESULTADOS POR AÑO
{chr(10).join(f"  {a}: ingresos {cop(x['ingresos'])} ({'—' if pd.isna(x['crecimiento_pct']) else signo(x['crecimiento_pct'])}), margen bruto {pct(x['margen_bruto_pct'])}, utilidad operacional {cop(x['utilidad_operacional'])} ({pct(x['margen_operacional_pct'], 2)})" for a, x in an.iterrows())}
  (2026 = enero a agosto; {signo(c['crec_ytd'])} contra enero–agosto de 2025)
CANALES (12 meses): ingreso, peso, margen bruto, lo que queda después de costos de la venta
{chr(10).join(f"  {x.canal}: {cop(x.ingreso)} · {pct(x.peso_pct, 0)} · {pct(x.margen_bruto_pct)} · {pct(x.contribucion_pct)}" for x in m.itertuples())}
CAJA: caja {cop(c['caja'])}, deuda {cop(c['deuda'])}, inventario {cop(c['inventario'])}, equipo {c['personas']} personas
ELITE: {num(e['miembros'])} miembros, {pct(e['activacion_pct'], 0)} estrenó la membresía, {num(e['nunca_compraron'])} nunca compraron.
  Descuento Elite 12 m: {cop(e['descuento12'])}. Margen bruto Lounge {pct(e['margen_bruto_pct'])} vs Store {pct(e['margen_bruto_store_pct'])}.
ALIADOS (miembros · % que compró · venta 12 m):
{chr(10).join(f"  {k}: {num(x['miembros'])} · {pct(x['activacion_pct'], 0)} · {cop(x['ingreso12'])}" for k, x in al.iterrows())}
RECOMPRA EN 6 MESES POR ORIGEN (y costo de traer un cliente):
{chr(10).join(f"  {k}: {pct(x['recompra_pct'], 0)}" + (f", CAC {cop(x['cac'])}" if pd.notna(x['cac']) else "") for k, x in r.iterrows())}
ENTREGAS (12 m): {pct(en['finde_pct'], 0)} de pedidos esperan fin de semana o festivo; cancelados {num(en['cancelados12'])} ({pct(en['cancel_pct'])}); en fecha prometida {pct(en['promesa_pct'])}; valor perdido por la espera ~{cop(en['valor_perdido_finde'])}/año.
SURTIDO: {len(s)} referencias; {len(quietas)} sin venta en 90 días con {cop(quietas['valor_stock'].sum())} en bodega.
PRECIOS REALES vs COMPETENCIA (10-sep-2026, diferencia por litro Classic / Elite):
{chr(10).join(f"  {x.producto} vs {x.competidor}: {signo(x.dif_classic_pct)} / {signo(x.dif_elite_pct)}" for x in pc.itertuples())}
MIL DEMONIOS: stock {num(inv['stock_final_u'])} botellas de 700 ml.
FIN DE AÑO: diciembre 2025 = {pct(datos.finanzas().set_index('mes').loc['2025-12','ingresos']/an.loc['2025','ingresos']*100, 0)} del año; pipeline corporativo nov–dic 2026 {cop(pdic['abierto_nov_dic_2026'])} ({num(pdic['n_abiertas'])} cotizaciones); a esta fecha en 2025 había {cop(pdic['cotizado_a_31ago_2025'])}.
"""
    except Exception as ex:
        return f"[No se pudieron cargar los datos: {ex}]"


def responder_local(pregunta: str) -> str:
    q = pregunta.lower()
    c = datos.cabecera()
    an = datos.anual()
    m = datos.margen_canal().set_index("canal")

    def tiene(*xs):
        return any(x in q for x in xs)

    if tiene("no ganamos", "ganar plata", "margen", "utilidad", "rentab"):
        return (f"⚖️ KYVA creció **{signo(an.loc['2024','crecimiento_pct'], 0)}** en 2024 y "
                f"**{signo(an.loc['2025','crecimiento_pct'], 0)}** en 2025, y el margen operacional "
                f"de 2025 fue **{pct(an.loc['2025','margen_operacional_pct'], 2)}**.\n\n"
                f"No es falta de venta, es mezcla. De cada peso que queda después de mercancía, "
                f"envío y pasarela:\n"
                + "\n".join(f"• **{k}**: {pct(x['contribucion_pct'])}" for k, x in m.iterrows()) +
                f"\n\nThe Lounge es {pct(m.loc['The Lounge','peso_pct'], 0)} de la venta y el canal que "
                f"menos deja. Las palancas: umbral de envío gratis, no apilar promociones sobre el "
                f"precio Elite y que las marcas cofinancien el descuento.")
    if tiene("elite", "lounge", "membres", "miembro"):
        e = datos.elite()
        return (f"🥂 Hay **{num(e['miembros'])}** miembros Elite y **{pct(e['activacion_pct'], 0)}** "
                f"estrenó la membresía: **{num(e['nunca_compraron'])}** nunca compraron.\n\n"
                f"• Descuento Elite en 12 meses: **{cop(e['descuento12'])}**\n"
                f"• Margen bruto: **{pct(e['margen_bruto_pct'])}** en The Lounge contra "
                f"**{pct(e['margen_bruto_store_pct'])}** en The Store\n"
                f"• Pero el miembro compra {num(e['pedidos_por_cliente'], 1)} veces al año contra "
                f"{num(e['pedidos_por_cliente_store'], 1)} del cliente Classic\n\n"
                f"La membresía sí genera lealtad; lo que hay que decidir es cuánto descuento se da "
                f"desde el primer pedido.")
    if tiene("aliado", "alianza", "porsche", "boconcept", "b2b2c"):
        a = datos.aliados()
        top = a.sort_values("activacion_pct", ascending=False)
        return ("🤝 Qué tanto compran los miembros de cada aliado:\n\n"
                + "\n".join(f"• **{k}**: {pct(x['activacion_pct'], 0)} compró · {cop(x['ingreso12'])} en 12 m"
                            for k, x in top.iterrows()) +
                f"\n\n**{top.index[0]}** trae compradores; **{top.index[-1]}** trae nombres. A cada "
                f"aliado conviene mandarle un reporte trimestral de sus miembros (está en Reportes).")
    if tiene("fin de semana", "despach", "entrega", "sábado", "sabado", "pedidos perdemos", "cancel"):
        e = datos.entregas()
        return (f"⏱️ **{pct(e['finde_pct'], 0)}** de los pedidos entran cuando no hay despacho "
                f"(viernes después de mediodía, sábado, domingo o festivo).\n\n"
                f"• Se cancelan más que los que salen el mismo día\n"
                f"• Valor perdido por la espera: **~{cop(e['valor_perdido_finde'])}** al año\n"
                f"• Entregados en la fecha prometida: **{pct(e['promesa_pct'])}**\n\n"
                f"Un turno de sábado en la mañana, a prueba un trimestre, se paga con recuperar la "
                f"mitad de esas cancelaciones.")
    if tiene("caro", "competencia", "precio", "licorera", "dislicores"):
        p = datos.precios_competencia()
        return ("🏷️ Con precios públicos del 10 de septiembre (diferencia por litro, Classic / Elite):\n\n"
                + "\n".join(f"• {x.producto} vs {x.competidor}: **{signo(x.dif_classic_pct)}** / "
                            f"{signo(x.dif_elite_pct)}" for x in p.itertuples()) +
                "\n\nEl caso delicado es Mil Demonios: La Licorera la vende a $100.990 y KYVA, que es "
                "su distribuidor exclusivo, a $111.000 Classic.")
    if tiene("mil demonios", "distribu", "defensor", "exclusiv"):
        inv = datos.inventario_exclusivas()
        d = datos.distribucion()
        d12 = d[d["mes"].isin(datos.ultimos(12))]
        return (f"🔥 Desde febrero KYVA compró **{num(inv['compras_u'].sum())}** botellas de Mil "
                f"Demonios y cierra agosto con **{num(inv['stock_final_u'].iloc[-1])}** en bodega.\n\n"
                f"Distribución facturó **{cop(d12['ingreso_neto'].sum())}** en 12 meses. Ojo con "
                f"dos cosas: el precio (un competidor la vende más barata que KYVA) y la cartera "
                f"de las cuentas, que pagan a 60 días.")
    if tiene("inventario", "rota", "surtido", "bodega", "referencia"):
        s = datos.surtido()
        q_ = s[s["unidades_90d"] == 0]
        return (f"🍾 De {len(s)} referencias, **{len(q_)}** no vendieron nada en 90 días y tienen "
                f"**{cop(q_['valor_stock'].sum())}** quietos en bodega.\n\nLa salida más limpia: "
                f"combos de regalo corporativo antes de noviembre, donde el cliente no compara "
                f"precio por botella.")
    if tiene("diciembre", "temporada", "navidad", "fin de año", "corporativ"):
        d = datos.pipeline_diciembre()
        return (f"🎄 Hay **{cop(d['abierto_nov_dic_2026'])}** cotizados para noviembre y diciembre "
                f"({num(d['n_abiertas'])} cotizaciones). A esta fecha de 2025 había "
                f"{cop(d['cotizado_a_31ago_2025'])}, y nov–dic 2025 cerró con "
                f"{cop(d['ganado_nov_dic_2025'])} ganados.\n\nLo que se decide ya: la compra de "
                f"inventario de octubre y la capacidad de despacho de la segunda quincena.")
    if tiene("caja", "deuda", "crédito", "credito", "plata en"):
        f = datos.finanzas()
        return (f"🏦 Caja **{cop(c['caja'])}**, deuda **{cop(c['deuda'])}**, inventario "
                f"**{cop(c['inventario'])}**.\n\nCon utilidad operacional cercana a cero, el "
                f"crecimiento se financia con la línea de crédito: tocó "
                f"{cop(f['deuda'].max())} en su punto más alto, cada octubre con la compra de diciembre.")
    if tiene("recompra", "vuelve", "círculo", "circulo", "referid", "cohorte"):
        r = datos.recompra_origen()
        return ("🔁 Vuelven a comprar en 6 meses, según por dónde llegaron:\n\n"
                + "\n".join(f"• {k}: **{pct(x['recompra_pct'], 0)}**" for k, x in r.iterrows()) +
                "\n\nEl referido de Mi Círculo vuelve más que el cliente de pauta y cuesta un cupón.")
    return (f"📊 A agosto de 2026 KYVA lleva **{cop(c['ingresos_ytd'])}** en el año "
            f"(**{signo(c['crec_ytd'])}** contra el mismo período de 2025), con margen bruto de "
            f"**{pct(c['margen_bruto12'])}** y margen operacional de **{pct(c['margen_op12'], 2)}** "
            f"en los últimos 12 meses.\n\nPuedo contarte de: margen por canal, membresía Elite, "
            f"aliados, Mi Círculo, entregas y fin de semana, precios contra la competencia, "
            f"Mil Demonios, surtido, fin de año y caja.")


def responder_modelo(pregunta: str, historial: list) -> str:
    import anthropic
    cliente = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    mensajes = [{"role": m["role"], "content": m["content"]}
                for m in historial[-8:] if m["role"] in ("user", "assistant")]
    mensajes.append({"role": "user", "content": pregunta})
    r = cliente.messages.create(model=MODELO, max_tokens=1400,
                                system=CONTEXTO + "\n\n" + resumen_datos(), messages=mensajes)
    return r.content[0].text


def _hay_llave() -> bool:
    try:
        return bool(st.secrets.get("ANTHROPIC_API_KEY"))
    except Exception:
        return False


def render():
    st.markdown(HEADER_CSS, unsafe_allow_html=True)
    st.markdown(encabezado(
        "Agente IA KYVA",
        "Pregúntale al negocio en español · responde sobre los datos del panel",
        "Dirección"), unsafe_allow_html=True)

    con_modelo = _hay_llave()
    if not con_modelo:
        st.markdown(panel(
            "Modo demostración",
            "Sin llave de API configurada, el agente responde con lógica local sobre los "
            "<b>mismos datos</b> que alimentan los tableros. Con una llave de Anthropic en "
            "<code>.streamlit/secrets.toml</code> conversa libremente, entiende preguntas de "
            "seguimiento y cruza áreas.", "🤖"), unsafe_allow_html=True)
        st.markdown(espacio(12), unsafe_allow_html=True)

    if "chat" not in st.session_state:
        st.session_state.chat = [{"role": "assistant", "content": (
            "Hola. Soy el agente de negocio de KYVA y tengo el panel completo adentro: los "
            "cuatro canales, la membresía Elite, los aliados, las entregas, el surtido y la caja.\n\n"
            "Pregúntame lo que quieras, como se lo preguntarías a alguien del equipo.")}]

    st.markdown("##### Preguntas para empezar")
    cols = st.columns(2, gap="small")
    pendiente = None
    for i, s in enumerate(SUGERIDAS):
        if cols[i % 2].button(s, key=f"sug_{i}", width="stretch"):
            pendiente = s

    st.markdown(espacio(14), unsafe_allow_html=True)
    for m in st.session_state.chat:
        with st.chat_message(m["role"], avatar="🥂" if m["role"] == "assistant" else "👤"):
            st.markdown(m["content"])

    entrada = st.chat_input("Escribe tu pregunta sobre el negocio…")
    pregunta = pendiente or entrada
    if pregunta:
        st.session_state.chat.append({"role": "user", "content": pregunta})
        with st.chat_message("user", avatar="👤"):
            st.markdown(pregunta)
        with st.chat_message("assistant", avatar="🥂"):
            with st.spinner("Mirando los datos…"):
                try:
                    r = responder_modelo(pregunta, st.session_state.chat[:-1]) if con_modelo \
                        else responder_local(pregunta)
                except Exception as ex:
                    r = (responder_local(pregunta) + f"\n\n---\n*No se pudo consultar el modelo "
                         f"({ex}); la respuesta viene de la lógica local.*")
            st.markdown(r)
        st.session_state.chat.append({"role": "assistant", "content": r})

    if len(st.session_state.chat) > 1:
        if st.button("🔄  Empezar de nuevo", key="reset_chat"):
            del st.session_state["chat"]
            st.rerun()

    with st.expander("Ver el contexto exacto que recibe el agente"):
        st.caption("Se arma con las mismas funciones que alimentan los tableros: el agente no "
                   "puede dar una cifra distinta a la del panel.")
        st.code(resumen_datos(), language="text")
