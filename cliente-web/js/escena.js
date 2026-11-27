/* Dibujo de la alcantarilla y de las ratas (todo con código, sin imágenes). */
(function () {
  "use strict";

  const ANCHO = 960;
  const ALTO = 600;
  const LINEA = "#1c2422";
  const movimientoReducido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function redondeado(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  function mezclar(hex, otro, f) {
    const a = parseInt(hex.slice(1), 16), b = parseInt(otro.slice(1), 16);
    const c = (s) => Math.round(((a >> s) & 255) * (1 - f) + ((b >> s) & 255) * f);
    return `rgb(${c(16)},${c(8)},${c(0)})`;
  }

  /* ---------------- Fondo (se dibuja una sola vez) ---------------- */
  function ladrillos(ctx, x0, y0, x1, y1, alto, ancho, color, junta) {
    ctx.fillStyle = color;
    ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
    ctx.strokeStyle = junta;
    ctx.lineWidth = 2;
    let fila = 0;
    for (let y = y0; y < y1; y += alto, fila++) {
      ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke();
      for (let x = x0 + (fila % 2) * (ancho / 2); x < x1; x += ancho) {
        ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x, Math.min(y + alto, y1)); ctx.stroke();
      }
    }
  }

  function tubo(ctx, puntos, grosor, color) {
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();
    puntos.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
    ctx.strokeStyle = LINEA; ctx.lineWidth = grosor + 6; ctx.stroke();
    ctx.strokeStyle = color; ctx.lineWidth = grosor; ctx.stroke();
    ctx.strokeStyle = "rgba(255,255,255,0.25)"; ctx.lineWidth = grosor * 0.25;
    ctx.beginPath();
    puntos.forEach(([x, y], i) => (i ? ctx.lineTo(x - grosor * 0.2, y - grosor * 0.2) : ctx.moveTo(x - grosor * 0.2, y - grosor * 0.2)));
    ctx.stroke();
  }

  function caja(ctx, x, y) {
    // caja de madera con un queso encima
    redondeado(ctx, x - 46, y - 64, 92, 64, 6);
    ctx.fillStyle = "#a8743f"; ctx.fill();
    ctx.lineWidth = 3; ctx.strokeStyle = LINEA; ctx.stroke();
    ctx.strokeStyle = "#7d5228"; ctx.lineWidth = 3;
    for (const yy of [y - 43, y - 22]) { ctx.beginPath(); ctx.moveTo(x - 44, yy); ctx.lineTo(x + 44, yy); ctx.stroke(); }
    ctx.beginPath();
    ctx.moveTo(x - 30, y - 64); ctx.lineTo(x + 34, y - 64); ctx.lineTo(x + 34, y - 92); ctx.closePath();
    ctx.fillStyle = "#ffc94a"; ctx.fill();
    ctx.strokeStyle = LINEA; ctx.lineWidth = 3; ctx.stroke();
    ctx.fillStyle = "#e9a422";
    for (const [cx, cy, r] of [[x + 20, y - 72, 4], [x + 6, y - 68, 3], [x + 27, y - 82, 2.5]]) {
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fill();
    }
  }

  function lata(ctx, x, y) {
    // lata de sardinas usada como cama
    ctx.beginPath(); ctx.ellipse(x, y, 62, 22, 0, 0, Math.PI * 2);
    ctx.fillStyle = "#b7c2c8"; ctx.fill();
    ctx.lineWidth = 3; ctx.strokeStyle = LINEA; ctx.stroke();
    ctx.beginPath(); ctx.ellipse(x, y - 3, 50, 15, 0, 0, Math.PI * 2);
    ctx.fillStyle = "#e46a6a"; ctx.fill(); // cobija
    ctx.lineWidth = 2.5; ctx.stroke();
    ctx.beginPath(); ctx.ellipse(x - 34, y - 6, 13, 8, -0.2, 0, Math.PI * 2);
    ctx.fillStyle = "#f4efe6"; ctx.fill(); ctx.stroke(); // almohada
  }

  function vela(ctx, x, y) {
    const halo = ctx.createRadialGradient(x, y - 50, 4, x, y - 50, 90);
    halo.addColorStop(0, "rgba(255,196,90,0.45)");
    halo.addColorStop(1, "rgba(255,196,90,0)");
    ctx.fillStyle = halo;
    ctx.fillRect(x - 90, y - 140, 180, 180);
    redondeado(ctx, x - 9, y - 38, 18, 38, 4);
    ctx.fillStyle = "#f4efe6"; ctx.fill();
    ctx.lineWidth = 3; ctx.strokeStyle = LINEA; ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x, y - 58); ctx.quadraticCurveTo(x + 9, y - 46, x, y - 40); ctx.quadraticCurveTo(x - 9, y - 46, x, y - 58);
    ctx.fillStyle = "#ffb13b"; ctx.fill();
    ctx.lineWidth = 2; ctx.stroke();
  }

  function letrero(ctx, x, y) {
    redondeado(ctx, x - 82, y - 22, 164, 44, 8);
    ctx.fillStyle = "#3f6f5c"; ctx.fill();
    ctx.lineWidth = 3; ctx.strokeStyle = LINEA; ctx.stroke();
    ctx.strokeStyle = "rgba(255,255,255,0.6)"; ctx.lineWidth = 2;
    redondeado(ctx, x - 75, y - 15, 150, 30, 5); ctx.stroke();
    ctx.fillStyle = "#f4efe6";
    ctx.font = "700 17px 'Baloo 2', ui-rounded, sans-serif";
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText("La Alcantarilla", x, y + 1);
  }

  function crearFondo() {
    const k = 2; // se dibuja al doble para que se vea nítido
    const lienzo = document.createElement("canvas");
    lienzo.width = ANCHO * k;
    lienzo.height = ALTO * k;
    const ctx = lienzo.getContext("2d");
    ctx.scale(k, k);
    ctx.lineJoin = "round";
    ctx.lineCap = "round";

    // pared de ladrillo
    ladrillos(ctx, 0, 0, ANCHO, 215, 22, 56, "#5c6b62", "#47544d");
    const sombra = ctx.createLinearGradient(0, 0, 0, 215);
    sombra.addColorStop(0, "rgba(20,28,26,0.55)");
    sombra.addColorStop(1, "rgba(20,28,26,0)");
    ctx.fillStyle = sombra;
    ctx.fillRect(0, 0, ANCHO, 215);

    // túnel del fondo
    ctx.beginPath();
    ctx.moveTo(400, 215); ctx.lineTo(400, 120); ctx.arc(480, 120, 80, Math.PI, 0); ctx.lineTo(560, 215); ctx.closePath();
    const tunel = ctx.createRadialGradient(480, 175, 10, 480, 160, 110);
    tunel.addColorStop(0, "#3b5a4f");
    tunel.addColorStop(1, "#111816");
    ctx.fillStyle = tunel; ctx.fill();
    ctx.lineWidth = 10; ctx.strokeStyle = "#7a8a80"; ctx.stroke();
    ctx.lineWidth = 3; ctx.strokeStyle = LINEA; ctx.stroke();

    // rayos de luz que entran por la coladera
    const luz = ctx.createLinearGradient(0, 0, 0, 420);
    luz.addColorStop(0, "rgba(255,236,170,0.55)");
    luz.addColorStop(1, "rgba(255,236,170,0)");
    ctx.fillStyle = luz;
    ctx.beginPath(); ctx.moveTo(150, 0); ctx.lineTo(250, 0); ctx.lineTo(330, 420); ctx.lineTo(120, 420); ctx.closePath(); ctx.fill();
    // coladera
    redondeado(ctx, 140, -10, 120, 26, 6);
    ctx.fillStyle = "#2a3330"; ctx.fill();
    ctx.lineWidth = 3; ctx.strokeStyle = LINEA; ctx.stroke();
    ctx.fillStyle = "#ffeeb5";
    for (let i = 0; i < 6; i++) ctx.fillRect(150 + i * 18, 0, 9, 10);

    // tubos
    tubo(ctx, [[-10, 62], [330, 62], [330, 150]], 16, "#8fa39a");
    tubo(ctx, [[970, 40], [760, 40], [760, 120], [690, 120]], 20, "#b0715a");
    ctx.fillStyle = LINEA; // bocas de los tubos
    ctx.beginPath(); ctx.ellipse(330, 156, 12, 5, 0, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.ellipse(686, 120, 5, 13, 0, 0, Math.PI * 2); ctx.fill();
    // baba verde que escurre del tubo
    ctx.fillStyle = "#7cc56b";
    ctx.beginPath(); ctx.moveTo(682, 112); ctx.quadraticCurveTo(670, 140, 676, 168); ctx.quadraticCurveTo(686, 150, 690, 128); ctx.closePath(); ctx.fill();

    letrero(ctx, 840, 140);

    // canal de agua (el brillo animado se dibuja aparte)
    const agua = ctx.createLinearGradient(0, 205, 0, 250);
    agua.addColorStop(0, "#2f5a4a");
    agua.addColorStop(1, "#4f8a6b");
    ctx.fillStyle = agua;
    ctx.fillRect(0, 205, ANCHO, 45);
    ctx.strokeStyle = LINEA; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(0, 205); ctx.lineTo(ANCHO, 205); ctx.stroke();

    // banqueta de piedra donde caminan las ratas
    const piso = ctx.createLinearGradient(0, 250, 0, ALTO);
    piso.addColorStop(0, "#8d968c");
    piso.addColorStop(1, "#6b756c");
    ctx.fillStyle = piso;
    ctx.fillRect(0, 250, ANCHO, ALTO - 250);
    ctx.strokeStyle = "rgba(28,36,34,0.25)"; ctx.lineWidth = 2;
    for (let y = 290, fila = 0; y < ALTO; y += 48 + fila * 6, fila++) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(ANCHO, y); ctx.stroke();
    }
    for (let x = -40; x < ANCHO + 80; x += 96) {
      ctx.beginPath(); ctx.moveTo(x + 30, 250); ctx.lineTo(x - 30, ALTO); ctx.stroke();
    }
    // orilla de la banqueta
    redondeado(ctx, -10, 244, ANCHO + 20, 16, 6);
    ctx.fillStyle = "#a7afa5"; ctx.fill();
    ctx.lineWidth = 3; ctx.strokeStyle = LINEA; ctx.stroke();

    // charcos
    ctx.fillStyle = "rgba(79,138,107,0.55)";
    for (const [x, y, rx] of [[640, 470, 80], [260, 545, 60], [880, 560, 50]]) {
      ctx.beginPath(); ctx.ellipse(x, y, rx, rx * 0.28, 0, 0, Math.PI * 2); ctx.fill();
    }
    ctx.strokeStyle = "rgba(255,255,255,0.5)"; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.moveTo(605, 463); ctx.lineTo(640, 458); ctx.stroke();

    lata(ctx, 110, 330);
    vela(ctx, 470, 300);
    caja(ctx, 860, 330);
    return lienzo;
  }

  /* ---------------- Rata ---------------- */
  function dibujarJugador(ctx, j, t, esYo) {
    const x = j.x, y = j.y;
    const camina = j.caminando;
    const bote = camina ? Math.abs(Math.sin(t * 12)) * -4 : Math.sin(t * 2 + j.fase) * 0.8;
    const dir = j.dir || 1;
    const pelo = j.color;
    const panza = mezclar(pelo, "#ffffff", 0.55);
    const rosa = "#f4a3b4";

    // sombra
    ctx.fillStyle = "rgba(28,36,34,0.25)";
    ctx.beginPath(); ctx.ellipse(x, y, 24, 6, 0, 0, Math.PI * 2); ctx.fill();

    // cola (detrás del cuerpo, del lado contrario a donde mira)
    const meneo = Math.sin(t * (camina ? 10 : 3) + j.fase) * 6;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(x - dir * 14, y - 12);
    ctx.bezierCurveTo(x - dir * 40, y - 6, x - dir * 36, y - 34 + meneo, x - dir * 54, y - 30 + meneo);
    ctx.strokeStyle = LINEA; ctx.lineWidth = 8; ctx.stroke();
    ctx.strokeStyle = rosa; ctx.lineWidth = 4; ctx.stroke();

    // patitas
    const paso = camina ? Math.sin(t * 12) * 4 : 0;
    ctx.fillStyle = rosa; ctx.strokeStyle = LINEA; ctx.lineWidth = 2.5;
    for (const [dx, dy] of [[-8, paso], [8, -paso]]) {
      ctx.beginPath(); ctx.ellipse(x + dx, y - 3 + dy * 0.4, 7, 4.5, 0, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    }

    const cy = y - 24 + bote;
    // cuerpo
    ctx.beginPath(); ctx.ellipse(x, cy, 20, 21, 0, 0, Math.PI * 2);
    ctx.fillStyle = pelo; ctx.fill();
    ctx.lineWidth = 3; ctx.strokeStyle = LINEA; ctx.stroke();
    ctx.beginPath(); ctx.ellipse(x + dir * 3, cy + 6, 11, 12, 0, 0, Math.PI * 2);
    ctx.fillStyle = panza; ctx.fill();

    // cabeza
    const hx = x + dir * 6, hy = cy - 22;
    // orejas
    for (const ox of [-12, 10]) {
      const ex = hx + ox - dir * 2, ey = hy - 12;
      ctx.beginPath(); ctx.arc(ex, ey, 10, 0, Math.PI * 2);
      ctx.fillStyle = pelo; ctx.fill();
      ctx.lineWidth = 3; ctx.strokeStyle = LINEA; ctx.stroke();
      ctx.beginPath(); ctx.arc(ex, ey, 5.5, 0, Math.PI * 2);
      ctx.fillStyle = rosa; ctx.fill();
    }
    // cara con hocico puntiagudo
    ctx.beginPath();
    ctx.moveTo(hx - dir * 15, hy - 6);
    ctx.quadraticCurveTo(hx - dir * 14, hy - 17, hx, hy - 16);
    ctx.quadraticCurveTo(hx + dir * 12, hy - 15, hx + dir * 24, hy + 2);
    ctx.quadraticCurveTo(hx + dir * 12, hy + 12, hx - dir * 2, hy + 11);
    ctx.quadraticCurveTo(hx - dir * 16, hy + 8, hx - dir * 15, hy - 6);
    ctx.fillStyle = pelo; ctx.fill();
    ctx.lineWidth = 3; ctx.strokeStyle = LINEA; ctx.stroke();
    // dientes
    ctx.fillStyle = "#ffffff"; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.rect(hx + dir * 13 - 3, hy + 7, 6, 5); ctx.fill(); ctx.stroke();
    // nariz
    ctx.beginPath(); ctx.arc(hx + dir * 24, hy + 1, 4, 0, Math.PI * 2);
    ctx.fillStyle = "#f06d8b"; ctx.fill(); ctx.lineWidth = 2; ctx.stroke();
    // bigotes
    ctx.strokeStyle = LINEA; ctx.lineWidth = 1.5;
    for (const dy of [-3, 3]) {
      ctx.beginPath(); ctx.moveTo(hx + dir * 18, hy + 3); ctx.lineTo(hx + dir * 32, hy + 3 + dy * 2); ctx.stroke();
    }
    // ojo (parpadea de vez en cuando)
    const ex = hx + dir * 6, ey = hy - 5;
    if ((t + j.fase * 3) % 4 < 0.12) {
      ctx.lineWidth = 2.5;
      ctx.beginPath(); ctx.moveTo(ex - 3.5, ey); ctx.lineTo(ex + 3.5, ey); ctx.stroke();
    } else {
      ctx.fillStyle = LINEA;
      ctx.beginPath(); ctx.arc(ex, ey, 4, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#ffffff";
      ctx.beginPath(); ctx.arc(ex + 1.3, ey - 1.4, 1.5, 0, Math.PI * 2); ctx.fill();
    }
    // cachete
    ctx.fillStyle = "rgba(255,120,150,0.5)";
    ctx.beginPath(); ctx.ellipse(hx + dir * 4, hy + 4, 4, 2.6, 0, 0, Math.PI * 2); ctx.fill();

    // nombre
    ctx.font = "700 13px 'Baloo 2', ui-rounded, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const w = ctx.measureText(j.nombre).width + 14;
    redondeado(ctx, x - w / 2, y + 7, w, 19, 9);
    ctx.fillStyle = esYo ? "#ffb13b" : "rgba(244,239,230,0.95)";
    ctx.fill();
    ctx.lineWidth = 2; ctx.strokeStyle = LINEA; ctx.stroke();
    ctx.fillStyle = LINEA;
    ctx.fillText(j.nombre, x, y + 17);
  }

  /* ---------------- Burbuja de texto ---------------- */
  function partirLineas(ctx, texto, ancho) {
    const palabras = texto.split(" ");
    const lineas = [];
    let actual = "";
    for (const p of palabras) {
      const prueba = actual ? actual + " " + p : p;
      if (ctx.measureText(prueba).width > ancho && actual) {
        lineas.push(actual);
        actual = p;
      } else {
        actual = prueba;
      }
      while (ctx.measureText(actual).width > ancho && actual.length > 1) { // palabra muy larga
        let corte = actual.length - 1;
        while (corte > 1 && ctx.measureText(actual.slice(0, corte)).width > ancho) corte--;
        lineas.push(actual.slice(0, corte));
        actual = actual.slice(corte);
      }
    }
    if (actual) lineas.push(actual);
    if (lineas.length > 4) {
      lineas.length = 4;
      lineas[3] = lineas[3].slice(0, -1) + "…";
    }
    return lineas;
  }

  function dibujarBurbuja(ctx, j, ahora) {
    const b = j.burbuja;
    if (!b || ahora > b.hasta) return;
    const alfa = Math.min(1, (b.hasta - ahora) / 600);
    ctx.save();
    ctx.globalAlpha = alfa;
    ctx.font = "600 14px 'Baloo 2', ui-rounded, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const lineas = partirLineas(ctx, b.texto, 180);
    const alto = 18;
    const w = Math.max(...lineas.map((l) => ctx.measureText(l).width)) + 22;
    const h = lineas.length * alto + 12;
    const bx = Math.max(4, Math.min(ANCHO - w - 4, j.x - w / 2));
    const by = j.y - 76 - h;
    redondeado(ctx, bx, by, w, h, 12);
    ctx.fillStyle = b.censurado ? "#ffecec" : "#ffffff";
    ctx.fill();
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = b.censurado ? "#e5484d" : LINEA;
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(j.x - 7, by + h - 1.5);
    ctx.lineTo(j.x, by + h + 9);
    ctx.lineTo(j.x + 7, by + h - 1.5);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = b.censurado ? "#8f1d22" : LINEA;
    lineas.forEach((l, i) => ctx.fillText(l, bx + w / 2, by + 6 + alto / 2 + i * alto));
    ctx.restore();
  }

  /* ---------------- Ambiente animado: agua, gotas y polvo en la luz ---------------- */
  const gotas = [{ x: 330, y0: 160, v: 0, y: 160, espera: 0.5 }, { x: 680, y0: 132, v: 0, y: 132, espera: 1.4 },
                 { x: 600, y0: 0, v: 0, y: 0, espera: 2.2 }];
  const polvo = Array.from({ length: movimientoReducido ? 0 : 24 }, () => ({
    x: 140 + Math.random() * 160, y: Math.random() * 400, v: 4 + Math.random() * 8, o: Math.random() * 6,
  }));

  function dibujarAmbiente(ctx, t, dt) {
    ctx.save();
    ctx.beginPath(); ctx.rect(0, 0, ANCHO, ALTO); ctx.clip();
    ambiente(ctx, t, dt);
    ctx.restore();
  }

  function ambiente(ctx, t, dt) {
    // brillo del agua que corre
    ctx.strokeStyle = "rgba(200,240,210,0.45)";
    ctx.lineWidth = 2;
    const corrimiento = movimientoReducido ? 0 : (t * 30) % 120;
    for (let i = -1; i < 9; i++) {
      for (const [dy, largo] of [[214, 34], [230, 22], [241, 28]]) {
        const xx = i * 120 + corrimiento + (dy % 3) * 40;
        ctx.beginPath(); ctx.moveTo(xx, dy); ctx.lineTo(xx + largo, dy); ctx.stroke();
      }
    }
    if (movimientoReducido) return;
    // gotas que caen de los tubos
    for (const g of gotas) {
      if (g.espera > 0) { g.espera -= dt; continue; }
      g.v += 600 * dt;
      g.y += g.v * dt;
      if (g.y > 222) {
        ctx.strokeStyle = "rgba(200,240,210,0.7)"; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.ellipse(g.x, 224, 10, 3, 0, 0, Math.PI * 2); ctx.stroke();
        g.y = g.y0; g.v = 0; g.espera = 1.5 + Math.random() * 2;
        continue;
      }
      ctx.fillStyle = "#bfe8cf";
      ctx.beginPath(); ctx.ellipse(g.x, g.y, 2.5, 4, 0, 0, Math.PI * 2); ctx.fill();
    }
    // polvito flotando en el rayo de luz
    ctx.fillStyle = "rgba(255,240,190,0.75)";
    for (const p of polvo) {
      p.y += p.v * dt;
      p.x += Math.sin(t + p.o) * 6 * dt;
      if (p.y > 410) { p.y = 0; p.x = 140 + Math.random() * 160; }
      const ancho = 50 + p.y * 0.25;
      if (Math.abs(p.x - (200 + p.y * 0.04)) > ancho) continue;
      ctx.beginPath(); ctx.arc(p.x, p.y, 1.5, 0, Math.PI * 2); ctx.fill();
    }
  }

  function dibujarMarca(ctx, m, ahora) {
    const p = (ahora - m.inicio) / 500;
    if (p > 1) return false;
    ctx.save();
    ctx.globalAlpha = 1 - p;
    ctx.strokeStyle = "#ffb13b";
    ctx.lineWidth = 3;
    ctx.beginPath(); ctx.ellipse(m.x, m.y, 8 + p * 18, (8 + p * 18) * 0.4, 0, 0, Math.PI * 2); ctx.stroke();
    ctx.restore();
    return true;
  }

  window.Escena = { ANCHO, ALTO, crearFondo, dibujarJugador, dibujarBurbuja, dibujarAmbiente, dibujarMarca };
})();
