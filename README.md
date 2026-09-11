# KYVA · Panel de Negocio

Demo construido por **[Calybrat](https://calybrat.com)** para **KYVA**, la tienda
online de licores, vinos y cervezas premium de Bogotá — «join the circle».

No es una plantilla con el logo cambiado. Es un panel diseñado alrededor de cómo
gana plata KYVA: cuatro canales con márgenes muy distintos (The Store, The Lounge,
corporativo y distribución de marcas), una membresía Elite que casi siempre llega
regalada por un aliado, un programa de referidos que es el propio lema de la marca,
y una operación de despacho que cierra justo cuando más se compra licor.

La pregunta que atraviesa todo el panel es la que dejan las cifras públicas: **KYVA
más que duplicó sus ingresos en 2024 y otra vez en 2025, y su margen operacional
de 2025 fue 0,08%.** ¿Crecer le está dejando plata?

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Qué contesta el panel

| Grupo | Módulo | La pregunta que responde |
|---|---|---|
| El lunes a las 7 | **Tablero Ejecutivo** | ¿Cómo cerró la semana y cómo va el año? |
| ¿Crecer nos deja plata? | **Dónde se va el margen** | De lo que paga el cliente, ¿cuánto le queda a KYVA, peso por peso? |
| | **Los cuatro negocios** | ¿Cuánto pesa, crece y deja cada canal? |
| | **Caja y capital de trabajo** | ¿Por qué crecer con margen cero pide deuda cada octubre? |
| ¿Quién compra y vuelve? | **Recompra y cohortes** | ¿Vuelve el cliente, según por dónde llegó? |
| | **Membresía Elite** | ¿Cuánto cuesta la membresía y cuántos la usan? |
| | **Alianzas B2B2C** | ¿Qué aliado trae miembros que compran? |
| | **Mi Círculo** | ¿Cuánto rinde el programa de referidos y quién lo mueve? |
| ¿Qué vendemos y a qué precio? | **Surtido y rotación** | ¿Qué referencias venden, cuáles dejan margen y cuáles no se mueven? |
| | **Precio vs. competencia** | ¿Es KYVA de verdad más barata? (precios reales) |
| | **Marcas en distribución** | ¿Cómo va la exclusiva de Mil Demonios? |
| ¿Llegamos a tiempo? | **Pide AM, recibe PM** | ¿Cuánto cuesta no despachar el fin de semana? |
| ¿Qué viene? | **Temporada de fin de año** | ¿Qué hay que decidir en septiembre para diciembre? |
| Dirección | **Reportes Automáticos** | Comité del lunes, junta de socios, reporte por aliado, entregas |
| | **Agente IA KYVA** | Preguntarle al negocio en español |

---

## Los puntos débiles que el panel nombra

Elogiar es fácil. Estos son los hallazgos que se sostienen en información pública:

1. **Crecimiento sin utilidad.** +120% en 2024, +130% en 2025, margen operacional de
   0,08% (EMIS). El panel lo explica por mezcla: el canal Elite deja mucho menos por
   peso vendido que The Store.
2. **El horario de despacho no coincide con el de consumo.** KYVA despacha lunes a
   jueves de 8 a 5 y el viernes hasta las 4 (kyva.co/faq). Todo lo que entra el viernes
   por la tarde, el sábado o el domingo espera al lunes — o al martes, si es festivo.
3. **El precio Classic no siempre gana.** Precios reales del 10-sep-2026: Old Parr 12
   (500 ml) está a $110.200 en KYVA y $105.990 en Dislicores.
4. **Conflicto de canal en la exclusiva.** KYVA distribuye Mil Demonios en exclusiva y la
   vende a $111.000 Classic; La Licorera la tiene a $100.990.
5. **Membresías regaladas que nunca se estrenan.** El modelo B2B2C infla el número de
   miembros más que la venta (supuesto del modelo, a validar con los datos reales).

---

## Los datos

Son **simulados**, pero no inventados a ciegas. El modelo está anclado a cifras
públicas de KYVA y todo lo demás se deriva de ahí con supuestos de retail de licores
declarados explícitamente en [`data/generate_data.py`](data/generate_data.py).

### Anclas públicas usadas

| Dato | Valor | Fuente |
|---|---|---|
| Constitución de KYVA SAS | 13 de agosto de 2019 | [EMIS](https://www.emis.com/php/company-profile/CO/Kyva_Sas_es_13312007.html) |
| Ventas 2021 | entre $1.000 y $2.000 millones | [einforma](https://directorio-empresas.einforma.co/informacion-empresa/kyva-sas) · [InformaColombia](https://www.informacolombia.com/directorio-empresas/informacion-empresa/kyva-sas) |
| Crecimiento de ingresos 2024 | **+120,03%** | EMIS |
| Crecimiento de ingresos 2025 | **+130,46%** | [EMIS](https://www.emis.com/php/company-profile/CO/Kyva_Sas_es_13312007.html) |
| Margen operacional 2025 | **0,08%** | EMIS |
| Crecimiento de la utilidad operacional 2025 | +135,71% | EMIS |
| Empleados en 2026 | 13 | EMIS |
| Fundador y CEO, ex-CFO de Pernod Ricard Colombia; socio y CMO | Romain Senechal · Mathieu Colombier | [COPU](https://copu.media/romain-senechal-%F0%9F%87%AB%F0%9F%87%B7-socio-fundador-de-kyva-nos-cuenta-la-llegada-de-esta-tienda-online-de-licores-privada-a-colombia-%F0%9F%87%A8%F0%9F%87%B4/) · [Produ](https://www.produ.com/mercadeo/noticias/kyva-y-la-vision-de-romain-senechal-un-ecosistema-digital-para-marcas-premium-en-colombia/) |
| Modelo B2B2C, The Lounge y The Store (oct-2023), hasta -25% permanente | | [COPU, lanzamiento de The Store](https://copu.media/kyva-lanza-the-store-la-tienda-online-con-mas-de-500-referencias-de-licores-premium-en-colombia-%F0%9F%87%A8%F0%9F%87%B4/) |
| Aliados: Porsche, Carmiña Villegas, Argento & Bourbon, Foro de Presidentes, EO, BoConcept, Café San Alberto | | COPU · Produ · [kyva.co](https://kyva.co/) |
| Lanzamiento de la membresía Élite en el Porsche Center, +250 asistentes | sep-2025 | Produ |
| Distribuidor exclusivo de Mil Demonios (2026); Ron Defensor y Marcel Thorel | | [LinkedIn de KYVA](https://www.linkedin.com/company/kyva-co/) |
| Más de 300 referencias; 85 whiskies | | [kyva.co/tienda](https://kyva.co/tienda/) |
| Membresía Classic y Elite, Mi Círculo, envío $18.000 bajo $300.000, horario de despacho, cobertura Bogotá y Sabana | | [kyva.co/faq](https://kyva.co/faq/) |
| Precios Classic y Elite de 22 referencias; stock de Mil Demonios (1.200 u) | vistos el 10-sep-2026 | [kyva.co](https://kyva.co/categoria-producto/licor/whisky-licor-2/) |
| Precios de competidores | vistos el 10-sep-2026 | [La Licorera](https://lalicorera.com/productos/aguardiente/mil-demonios) · [Dislicores](https://www.dislicores.com/old-parr) · [Éxito](https://www.exito.com/whisky-chivas-regal-12-a-os-x-1000-ml-327638/p) |
| Mil Demonios: 55.000–60.000 botellas al año, presente en 8 de 32 departamentos | dic-2025 | [El Tiempo](https://www.eltiempo.com/economia/empresas/n-p-n-p-1000-demonios-el-aguardiente-premium-colombiano-que-quiere-conquistar-nuevas-categorias-3514213) |
| Diciembre ≈ 20% de la venta anual de aguardiente | | [El Colombiano](https://www.elcolombiano.com/negocios/aguardiente-en-diciembre-ventas-se-disparan-en-antioquia-y-colombia-AG26026677) |
| IVA del 19% a licores (Decreto 1474 de 2025), suspendido el 29-ene-2026 e inexequible el 15-abr-2026 | | [Radio Nacional](https://www.radionacional.co/actualidad/corte-constitucional-tumbo-iva-del-19-licores-y-apuestas-en-linea) · [Infobae](https://www.infobae.com/colombia/2026/04/09/la-corte-constitucional-tumbo-la-emergencia-economica-decretada-por-el-gobierno-petro/) |

### Qué produce el modelo

Trece tablas, simuladas desde enero de 2022 y guardadas desde **enero de 2023**, con
corte al **31 de agosto de 2026**. Todo en pesos colombianos.

- `pedidos.csv.gz` — cada pedido de The Store y The Lounge, con su hora, zona,
  ventana de despacho, descuento, envío, pasarela, margen y si se canceló
- `clientes.csv.gz` — cada cliente, con su origen, aliado y quién lo refirió
- `catalogo.csv` / `ventas_sku_mes.csv.gz` — el surtido y su rotación mes a mes
- `miembros.csv.gz` — los miembros Elite, incluidos los que nunca compraron
- `corporativo.csv` — cotizaciones corporativas ganadas, perdidas y abiertas
- `distribucion.csv`, `cuentas_distribucion.csv`, `inventario_exclusivas.csv`
- `finanzas.csv` — estado de resultados, capital de trabajo, caja y deuda
- `precios_competencia.csv` — **precios reales**, no simulados

### La consistencia está garantizada por construcción

Se simula cada cliente, cada pedido y cada línea de producto; ingresos, márgenes,
cohortes, rotación y estado de resultados se **derivan** de esa simulación. Los
indicadores que aparecen en más de una pantalla se calculan **una sola vez** en
[`utils/datos.py`](utils/datos.py). El agente y los reportes usan las mismas funciones.

Los "otros gastos" (un fijo mensual más un porcentaje de ingresos) se calibran una
sola vez contra las dos cifras públicas de utilidad operacional (2024 y 2025), y la
misma regla se aplica a todos los meses. El generador imprime al final la
verificación contra cada ancla:

```bash
python3 data/generate_data.py
```

### Supuestos que conviene validar con los datos reales

Tasas de recompra, activación de membresías por aliado, profundidad del descuento
Elite en el tiempo, valor del cupón de Mi Círculo ($25.000), costo de envío por zona,
márgenes por categoría y el sell-in de distribución. Son razonables para el sector,
pero son supuestos: la conversación con KYVA es justamente para reemplazarlos por
sus cifras.

---

## Identidad visual

Los colores salen de las variables globales que declara el tema de `kyva.co` y
coinciden con los rellenos del logo SVG que sirve el propio sitio:

| | |
|---|---|
| `#0E113A` | `--e-global-color-primary` · el círculo del logo |
| `#CE6264` | `--e-global-color-secondary` · coral |
| `#9193A1` | `--e-global-color-accent` · gris lila |
| `#E5E1E6` | lavanda · las letras del logo |

Tipografías del sitio: Montserrat, Source Sans y DM Serif Display (la serifa del
logotipo, usada en los títulos). El logo de `assets/` es el SVG de kyva.co. El
**círculo** que aparece en cada encabezado no es decoración: el logo es un círculo,
el lema es «join the circle» y el programa de referidos se llama Mi Círculo.

---

## El agente IA

Sin configurar nada, responde con lógica local sobre los mismos datos del panel. Para
que converse con un modelo:

```toml
# .streamlit/secrets.toml   (nunca se commitea)
ANTHROPIC_API_KEY = "sk-ant-..."
```

## Pruebas

```bash
python3 pruebas.py
```

Abre los quince módulos con el runner headless de Streamlit y falla si alguno lanza
una excepción.

## Registro de visitas

El demo es de acceso libre. Cada visita queda registrada (fecha, IP y ciudad
aproximada) y solo se ve entrando con `?accesos=calybrat` en la URL. En Streamlit
Cloud el registro se reinicia con cada despliegue.

---

**Datos simulados con fines de demostración.** Este panel no contiene información
confidencial de KYVA ni pretende representar sus cifras reales, salvo las públicas
citadas arriba. Construido por Calybrat como propuesta de producto.
