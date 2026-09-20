# De panel a software de alta gerencia — plan de trabajo

Rama `demo-alta-gerencia`. Nada de esto toca `main` ni la URL que Javier puede
abrir en cualquier momento.

## El encargo

Convertir el panel en algo que **opere la empresa**, no que la reporte. Supuesto
de trabajo dado por Nicolás: *todo se puede conectar y hay permisos para todo*.
Sencillo por fuera, potente por dentro, con la identidad de KYVA.

## El hallazgo que ordena el trabajo

El demo actual está bien investigado y anclado a cifras públicas: The Store, The
Lounge, Mi Círculo y la membresía Elite **son marca real de KYVA** (kyva.co,
COPU, LinkedIn). Eso no se toca.

Pero en la reunión del 19-sep Javier describió un negocio que el panel no
muestra:

| Lo que dijo Javier | Lo que tiene el demo hoy |
|---|---|
| «Vinos, licores, **cervezas** y complementarios» | ✓ el catálogo ya los trae |
| Operación en Bogotá **y Medellín** | ✗ **solo Bogotá** |
| Canales: e-commerce, membresías, **empresas, restaurantes, bares, discotecas, clubes sociales** | ✗ los cuatro de on-premise **no existen** |
| «**El B2B es el peso actual**; el B2C es un espacio de experimentación» | ✗ el demo es 76% B2C |

**Las dos cosas son ciertas a la vez.** KYVA de cara al público es la tienda
online; la empresa que Javier dirige además distribuye a establecimientos —son
distribuidores exclusivos de Mil Demonios, Ron Defensor y Marcel Thorel—. Lo que
falta no es corregir el modelo: es **añadir la capa que Javier dice que pesa**.

Por eso el canal de distribución crece con fuerza en los meses recientes en vez
de reescribir el histórico. Es honesto —Medellín es nuevo, el empuje a B2B es
reciente— y no destruye nada investigado.

## Qué se construye

### La capa de datos (`data/gen_b2b.py`)

Todo derivado del catálogo y de las ventas que ya existen, nunca en paralelo.

| Tabla | Para qué |
|---|---|
| `cuentas.csv` | Los establecimientos: tipo, ciudad, zona, cupo de crédito, vendedor, frecuencia de visita |
| `ventas_cuenta_mes.csv` | Qué compró cada cuenta, mes a mes |
| `vendedores.csv` | El equipo comercial de las dos ciudades |
| `entregas.csv` | Cada entrega con su ruta, costo y peso |
| `hilos.csv` | Las conversaciones del equipo sobre los números |
| `decisiones.csv` | La bandeja: lo que espera que alguien decida |

### Los módulos

| # | Módulo | Por qué un gerente lo abre |
|---|---|---|
| **20** | **Centro de decisiones** | La bandeja de lo que hay que aprobar hoy. Es lo que convierte el panel de lectura en operación |
| **21** | **Rentabilidad por cuenta** | El punto ciego #1 de un distribuidor: sabe cuánto le vende a cada bar, no cuánto le deja |
| **22** | **Hilos del equipo** | Discutir un número donde está el número, no en un WhatsApp aparte |
| **23** | **Equipo comercial** | Margen por vendedor, no venta. Y qué comisión sale de ahí |
| **24** | **Rutas y costo de entrega** | Cuánto cuesta cada entrega y qué zonas pierden plata |
| **25** | **Simulador** | Mover una palanca y ver el efecto antes de tomarla |
| **15↑** | **Agente que ejecuta** | Que arme un pedido de verdad, no que lo explique |

## Las reglas que no se rompen

1. **Consistencia por construcción.** Nada se genera en paralelo a algo que ya
   existe. Si dos pantallas pueden contradecirse, el dato se calcula en un solo
   sitio y las dos lo leen.
2. **Nada que mueva plata se ejecuta solo.** El sistema prepara, un humano
   confirma. Es lo que permite que un director de operaciones diga que sí.
3. **Las fallas se muestran.** Javier preguntó por el nivel de error. Un panel
   con 100% de acierto contesta esa pregunta con una mentira.
4. **Se prueba entrando a la pantalla**, no leyendo el menú. El 19-sep di por
   desplegado algo que estaba caído porque verifiqué la señal fácil.
5. **La marca sale de los archivos**, no del ojo: navy `#0E113A`, coral
   `#CE6264`, pálido `#E5E1E6`, y el SVG real del sitio.

## Bitácora

Se anota al terminar cada bloque, con lo que costó y lo que se aprendió.

### 2026-09-19 · Arranque
Rama creada. Reconocido el modelo de datos completo (19 módulos, 4.500 líneas,
21 tablas). Detectado el hueco de on-premise y de Medellín. Plan escrito.
