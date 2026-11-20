// Chat tipo WhatsApp + gráficos de emociones.
// Habla con el servidor Python (servidor.py) por /api/mensaje y pinta lo que devuelve.

const $ = (id) => document.getElementById(id);
const chat = $("chat"), entrada = $("entrada"), enviar = $("enviar"), tooltip = $("tooltip");
let ultimo = null;          // últimos datos recibidos
let nombre = "";            // nombre que la persona ha elegido para el chat

// ---------------------------------------------------------------- utilidades
const escapar = (t) => String(t).replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const hora = () => new Date().toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const NS = "http://www.w3.org/2000/svg";
const svgEl = (tag, attrs = {}) => {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
};

function mostrarTooltip(html, x, y) {
  tooltip.innerHTML = html;
  tooltip.hidden = false;
  const r = tooltip.getBoundingClientRect();
  tooltip.style.left = Math.min(x + 12, innerWidth - r.width - 8) + "px";
  tooltip.style.top = Math.max(8, y - r.height - 12) + "px";
}
const ocultarTooltip = () => { tooltip.hidden = true; };

// ---------------------------------------------------------------- nombre del chat
const guardado = (() => { try { return localStorage.getItem("emociones.nombre") || ""; } catch { return ""; } })();

function ponerNombre(n) {
  nombre = n.trim().replace(/\s+/g, " ").slice(0, 30);
  $("nombre-chat").textContent = nombre;
  $("avatar").textContent = nombre.charAt(0) || "?";
  document.title = `${nombre} · Emotion Analysis`;
  try { localStorage.setItem("emociones.nombre", nombre); } catch { /* sin almacenamiento */ }
}

function pedirNombre() {
  $("capa-nombre").hidden = false;
  $("entrada-nombre").value = nombre;
  $("entrada-nombre").focus();
}

$("form-nombre").addEventListener("submit", (e) => {
  e.preventDefault();
  const n = $("entrada-nombre").value.trim();
  if (!n) return;
  const primeraVez = !nombre;
  ponerNombre(n);
  $("capa-nombre").hidden = true;
  if (primeraVez || !chat.children.length) saludo();
  entrada.focus();
});
$("cambiar-nombre").addEventListener("click", pedirNombre);

// ---------------------------------------------------------------- burbujas
function burbuja(texto, quien, extra = "") {
  const b = document.createElement("div");
  b.className = `burbuja ${quien}`;
  const check = quien === "yo" ? '<span class="check">✓✓</span>' : "";
  b.innerHTML = `<div>${escapar(texto)}</div>${extra}<div class="meta">${hora()}${check}</div>`;
  chat.appendChild(b);
  chat.scrollTop = chat.scrollHeight;
  return b;
}

function escribiendo(si) {
  $("estado-contacto").textContent = si ? "escribiendo…" : "en línea";
  const viejo = chat.querySelector(".escribiendo");
  if (viejo) viejo.remove();
  if (si) {
    const b = document.createElement("div");
    b.className = "burbuja otro escribiendo";
    b.innerHTML = "<span></span><span></span><span></span>";
    chat.appendChild(b);
    chat.scrollTop = chat.scrollHeight;
  }
}

// Detalle del análisis dentro de la burbuja (botón "análisis")
function detalle(d) {
  const a = d.analisis;
  const filas = [
    `<div><b>${escapar(a.dominante.nombre)}</b>${a.por_contexto ? " (por el contexto)" : ""}
       · ${escapar(a.estado)}</div>`,
  ];
  if (a.otras_personas.length)
    filas.push(`<div><b>Otras personas:</b> ${a.otras_personas
      .map((o) => `${escapar(o.quien)} (${escapar(o.emocion.toLowerCase())})`).join(", ")}</div>`);
  if (a.senales.length)
    filas.push(`<div><b>Cómo lo dices:</b> ${a.senales.map((s) => escapar(s.nombre)).join(", ")}</div>`);
  if (a.distorsiones.length)
    filas.push(`<div><b>Pensamientos:</b> ${a.distorsiones
      .map((x) => `${escapar(x.nombre)} («${escapar(x.evidencia)}»)`).join(", ")}</div>`);
  filas.push(`<div>Análisis: ${escapar(a.fuente)} · Respuesta: ${escapar(d.respuesta_de)}</div>`);
  return `<div class="info" hidden>${filas.join("")}</div>`;
}

function respuestaDelSistema(d) {
  const b = burbuja(d.respuesta, "otro", detalle(d));
  if (d.analisis.riesgo === "alto") b.classList.add("riesgo");
  const boton = document.createElement("button");
  boton.className = "info-boton";
  boton.type = "button";
  boton.textContent = "análisis";
  boton.onclick = () => { const i = b.querySelector(".info"); i.hidden = !i.hidden; };
  b.querySelector(".meta").prepend(boton);
}

function saludo() { burbuja(`¡Hola! Soy ${nombre}. Cuéntame qué tal estás.`, "otro"); }

// ---------------------------------------------------------------- envío
async function mandar(texto) {
  burbuja(texto, "yo");
  entrada.value = "";
  enviar.disabled = true;
  escribiendo(true);
  try {
    const r = await fetch("/api/mensaje", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto, nombre }),
    });
    const d = await r.json();
    escribiendo(false);
    if (!r.ok) throw new Error(d.error || r.statusText);
    respuestaDelSistema(d);
    ultimo = d;
    pintarAhora(d);
    avanzarTono(d.conversacion.tono);
    actualizarTarta(d.conversacion.acumulado);
  } catch (e) {
    escribiendo(false);
    burbuja("No he podido conectar con el servidor. ¿Sigue abierto servidor.py?", "otro");
  } finally {
    enviar.disabled = false;
    entrada.focus();
  }
}

$("formulario").addEventListener("submit", (e) => {
  e.preventDefault();
  const t = entrada.value.trim();
  if (t && !enviar.disabled && nombre) mandar(t);
});

$("reiniciar").addEventListener("click", async () => {
  await fetch("/api/reiniciar", { method: "POST" });
  chat.innerHTML = "";
  ultimo = null;
  pintarAhora(null);
  reiniciarTono();
  reiniciarTarta();
  saludo();
});

// ================================================================ 1) AHORA
const ICONO_ALERTA = `<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
  <path fill="currentColor" d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>`;

function pintarAhora(d) {
  const caja = $("ahora");
  if (!d) { caja.className = "ahora vacio"; caja.textContent = "Escribe un mensaje para empezar"; return; }
  const a = d.analisis;
  const n = { nula: 0, baja: 1, media: 2, alta: 3 }[a.intensidad] ?? 0;
  const pista = [1, 2, 3].map((i) => `<span class="${i <= n ? "lleno" : ""}"></span>`).join("");
  const alerta = a.riesgo === "alto"
    ? `<div class="alerta">${ICONO_ALERTA}Riesgo: llama al 024 (gratis, 24 h)</div>`
    : a.riesgo === "moderado" ? `<div class="alerta">${ICONO_ALERTA}Desesperanza: 024 si lo necesitas</div>` : "";
  // Emociones de OTRAS personas de las que habla: se muestran aparte, no son suyas
  const otras = a.otras_personas.length
    ? `<div class="otras"><span>Otras personas:</span> ${a.otras_personas
        .map((o) => `${escapar(o.quien)} (${escapar(o.emocion.toLowerCase())})`).join(", ")}</div>`
    : "";
  caja.className = "ahora";
  caja.innerHTML = `
    <div class="ahora-nombre">${escapar(a.dominante.nombre)}</div>
    <div class="ahora-detalle">${escapar(a.estado)}${a.por_contexto ? " · por el contexto" : ""}</div>
    <div class="medidor">
      <div class="medidor-etiqueta"><span>Intensidad</span><span>${escapar(a.intensidad)}</span></div>
      <div class="medidor-pista">${pista}</div>
    </div>${otras}${alerta}`;
}

// ================================================================ 2) TONO (línea que avanza)
// El marco (rejilla, etiquetas) se dibuja una vez. Cada mensaje AÑADE un tramo y un
// punto con animación; el eje va siempre de -1 a +1, así que nada se reescala.
// Cuando no caben más puntos, la serie se desliza hacia la izquierda.
const PASO = 56;                                    // píxeles entre mensajes
const M = { izq: 82, der: 14, arr: 12, aba: 22 };
const tono = { puntos: [], W: 0, H: 0, desplazamiento: 0 };

const xDe = (i) => M.izq + 16 + i * PASO;
const yDe = (v) => M.arr + ((1 - v) / 2) * (tono.H - M.arr - M.aba);

function marcoTono() {
  const caja = $("grafico-tono");
  tono.W = caja.clientWidth;
  tono.H = caja.clientHeight;
  const { W, H } = tono;
  const svg = svgEl("svg", { width: W, height: H });
  const defs = svgEl("defs");
  const clip = svgEl("clipPath", { id: "recorte" });
  clip.appendChild(svgEl("rect", { x: M.izq, y: 0, width: W - M.izq - M.der, height: H }));
  defs.appendChild(clip);
  svg.appendChild(defs);
  for (const [v, t] of [[1, "agradable"], [0, "neutro"], [-1, "desagradable"]]) {
    svg.appendChild(svgEl("line", { x1: M.izq, x2: W - M.der, y1: yDe(v), y2: yDe(v),
      stroke: v === 0 ? css("--eje") : css("--rejilla"), "stroke-width": 1 }));
    const etiqueta = svgEl("text", { x: M.izq - 8, y: yDe(v) + 4, "text-anchor": "end" });
    etiqueta.textContent = t;
    svg.appendChild(etiqueta);
  }
  const recorte = svgEl("g", { "clip-path": "url(#recorte)" });
  const serie = svgEl("g", { class: "serie", id: "serie" });
  serie.appendChild(svgEl("g", { id: "tramos" }));
  serie.appendChild(svgEl("g", { id: "puntos" }));
  serie.appendChild(svgEl("g", { id: "marcas" }));
  recorte.appendChild(serie);
  svg.appendChild(recorte);
  const cruz = svgEl("line", { id: "cruz", y1: M.arr, y2: H - M.aba, stroke: css("--eje"),
    "stroke-width": 1, visibility: "hidden" });
  svg.appendChild(cruz);
  const pista = svgEl("text", { id: "pista-tono", x: (M.izq + W) / 2, y: yDe(0.5) + 4, "text-anchor": "middle" });
  pista.textContent = "Aquí verás cómo cambia el tono, mensaje a mensaje";
  svg.appendChild(pista);
  const zona = svgEl("rect", { x: M.izq, y: 0, width: W - M.izq - M.der, height: H, fill: "transparent" });
  svg.appendChild(zona);
  caja.replaceChildren(svg);

  zona.addEventListener("mousemove", (ev) => {
    const n = tono.puntos.length;
    if (!n) return;
    const px = ev.clientX - caja.getBoundingClientRect().left + tono.desplazamiento;
    const i = Math.max(0, Math.min(n - 1, Math.round((px - M.izq - 16) / PASO)));
    const p = tono.puntos[i];
    const xv = xDe(i) - tono.desplazamiento;
    cruz.setAttribute("x1", xv); cruz.setAttribute("x2", xv); cruz.setAttribute("visibility", "visible");
    mostrarTooltip(`<b>Mensaje ${i + 1}</b> · ${escapar(p.emocion)}<br>
      Tono: ${p.valencia > 0 ? "+" : ""}${p.valencia.toFixed(2)}<br>
      <span style="color:var(--tinta-2)">«${escapar(p.texto)}»</span>`, ev.clientX, ev.clientY);
  });
  zona.addEventListener("mouseleave", () => { cruz.setAttribute("visibility", "hidden"); ocultarTooltip(); });
}

function anadirPunto(p, animar) {
  const svg = $("grafico-tono");
  const i = tono.puntos.length;
  tono.puntos.push(p);
  svg.querySelector("#pista-tono")?.remove();
  const x = xDe(i), y = yDe(p.valencia);
  if (i > 0) {                                       // tramo desde el punto anterior
    const xa = xDe(i - 1), ya = yDe(tono.puntos[i - 1].valencia);
    const largo = Math.hypot(x - xa, y - ya);
    const tramo = svgEl("path", { d: `M${xa},${ya} L${x},${y}`, fill: "none", stroke: css("--serie"),
      "stroke-width": 2, "stroke-linecap": "round", "stroke-dasharray": largo,
      "stroke-dashoffset": animar ? largo : 0, class: animar ? "tramo" : "" });
    svg.querySelector("#tramos").appendChild(tramo);
  }
  svg.querySelector("#puntos").appendChild(svgEl("circle", { cx: x, cy: y, r: 4.5,
    fill: css("--serie"), stroke: css("--superficie"), "stroke-width": 2,
    class: animar ? "punto-nuevo" : "" }));
  const marca = svgEl("text", { x, y: tono.H - 6, "text-anchor": "middle" });
  marca.textContent = i + 1;
  svg.querySelector("#marcas").appendChild(marca);
  // Si el nuevo punto no cabe, desplazamos toda la serie (con transición CSS)
  tono.desplazamiento = Math.max(0, x - (tono.W - M.der - 16));
  const serie = svg.querySelector("#serie");
  if (!animar) serie.style.transition = "none";
  serie.style.transform = `translateX(${-tono.desplazamiento}px)`;
  if (!animar) { serie.getBoundingClientRect(); serie.style.transition = ""; }
}

function avanzarTono(lista) {
  for (let i = tono.puntos.length; i < lista.length; i++) anadirPunto(lista[i], true);
}
function reiniciarTono() { tono.puntos = []; tono.desplazamiento = 0; marcoTono(); }

// ================================================================ 3) TARTA
// Cada emoción recibe un color la primera vez que aparece y lo conserva toda la
// conversación (el color sigue a la emoción, no a su posición). Hay 8 colores
// distinguibles: se muestran hasta 5 emociones y el resto va a "Otras" (máx. 6 porciones).
const tarta = { color: new Map(), libres: [1, 2, 3, 4, 5, 6, 7, 8], previo: new Map(), info: new Map() };

function partesTarta(lista) {
  const principales = lista.length > 6 ? lista.slice(0, 5) : lista.slice(0, 6);
  let otras = lista.slice(principales.length).reduce((s, e) => s + e.pct, 0);
  const partes = [];
  for (const e of principales) {
    if (!tarta.color.has(e.id)) {
      if (!tarta.libres.length) { otras += e.pct; continue; }   // sin colores libres: a "Otras"
      tarta.color.set(e.id, tarta.libres.shift());
    }
    partes.push({ clave: e.id, nombre: e.nombre, pct: e.pct, color: `var(--c${tarta.color.get(e.id)})` });
  }
  if (otras >= 0.5) partes.push({ clave: "otras", nombre: "Otras", pct: otras, color: "var(--otras)" });
  return partes;
}

function dibujarTarta(claves, fracciones) {
  const R = 56, C = 60;
  const svg = svgEl("svg", { width: 120, height: 120, viewBox: "0 0 120 120", role: "img",
    "aria-label": "Reparto de emociones en la conversación" });
  let angulo = -Math.PI / 2;                         // empieza arriba, sentido horario
  claves.forEach((clave, k) => {
    const f = fracciones[k];
    if (f < 0.002) return;
    const info = tarta.info.get(clave);
    const estilo = `fill:${info.color};stroke:var(--superficie);stroke-width:2`;
    let forma;
    if (f > 0.998) {
      forma = svgEl("circle", { cx: C, cy: C, r: R, style: estilo });
    } else {
      const a2 = angulo + f * 2 * Math.PI;
      const [x1, y1] = [C + R * Math.cos(angulo), C + R * Math.sin(angulo)];
      const [x2, y2] = [C + R * Math.cos(a2), C + R * Math.sin(a2)];
      forma = svgEl("path", { style: estilo,
        d: `M${C},${C} L${x1},${y1} A${R},${R} 0 ${f > 0.5 ? 1 : 0} 1 ${x2},${y2} Z` });
      angulo = a2;
    }
    forma.addEventListener("mousemove", (ev) =>
      mostrarTooltip(`<b>${escapar(info.nombre)}</b>: ${info.pct.toFixed(0)} % de la conversación`,
        ev.clientX, ev.clientY));
    forma.addEventListener("mouseleave", ocultarTooltip);
    svg.appendChild(forma);
  });
  return svg;
}

function actualizarTarta(lista) {
  const caja = $("grafico-tarta");
  if (!lista.length) return;
  const partes = partesTarta(lista);
  const total = partes.reduce((s, p) => s + p.pct, 0) || 1;
  const hasta = new Map(partes.map((p) => [p.clave, p.pct / total]));
  partes.forEach((p) => tarta.info.set(p.clave, p));
  // Claves: las nuevas en su orden + las que desaparecen (se encogen hasta 0)
  const claves = [...hasta.keys(), ...[...tarta.previo.keys()].filter((k) => !hasta.has(k))];
  const desde = tarta.previo;

  // Leyenda (siempre: nombre + porcentaje; la identidad nunca va solo por color)
  const leyenda = document.createElement("ul");
  leyenda.className = "leyenda";
  leyenda.innerHTML = partes.map((p) => `<li><span class="muestra" style="background:${p.color}"></span>
    <span class="nombre-l">${escapar(p.nombre)}</span><span class="pct">${p.pct.toFixed(0)} %</span></li>`).join("");

  let svgActual = caja.querySelector("svg");
  if (!svgActual) { caja.replaceChildren(); }
  caja.querySelector(".leyenda")?.remove();
  caja.querySelector(".vacio-grafico")?.remove();

  // Animación: de las fracciones anteriores a las nuevas en 500 ms
  const inicio = performance.now(), DUR = 500;
  const suave = (t) => 1 - Math.pow(1 - t, 3);
  function cuadro(ahora) {
    const k = suave(Math.min(1, (ahora - inicio) / DUR));
    const fr = claves.map((c) => (desde.get(c) || 0) * (1 - k) + (hasta.get(c) || 0) * k);
    const nuevo = dibujarTarta(claves, fr);
    const viejo = caja.querySelector("svg");
    viejo ? viejo.replaceWith(nuevo) : caja.prepend(nuevo);
    if (k < 1) requestAnimationFrame(cuadro);
  }
  requestAnimationFrame(cuadro);
  caja.appendChild(leyenda);
  tarta.previo = hasta;
}

function reiniciarTarta() {
  tarta.color.clear();
  tarta.libres = [1, 2, 3, 4, 5, 6, 7, 8];
  tarta.previo = new Map();
  tarta.info.clear();
  $("grafico-tarta").innerHTML = '<div class="vacio-grafico">Todavía no hay emociones</div>';
}

// ---------------------------------------------------------------- arranque
// El marco del tono se dibuja cuando el recuadro TIENE tamaño (al cargar puede medir 0)
// y se redibuja, sin animación, cada vez que cambia de tamaño.
let temporizador;
new ResizeObserver((entradas) => {
  const { width, height } = entradas[0].contentRect;
  if (!width || !height || (width === tono.W && height === tono.H)) return;
  clearTimeout(temporizador);
  temporizador = setTimeout(() => {
    const puntos = tono.puntos;
    reiniciarTono();
    puntos.forEach((p) => anadirPunto(p, false));
  }, 50);
}).observe($("grafico-tono"));

pintarAhora(null);
reiniciarTarta();
if (guardado) { ponerNombre(guardado); saludo(); entrada.focus(); }
else pedirNombre();
