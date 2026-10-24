/**
 * Interfaz de PDF Local: cuadrícula de herramientas, panel de subida y descarga del resultado.
 * Cada clave de TOOLS debe coincidir con una entrada del registro en tools/__init__.py.
 */

const PDF_ACCEPT = "application/pdf";
const OFFICE_ACCEPT = ".doc,.docx,.xls,.xlsx,.ppt,.pptx,.odt,.ods,.odp,.rtf,.txt";

// Opción: [nombre del campo, etiqueta, valor por defecto | lista de valores, tipo de input]
const TOOLS = {
  merge: {name: "Unir PDF", desc: "Combina varios PDF en uno", multi: true},
  split: {name: "Dividir PDF", desc: "Separa por rangos", pages: "split", opts: [["ranges", "", "", "hidden"]]},
  compress: {name: "Comprimir PDF", desc: "Reduce el tamaño", pages: "view", opts: [["level", "Compresión", ["media", "baja", "alta"]]]},
  rotate: {name: "Rotar PDF", desc: "Gira páginas", pages: "rotate", opts: [["angle", "Ángulo", ["90", "180", "270"]], ["pages", "", "", "hidden"]]},
  organize: {name: "Organizar páginas", desc: "Reordena o elimina", pages: "organize", opts: [["order", "", "", "hidden"]]},
  pdf_to_img: {name: "PDF a imagen", desc: "Cada página a JPG/PNG", pages: "view", opts: [["fmt", "Formato", ["jpg", "png"]], ["dpi", "DPI", ["150", "300", "72"]]]},
  pdf_to_word: {name: "PDF a Word", desc: "PDF a DOCX editable", pages: "view"},
  pdf_to_excel: {name: "PDF a Excel", desc: "Tablas del PDF a XLSX", pages: "view"},
  pdf_to_ppt: {name: "PDF a PowerPoint", desc: "Una diapositiva por página", pages: "view"},
  img_to_pdf: {name: "Imagen a PDF", desc: "JPG/PNG a PDF", multi: true, accept: "image/*"},
  protect: {name: "Proteger PDF", desc: "Añade contraseña AES-256", pages: "view", opts: [["password", "Contraseña", "", "password"]]},
  unlock: {name: "Desbloquear PDF", desc: "Quita contraseña", opts: [["password", "Contraseña actual", "", "password"]]},
  watermark: {name: "Marca de agua", desc: "Texto diagonal", pages: "view", opts: [["text", "Texto", "CONFIDENCIAL"], ["opacity", "Opacidad (0-1)", "0.25"]]},
  page_numbers: {name: "Numerar páginas", desc: "Pie de página", pages: "view", opts: [["fmt", "Formato ({n}, {total})", "{n} / {total}"]]},
  ocr: {name: "OCR", desc: "Hace buscable un PDF escaneado", pages: "view", opts: [["lang", "Idioma", ["spa", "eng", "spa+eng"]]]},
  office_to_pdf: {name: "Office a PDF", desc: "Word/Excel/PPT a PDF", accept: OFFICE_ACCEPT},
};

/** Atajo para document.getElementById. */
const $ = id => document.getElementById(id);
/** Herramienta abierta y archivos elegidos por el usuario. */
const state = {tool: null, files: [], pages: [], cuts: new Set()};
/** Portada en miniatura de cada archivo de la lista (se calcula una sola vez). */
const fileThumbs = new WeakMap();
/** Ancho en px de las miniaturas generadas en el navegador (imágenes). */
const THUMB_WIDTH = 140;
/** Contador para descartar respuestas de vistas previas ya sustituidas por otro archivo. */
let previewRequest = 0;

/** Instrucciones bajo la cuadrícula de miniaturas según el modo de páginas. */
const PAGE_HINTS = {
  organize: "Arrastra las páginas para reordenarlas. ✕ elimina o restaura una página.",
  rotate: "Haz clic en las páginas a girar. Sin selección se giran todas.",
  split: "Haz clic en la línea entre dos páginas para cortar ahí. Sin cortes = una página por archivo.",
  view: "Vista previa del documento.",
};

/** Botones rápidos sobre las miniaturas: [texto, acción] por modo. */
const PAGE_ACTIONS = {
  organize: [
    ["Restaurar orden", () => state.pages.sort((a, b) => a.n - b.n).forEach(p => { p.removed = false; })],
    ["Invertir orden", () => state.pages.reverse()],
  ],
  rotate: [
    ["Seleccionar todas", () => state.pages.forEach(p => { p.selected = true; })],
    ["Quitar selección", () => state.pages.forEach(p => { p.selected = false; })],
  ],
  split: [
    ["Cortar en cada página", () => { state.cuts = new Set(state.pages.slice(0, -1).map((_, i) => i)); }],
    ["Quitar cortes", () => state.cuts.clear()],
  ],
  view: [],
};

/** Escapa texto antes de insertarlo en innerHTML. */
function escapeHtml(text) {
  return String(text).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
}

/** Muestra un aviso de estado o error bajo el botón Procesar. */
function showMessage(text) {
  $("msg").textContent = text;
}

/**
 * Pinta una tarjeta por herramienta; las no disponibles quedan desactivadas.
 * @param {Object<string, boolean>} availability Respuesta de /api/tools.
 */
function renderGrid(availability) {
  for (const [key, tool] of Object.entries(TOOLS)) {
    const card = document.createElement("div");
    card.className = "tool" + (availability[key] ? "" : " off");
    card.innerHTML = `<b>${tool.name}</b><small>${tool.desc}</small>`;
    if (availability[key]) card.onclick = () => openTool(key);
    $("grid").append(card);
  }
}

/**
 * HTML de un campo de opción: select si el valor por defecto es una lista, input si no.
 * @param {Array} option [nombre, etiqueta, valorPorDefecto, tipo]
 */
function renderOption([name, label, defaultValue, type = "text"]) {
  if (type === "hidden") return `<input name="${name}" type="hidden">`;
  const field = Array.isArray(defaultValue)
    ? `<select name="${name}">${defaultValue.map(v => `<option>${escapeHtml(v)}</option>`).join("")}</select>`
    : `<input name="${name}" value="${escapeHtml(defaultValue)}" type="${type}">`;
  return `<label>${label}</label>${field}`;
}

/**
 * Hace reordenables con el ratón los hijos de container (HTML5 drag & drop).
 * @param {HTMLElement} container Cada hijo representa items[i] en el mismo orden.
 * @param {Array} items Lista que se reordena in situ.
 * @param {Function} onChange Se llama tras cada movimiento para repintar.
 */
function makeSortable(container, items, onChange) {
  [...container.children].forEach((el, index) => {
    el.draggable = true;
    el.ondragstart = e => { e.dataTransfer.setData("text/plain", index); el.classList.add("dragging"); };
    el.ondragend = () => el.classList.remove("dragging");
    el.ondragover = e => { e.preventDefault(); el.classList.add("target"); };
    el.ondragleave = () => el.classList.remove("target");
    el.ondrop = e => {
      const from = e.dataTransfer.getData("text/plain");
      if (from === "") return;
      e.preventDefault();
      e.stopPropagation();
      items.splice(index, 0, ...items.splice(Number(from), 1));
      onChange();
    };
  });
}

/**
 * Tarjeta de miniatura con imagen y pie. La imagen se carga en diferido (solo al
 * acercarse a la pantalla) y ratio reserva su hueco para que la cuadrícula no salte.
 */
function thumbCard(src, caption, ratio) {
  const card = document.createElement("div");
  card.className = "thumb";
  const style = ratio ? ` style="aspect-ratio:1/${ratio}"` : "";
  card.innerHTML = `<img alt="" loading="lazy" decoding="async"${style} ${src ? `src="${src}"` : ""}><span>${escapeHtml(caption)}</span>`;
  return card;
}

/** Botón ✕ de una tarjeta; no propaga el clic a la tarjeta. */
function removeButton(onClick) {
  const button = Object.assign(document.createElement("b"), {className: "x", textContent: "✕", title: "Quitar"});
  button.onclick = e => { e.stopPropagation(); onClick(); };
  return button;
}

/**
 * Registra un PDF en /api/preview.
 * @returns {Promise<{id: string, ratios: number[]}>}
 */
async function uploadPreview(file) {
  const form = new FormData();
  form.append("files", file);
  const response = await fetch("/api/preview", {method: "POST", body: form});
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error || response.status);
  return body;
}

/** URL de la miniatura de la página n (base 1) de una vista previa. */
const previewUrl = (id, n) => `/api/preview/${id}/${n}`;

/**
 * Miniatura reducida de una imagen: evita que el navegador mantenga decodificada
 * una foto de varios megapíxeles solo para pintarla a 140 px.
 */
async function imageThumb(file) {
  try {
    const bitmap = await createImageBitmap(file, {resizeWidth: THUMB_WIDTH, resizeQuality: "medium"});
    const canvas = Object.assign(document.createElement("canvas"), {width: bitmap.width, height: bitmap.height});
    canvas.getContext("2d").drawImage(bitmap, 0, 0);
    bitmap.close();
    return URL.createObjectURL(await new Promise(resolve => canvas.toBlob(resolve, "image/jpeg", 0.8)));
  } catch {
    return URL.createObjectURL(file);
  }
}

/** Portada de un archivo (se calcula una sola vez): reducida en el navegador o 1ª página del PDF. */
function fileThumb(file) {
  if (!fileThumbs.has(file)) {
    fileThumbs.set(file, file.type.startsWith("image/")
      ? imageThumb(file)
      : uploadPreview(file).then(({id}) => previewUrl(id, 1)));
  }
  return fileThumbs.get(file);
}

/** Refresca la lista de archivos; en herramientas multiarchivo es reordenable arrastrando. */
function renderFiles() {
  const list = $("list");
  const multi = TOOLS[state.tool].multi;
  list.className = multi ? "pages" : "";
  if (!multi) {
    list.replaceChildren(...state.files.map(f => Object.assign(document.createElement("li"), {textContent: f.name})));
    return showMessage("");
  }
  list.replaceChildren(...state.files.map((f, i) => {
    const card = thumbCard("", `${i + 1}. ${f.name}`);
    card.title = f.name;
    fileThumb(f).then(src => { if (src) card.querySelector("img").src = src; }).catch(() => {});
    card.append(removeButton(() => { state.files.splice(state.files.indexOf(f), 1); renderFiles(); }));
    return card;
  }));
  makeSortable(list, state.files, renderFiles);
  $("hint").textContent = state.files.length > 1 ? "Arrastra los archivos para cambiar el orden en que se unirán." : "";
  showMessage("");
}

/** Pide las miniaturas del PDF elegido y pinta la cuadrícula de páginas. */
async function loadPages() {
  Object.assign(state, {pages: [], cuts: new Set()});
  renderPages();
  const request = ++previewRequest;
  if (!TOOLS[state.tool].pages || !state.files.length) return;
  showMessage("Cargando vista previa…");
  const {id, ratios} = await uploadPreview(state.files[0]);
  if (request !== previewRequest) return;
  state.pages = ratios.map((ratio, i) => ({n: i + 1, src: previewUrl(id, i + 1), ratio, removed: false, selected: false}));
  showMessage("");
  renderPages();
}

/** Construye los nodos de cada página por modo de herramienta. */
const PAGE_RENDERERS = {
  organize(page) {
    const card = thumbCard(page.src, page.n, page.ratio);
    card.classList.toggle("del", page.removed);
    card.title = "Arrastra para mover";
    card.append(removeButton(() => { page.removed = !page.removed; renderPages(); }));
    return [card];
  },
  rotate(page) {
    const card = thumbCard(page.src, page.n, page.ratio);
    const anySelected = state.pages.some(p => p.selected);
    card.classList.toggle("sel", page.selected);
    const angle = Number($("opts").elements.angle.value);
    // A 90/270 la página queda apaisada: se reduce para que quepa en la tarjeta vertical.
    if (page.selected || !anySelected) card.querySelector("img").style.transform = `rotate(${angle}deg)${angle % 180 ? " scale(.75)" : ""}`;
    card.style.cursor = "pointer";
    card.title = page.selected ? "Clic para no girar" : "Clic para girar esta página";
    card.onclick = () => { page.selected = !page.selected; renderPages(); };
    return [card];
  },
  split(page, i) {
    const card = thumbCard(page.src, `${page.n} · Parte ${splitPartOf(i)}`, page.ratio);
    card.style.cursor = "default";
    card.dataset.part = splitPartOf(i) % 2;
    if (i === state.pages.length - 1) return [card];
    const gap = Object.assign(document.createElement("div"), {className: "gap", title: state.cuts.has(i) ? "Quitar corte" : "Cortar aquí"});
    gap.innerHTML = "<i>✂</i>";
    gap.classList.toggle("cut", state.cuts.has(i));
    gap.onclick = () => { state.cuts.has(i) ? state.cuts.delete(i) : state.cuts.add(i); renderPages(); };
    return [card, gap];
  },
  view(page) {
    const card = thumbCard(page.src, page.n, page.ratio);
    card.style.cursor = "default";
    return [card];
  },
};

/** Número de archivo de salida (1..n) al que irá la página i al dividir. */
function splitPartOf(i) {
  return state.cuts.size ? [...state.cuts].filter(c => c < i).length + 1 : i + 1;
}

/** Texto de resumen del estado actual de la selección. */
const PAGE_SUMMARY = {
  organize: () => `${state.pages.filter(p => !p.removed).length} de ${state.pages.length} páginas en el resultado`,
  rotate: () => { const n = state.pages.filter(p => p.selected).length; return n ? `${n} página(s) a girar` : "Se girarán todas las páginas"; },
  split: () => `Se crearán ${state.cuts.size ? state.cuts.size + 1 : state.pages.length} archivo(s)`,
  view: () => `${state.pages.length} página(s)`,
};

/** Campo oculto que espera el backend por modo y cómo calcularlo. */
const PAGE_FIELDS = {
  organize: ["order", () => state.pages.filter(p => !p.removed).map(p => p.n).join(",")],
  rotate: ["pages", () => state.pages.filter(p => p.selected).map(p => p.n).join(",")],
  split: ["ranges", splitRanges],
  view: null,
};

/** Convierte los cortes en grupos "1-3;4-6"; vacío si no hay cortes. */
function splitRanges() {
  if (!state.cuts.size) return "";
  const ends = [...state.cuts].sort((a, b) => a - b).map(i => i + 1).concat(state.pages.length);
  return ends.map((end, k) => `${k ? ends[k - 1] + 1 : 1}-${end}`).join(";");
}

/** Pinta las miniaturas según el modo de la herramienta y sincroniza su campo oculto. */
function renderPages() {
  const mode = TOOLS[state.tool].pages;
  const ready = Boolean(mode && state.pages.length);
  if (!TOOLS[state.tool].multi) $("hint").textContent = ready ? `${PAGE_HINTS[mode]} ${PAGE_SUMMARY[mode]()}.` : "";
  $("actions").replaceChildren(...(ready ? PAGE_ACTIONS[mode] : []).map(([label, action]) => {
    const button = Object.assign(document.createElement("button"), {type: "button", className: "chip", textContent: label});
    button.onclick = () => { action(); renderPages(); };
    return button;
  }));
  if (!mode) return $("pages").replaceChildren();
  $("pages").replaceChildren(...state.pages.flatMap((page, i) => PAGE_RENDERERS[mode](page, i)));
  if (mode === "organize") makeSortable($("pages"), state.pages, renderPages);
  if (!PAGE_FIELDS[mode]) return;
  const [name, compute] = PAGE_FIELDS[mode];
  $("opts").elements[name].value = compute();
}

/** Alterna entre la cuadrícula y el panel de una herramienta. */
function showPanel(visible) {
  $("panel").style.display = visible ? "block" : "none";
  $("grid").style.display = visible ? "none" : "";
}

/** Abre el panel de la herramienta key con sus opciones por defecto. */
function openTool(key) {
  const tool = TOOLS[key];
  Object.assign(state, {tool: key, files: []});
  $("title").textContent = tool.name;
  $("file").multiple = Boolean(tool.multi);
  $("file").accept = tool.accept || PDF_ACCEPT;
  $("opts").innerHTML = (tool.opts || []).map(renderOption).join("");
  $("opts").onchange = () => tool.pages === "rotate" && renderPages();
  renderFiles();
  loadPages();
  showPanel(true);
}

/** Añade archivos; las herramientas de un solo archivo sustituyen el anterior. */
function addFiles(fileList) {
  const incoming = [...fileList];
  state.files = TOOLS[state.tool].multi ? state.files.concat(incoming) : incoming.slice(0, 1);
  renderFiles();
  loadPages().catch(err => showMessage("Error: " + err.message));
}

/** Nombre de archivo enviado por el servidor en Content-Disposition. */
function downloadName(response) {
  const header = response.headers.get("Content-Disposition") || "";
  const star = header.match(/filename\*=UTF-8''([^;]+)/i);
  if (star) return decodeURIComponent(star[1]);
  const match = header.match(/filename="?([^";]+)/);
  return match ? match[1] : "resultado";
}

/**
 * Descarga la respuesta como archivo sin salir de la página.
 * @returns {Promise<string>} Nombre del archivo descargado.
 */
async function downloadBlob(response) {
  const link = Object.assign(document.createElement("a"), {
    href: URL.createObjectURL(await response.blob()),
    download: downloadName(response),
  });
  link.click();
  URL.revokeObjectURL(link.href);
  return link.download;
}

/** Envía archivos y opciones a /api/<herramienta> y gestiona la respuesta. */
async function processFiles() {
  if (!state.files.length) return showMessage("Agrega al menos un archivo.");
  if (TOOLS[state.tool].pages === "organize" && !$("opts").elements.order.value) return showMessage("No puedes eliminar todas las páginas.");
  const form = new FormData($("opts"));
  state.files.forEach(f => form.append("files", f));
  showMessage("Procesando…");
  $("go").disabled = true;
  const response = await fetch(`/api/${state.tool}`, {method: "POST", body: form}).finally(() => { $("go").disabled = false; });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    return showMessage("Error: " + (body.error || response.status));
  }
  showMessage("Listo: " + await downloadBlob(response));
}

/** Conecta clic, arrastrar y soltar con el selector de archivos. */
function bindDropZone() {
  const zone = $("drop");
  zone.onclick = () => $("file").click();
  zone.ondragover = e => { e.preventDefault(); zone.classList.add("over"); };
  zone.ondragleave = () => zone.classList.remove("over");
  zone.ondrop = e => { e.preventDefault(); zone.classList.remove("over"); addFiles(e.dataTransfer.files); };
  $("file").onchange = e => { addFiles(e.target.files); e.target.value = ""; };
}

bindDropZone();
$("back").onclick = () => showPanel(false);
$("go").onclick = () => processFiles().catch(err => showMessage("Error: " + err.message));
fetch("/api/tools").then(r => r.json()).then(renderGrid);
