# De panel a software de alta gerencia

Rama `demo-alta-gerencia`. **Nada de esto toca `main` ni la URL que Javier puede
abrir** — `kyva-demo.streamlit.app` sigue sirviendo la versión anterior.

```bash
cd Apps/kyva-demo
git checkout demo-alta-gerencia
pip install -r requirements.txt
python3 pruebas.py          # las 33 pantallas
streamlit run app.py
```

---

## Qué cambió, en una línea

**De 15 pantallas que explican a 33 que operan.** El panel pasó de contestar
«qué pasó» a contestar «qué hago hoy, quién responde y para cuándo».

| | Antes | Ahora |
|---|---|---|
| Pantallas | 15 | **33** |
| Tablas de datos | 21 | **34** |
| Líneas | 4.500 | **~14.000** |
| Controles interactivos | 6 en total | filtros globales + clic en gráficos + formularios |
| Lo que sobrevive al refresco | nada | decisiones, compromisos e hilos |

---

## Cómo se trabajó

No en solitario. Se montó un comité de agentes con encargos distintos, y **los
cuatro encontraron cosas que yo no había visto**:

| Agente | Qué encontró |
|---|---|
| **COO adversario** (15 años en distribución de licores) | Cinco huecos de sector y la objeción de fondo: *«yo no pago por que me expliquen mi empresa; pago por dejar de perder plata los martes»* |
| **Investigación técnica** | El panel estaba escrito con vocabulario de Streamlit 1.25 corriendo sobre 1.60: 35 gráficos estáticos, 198 tarjetas de HTML a mano, cero mapas |
| **Dirección de diseño** | La paleta fallaba los chequeos de contraste, `kpi()` tenía un `height:100%` que no funciona, el sidebar no marcaba dónde estabas, y el CSS tenía código muerto desde la 1.35 |
| **Auditoría del resultado** (sin contexto, solo capturas) | Dos bugs **míos** que había publicado, y la falta de jerarquía visual |

Más un **workflow de 21 agentes** que construyó siete módulos en paralelo, cada
uno con revisión adversaria y corrección. Los revisores encontraron
contradicciones entre pantallas, supuestos ocultos y números imposibles; los
correctores aplicaron lo real y **rechazaron con argumento lo que no lo era**.

> **Ninguna afirmación de un agente se aplicó sin verificarla.** El de
> investigación dijo Streamlit 1.64; la instalada es 1.60, así que
> `st.echarts_chart` no existe y no se usa. Tres de sus recomendaciones eran de
> una versión que no tenemos, y `st.status(type="step")` llegó a romper una
> pantalla antes de que lo comprobara.

---

## El hallazgo que ordenó el trabajo de producto

El demo estaba bien investigado: The Store, The Lounge, Mi Círculo y la
membresía Elite **son marca real de KYVA** (kyva.co, COPU, LinkedIn). Eso no se
tocó.

Pero en la reunión del 19-sep Javier describió un negocio que el panel no
mostraba:

| Lo que dijo Javier | Lo que tenía el demo |
|---|---|
| Vinos, licores, **cervezas** y complementarios | ✓ el catálogo ya los traía |
| Operación en Bogotá **y Medellín** | ✗ **solo Bogotá** |
| Canales: e-commerce, membresías, **empresas, restaurantes, bares, discotecas, clubes sociales** | ✗ los de on-premise **no existían** |
| «**El B2B es el peso actual**» | ✗ el demo era 76% B2C |

**Las dos cosas son ciertas a la vez.** KYVA de cara al público es la tienda en
línea; la empresa que Javier dirige además distribuye a establecimientos. Lo que
faltaba no era corregir el modelo: era **añadir la capa que él dice que pesa**.

---

## Las capas

### 1. Datos — 13 tablas nuevas, todas derivadas

`data/gen_b2b.py` y `data/gen_gerencia.py`. La regla no se rompe nunca: **nada
se genera en paralelo a algo que ya existe.**

- El inventario por bodega suma exacto el `stock_u` del catálogo (17.945 = 17.945).
- El B2B cuadra al 100% con lo que `finanzas.csv` ya declaraba (3.187 M vs 3.189 M).

**Tres calibraciones que costaron trabajo y no son obvias:**

1. **El margen no se saca restando el descuento al precio de góndola.** Eso daba
   6,6%, imposible. Un distribuidor vende sobre su lista mayorista, que parte
   del costo. Ahora 16-30% por canal, contra referencia real del sector. *(El
   mismo error se coló otra vez en el copiloto y hubo que corregirlo dos veces.)*
2. **Sin cola larga todas las cuentas se parecen y no hay nada que decidir.**
   Con `lognormal(σ=0,92)` aparecen las cuentas chiquitas a las que se va muchas
   veces — que es el hallazgo del módulo de rentabilidad.
3. **Una entrega de última milla no cuesta 42 mil sino 68.** Con el número bajo
   la logística no pesaba y el módulo se quedaba sin historia.

### 2. Arquitectura — las dos objeciones de fondo del COO

> *«En 23 módulos hay 6 controles interactivos. No puedo pedirle "muéstrame solo
> Medellín". Eso no es un panel de gerencia: es un PDF con colores bonitos.»*

**`utils/filtros.py`** — filtros globales de ciudad, canal, vendedor y periodo,
que persisten al cambiar de pantalla y avisan con una cinta cuando la vista está
filtrada. Un panel filtrado que parece completo es peor que no tener filtros.

> *«Ese botón que dice "Decidir" guarda en la memoria de mi navegador. Refresco
> la página y se borró.»*

**`utils/estado.py`** — persistencia en disco. Y el arreglo no es técnico sino
de concepto: decidir exige elegir **dueño y plazo**, y toda decisión genera un
compromiso que aparece en el comité del lunes.

### 3. Interfaz — `utils/ui.py`

Gráficos clicables (`on_select`), fichas modales que **bajan hasta la factura**,
mapa 3D de zonas sin proveedor de teselas, tablas con barras de progreso dentro.

### 4. Salida — `utils/exportar.py`

El libro de Excel para la junta: siete hojas con portada fechada, encabezado
congelado, filtro automático y formatos. Se arma **al pulsar**, no al abrir.

---

## Las 33 pantallas

| Grupo | Pantallas |
|---|---|
| **El lunes a las 7** | Centro de decisiones · Comité del lunes · Tablero Ejecutivo |
| **¿Dónde está la caja?** | Cartera · Caja y capital de trabajo · Presupuesto y brecha |
| **¿Quién nos deja plata?** | Rentabilidad por cuenta · Dónde se va el margen · Los cuatro negocios · Equipo comercial |
| **¿Estamos cumpliendo?** | Marcas y rebate · Lo que no se vendió · Rutas y costo de servir · Pide AM, recibe PM |
| **¿Qué hay que comprar?** | Reposición y compras · Vencimientos · Surtido y rotación |
| **¿Qué pasa en el punto?** | Lo que pasa dentro del bar · Precio vs. competencia · Marcas en distribución |
| **¿Qué viene?** | Proyección de cierre · Temporada de fin de año · Simulador |
| **¿Qué se hace solo?** | **Copiloto de pedidos** · Automatizaciones · Alertas |
| **El canal directo** | Recompra · Membresía Elite · Alianzas B2B2C · Mi Círculo |
| **Dirección** | Hilos del equipo · Reportes Automáticos · Agente IA |

### Las cuatro que hay que mostrar primero

1. **Centro de decisiones** — la bandeja de lo que espera una decisión, ordenada
   **por plata en juego** y no por gravedad declarada. Junta ocho sistemas.
2. **Copiloto de pedidos** — de un WhatsApp a un pedido armado en Loggro, en
   seis pasos, esperando aprobación. Es lo que Javier pidió textualmente.
3. **Rentabilidad por cuenta** — clic en un punto y se abre la ficha con sus
   facturas una por una.
4. **Marcas y rebate** — donde está la utilidad de verdad. En doce meses se
   dejaron ir **19,7 M** por quedarse corto de tramo.

---

## Las reglas que no se rompen

1. **Consistencia por construcción.** Si dos pantallas pueden contradecirse, el
   dato se calcula en un solo sitio y las dos lo leen.
2. **Nada que mueva plata se ejecuta solo.** El sistema prepara, un humano
   confirma. Es lo que permite que un director de operaciones diga que sí.
3. **Las fallas se muestran.** Javier preguntó por el nivel de error; un panel
   con 100% de acierto contesta esa pregunta con una mentira.
4. **Se verifica entrando a la pantalla**, no leyendo el menú. El 19-sep di por
   desplegado algo que estaba caído porque comprobé la señal fácil.
5. **Ninguna afirmación de un agente se aplica sin verificarla.**
6. **Los supuestos van a la vista**, no escondidos dentro del cálculo.

---

## Los errores propios, anotados

Están aquí porque cada uno costó, y porque el patrón se repite:

| Error | Cómo salió |
|---|---|
| `$Julián Mora M` en un eje | `light()` aplicaba el formato de moneda al eje Y sin mirar si la barra era horizontal. Lo cazó la auditoría de diseño, no yo |
| `Margen servido (×4 para verlo)` | Multipliqué una serie para que se viera y lo **confesé en la leyenda**. Ningún producto expone un factor de deformación |
| «El ranking se voltea» cuando no se voltea | El margen absoluto sigue a la venta. Lo que sí se voltea es la **tasa** — 4 de 5 cambian de puesto |
| Fill rate del 35% | Medía solo sobre las líneas que fallaron |
| Margen del 6,6% | Precio de góndola menos descuento. Dos veces |
| `st.status(type="step")` | Verifiqué que el parámetro existía, no sus valores. Llega en 1.63; tenemos 1.60 |
| «Por encima del cupo» | Cuando lo que fallaba era una factura vencida. Decir mal por qué se bloqueó un pedido hace que el vendedor discuta con el sistema |
| «Quitar filtros» no limpiaba | Hay que borrar el diccionario **y** la clave de cada selectbox |

---

## Verificación

- `python3 pruebas.py` — las 33 pantallas cargan.
- **33 de 33 verificadas en navegador real**, entrando a cada una y buscando
  trazas de error en el contenido renderizado.
- Probadas a mano: el filtro global cambia el dato y persiste al navegar, el
  clic en el gráfico abre la ficha, la ficha baja hasta la factura, el libro de
  Excel se genera y abre.

---

## Lo que queda

- **Consolidar lo que se solapa.** Los cuatro módulos de B2C son uno solo;
  automatizaciones y alertas también. 33 pantallas es mucho: el COO lo dijo y
  tiene razón.
- **Presupuesto cargable**, no derivado.
- **Usuarios y roles.** Sin login no hay delegación de verdad.
- **Trazabilidad hasta el documento** en todas las pantallas, no solo en
  cuentas.
- Que el módulo 15 (Agente IA) se funda con el copiloto: ahora uno responde y
  el otro ejecuta, y deberían ser el mismo.
