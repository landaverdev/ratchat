/* Lógica del juego: conexión con el servidor, movimiento, chat, advertencias y baneo. */
(function () {
  "use strict";

  const E = window.Escena;
  const $ = (id) => document.getElementById(id);
  const ui = {
    lienzo: $("escena"),
    entrada: $("pantalla-entrada"),
    formEntrada: $("form-entrada"),
    nombre: $("campo-nombre"),
    errorEntrada: $("error-entrada"),
    botonEntrar: $("boton-entrar"),
    estado: $("estado-conexion"),
    hud: $("hud"),
    conectados: $("conectados"),
    cristales: $("cristales"),
    panelChat: $("panel-chat"),
    botonHistorial: $("boton-historial"),
    lista: $("lista-chat"),
    formChat: $("form-chat"),
    campoChat: $("campo-chat"),
    aviso: $("aviso"),
    modalAdv: $("modal-advertencia"),
    advTitulo: $("adv-titulo"),
    advTexto: $("adv-texto"),
    advContador: $("adv-contador"),
    notaChat: $("nota-chat"),
    cerrarAdv: $("cerrar-advertencia"),
    modalBan: $("modal-baneo"),
    banTexto: $("ban-texto"),
    otroUsuario: $("otro-usuario"),
  };

  /* ---------------- Estado ---------------- */
  const estado = {
    ws: null,
    enJuego: false,
    baneado: false,
    miId: null,
    mundo: { x_min: 40, x_max: 920, y_min: 255, y_max: 575 },
    maxAdv: 3,
    jugadores: new Map(),
    marcas: [],
    ping: null,
  };

  // Jugadores de adorno que se ven detrás de la pantalla de entrada
  const DEMO = [
    { id: "d1", nombre: "Queso", color: "#9aa3a8", x: 300, y: 430 },
    { id: "d2", nombre: "Ratatú", color: "#c9b39a", x: 600, y: 370 },
    { id: "d3", nombre: "Bigotes", color: "#b98fd9", x: 770, y: 540 },
  ];

  function nuevoJugador(p) {
    return { ...p, tx: p.x, ty: p.y, dir: 1, caminando: false, fase: Math.random() * 6, burbuja: null };
  }

  function ponerDemo() {
    estado.jugadores.clear();
    DEMO.forEach((p) => estado.jugadores.set(p.id, nuevoJugador(p)));
  }
  ponerDemo();

  /* ---------------- Dibujo ---------------- */
  const ctx = ui.lienzo.getContext("2d");
  let fondo = E.crearFondo();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => (fondo = E.crearFondo()));

  const vista = { escala: 1, offX: 0, offY: 0, ancho: 0, alto: 0, dpr: 1 };

  function ajustarTamano() {
    const w = ui.lienzo.clientWidth, h = ui.lienzo.clientHeight;
    if (!w || !h) return;
    vista.dpr = Math.min(window.devicePixelRatio || 1, 2);
    ui.lienzo.width = Math.round(w * vista.dpr);
    ui.lienzo.height = Math.round(h * vista.dpr);
    vista.ancho = w;
    vista.alto = h;
    // En pantallas angostas (celular vertical) la sala llena el alto y la cámara sigue al jugador
    vista.escala = w / h < 1.25 ? Math.min(h / E.ALTO, (w * 3) / E.ANCHO) : Math.min(w / E.ANCHO, h / E.ALTO);
    vista.offY = Math.max(0, (h - E.ALTO * vista.escala) / 2);
    actualizarCamara(true);
  }

  function actualizarCamara(inmediato) {
    const anchoMundo = E.ANCHO * vista.escala;
    let objetivo;
    if (anchoMundo <= vista.ancho) {
      objetivo = (vista.ancho - anchoMundo) / 2;
    } else {
      const yo = estado.jugadores.get(estado.miId);
      const centro = yo ? yo.x : E.ANCHO / 2;
      objetivo = Math.min(0, Math.max(vista.ancho - anchoMundo, vista.ancho / 2 - centro * vista.escala));
    }
    vista.offX = inmediato ? objetivo : vista.offX + (objetivo - vista.offX) * 0.12;
  }

  new ResizeObserver(ajustarTamano).observe(ui.lienzo);

  const VELOCIDAD = 170; // unidades del mundo por segundo
  let anterior = performance.now();

  function cuadro(ahoraMs) {
    const dt = Math.min(0.05, (ahoraMs - anterior) / 1000);
    anterior = ahoraMs;
    const t = ahoraMs / 1000;

    for (const j of estado.jugadores.values()) {
      const dx = j.tx - j.x, dy = j.ty - j.y;
      const dist = Math.hypot(dx, dy);
      j.caminando = dist > 1;
      if (j.caminando) {
        const paso = Math.min(dist, VELOCIDAD * dt);
        j.x += (dx / dist) * paso;
        j.y += (dy / dist) * paso;
        if (Math.abs(dx) > 2) j.dir = dx > 0 ? 1 : -1;
      }
    }
    actualizarCamara(false);

    ctx.setTransform(vista.dpr, 0, 0, vista.dpr, 0, 0);
    const g = ctx.createLinearGradient(0, 0, 0, vista.alto);
    g.addColorStop(0, "#38433e");
    g.addColorStop(0.42, "#47544d");
    g.addColorStop(0.42, "#8d968c");
    g.addColorStop(1, "#6b756c");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, vista.ancho, vista.alto);

    ctx.setTransform(vista.dpr * vista.escala, 0, 0, vista.dpr * vista.escala, vista.dpr * vista.offX, vista.dpr * vista.offY);
    ctx.drawImage(fondo, 0, 0, E.ANCHO, E.ALTO);
    E.dibujarAmbiente(ctx, t, dt);
    estado.marcas = estado.marcas.filter((m) => E.dibujarMarca(ctx, m, ahoraMs));

    const orden = [...estado.jugadores.values()].sort((a, b) => a.y - b.y);
    for (const j of orden) E.dibujarJugador(ctx, j, t, j.id === estado.miId);
    for (const j of orden) E.dibujarBurbuja(ctx, j, ahoraMs);

    requestAnimationFrame(cuadro);
  }
  requestAnimationFrame(cuadro);

  /* ---------------- Movimiento ---------------- */
  ui.lienzo.addEventListener("pointerdown", (ev) => {
    if (!estado.enJuego) return;
    const yo = estado.jugadores.get(estado.miId);
    if (!yo) return;
    const r = ui.lienzo.getBoundingClientRect();
    const m = estado.mundo;
    const x = Math.max(m.x_min, Math.min(m.x_max, (ev.clientX - r.left - vista.offX) / vista.escala));
    const y = Math.max(m.y_min, Math.min(m.y_max, (ev.clientY - r.top - vista.offY) / vista.escala));
    yo.tx = x;
    yo.ty = y;
    estado.marcas.push({ x, y, inicio: performance.now() });
    enviar({ tipo: "mover", x: Math.round(x), y: Math.round(y) });
  });

  /* ---------------- Conexión ---------------- */
  function urlServidor() {
    const base = (window.RATCHAT_CONFIG && window.RATCHAT_CONFIG.servidor || "").replace(/\/+$/, "");
    if (base) return base.replace(/^http/, "ws") + "/ws";
    const protocolo = location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocolo}//${location.host}/ws`;
  }

  /* Render (plan gratis) duerme el servidor: la primera visita tarda hasta ~1 minuto en despertarlo.
     Antes de abrir el WebSocket le preguntamos a /salud hasta que conteste. */
  const pausa = (ms) => new Promise((r) => setTimeout(r, ms));
  async function despertarServidor() {
    const base = (window.RATCHAT_CONFIG && window.RATCHAT_CONFIG.servidor || "").replace(/\/+$/, "");
    if (!base) return;
    for (let intento = 0; intento < 30; intento++) {
      const control = new AbortController();
      const corte = setTimeout(() => control.abort(), 8000);
      try {
        const r = await fetch(base + "/salud", { cache: "no-store", signal: control.signal });
        clearTimeout(corte);
        if (r.ok) return;
      } catch { clearTimeout(corte); }
      if (intento === 1) ui.estado.textContent = "El servidor está despertando, puede tardar hasta un minuto…";
      await pausa(3000);
    }
  }

  async function conectarConReintentos() {
    let ultimo;
    for (let intento = 0; intento < 4; intento++) {
      try { return await conectar(); } catch (e) { ultimo = e; await pausa(1500); }
    }
    throw ultimo;
  }

  function enviar(obj) {
    if (estado.ws && estado.ws.readyState === WebSocket.OPEN) estado.ws.send(JSON.stringify(obj));
  }

  function conectar() {
    return new Promise((resolver, rechazar) => {
      if (estado.ws && estado.ws.readyState === WebSocket.OPEN) return resolver();
      let ws;
      try {
        ws = new WebSocket(urlServidor());
      } catch (e) {
        return rechazar(e);
      }
      estado.ws = ws;
      let abierto = false;
      const lento = setTimeout(() => {
        ui.estado.textContent = "El servidor está despertando, puede tardar hasta un minuto…";
      }, 3000);

      ws.onopen = () => {
        abierto = true;
        clearTimeout(lento);
        clearInterval(estado.ping);
        estado.ping = setInterval(() => enviar({ tipo: "ping" }), 25000);
        resolver();
      };
      ws.onmessage = (ev) => {
        let datos;
        try { datos = JSON.parse(ev.data); } catch { return; }
        manejar(datos);
      };
      ws.onclose = () => {
        clearTimeout(lento);
        clearInterval(estado.ping);
        if (estado.ws === ws) estado.ws = null;
        if (!abierto) return rechazar(new Error("sin conexión"));
        if (estado.enJuego && !estado.baneado) {
          salirDelJuego();
          mostrarError("Se perdió la conexión con el servidor. Vuelve a entrar.");
        }
      };
    });
  }

  const TEXTOS_ADV = {
    groseria: ["Ahí no se permiten groserías", "Aunque sea en buena onda: censuramos las groserías en el chat de todos."],
    insulto: ["Ese mensaje tenía un insulto", "Lo censuramos en el chat de todos."],
    odio: ["Ese mensaje tenía palabras de odio", "No se permiten insultos discriminatorios. Lo censuramos en el chat de todos."],
    amenaza: ["Ese mensaje tenía una amenaza", "No se permiten amenazas ni violencia. Lo censuramos en el chat de todos."],
  };

  /* ---------------- Mensajes del servidor ---------------- */
  function manejar(d) {
    switch (d.tipo) {
      case "error_ingreso":
        mostrarError(d.mensaje);
        ui.botonEntrar.disabled = false;
        ui.estado.textContent = "";
        break;

      case "bienvenida":
        estado.miId = d.id;
        estado.mundo = d.mundo;
        estado.maxAdv = d.max_advertencias;
        if (d.vida_mensaje) ui.notaChat.textContent = `· se borra a los ${Math.round(d.vida_mensaje / 60)} min`;
        estado.enJuego = true;
        estado.baneado = false;
        estado.jugadores.clear();
        d.jugadores.forEach((p) => estado.jugadores.set(p.id, nuevoJugador(p)));
        ui.lista.innerHTML = "";
        d.historial.forEach((m) => agregarAlChat(m));
        pintarAdvertencias(0);
        contarConectados();
        ui.entrada.hidden = true;
        ui.hud.hidden = false;
        document.getElementById("app").classList.add("en-juego");
        ui.botonEntrar.disabled = false;
        ui.estado.textContent = "";
        actualizarCamara(true);
        requestAnimationFrame(ajustarTamano);
        break;

      case "entra":
        estado.jugadores.set(d.jugador.id, nuevoJugador(d.jugador));
        contarConectados();
        break;

      case "sale":
        estado.jugadores.delete(d.id);
        contarConectados();
        break;

      case "mover": {
        const j = estado.jugadores.get(d.id);
        if (j) { j.tx = d.x; j.ty = d.y; }
        break;
      }

      case "chat": {
        const j = estado.jugadores.get(d.id);
        if (j) j.burbuja = { texto: d.texto, censurado: d.censurado, hasta: performance.now() + 5000 + d.texto.length * 60 };
        agregarAlChat(d);
        break;
      }

      case "sistema":
        agregarAlChat(d);
        break;

      case "borrar":
        borrarMensajes(d.ids);
        break;

      case "advertencia": {
        pintarAdvertencias(d.numero);
        const t = TEXTOS_ADV[d.categoria] || TEXTOS_ADV.groseria;
        ui.advTitulo.textContent = t[0];
        ui.advTexto.textContent = t[1];
        ui.advContador.textContent = d.numero === d.maximo - 1
          ? `Advertencia ${d.numero} de ${d.maximo}. Una más y serás baneado.`
          : `Advertencia ${d.numero} de ${d.maximo}. A la ${d.maximo}.ª te banean.`;
        abrirModal(ui.modalAdv, ui.cerrarAdv);
        break;
      }

      case "baneado":
        estado.baneado = true;
        pintarAdvertencias(d.maximo);
        cerrarModal(ui.modalAdv);
        ui.banTexto.textContent = `Acumulaste ${d.maximo} advertencias por lenguaje inapropiado. El usuario "${d.nombre}" ya no puede entrar, pero puedes volver con otro nombre.`;
        abrirModal(ui.modalBan, ui.otroUsuario);
        break;

      case "aviso":
        mostrarAviso(d.mensaje);
        break;
    }
  }

  /* ---------------- Interfaz ---------------- */
  function contarConectados() {
    const n = estado.jugadores.size;
    ui.conectados.textContent = n === 1 ? "1 en la sala" : `${n} en la sala`;
  }

  function pintarAdvertencias(n) {
    [...ui.cristales.children].forEach((c, i) => c.classList.toggle("roto", i < n));
    ui.cristales.setAttribute("aria-label", `${n} de ${estado.maxAdv} advertencias`);
  }

  function agregarAlChat(m) {
    const li = document.createElement("li");
    if (m.mid) li.dataset.mid = m.mid;
    if (m.tipo === "sistema") {
      li.className = "sistema";
      li.textContent = m.texto;
    } else {
      if (m.censurado) li.className = "censurado";
      const quien = document.createElement("span");
      quien.className = "quien";
      quien.style.setProperty("--color", m.color);
      quien.textContent = m.nombre + ": ";
      const texto = document.createElement("span");
      texto.className = "texto";
      texto.textContent = m.texto;
      li.append(quien, texto);
      if (m.censurado) {
        const marca = document.createElement("span");
        marca.className = "marca";
        marca.textContent = "censurado";
        li.append(marca);
      }
    }
    ui.lista.append(li);
    while (ui.lista.children.length > 80) ui.lista.firstChild.remove();
    ui.lista.scrollTop = ui.lista.scrollHeight;
  }

  /* Los mensajes viejos se borran en el servidor: aquí se quitan del chat, del más antiguo al más nuevo. */
  function borrarMensajes(ids) {
    ids.forEach((mid, k) => {
      const li = ui.lista.querySelector(`[data-mid="${mid}"]`);
      if (!li) return;
      setTimeout(() => {
        li.classList.add("se-va");
        setTimeout(() => li.remove(), 350);
      }, k * 120);
    });
  }

  let ultimoFoco = null;
  function abrirModal(modal, boton) {
    ultimoFoco = document.activeElement;
    modal.hidden = false;
    boton.focus();
  }
  function cerrarModal(modal) {
    modal.hidden = true;
    if (ultimoFoco && document.body.contains(ultimoFoco) && !ui.hud.hidden) ultimoFoco.focus({ preventScroll: true });
  }

  let temporizadorAviso;
  function mostrarAviso(texto) {
    ui.aviso.textContent = texto;
    ui.aviso.hidden = false;
    clearTimeout(temporizadorAviso);
    temporizadorAviso = setTimeout(() => (ui.aviso.hidden = true), 2000);
  }

  function mostrarError(texto) {
    ui.errorEntrada.textContent = texto;
    ui.errorEntrada.hidden = false;
  }

  function salirDelJuego() {
    estado.enJuego = false;
    estado.miId = null;
    ui.hud.hidden = true;
    document.getElementById("app").classList.remove("en-juego");
    cerrarModal(ui.modalAdv);
    ui.modalBan.hidden = true;
    ui.entrada.hidden = false;
    ui.botonEntrar.disabled = false;
    ponerDemo();
    requestAnimationFrame(ajustarTamano);
  }

  /* ---------------- Eventos ---------------- */
  ui.formEntrada.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const nombre = ui.nombre.value.trim();
    ui.errorEntrada.hidden = true;
    if (nombre.length < 2) return mostrarError("Escribe un nombre de al menos 2 letras.");
    ui.botonEntrar.disabled = true;
    ui.estado.textContent = "Conectando…";
    try {
      await despertarServidor();
      ui.estado.textContent = "Conectando…";
      await conectarConReintentos();
      enviar({ tipo: "entrar", nombre });
    } catch {
      ui.botonEntrar.disabled = false;
      ui.estado.textContent = "";
      mostrarError("No se pudo conectar con el servidor. Revisa tu internet y que el servidor de Render esté activo, e intenta de nuevo.");
    }
  });

  ui.formChat.addEventListener("submit", (ev) => {
    ev.preventDefault();
    const texto = ui.campoChat.value.trim();
    if (!texto) return;
    enviar({ tipo: "chat", texto });
    ui.campoChat.value = "";
  });

  ui.cerrarAdv.addEventListener("click", () => cerrarModal(ui.modalAdv));
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && !ui.modalAdv.hidden) cerrarModal(ui.modalAdv);
  });

  ui.otroUsuario.addEventListener("click", () => {
    estado.baneado = false;
    if (estado.ws) estado.ws.close();
    salirDelJuego();
    ui.nombre.value = "";
    ui.errorEntrada.hidden = true;
    ui.nombre.focus();
  });

  ui.botonHistorial.addEventListener("click", () => {
    const abierto = ui.panelChat.classList.toggle("abierto");
    ui.botonHistorial.setAttribute("aria-expanded", String(abierto));
    ui.lista.scrollTop = ui.lista.scrollHeight;
  });
})();
