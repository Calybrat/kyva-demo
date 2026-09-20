# De panel a software de alta gerencia

Rama `demo-alta-gerencia`. **Nada de esto toca `main` ni la URL que Javier puede
abrir** (`kyva-demo.streamlit.app` sigue sirviendo la versión anterior).

---

## El encargo

Convertir el panel en algo que **opere la empresa**, no que la reporte. Supuesto
de trabajo: todo se puede conectar y hay permisos para todo. Sencillo por fuera,
potente por dentro, con la identidad de KYVA.

## Cómo se trabajó

No en solitario. Se montó un comité de agentes con encargos distintos, y **tres
de los cuatro encontraron cosas que yo no había visto**:

| Agente | Qué encontró |
|---|---|
| **COO adversario** (15 años en distribución de licores) | Cinco huecos de sector y la objeción de fondo: *«yo no pago por que me expliquen mi empresa; pago por dejar de perder plata los martes»* |
| **Investigación técnica** | El panel está escrito con vocabulario de Streamlit 1.25 corriendo sobre 1.60. 35 gráficos estáticos, 198 tarjetas de HTML a mano, cero mapas |
| **Dirección de diseño** | La paleta falla los chequeos de contraste, `kpi()` tiene un `height:100%` que no funciona, el sidebar no marca dónde estás, y el CSS tiene código muerto desde la 1.35 |
| **Auditoría de terceros** | Confirmó que usar APIs nativas en vez de paquetes externos era lo correcto: `streamlit-plotly-events` está muerto y ya es nativo |

**Ninguna afirmación de un agente se aplicó sin verificarla.** El de
investigación dijo Streamlit 1.64; la instalada es 1.60, así que
`st.echarts_chart` no existe y no se usa. Tres de sus recomendaciones eran de
una versión que no tenemos.

---

## El hallazgo que ordenó el trabajo de producto

El demo estaba bien investigado y anclado a cifras públicas: The Store, The
Lounge, Mi Círculo y la membresía Elite **son marca real de KYVA** (kyva.co,
COPU, LinkedIn). Eso no se tocó.

Pero en la reunión del 19-sep Javier describió un negocio que el panel no
mostraba:

| Lo que dijo Javier | Lo que tenía el demo |
|---|---|
| Vinos, licores, **cervezas** y complementarios | ✓ el catálogo ya los traía |
| Operación en Bogotá **y Medellín** | ✗ **solo Bogotá** |
| Canales: e-commerce, membresías, **empresas, restaurantes, bares, discotecas, clubes sociales** | ✗ los de on-premise **no existían** |
| «**El B2B es el peso actual**» | ✗ el demo era 76% B2C |

**Las dos cosas son ciertas a la vez.** KYVA de cara al público es la tienda en
línea; la empresa que Javier dirige además distribuye a establecimientos —son
distribuidores exclusivos de Mil Demonios, Ron Defensor y Marcel Thorel—. Lo que
faltaba no era corregir el modelo: era **añadir la capa que él dice que pesa**.

---

## Lo que se construyó

### Capa de datos — 13 tablas nuevas, todas derivadas

`data/gen_b2b.py` y `data/gen_gerencia.py`. La regla no se rompe nunca: **nada se
genera en paralelo a algo que ya existe.** El inventario por bodega suma exacto
el `stock_u` del catálogo (17.945 = 17.945) y el B2B cuadra al 100% con lo que
`finanzas.csv` ya declaraba (3.187 M contra 3.189 M). Si se generara suelto, un
día la pantalla de surtido diría 108 botellas de Chivas y la de reposición 74.

| Tabla | Qué resuelve |
|---|---|
| `cuentas`, `ventas_cuenta_mes`, `entregas` | Los 61 establecimientos, su venta y lo que cuesta servirlos |
| `facturas` | **Cartera de verdad**, no `venta × plazo/30` |
| `marcas_mes`, `rebates` | Cuota, bonificación y rebate escalonado |
| `quiebres`, `devoluciones` | Lo que NO se vendió, con motivo y responsable |
| `lotes` | Vencimientos — venden cerveza |
| `punto_venta` | Precio en carta, material POP, competencia en la barra |
| `presupuesto` | El compromiso contra el que se mide todo |
| `compromisos` | Lo que alguien dijo que iba a hacer, con fecha |
| `vendedores`, `hilos`, `decisiones` | Equipo, conversaciones y bandeja |

**Tres calibraciones costaron trabajo y quedan anotadas porque no son obvias:**

1. **El margen no se saca restando el descuento al precio de góndola.** Eso daba
   6,6%, imposible. Un distribuidor vende sobre su lista mayorista, que parte
   del costo. Ahora 16-30% por canal, contra referencia real del sector.
2. **Sin cola larga todas las cuentas se parecen y no hay nada que decidir.** Con
   `lognormal(σ=0,92)` aparecen las cuentas chiquitas a las que se va muchas
   veces — que es el hallazgo del módulo de rentabilidad.
3. **Una entrega de última milla no cuesta 42 mil sino 68.** Con el número bajo
   la logística no pesaba y el módulo se quedaba sin historia.

### Módulos nuevos — de 15 a 27

| # | Módulo | Por qué un gerente lo abre |
|---|---|---|
| 20 | **Centro de decisiones** | La bandeja de lo que hay que aprobar hoy, ordenada **por plata en juego** y no por gravedad declarada. Junta ocho sistemas |
| 21 | **Rentabilidad por cuenta** | El punto ciego #1: el ERP sabe cuánto vende, el operador logístico cuánto cuesta repartir, nadie junta las dos |
| 22 | **Equipo comercial** | Margen por vendedor, no venta. El ranking por venta premia al que más descuento regala |
| 23 | **Rutas y costo de servir** | El margen bruto se decide una vez; el costo de servir, todos los días |
| 24 | **Hilos del equipo** | La discusión pegada al número, con desenlace escrito |
| 25 | **Simulador** | Cada palanca declara su contrapartida |
| 26 | **Cartera** | Factura por factura, con el atraso real contra el pactado |
| 27 | **Marcas y rebate** | Donde está la utilidad de verdad |
| 28 | **Nivel de servicio** | Lo que no se vendió |
| 29 | **Presupuesto** | El compromiso contra el que se mide |
| 30 | **Comité del lunes** | Los compromisos vencidos, arriba y en rojo |
| 31 | **El punto de venta** | Qué pasa dentro del bar |
| 32 | **Vencimientos** | Qué hay que sacar antes de que se venza |

### Lo arquitectónico — las dos objeciones de fondo del COO

> *«En 23 módulos hay 6 controles interactivos. No puedo pedirle "muéstrame solo
> Medellín". Eso no es un panel de gerencia: es un PDF con colores bonitos.»*

`utils/filtros.py` — **filtros globales** de ciudad, canal, vendedor y periodo,
que persisten al cambiar de pantalla y avisan con una cinta cuando la vista está
filtrada. Un panel filtrado que parece completo es peor que no tener filtros.

> *«Ese botón que dice "Decidir" guarda en la memoria de mi navegador. Refresco
> la página y se borró. Eso no es un sistema de gerencia, eso es una demo.»*

`utils/estado.py` — **persistencia en disco**. Y el arreglo no es técnico sino
de concepto: decidir exige elegir **dueño y plazo**, y toda decisión genera un
compromiso que aparece en el comité del lunes.

### Lo visual — de dashboard a producto

- **`config.toml`** pasó de 6 líneas a un tema completo. Lo que más rinde: las
  tres paletas de gráfico se declaran una vez y las heredan las 27 pantallas.
- **Paleta validada** con OKLab y simulación de daltonismo. La anterior fallaba:
  coral contra gris daba ΔE 14,8 con un piso de 15, y son dos canales que van
  pegados en cada barra apilada.
- **Sin emoji** en navegación, tarjetas ni paneles. Es la firma más reconocible
  de un panel generado por IA.
- **Sidebar con estado activo** y buscador. Antes eran 33 filas idénticas.
- **Gráficos clicables** — hacer clic en una cuenta abre su ficha con sus
  facturas una por una.
- **Mapa 3D** de zonas de Bogotá y Medellín, sin proveedor de teselas ni llave
  de API.
- **`PLOTLY_CONFIG`** esconde la modebar, que es la firma visual más delatora.

---

## Las reglas que no se rompen

1. **Consistencia por construcción.** Si dos pantallas pueden contradecirse, el
   dato se calcula en un solo sitio y las dos lo leen.
2. **Nada que mueva plata se ejecuta solo.** El sistema prepara, un humano
   confirma.
3. **Las fallas se muestran.** Javier preguntó por el nivel de error; un panel
   con 100% de acierto contesta esa pregunta con una mentira.
4. **Se prueba entrando a la pantalla**, no leyendo el menú.
5. **Ninguna afirmación de un agente se aplica sin verificarla.**

---

## Bitácora

**2026-09-19 · Arranque.** Rama creada. Reconocido el modelo (19 módulos, 21
tablas). Detectado el hueco de on-premise y de Medellín.

**2026-09-19 · Capa B2B.** 61 cuentas, 622 meses-cuenta. Tres calibraciones de
realismo corregidas contra referencia del sector.

**2026-09-20 · Comité de agentes.** Cuatro revisores en paralelo. El COO
adversario encontró cinco huecos de sector; el de investigación, la brecha de
versión de Streamlit; el de diseño, los fallos de contraste y el CSS muerto.

**2026-09-20 · Capa de gerencia.** Cartera real, marcas, quiebres, lotes, punto
de venta, presupuesto y compromisos. Dos números imposibles corregidos: fill
rate del 35% (estaba midiendo solo sobre las líneas que fallaron) y rebate
perdido en cero (el filtro no miraba el tramo siguiente).

**2026-09-20 · Filtros globales y persistencia.** Las dos objeciones de fondo.

**2026-09-20 · Rediseño.** Tema, paleta validada, sin emoji, sidebar con estado,
gráficos clicables, mapa. Corregido un bug visible: dos importes en una frase de
markdown activaban el modo LaTeX de Streamlit.

---

## Lo que queda

- Aplicar lo que devuelva la auditoría de diseño del resultado.
- Exportación a Excel (`XlsxWriter`, Python puro, sin dependencias de sistema).
- Consolidar módulos que se solapan: los cuatro de B2C son uno solo, y
  automatizaciones + alertas también.
- El agente del módulo 15 sigue respondiendo en vez de ejecutar.
