// Chat tipo WhatsApp + gráficos de emociones.
// Habla con el servidor Python (servidor.py) por /api/mensaje y pinta lo que devuelve.

const $ = (id) => document.getElementById(id);
const chat = $("chat"), entrada = $("entrada"), enviar = $("enviar"), tooltip = $("tooltip");
let ultimo = null;   // últimos datos recibidos (para repintar al cambiar el tamaño)

// ---------------------------------------------------------------- utilidades
const escapar = (t) => t.replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const hora = () => new Date().toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

function mostrarTooltip(html, x, y) {
  tooltip.innerHTML = html;
  tooltip.hidden = false;
  const r = tooltip.getBoundingClientRect();
  tooltip.style.left = Math.min(x + 12, innerWidth - r.width - 8) + "px";
  tooltip.style.top = Math.max(8, y - r.height - 12) + "px";
}
const ocultarTooltip = () => { tooltip.hidden = true; };

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

// Detalle del análisis dentro de la burbuja (botón "ⓘ análisis")
function detalle(d) {
  const a = d.analisis;
  const filas = [
    `<div><b>${a.dominante.icono} ${a.dominante.nombre}</b>${a.por_contexto ? " (por el contexto)" : ""}
       · ${escapar(a.estado)}</div>`,
  ];
  if (a.senales.length)
    filas.push(`<div><b>Cómo lo dices:</b> ${a.senales.map((s) => escapar(s.nombre)).join(", ")}</div>`);
  if (a.distorsiones.length)
    filas.push(`<div><b>Pensamientos:</b> ${a.distorsiones
      .map((x) => `${escapar(x.nombre)} («${escapar(x.evidencia)}»)`).join(", ")}</div>`);
  filas.push(`<div>Análisis: ${escapar(a.fuente)} · Respuesta: ${escapar(d.respuesta_de)}</div>`);
  return `<div class="info" hidden>${filas.join("")}</div>`;
}

function respuestaDelSistema(d) {
  const extra = detalle(d);
  const b = burbuja(d.respuesta, "otro", extra);
  if (d.analisis.riesgo === "alto") b.classList.add("riesgo");
  const meta = b.querySelector(".meta");
  const boton = document.createElement("button");
  boton.className = "info-boton";
  boton.type = "button";
  boton.textContent = "ⓘ análisis";
  boton.onclick = () => { const i = b.querySelector(".info"); i.hidden = !i.hidden; };
  meta.prepend(boton);
}

// ---------------------------------------------------------------- envío
async function mandar(texto) {
  burbuja(texto, "yo");
  entrada.value = "";
  enviar.disabled = true;
  escribiendo(true);
  try {
    const r = await fetch("/api/mensaje", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto }),
    });
    const d = await r.json();
    escribiendo(false);
    if (!r.ok) throw new Error(d.error || r.statusText);
    respuestaDelSistema(d);
    ultimo = d;
    pintarPanel(d);
  } catch (e) {
    escribiendo(false);
    burbuja("⚠ No he podido conectar con el servidor. ¿Sigue abierto servidor.py?", "otro");
  } finally {
    enviar.disabled = false;
    entrada.focus();
  }
}

$("formulario").addEventListener("submit", (e) => {
  e.preventDefault();
  const t = entrada.value.trim();
  if (t && !enviar.disabled) mandar(t);
});

$("reiniciar").addEventListener("click", async () => {
  await fetch("/api/reiniciar", { method: "POST" });
  chat.innerHTML = "";
  ultimo = null;
  pintarPanel(null);
  saludo();
});

function saludo() { burbuja("¡Hola! Cuéntame qué tal estás 🙂", "otro"); }

// ---------------------------------------------------------------- panel
function pintarPanel(d) {
  pintarAhora(d);
  pintarTono(d ? d.conversacion.tono : []);
  pintarAcumulado(d ? d.conversacion.acumulado : []);
}

// 1) Tarjeta "Ahora": emoción del último mensaje + medidor de intensidad
function pintarAhora(d) {
  const caja = $("ahora");
  if (!d) { caja.className = "ahora vacio"; caja.textContent = "Escribe un mensaje para empezar"; return; }
  const a = d.analisis;
  const niveles = { nula: 0, baja: 1, media: 2, alta: 3 };
  const n = niveles[a.intensidad] ?? 0;
  const pista = [1, 2, 3].map((i) => `<span class="${i <= n ? "lleno" : ""}"></span>`).join("");
  const alerta = a.riesgo === "alto"
    ? `<div class="alerta">⚠ Riesgo: ${escapar(a.recursos[0] || "llama al 024")}</div>`
    : a.riesgo === "moderado" ? `<div class="alerta">⚠ Desesperanza · 024</div>` : "";
  caja.className = "ahora";
  caja.innerHTML = `
    <div class="ahora-emocion">
      <span class="ahora-icono" aria-hidden="true">${a.dominante.icono}</span>
      <span class="ahora-nombre">${escapar(a.dominante.nombre)}</span>
    </div>
    <div class="ahora-detalle">${escapar(a.estado)}${a.por_contexto ? " · por el contexto" : ""}</div>
    <div class="medidor">
      <div class="medidor-etiqueta"><span>Intensidad</span><span>${escapar(a.intensidad)}</span></div>
      <div class="medidor-pista">${pista}</div>
    </div>${alerta}`;
}

// 2) Línea: valencia de cada mensaje (-1 desagradable ... +1 agradable)
function pintarTono(puntos) {
  const caja = $("grafico-tono");
  if (!puntos.length) {
    caja.innerHTML = '<div class="vacio-grafico">Aquí verás cómo cambia el tono, mensaje a mensaje</div>';
    return;
  }
  const W = caja.clientWidth, H = caja.clientHeight;
  const m = { izq: 78, der: 14, arr: 10, aba: 22 };
  const ancho = W - m.izq - m.der, alto = H - m.arr - m.aba;
  const n = puntos.length;
  const x = (i) => m.izq + (n === 1 ? ancho / 2 : (i / (n - 1)) * ancho);
  const y = (v) => m.arr + ((1 - v) / 2) * alto;

  const ns = "http://www.w3.org/2000/svg";
  let s = `<svg xmlns="${ns}" width="${W}" height="${H}">`;
  // rejilla y eje de cero (recesivos)
  for (const [v, t] of [[1, "agradable"], [0, "neutro"], [-1, "desagradable"]]) {
    s += `<line x1="${m.izq}" x2="${W - m.der}" y1="${y(v)}" y2="${y(v)}"
            stroke="${v === 0 ? css("--eje") : css("--rejilla")}" stroke-width="1"/>`;
    s += `<text x="${m.izq - 8}" y="${y(v) + 4}" text-anchor="end">${t}</text>`;
  }
  s += `<text x="${m.izq}" y="${H - 4}">mensaje 1</text>`;
  if (n > 1) s += `<text x="${W - m.der}" y="${H - 4}" text-anchor="end">mensaje ${n}</text>`;
  // línea
  if (n > 1) {
    const d = puntos.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p.valencia)}`).join(" ");
    s += `<path d="${d}" fill="none" stroke="${css("--serie")}" stroke-width="2"
            stroke-linejoin="round" stroke-linecap="round"/>`;
  }
  // puntos (8px, con anillo del color de la superficie) + icono en el último
  puntos.forEach((p, i) => {
    s += `<circle cx="${x(i)}" cy="${y(p.valencia)}" r="4.5" fill="${css("--serie")}"
            stroke="${css("--superficie")}" stroke-width="2"/>`;
  });
  const u = puntos[n - 1];
  s += `<text x="${x(n - 1)}" y="${y(u.valencia) - 10}" text-anchor="middle"
          style="font-size:16px">${u.icono}</text>`;
  // capa invisible para el hover: cruz + tooltip
  s += `<line id="cruz" y1="${m.arr}" y2="${H - m.aba}" stroke="${css("--eje")}" stroke-width="1" visibility="hidden"/>`;
  s += `<rect id="zona" x="${m.izq - 10}" y="0" width="${ancho + 20}" height="${H}" fill="transparent"/>`;
  s += "</svg>";
  caja.innerHTML = s;

  const zona = caja.querySelector("#zona"), cruz = caja.querySelector("#cruz");
  zona.addEventListener("mousemove", (ev) => {
    const r = caja.getBoundingClientRect();
    const px = ev.clientX - r.left;
    const i = n === 1 ? 0 : Math.max(0, Math.min(n - 1, Math.round(((px - m.izq) / ancho) * (n - 1))));
    const p = puntos[i];
    cruz.setAttribute("x1", x(i)); cruz.setAttribute("x2", x(i)); cruz.setAttribute("visibility", "visible");
    const signo = p.valencia > 0 ? "+" : "";
    mostrarTooltip(`<b>Mensaje ${i + 1}</b> · ${p.icono} ${escapar(p.emocion)}<br>
      Tono: ${signo}${p.valencia.toFixed(2)}<br><span style="color:var(--tinta-2)">«${escapar(p.texto)}»</span>`,
      ev.clientX, ev.clientY);
  });
  zona.addEventListener("mouseleave", () => { cruz.setAttribute("visibility", "hidden"); ocultarTooltip(); });
}

// 3) Barras horizontales ordenadas: emociones acumuladas en la conversación
function pintarAcumulado(lista) {
  const caja = $("grafico-acumulado");
  if (!lista.length) {
    caja.innerHTML = '<div class="vacio-grafico">Todavía no hay emociones</div>';
    return;
  }
  const max = Math.max(...lista.map((e) => e.pct));
  caja.innerHTML = lista.map((e) => `
    <div class="barra-fila" data-tip="${e.icono} ${escapar(e.nombre)}: ${e.pct.toFixed(0)} % de la conversación">
      <span class="barra-nombre">${e.icono} ${escapar(e.nombre)}</span>
      <span class="barra-pista"><span class="barra-valor" style="display:block;width:${(e.pct / max) * 100}%"></span></span>
      <span class="barra-pct">${e.pct.toFixed(0)} %</span>
    </div>`).join("");
  caja.querySelectorAll(".barra-fila").forEach((f) => {
    f.addEventListener("mousemove", (ev) => mostrarTooltip(f.dataset.tip, ev.clientX, ev.clientY));
    f.addEventListener("mouseleave", ocultarTooltip);
  });
}

addEventListener("resize", () => pintarTono(ultimo ? ultimo.conversacion.tono : []));
pintarPanel(null);
saludo();
entrada.focus();
