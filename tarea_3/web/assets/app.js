/* Dashboard: brecha digital en el Perú, ENAHO 2015-2025 */
(() => {
  "use strict";

  // ---------- Configuración ----------
  const ANIOS = d3.range(2015, 2026);
  const PRIMER_ANIO = { usa_celular: 2019, usa_computadora: 2019, internet_fijo: 2023, internet_solo_movil: 2023 };
  const UNIDAD_HOGAR = new Set(["celular", "internet", "internet_fijo", "internet_solo_movil", "sin_tic", "tel_fijo"]);
  const DIM_HOGAR = new Set(["area", "quintil", "pobreza"]);
  const GRUPOS = {
    area: ["Urbano", "Rural"],
    sexo: ["Hombre", "Mujer"],
    lengua: ["Castellano", "Lengua indígena"],
    pobreza: ["Pobre extremo", "Pobre no extremo", "No pobre"],
    quintil: ["Q1", "Q2", "Q3", "Q4", "Q5"],
    grupo_edad: ["6-11", "12-17", "18-24", "25-44", "45-64", "65+"],
  };
  const ETIQ_GRUPO = { Q1: "Q1 (20 % de menor gasto)", Q5: "Q5 (20 % de mayor gasto)", "65+": "65 a más", "6-11": "6 a 11", "12-17": "12 a 17", "18-24": "18 a 24", "25-44": "25 a 44", "45-64": "45 a 64" };
  const ETIQ_DIM = { area: "área", sexo: "sexo", lengua: "lengua materna", pobreza: "condición de pobreza", quintil: "quintil de gasto", grupo_edad: "grupo de edad" };
  const ORDINAL = new Set(["pobreza", "quintil", "grupo_edad"]);
  const CODIGOS = {}; // nombre -> código de departamento

  const S = { ind: "usa_internet", anio: 2025, ambito: "Total", geo: "Perú", dim: "quintil" };
  const DEF = { ...S };
  const idx = new Map();
  const cargados = new Set();
  let META = null, GEO = null, timer = null;

  const $ = (s) => document.querySelector(s);
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const fmt = (v) => (v == null ? "—" : d3.format(".1f")(v).replace("-", "−"));
  const fmtpp = (v) => (v == null ? "—" : (v > 0 ? "+" : v < 0 ? "−" : "") + d3.format(".1f")(Math.abs(v)));
  const key = (a, amb, g, dim, gr, ind) => `${a}|${amb}|${g}|${dim}|${gr}|${ind}`;
  const etq = (g) => ETIQ_GRUPO[g] || g;

  function get(ind, anio, amb, geo, dim = "nacional", grupo = "Total") {
    if (dim === "area") { return idx.get(key(anio, grupo, geo, "nacional", "Total", ind)) || null; }
    return idx.get(key(anio, amb, geo, dim, grupo, ind)) || null;
  }
  const val = (...a) => { const r = get(...a); return r ? r.v : null; };

  function cargar(json) {
    const c = json.columnas;
    const I = Object.fromEntries(c.map((k, i) => [k, i]));
    for (const f of json.filas) {
      idx.set(key(f[I.anio], f[I.ambito], f[I.geo], f[I.dimension], f[I.grupo], f[I.indicador]),
        { v: f[I.v], e: f[I.e], n: f[I.n] });
    }
  }
  async function asegurarDepto(geo) {
    if (geo === "Perú" || cargados.has(geo)) return;
    const j = await d3.json(`data/departamentos/${CODIGOS[geo]}.json`);
    cargar(j); cargados.add(geo);
  }

  // ---------- Paletas ----------
  function colorGrupo(dim, g) {
    const lista = GRUPOS[dim];
    if (ORDINAL.has(dim)) {
      const rampa = css(`--o${lista.length}`).split(",").map((c) => c.trim());
      return rampa[lista.indexOf(g)];
    }
    return css(lista.indexOf(g) === 0 ? "--s1" : "--s2");
  }
  const colorAmbito = (a) => (a === "Urbano" ? css("--s1") : a === "Rural" ? css("--s2") : css("--ref"));

  // ---------- Tooltip ----------
  const tip = $("#tip");
  function showTip(html, ev) {
    tip.innerHTML = html; tip.style.opacity = 1;
    const w = tip.offsetWidth, h = tip.offsetHeight;
    let x = ev.clientX + 14, y = ev.clientY + 14;
    if (x + w > innerWidth - 8) x = ev.clientX - w - 14;
    if (y + h > innerHeight - 8) y = ev.clientY - h - 14;
    tip.style.left = x + "px"; tip.style.top = y + "px";
  }
  const hideTip = () => { tip.style.opacity = 0; };
  const filaTip = (color, nombre, r) =>
    `<div class="t-r"><span><i style="background:${color}"></i>${nombre}</span><b>${r ? fmt(r.v) + " %" : "sin dato"}</b></div>` +
    (r ? `<div class="t-r muted small"><span></span><span>± ${fmt(r.e)} pp · n = ${d3.format(",")(r.n).replace(/,/g, " ")}</span></div>` : "");

  // ---------- Textos de contexto ----------
  const nombreInd = () => META.indicadores[S.ind].nombre;
  const esHogar = () => UNIDAD_HOGAR.has(S.ind);
  const ambTxt = () => (S.ambito === "Total" ? "" : ` · ámbito ${S.ambito.toLowerCase()}`);
  const geoTxt = () => (S.geo === "Perú" ? "Perú" : S.geo);

  function avisos() {
    const msgs = [];
    const p = PRIMER_ANIO[S.ind];
    if (p && S.anio < p) { msgs.push(`Este indicador existe desde ${p}; se muestra ${p}.`); }
    if (S.ind === "internet" && S.anio >= 2023) msgs.push("Desde 2023 «hogares con internet» incluye la conexión móvil y no es comparable con años previos.");
    if (S.anio === 2020 && ["usa_diario", "usa_celular", "usa_computadora"].includes(S.ind)) msgs.push("2020 es referencial: entre abril y setiembre la encuesta fue telefónica y no preguntó frecuencia ni dispositivo.");
    if (esHogar() && !DIM_HOGAR.has(S.dim)) msgs.push("Los indicadores de hogar no se desagregan por sexo, edad ni lengua; se muestra el quintil de gasto.");
    $("#aviso").textContent = msgs.join(" ");
  }
  const anioEf = () => Math.max(S.anio, PRIMER_ANIO[S.ind] || 2015);
  const dimEf = () => (esHogar() && !DIM_HOGAR.has(S.dim) ? "quintil" : S.dim);

  // ---------- KPIs ----------
  function kpis() {
    const a = anioEf(), p0 = PRIMER_ANIO[S.ind] || 2015;
    const r = get(S.ind, a, S.ambito, S.geo);
    const r0 = get(S.ind, p0, S.ambito, S.geo);
    const urb = val(S.ind, a, "Urbano", S.geo), rur = val(S.ind, a, "Rural", S.geo);
    const q1 = val(S.ind, a, S.ambito, S.geo, "quintil", "Q1"), q5 = val(S.ind, a, S.ambito, S.geo, "quintil", "Q5");
    const deps = Object.keys(CODIGOS).map((g) => ({ g, v: val(S.ind, a, S.ambito, g) })).filter((d) => d.v != null);
    const min = d3.least(deps, (d) => d.v), max = d3.greatest(deps, (d) => d.v);
    const cambio = r && r0 && a !== p0 ? r.v - r0.v : null;
    const quiebre = S.ind === "internet" && a >= 2023;
    const cards = [
      { l: `${nombreInd()} · ${geoTxt()}${ambTxt()}, ${a}`, v: r ? `${fmt(r.v)}<small> %</small>` : "—", s: r ? `± ${fmt(r.e)} pp · ${d3.format(",")(r.n).replace(/,/g, " ")} observaciones` : "sin dato suficiente" },
      { l: `Cambio desde ${p0}`, v: cambio == null || quiebre ? "—" : `<span class="${cambio >= 0 ? "" : ""}">${fmtpp(cambio)}</span><small> pp</small>`, s: quiebre ? "no comparable: cambio de pregunta en 2023" : r0 ? `${p0}: ${fmt(r0.v)} %` : "" },
      { l: `Brecha urbano − rural · ${geoTxt()}, ${a}`, v: urb != null && rur != null ? `${fmt(urb - rur)}<small> pp</small>` : "—", s: urb != null && rur != null ? `urbano ${fmt(urb)} % · rural ${fmt(rur)} %` : "sin muestra rural suficiente" },
      { l: `Brecha Q5 − Q1 de gasto · ${geoTxt()}${ambTxt()}`, v: q1 != null && q5 != null ? `${fmt(q5 - q1)}<small> pp</small>` : "—", s: q1 != null && q5 != null ? `Q1 ${fmt(q1)} % · Q5 ${fmt(q5)} %` : "cargando o sin muestra" },
      { l: `Departamento con menor valor${ambTxt()}, ${a}`, v: min ? `<span style="font-size:22px">${min.g}</span>` : "—", s: min ? `${fmt(min.v)} % · el mayor: ${max.g} (${fmt(max.v)} %)` : "" },
    ];
    $("#kpis").innerHTML = cards.map((c) => `<div class="kpi"><div class="k-lbl">${c.l}</div><div class="k-val">${c.v}</div><div class="k-sub">${c.s}</div></div>`).join("");
  }

  // ---------- Mapa ----------
  function mapa() {
    const el = $("#c-mapa"); const W = el.clientWidth; const H = Math.min(520, Math.max(380, W * 0.95));
    const a = anioEf();
    $("#t-mapa").textContent = `${nombreInd()}, ${a}`;
    $("#s-mapa").textContent = `Porcentaje por departamento${ambTxt()}. Departamento seleccionado: ${geoTxt()}.`;
    const pasos = d3.range(7).map((i) => css(`--seq-${i}`));
    const valores = GEO.features.map((f) => val(S.ind, a, S.ambito, f.properties.nombre)).filter((v) => v != null);
    const ext = d3.extent(valores);
    const lo = Math.floor((ext[0] ?? 0) / 5) * 5, hi = Math.ceil((ext[1] ?? 100) / 5) * 5;
    const esc = d3.scaleQuantize().domain([lo, hi === lo ? lo + 5 : hi]).range(pasos);
    const proj = d3.geoMercator().fitExtent([[6, 6], [W * 0.78, H - 6]], GEO);
    const path = d3.geoPath(proj);
    const svg = d3.select(el).selectAll("svg").data([0]).join("svg").attr("width", W).attr("height", H).attr("role", "img")
      .attr("aria-label", `Mapa del Perú: ${nombreInd()} por departamento en ${a}`);
    svg.selectAll("path.dep").data(GEO.features, (d) => d.properties.cod).join("path")
      .attr("class", (d) => "dep" + (d.properties.nombre === S.geo ? " sel" : ""))
      .attr("d", path).attr("tabindex", 0)
      .attr("fill", (d) => { const v = val(S.ind, a, S.ambito, d.properties.nombre); return v == null ? css("--nodata") : esc(v); })
      .on("mousemove", (ev, d) => {
        const r = get(S.ind, a, S.ambito, d.properties.nombre); const pe = get(S.ind, a, S.ambito, "Perú");
        showTip(`<div class="t-h">${d.properties.nombre}</div>${filaTip(r ? esc(r.v) : css("--nodata"), String(a), r)}<div class="t-r muted"><span>Perú</span><span>${pe ? fmt(pe.v) + " %" : "—"}</span></div>`, ev);
      })
      .on("mouseleave", hideTip)
      .on("click", (ev, d) => setGeo(d.properties.nombre === S.geo ? "Perú" : d.properties.nombre))
      .on("keydown", (ev, d) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); setGeo(d.properties.nombre === S.geo ? "Perú" : d.properties.nombre); } })
      .raise();
    svg.selectAll("path.dep.sel").raise();
    // Leyenda de escala
    const lx = W * 0.8 + 6, ly = 24, lh = Math.min(26, (H - 80) / 7);
    const leg = svg.selectAll("g.leg").data([0]).join("g").attr("class", "leg").attr("transform", `translate(${lx},${ly})`);
    leg.selectAll("text.lt").data([0]).join("text").attr("class", "lt lbl-ink2").attr("y", -8).text("%");
    const cortes = esc.range().map((c) => esc.invertExtent(c));
    leg.selectAll("rect").data(cortes.slice().reverse()).join("rect").attr("x", 0).attr("y", (d, i) => i * lh).attr("width", 14).attr("height", lh - 2).attr("rx", 3)
      .attr("fill", (d) => esc((d[0] + d[1]) / 2));
    leg.selectAll("text.lv").data(cortes.slice().reverse()).join("text").attr("class", "lv").attr("x", 20).attr("y", (d, i) => i * lh + lh / 2 + 3)
      .text((d) => `${Math.round(d[0])}–${Math.round(d[1])}`);
    leg.selectAll("rect.nd").data([0]).join("rect").attr("class", "nd").attr("x", 0).attr("y", 7 * lh + 8).attr("width", 14).attr("height", lh - 2).attr("rx", 3).attr("fill", css("--nodata"));
    leg.selectAll("text.nd").data([0]).join("text").attr("class", "nd").attr("x", 20).attr("y", 7 * lh + 8 + lh / 2 + 3).text("sin dato");
  }

  // ---------- Ranking ----------
  function ranking() {
    const el = $("#c-rank"); const W = el.clientWidth; const a = anioEf();
    const pe = val(S.ind, a, S.ambito, "Perú");
    const datos = Object.keys(CODIGOS).map((g) => ({ g, r: get(S.ind, a, S.ambito, g) })).filter((d) => d.r).sort((x, y) => y.r.v - x.r.v);
    $("#t-rank").textContent = `Ranking de departamentos, ${a}`;
    $("#s-rank").textContent = `${nombreInd()}${ambTxt()} (%). Promedio nacional: ${fmt(pe)} %.`;
    const fila = 19, m = { t: 6, r: 44, b: 22, l: 104 }, H = m.t + m.b + fila * datos.length;
    const x = d3.scaleLinear().domain([0, Math.max(100, d3.max(datos, (d) => d.r.v + d.r.e) || 100)]).range([m.l, W - m.r]);
    const svg = d3.select(el).selectAll("svg").data([0]).join("svg").attr("width", W).attr("height", H).attr("role", "img").attr("aria-label", "Ranking de departamentos");
    svg.selectAll("g.gx").data([0]).join("g").attr("class", "gx").attr("transform", `translate(0,${H - m.b})`)
      .call(d3.axisBottom(x).ticks(5).tickSize(-(H - m.t - m.b)).tickFormat((d) => d + "%"))
      .call((g) => g.select(".domain").remove()).call((g) => g.selectAll("line").attr("class", "grid-line"));
    svg.selectAll("line.pe").data(pe != null ? [pe] : []).join("line").attr("class", "pe").attr("x1", (d) => x(d)).attr("x2", (d) => x(d))
      .attr("y1", m.t).attr("y2", H - m.b).attr("stroke", css("--ink")).attr("stroke-width", 1.5).attr("opacity", 0.7);
    const g = svg.selectAll("g.rows").data([0]).join("g").attr("class", "rows");
    const row = g.selectAll("g.row").data(datos, (d) => d.g).join((en) => { const r = en.append("g").attr("class", "row"); r.append("rect").attr("class", "bar"); r.append("text").attr("class", "nm"); r.append("text").attr("class", "vl"); r.append("rect").attr("class", "hit"); return r; });
    row.attr("transform", (d, i) => `translate(0,${m.t + i * fila})`).style("cursor", "pointer");
    row.select("rect.bar").attr("x", x(0)).attr("y", 3).attr("height", fila - 6).attr("rx", 3)
      .attr("width", (d) => Math.max(0, x(d.r.v) - x(0)))
      .attr("fill", (d) => (d.g === S.geo ? css("--s1") : css("--seq-2"))).attr("opacity", (d) => (S.geo === "Perú" || d.g === S.geo ? 1 : 0.45));
    row.select("text.nm").attr("x", m.l - 6).attr("y", fila / 2 + 4).attr("text-anchor", "end").attr("class", (d) => "nm " + (d.g === S.geo ? "lbl-ink" : "lbl-ink2")).text((d) => d.g);
    row.select("text.vl").attr("x", (d) => x(d.r.v) + 4).attr("y", fila / 2 + 4).attr("class", (d) => "vl " + (d.g === S.geo ? "lbl-ink" : "")).text((d) => fmt(d.r.v));
    row.select("rect.hit").attr("x", 0).attr("y", 0).attr("width", W).attr("height", fila).attr("fill", "transparent")
      .on("mousemove", (ev, d) => showTip(`<div class="t-h">${d.g}</div>${filaTip(css("--s1"), String(a), d.r)}`, ev))
      .on("mouseleave", hideTip).on("click", (ev, d) => setGeo(d.g === S.geo ? "Perú" : d.g));
    svg.selectAll("text.pe").data(pe != null ? [pe] : []).join("text").attr("class", "pe lbl-ink").attr("x", (d) => x(d) + 4).attr("y", H - m.b - 4).text("Perú");
  }

  // ---------- Gráfico de líneas genérico ----------
  function lineas(el, series, opts = {}) {
    const W = el.clientWidth, H = opts.h || 290, m = { t: 14, r: 92, b: 28, l: 40 };
    const desde = PRIMER_ANIO[S.ind] || 2015;
    const xs = ANIOS.filter((a) => a >= desde);
    const x = d3.scalePoint().domain(xs).range([m.l, W - m.r]).padding(0.1);
    const todos = series.flatMap((s) => s.pts.filter((p) => p.r));
    const ymax = Math.min(100, Math.ceil((d3.max(todos, (p) => p.r.v + p.r.e) ?? 100) / 10) * 10);
    const ymin = Math.max(0, Math.floor((d3.min(todos, (p) => p.r.v - p.r.e) ?? 0) / 10) * 10);
    const y = d3.scaleLinear().domain([ymin, ymax]).range([H - m.b, m.t]);
    const svg = d3.select(el).selectAll("svg").data([0]).join("svg").attr("width", W).attr("height", H).attr("role", "img").attr("aria-label", opts.aria || "Gráfico de líneas");
    svg.selectAll("*").remove();
    // 2020 sombreado
    if (xs.includes(2020)) {
      const bw = x.step();
      svg.append("rect").attr("x", x(2020) - bw / 2).attr("width", bw).attr("y", m.t).attr("height", H - m.t - m.b).attr("fill", css("--band-2020"));
      svg.append("text").attr("x", x(2020)).attr("y", m.t + 10).attr("text-anchor", "middle").attr("font-size", 10).text("pandemia");
    }
    if (S.ind === "internet") {
      const xq = (x(2022) + x(2023)) / 2;
      svg.append("line").attr("x1", xq).attr("x2", xq).attr("y1", m.t).attr("y2", H - m.b).attr("stroke", css("--muted")).attr("stroke-width", 1);
      svg.append("text").attr("x", xq + 4).attr("y", H - m.b - 6).attr("font-size", 10).text("cambio de pregunta");
    }
    svg.append("g").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5).tickSize(-(W - m.l - m.r)).tickFormat((d) => d + "%"))
      .call((g) => g.select(".domain").remove()).call((g) => g.selectAll("line").attr("class", "grid-line"));
    svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickValues(W < 420 ? xs.filter((a) => a % 2 === 1) : xs).tickSizeOuter(0));
    const seg = (s) => {
      const pts = s.pts.filter((p) => p.r && p.a >= desde);
      // la serie de internet del hogar se corta en 2023
      return S.ind === "internet" ? [pts.filter((p) => p.a < 2023), pts.filter((p) => p.a >= 2023)] : [pts];
    };
    const area = d3.area().x((p) => x(p.a)).y0((p) => y(Math.max(0, p.r.v - p.r.e))).y1((p) => y(Math.min(100, p.r.v + p.r.e)));
    const line = d3.line().x((p) => x(p.a)).y((p) => y(p.r.v));
    for (const s of series) for (const pts of seg(s)) {
      if (!pts.length) continue;
      svg.append("path").attr("d", area(pts)).attr("fill", s.color).attr("opacity", 0.13);
    }
    for (const s of series) for (const pts of seg(s)) {
      if (!pts.length) continue;
      svg.append("path").attr("d", line(pts)).attr("fill", "none").attr("stroke", s.color).attr("stroke-width", s.ref ? 1.5 : 2.2)
        .attr("stroke-dasharray", s.ref ? "4 3" : null).attr("stroke-linejoin", "round");
    }
    // marcador del año seleccionado
    const aSel = anioEf();
    for (const s of series) {
      const p = s.pts.find((q) => q.a === aSel && q.r);
      if (p) svg.append("circle").attr("cx", x(p.a)).attr("cy", y(p.r.v)).attr("r", 4.5).attr("fill", s.color).attr("stroke", css("--surface")).attr("stroke-width", 2);
    }
    // etiquetas directas al final (evitando choques)
    const fin = series.map((s) => { const p = [...s.pts].reverse().find((q) => q.r); return p ? { s, p, y: y(p.r.v) } : null; }).filter(Boolean).sort((a, b) => a.y - b.y);
    for (let i = 1; i < fin.length; i++) if (fin[i].y - fin[i - 1].y < 13) fin[i].y = fin[i - 1].y + 13;
    for (const f of fin) {
      svg.append("text").attr("x", x(f.p.a) + 8).attr("y", f.y + 4).attr("class", "lbl-ink2").attr("font-size", 11)
        .text(`${f.s.corto || f.s.nombre} ${fmt(f.p.r.v)}`);
    }
    // capa de hover
    const cross = svg.append("line").attr("y1", m.t).attr("y2", H - m.b).attr("stroke", css("--axis")).attr("opacity", 0);
    svg.append("rect").attr("x", m.l).attr("y", m.t).attr("width", W - m.l - m.r).attr("height", H - m.t - m.b).attr("fill", "transparent")
      .on("mousemove", (ev) => {
        const [mx] = d3.pointer(ev);
        const a = xs.reduce((b, c) => (Math.abs(x(c) - mx) < Math.abs(x(b) - mx) ? c : b), xs[0]);
        cross.attr("x1", x(a)).attr("x2", x(a)).attr("opacity", 1);
        const filas = series.map((s) => filaTip(s.color, s.nombre, (s.pts.find((p) => p.a === a) || {}).r)).join("");
        showTip(`<div class="t-h">${a}${a === 2020 ? " · año atípico" : ""}</div>${filas}`, ev);
      })
      .on("mouseleave", () => { cross.attr("opacity", 0); hideTip(); })
      .on("click", (ev) => { const [mx] = d3.pointer(ev); const a = xs.reduce((b, c) => (Math.abs(x(c) - mx) < Math.abs(x(b) - mx) ? c : b), xs[0]); setAnio(a); });
  }

  const leyenda = (el, items) => { el.innerHTML = items.map((i) => `<span><i style="background:${i.color}" class="${i.ref ? "dash" : ""}"></i>${i.nombre}</span>`).join(""); };

  function serieAmbito() {
    const series = ["Urbano", "Rural", "Total"].map((amb) => ({
      nombre: amb === "Total" ? `Total ${geoTxt()}` : amb, corto: amb, color: colorAmbito(amb), ref: amb === "Total",
      pts: ANIOS.map((a) => ({ a, r: get(S.ind, a, amb, S.geo) })),
    }));
    $("#t-serie").textContent = `Evolución: urbano frente a rural · ${geoTxt()}`;
    $("#s-serie").textContent = `${nombreInd()} (%). Haz clic en el gráfico para elegir el año.`;
    leyenda($("#l-serie"), series);
    lineas($("#c-serie"), series, { aria: "Serie temporal urbano y rural" });
    const urb0 = val(S.ind, PRIMER_ANIO[S.ind] || 2015, "Urbano", S.geo), rur0 = val(S.ind, PRIMER_ANIO[S.ind] || 2015, "Rural", S.geo);
    const urb1 = val(S.ind, 2025, "Urbano", S.geo), rur1 = val(S.ind, 2025, "Rural", S.geo);
    $("#n-serie").textContent = urb0 != null && rur0 != null && urb1 != null && rur1 != null && S.ind !== "internet"
      ? `Brecha urbano − rural: ${fmt(urb0 - rur0)} pp en ${PRIMER_ANIO[S.ind] || 2015} y ${fmt(urb1 - rur1)} pp en 2025.`
      : (S.ind === "internet" ? "La serie se corta en 2023 porque la pregunta pasó a incluir el internet móvil." : "");
  }

  function serieGrupos() {
    const dim = dimEf();
    const series = GRUPOS[dim].map((g) => ({
      nombre: etq(g), corto: g.replace("Lengua indígena", "Indígena").replace("Pobre no extremo", "No extremo").replace("Pobre extremo", "Extremo"),
      color: colorGrupo(dim, g), pts: ANIOS.map((a) => ({ a, r: get(S.ind, a, S.ambito, S.geo, dim, g) })),
    }));
    $("#t-grupos").textContent = `Evolución por ${ETIQ_DIM[dim]} · ${geoTxt()}`;
    $("#s-grupos").textContent = `${nombreInd()}${dim === "area" ? "" : ambTxt()} (%).`;
    leyenda($("#l-grupos"), series);
    lineas($("#c-grupos"), series, { aria: `Serie por ${ETIQ_DIM[dim]}` });
  }

  function barras() {
    const el = $("#c-barras"); const W = el.clientWidth; const a = anioEf(); const dim = dimEf();
    const datos = GRUPOS[dim].map((g) => ({ g, r: get(S.ind, a, S.ambito, S.geo, dim, g) }));
    const tot = dim === "area" ? val(S.ind, a, "Total", S.geo) : val(S.ind, a, S.ambito, S.geo);
    $("#t-barras").textContent = `La foto de ${a}: ${nombreInd().toLowerCase()} por ${ETIQ_DIM[dim]}`;
    $("#s-barras").textContent = `${geoTxt()}${dim === "area" ? "" : ambTxt()}. Diferencia entre el grupo más alto y el más bajo: ${(() => { const v = datos.filter((d) => d.r).map((d) => d.r.v); return v.length > 1 ? fmt(d3.max(v) - d3.min(v)) + " pp" : "—"; })()}.`;
    const fila = 34, m = { t: 20, r: 56, b: 24, l: 150 }, H = m.t + m.b + fila * datos.length;
    const x = d3.scaleLinear().domain([0, 100]).range([m.l, W - m.r]);
    const svg = d3.select(el).selectAll("svg").data([0]).join("svg").attr("width", W).attr("height", H).attr("role", "img").attr("aria-label", "Barras por grupo");
    svg.selectAll("*").remove();
    svg.append("g").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(5).tickSize(-(H - m.t - m.b)).tickFormat((d) => d + "%"))
      .call((g) => g.select(".domain").remove()).call((g) => g.selectAll("line").attr("class", "grid-line"));
    const row = svg.selectAll("g.row").data(datos).join("g").attr("transform", (d, i) => `translate(0,${m.t + i * fila})`);
    row.append("text").attr("x", m.l - 8).attr("y", fila / 2 + 4).attr("text-anchor", "end").attr("class", "lbl-ink2").attr("font-size", 12).text((d) => etq(d.g));
    row.filter((d) => d.r).append("rect").attr("x", x(0)).attr("y", 7).attr("height", fila - 14).attr("rx", 4)
      .attr("width", (d) => Math.max(0, x(d.r.v) - x(0))).attr("fill", (d) => colorGrupo(dim, d.g));
    row.filter((d) => d.r).append("line").attr("x1", (d) => x(Math.max(0, d.r.v - d.r.e))).attr("x2", (d) => x(Math.min(100, d.r.v + d.r.e)))
      .attr("y1", fila / 2).attr("y2", fila / 2).attr("stroke", css("--ink")).attr("stroke-width", 1.2).attr("opacity", 0.55);
    row.filter((d) => d.r).append("text").attr("x", (d) => x(Math.min(100, d.r.v + d.r.e)) + 5).attr("y", fila / 2 + 4).attr("class", "lbl-ink").attr("font-size", 12).text((d) => fmt(d.r.v) + " %");
    row.filter((d) => !d.r).append("text").attr("x", x(0) + 4).attr("y", fila / 2 + 4).text("muestra insuficiente");
    row.append("rect").attr("x", 0).attr("width", W).attr("height", fila).attr("fill", "transparent")
      .on("mousemove", (ev, d) => showTip(`<div class="t-h">${etq(d.g)} · ${a}</div>${filaTip(colorGrupo(dim, d.g), geoTxt(), d.r)}`, ev)).on("mouseleave", hideTip);
    if (tot != null) {
      svg.append("line").attr("x1", x(tot)).attr("x2", x(tot)).attr("y1", m.t).attr("y2", H - m.b).attr("stroke", css("--ink")).attr("stroke-width", 1.5);
      svg.append("text").attr("x", x(tot)).attr("y", 12).attr("text-anchor", "middle").attr("class", "lbl-ink").attr("font-size", 11).text(`${geoTxt()} ${fmt(tot)}`);
    }
  }

  // ---------- Conexión de los hogares (100 % apilado por quintil) ----------
  function conexion() {
    const el = $("#c-conexion"); const W = el.clientWidth; const a = Math.max(2023, S.anio);
    const cats = [
      { k: "fijo", nombre: "Internet fijo (con o sin móvil)", color: css("--s1") },
      { k: "movil", nombre: "Solo internet móvil", color: css("--s2") },
      { k: "sin", nombre: "Sin internet", color: css("--axis") },
    ];
    leyenda($("#l-conexion"), cats);
    const grupos = ["Total", ...GRUPOS.quintil];
    const datos = grupos.map((g) => {
      const dim = g === "Total" ? "nacional" : "quintil";
      const fijo = val("internet_fijo", a, S.ambito, S.geo, dim, g), movil = val("internet_solo_movil", a, S.ambito, S.geo, dim, g);
      if (fijo == null || movil == null) return { g, ok: false };
      return { g, ok: true, fijo, movil, sin: Math.max(0, 100 - fijo - movil) };
    });
    $("#s-conexion").textContent = `Hogares por tipo de conexión según quintil de gasto · ${geoTxt()}${ambTxt()}, ${a} (%).`;
    const fila = 34, m = { t: 4, r: 22, b: 24, l: 150 }, H = m.t + m.b + fila * datos.length;
    const x = d3.scaleLinear().domain([0, 100]).range([m.l, W - m.r]);
    const svg = d3.select(el).selectAll("svg").data([0]).join("svg").attr("width", W).attr("height", H).attr("role", "img").attr("aria-label", "Tipo de conexión de los hogares por quintil");
    svg.selectAll("*").remove();
    svg.append("g").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(5).tickSize(0).tickFormat((d) => d + "%")).call((g) => g.select(".domain").remove());
    const row = svg.selectAll("g.row").data(datos).join("g").attr("transform", (d, i) => `translate(0,${m.t + i * fila})`);
    row.append("text").attr("x", m.l - 8).attr("y", fila / 2 + 4).attr("text-anchor", "end").attr("class", (d) => (d.g === "Total" ? "lbl-ink" : "lbl-ink2")).attr("font-size", 12)
      .text((d) => (d.g === "Total" ? `Total ${geoTxt()}` : etq(d.g)));
    row.filter((d) => !d.ok).append("text").attr("x", m.l + 4).attr("y", fila / 2 + 4).text("muestra insuficiente");
    const ok = row.filter((d) => d.ok);
    for (const [i, c] of cats.entries()) {
      ok.append("rect").attr("y", 6).attr("height", fila - 12).attr("rx", 3)
        .attr("x", (d) => x(cats.slice(0, i).reduce((s, cc) => s + d[cc.k], 0)) + (i ? 1 : 0))
        .attr("width", (d) => Math.max(0, x(d[c.k]) - x(0) - (i ? 2 : 1))).attr("fill", c.color);
      ok.append("text").attr("y", fila / 2 + 4).attr("font-size", 11.5).attr("text-anchor", "middle")
        .attr("x", (d) => x(cats.slice(0, i).reduce((s, cc) => s + d[cc.k], 0) + d[c.k] / 2))
        .style("fill", i === 2 ? css("--ink") : "#fff").attr("font-weight", 600)
        .text((d) => ((x(d[c.k]) - x(0)) > 34 ? Math.round(d[c.k]) : ""));
    }
    ok.append("rect").attr("x", 0).attr("width", W).attr("height", fila).attr("fill", "transparent")
      .on("mousemove", (ev, d) => showTip(`<div class="t-h">${d.g === "Total" ? "Total " + geoTxt() : etq(d.g)} · ${a}</div>` +
        cats.map((c) => `<div class="t-r"><span><i style="background:${c.color}"></i>${c.nombre}</span><b>${fmt(d[c.k])} %</b></div>`).join(""), ev))
      .on("mouseleave", hideTip);
  }

  // ---------- Tabla y CSV ----------
  function filasSeleccion() {
    const dim = dimEf(); const out = [];
    for (const a of ANIOS) {
      const r = get(S.ind, a, S.ambito, S.geo);
      if (r) out.push({ anio: a, territorio: S.geo, ambito: S.ambito, grupo: "Total", ...r });
      for (const g of GRUPOS[dim]) { const q = get(S.ind, a, S.ambito, S.geo, dim, g); if (q) out.push({ anio: a, territorio: S.geo, ambito: dim === "area" ? g : S.ambito, grupo: dim === "area" ? "Total" : `${ETIQ_DIM[dim]}: ${g}`, ...q }); }
    }
    return out;
  }
  function tabla() {
    const f = filasSeleccion();
    $("#tabla").innerHTML = `<table><thead><tr><th>Año</th><th>Territorio</th><th>Ámbito</th><th>Grupo</th><th>%</th><th>± pp (95 %)</th><th>n</th></tr></thead><tbody>${f.map((r) => `<tr><td>${r.anio}</td><td>${r.territorio}</td><td>${r.ambito}</td><td>${r.grupo}</td><td>${fmt(r.v)}</td><td>${fmt(r.e)}</td><td>${r.n}</td></tr>`).join("")}</tbody></table>`;
  }
  $("#b-csv").addEventListener("click", () => {
    const f = filasSeleccion();
    const csv = ["indicador,anio,territorio,ambito,grupo,porcentaje,margen_error_95,n_muestra",
      ...f.map((r) => [S.ind, r.anio, r.territorio, r.ambito, r.grupo, r.v, r.e, r.n].map((c) => `"${String(c).replace(/"/g, '""')}"`).join(","))].join("\n");
    const url = URL.createObjectURL(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" }));
    const aEl = Object.assign(document.createElement("a"), { href: url, download: `brecha_digital_${S.ind}_${S.geo}_${S.ambito}.csv` });
    document.body.appendChild(aEl); aEl.click(); aEl.remove(); URL.revokeObjectURL(url);
  });

  // ---------- Estado y render ----------
  async function render() {
    if (!META || !GEO) return; // eventos (resize, tema) antes de que carguen los datos
    await asegurarDepto(S.geo);
    avisos(); kpis(); mapa(); ranking(); serieAmbito(); serieGrupos(); barras(); conexion(); tabla();
    try { history.replaceState(null, "", "#" + new URLSearchParams(S).toString()); } catch (e) { /* sin historial */ }
  }
  function sync() {
    $("#f-ind").value = S.ind; $("#f-anio").value = S.anio; $("#f-anio-out").textContent = S.anio;
    $("#f-geo").value = S.geo; $("#f-dim").value = S.dim;
    document.querySelectorAll("#f-ambito button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.v === S.ambito)));
  }
  function setGeo(g) { S.geo = g; sync(); render(); }
  function setAnio(a) { S.anio = a; sync(); render(); }

  $("#f-ind").addEventListener("change", (e) => { S.ind = e.target.value; render(); });
  $("#f-anio").addEventListener("input", (e) => { S.anio = +e.target.value; $("#f-anio-out").textContent = S.anio; render(); });
  $("#f-geo").addEventListener("change", (e) => setGeo(e.target.value));
  $("#f-dim").addEventListener("change", (e) => { S.dim = e.target.value; render(); });
  document.querySelectorAll("#f-ambito button").forEach((b) => b.addEventListener("click", () => { S.ambito = b.dataset.v; sync(); render(); }));
  $("#f-reset").addEventListener("click", () => { Object.assign(S, DEF); stop(); sync(); render(); });
  function stop() { clearInterval(timer); timer = null; $("#f-play").textContent = "▶"; }
  $("#f-play").addEventListener("click", () => {
    if (timer) return stop();
    $("#f-play").textContent = "❚❚";
    if (S.anio >= 2025) setAnio(PRIMER_ANIO[S.ind] || 2015);
    timer = setInterval(() => { if (S.anio >= 2025) return stop(); setAnio(S.anio + 1); }, 900);
  });
  $("#theme-btn").addEventListener("click", () => {
    const root = document.documentElement;
    const oscuro = root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    root.dataset.theme = oscuro ? "light" : "dark";
    try { localStorage.setItem("tema", root.dataset.theme); } catch (e) { /* sin almacenamiento */ }
    render();
  });
  try { const t = localStorage.getItem("tema"); if (t) document.documentElement.dataset.theme = t; } catch (e) { /* nada */ }
  let rz; addEventListener("resize", () => { clearTimeout(rz); rz = setTimeout(render, 150); });
  matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", render);

  // ---------- Inicio ----------
  Promise.all([d3.json("data/nacional.json"), d3.json("data/peru_departamentos.geojson")]).then(([nac, geo]) => {
    META = nac.meta; cargar(nac); GEO = geo;
    for (const f of geo.features) CODIGOS[f.properties.nombre] = f.properties.cod;
    const sel = $("#f-geo");
    Object.keys(CODIGOS).sort((a, b) => a.localeCompare(b, "es")).forEach((n) => sel.append(new Option(n, n)));
    // estado desde la URL
    try {
      const p = new URLSearchParams(location.hash.slice(1));
      if (p.get("ind") && META.indicadores[p.get("ind")]) S.ind = p.get("ind");
      if (p.get("anio")) S.anio = Math.min(2025, Math.max(2015, +p.get("anio")));
      if (["Total", "Urbano", "Rural"].includes(p.get("ambito"))) S.ambito = p.get("ambito");
      if (p.get("geo") && (p.get("geo") === "Perú" || CODIGOS[p.get("geo")])) S.geo = p.get("geo");
      if (p.get("dim") && GRUPOS[p.get("dim")]) S.dim = p.get("dim");
    } catch (e) { /* hash inválido */ }
    sync(); render();
  }).catch((err) => {
    $("#kpis").innerHTML = `<div class="kpi" style="grid-column:1/-1">No se pudieron cargar los datos (${err.message}). Si abriste el archivo directamente, sírvelo con <code>python -m http.server</code>.</div>`;
  });
})();
