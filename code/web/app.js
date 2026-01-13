/* eslint-disable no-console */
const DATA_URL = "../docs/risk_report.json";

function $(id) {
  return document.getElementById(id);
}

function clamp01(x) {
  return Math.max(0, Math.min(1, x));
}

function fmt(n, digits = 0) {
  if (Number.isNaN(n) || n === null || n === undefined) return "—";
  return Number(n).toFixed(digits);
}

function levelPillClass(level) {
  if (level === "High") return "pill high";
  if (level === "Medium") return "pill mid";
  return "pill low";
}

function normLevel(level) {
  if (!level) return "Low";
  if (level === "High" || level === "Medium" || level === "Low") return level;
  return String(level);
}

function getRiskScore(item) {
  if (typeof item?.risk_score === "number") return item.risk_score;
  if (typeof item?.risk === "object" && typeof item.risk.p_calibrated === "number") return item.risk.p_calibrated;
  return 0;
}

function getRiskLevel(item) {
  if (item?.risk_level) return normLevel(item.risk_level);
  if (item?.risk?.level) return normLevel(item.risk.level);
  return "Low";
}

function getNeedsReview(item) {
  if (typeof item?.needs_review === "boolean") return item.needs_review;
  if (typeof item?.risk?.needs_review === "boolean") return item.risk.needs_review;
  return false;
}

function getT0(item) {
  const sig = (item?.main_signals || [])[0];
  const t0 = sig?.time_window?.t0;
  return t0 || "—";
}

function canvasCtx(canvas) {
  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const w = Math.max(1, Math.round(rect.width));
  const h = Math.max(1, Math.round(rect.height));
  const pw = Math.max(1, Math.round(w * dpr));
  const ph = Math.max(1, Math.round(h * dpr));
  if (canvas.width !== pw || canvas.height !== ph) {
    canvas.width = pw;
    canvas.height = ph;
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, w, h };
}

function ellipsize(ctx, s, maxWidth) {
  const str = String(s ?? "");
  if (ctx.measureText(str).width <= maxWidth) return str;
  const ell = "…";
  let lo = 0;
  let hi = str.length;
  while (lo < hi) {
    const mid = Math.floor((lo + hi) / 2);
    const cand = str.slice(0, mid) + ell;
    if (ctx.measureText(cand).width <= maxWidth) lo = mid + 1;
    else hi = mid;
  }
  return str.slice(0, Math.max(0, lo - 1)) + ell;
}

function drawDonut(canvas, segments) {
  const { ctx, w, h } = canvasCtx(canvas);
  ctx.clearRect(0, 0, w, h);

  const cx = Math.floor(w * 0.5);
  const cy = Math.floor(h * 0.48);
  const r = Math.min(w, h) * 0.34;
  const thickness = r * 0.42;

  const total = segments.reduce((a, s) => a + s.value, 0) || 1;
  let start = -Math.PI / 2;

  for (const s of segments) {
    const angle = (s.value / total) * Math.PI * 2;
    ctx.beginPath();
    ctx.strokeStyle = s.color;
    ctx.lineWidth = thickness;
    ctx.lineCap = "round";
    ctx.arc(cx, cy, r, start, start + angle);
    ctx.stroke();
    start += angle;
  }

  // center label
  ctx.fillStyle = "rgba(233,238,252,.92)";
  ctx.font = "700 22px ui-sans-serif, system-ui";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(String(total), cx, cy - 6);
  ctx.fillStyle = "rgba(169,183,224,.78)";
  ctx.font = "12px ui-monospace, Menlo, Monaco";
  ctx.fillText("repos", cx, cy + 16);
}

function drawBars(canvas, items) {
  const { ctx, w, h } = canvasCtx(canvas);
  ctx.clearRect(0, 0, w, h);

  const padding = 14;
  const labelW = Math.max(120, Math.floor(w * 0.36));
  const left = padding + labelW;
  const top = padding + 6;
  const right = padding;
  const bottom = padding + 16;

  const chartW = w - left - right;
  const chartH = h - top - bottom;

  const max = Math.max(...items.map((x) => x.value), 1);
  const barH = chartH / (items.length || 1);

  // grid
  ctx.strokeStyle = "rgba(42,58,100,.22)";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const x = left + (chartW * i) / 4;
    ctx.beginPath();
    ctx.moveTo(x, top);
    ctx.lineTo(x, top + chartH);
    ctx.stroke();
  }

  ctx.font = "12px ui-monospace, Menlo, Monaco";
  ctx.textBaseline = "middle";

  for (let i = 0; i < items.length; i++) {
    const it = items[i];
    const y = top + i * barH + barH * 0.5;
    const len = (it.value / max) * chartW;

    // label
    ctx.fillStyle = "rgba(169,183,224,.85)";
    ctx.textAlign = "left";
    ctx.fillText(ellipsize(ctx, it.label, labelW - 12), padding, y);

    // bar background
    ctx.fillStyle = "rgba(42,58,100,.28)";
    ctx.fillRect(left, y - 7, chartW, 14);

    // bar
    const grad = ctx.createLinearGradient(left, 0, left + Math.max(1, len), 0);
    grad.addColorStop(0, "rgba(122,162,255,.92)");
    grad.addColorStop(1, "rgba(97,213,255,.70)");
    ctx.fillStyle = grad;
    ctx.fillRect(left, y - 7, Math.max(2, len), 14);

    // value
    ctx.fillStyle = "rgba(233,238,252,.9)";
    ctx.textAlign = "right";
    ctx.fillText(String(it.value), w - 8, y);
  }
}

function makeLegend(el, segments) {
  el.innerHTML = "";
  for (const s of segments) {
    const item = document.createElement("div");
    item.className = "item";
    const sw = document.createElement("span");
    sw.className = "swatch";
    sw.style.background = s.color;
    const text = document.createElement("span");
    text.textContent = `${s.label}: ${s.value}`;
    item.appendChild(sw);
    item.appendChild(text);
    el.appendChild(item);
  }
}

function renderTable(items) {
  const tbody = $("tableBody");
  tbody.innerHTML = "";

  const rows = items.slice(0, 200);
  for (const it of rows) {
    const tr = document.createElement("tr");
    tr.dataset.repo = it.repo;
    tr.addEventListener("click", () => showDetail(it));

    const score = getRiskScore(it);
    const level = getRiskLevel(it);
    const needsReview = getNeedsReview(it);
    const signals = Array.isArray(it.main_signals) ? it.main_signals.length : 0;
    const t0 = getT0(it);

    tr.innerHTML = `
      <td class="mono">${escapeHtml(it.repo || "—")}</td>
      <td>${fmt(score, 3)}</td>
      <td><span class="${levelPillClass(level)}">${level}</span></td>
      <td>${needsReview ? "Yes" : "No"}</td>
      <td>${signals}</td>
      <td class="mono">${escapeHtml(t0)}</td>
    `;
    tbody.appendChild(tr);
  }
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function barHtml(v, cls) {
  const w = Math.round(clamp01(v) * 100);
  return `<div class="bar ${cls}"><span style="width:${w}%"></span></div>`;
}

function showDetail(item) {
  $("detailEmpty").classList.add("hidden");
  $("detailBody").classList.remove("hidden");

  $("detailRepo").textContent = item.repo || "—";
  const level = getRiskLevel(item);
  const pill = $("detailLevel");
  pill.className = `${levelPillClass(level)}`;
  pill.textContent = level;

  const score = getRiskScore(item);
  $("detailScore").textContent = fmt(score, 3);
  $("detailReview").textContent = getNeedsReview(item) ? "Yes" : "No";

  const missing = item?.data_quality?.missing_rate;
  $("detailMissing").textContent = typeof missing === "number" ? fmt(missing * 100, 1) + "%" : "—";

  // signals
  const sigEl = $("detailSignals");
  sigEl.innerHTML = "";
  const signals = Array.isArray(item?.main_signals) ? item.main_signals : [];
  if (signals.length === 0) {
    sigEl.innerHTML = `<div class="aux">无主信号（可能为低风险或数据不足）。</div>`;
  } else {
    for (const s of signals.slice(0, 6)) {
      const name = s.signal_name || s.signal_id || "—";
      const dim = s.dimension || "unknown";
      const strength = Number(s.signal_strength || 0);
      const conf = Number(s.signal_confidence || 0);
      const t0 = s?.time_window?.t0 || s?.when?.start_month || "—";
      const end = s?.when?.end_month || "—";
      const z = s?.is_abnormal?.zscore_12_last;
      const pr = s?.is_abnormal?.percentile_rank_24m_last;
      const meaning = s.governance_meaning || "";

      const card = document.createElement("div");
      card.className = "sig";
      card.innerHTML = `
        <div class="sig-top">
          <div class="sig-name">${escapeHtml(name)}</div>
          <div class="sig-meta">${escapeHtml(dim)} · t0=${escapeHtml(t0)} → ${escapeHtml(end)}</div>
        </div>
        <div class="sig-bars">
          <div>
            <div class="sig-meta">strength ${fmt(strength, 2)}</div>
            ${barHtml(strength, "str")}
          </div>
          <div>
            <div class="sig-meta">confidence ${fmt(conf, 2)}</div>
            ${barHtml(conf, "conf")}
          </div>
        </div>
        <div class="sig-foot">
          ${meaning ? escapeHtml(meaning) : ""}
          <div style="margin-top:6px; color: rgba(169,183,224,.78); font-family: var(--mono)">
            abnormal: z12=${z === null || z === undefined ? "—" : fmt(z, 2)} · p24=${pr === null || pr === undefined ? "—" : fmt(pr, 2)}
          </div>
        </div>
      `;
      sigEl.appendChild(card);
    }
  }

  // aux explain (model)
  const auxEl = $("detailAux");
  const aux = item?.aux_explain || item?.explain || {};
  if (!aux || Object.keys(aux).length === 0) {
    auxEl.innerHTML = `<div class="aux">无模型辅助线索（baseline 或未生成）。</div>`;
    return;
  }

  const parts = [];
  if (Array.isArray(aux.top_metrics) && aux.top_metrics.length) {
    const top = aux.top_metrics.slice(0, 6).map((m) => `${m.metric}: ${fmt(m.score, 3)}`).join("<br/>");
    parts.push(`<div class="aux"><div>Top metrics（grad×input）：</div><div style="margin-top:6px; font-family:var(--mono)">${top}</div></div>`);
  }
  if (Array.isArray(aux.top_signals_lookback) && aux.top_signals_lookback.length) {
    const top = aux.top_signals_lookback
      .slice(0, 6)
      .map((s) => `${s.signal_id} ${s.dimension || ""} score=${fmt(s.score, 1)}`)
      .join("<br/>");
    parts.push(`<div class="aux" style="margin-top:10px"><div>Lookback signals：</div><div style="margin-top:6px; font-family:var(--mono)">${top}</div></div>`);
  }

  if (!parts.length) {
    auxEl.innerHTML = `<div class="aux"><code>${escapeHtml(JSON.stringify(aux).slice(0, 500))}</code></div>`;
  } else {
    auxEl.innerHTML = parts.join("");
  }
}

function applyFilters(allItems) {
  const q = ($("searchInput").value || "").trim().toLowerCase();
  const level = $("levelFilter").value;
  const reviewOnly = $("reviewOnly").checked;

  return allItems.filter((it) => {
    if (q && !(it.repo || "").toLowerCase().includes(q)) return false;
    if (level !== "all" && getRiskLevel(it) !== level) return false;
    if (reviewOnly && !getNeedsReview(it)) return false;
    return true;
  });
}

function computeDims(allItems) {
  const counts = new Map();
  for (const it of allItems) {
    const sigs = Array.isArray(it.main_signals) ? it.main_signals : [];
    for (const s of sigs.slice(0, 5)) {
      const d = s.dimension || "unknown";
      counts.set(d, (counts.get(d) || 0) + 1);
    }
  }
  const arr = Array.from(counts.entries()).map(([label, value]) => ({ label, value }));
  arr.sort((a, b) => b.value - a.value);
  return arr.slice(0, 6);
}

function computeSignals(allItems) {
  const counts = new Map();
  for (const it of allItems) {
    const sigs = Array.isArray(it.main_signals) ? it.main_signals : [];
    for (const s of sigs.slice(0, 6)) {
      const id = s.signal_id || "unknown";
      counts.set(id, (counts.get(id) || 0) + 1);
    }
  }
  const arr = Array.from(counts.entries()).map(([label, value]) => ({ label, value }));
  arr.sort((a, b) => b.value - a.value);
  return arr.slice(0, 8);
}

function computeRiskHist(allItems, bins = 12) {
  const counts = new Array(bins).fill(0);
  for (const it of allItems) {
    const v = clamp01(getRiskScore(it));
    const idx = Math.min(bins - 1, Math.floor(v * bins));
    counts[idx] += 1;
  }
  const items = [];
  for (let i = 0; i < bins; i++) {
    const a = i / bins;
    const b = (i + 1) / bins;
    items.push({ label: `${a.toFixed(2)}-${b.toFixed(2)}`, value: counts[i] });
  }
  return items;
}

function setStatus(text, ok = true) {
  $("statusLine").textContent = text;
  document.querySelector(".dot").style.background = ok ? "rgba(68,209,158,.9)" : "rgba(255,90,122,.9)";
}

async function loadData() {
  setStatus("加载数据中…", true);
  const res = await fetch(DATA_URL, { cache: "no-cache" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();

  const items = Array.isArray(data.items) ? data.items : [];
  const meta = {
    generated_at: data.generated_at || "",
    as_of_month: data.as_of_month || "",
    model: data.model || {},
    count: data.count || items.length,
  };
  return { meta, items };
}

function render(meta, items) {
  const byLevel = { High: 0, Medium: 0, Low: 0 };
  let review = 0;
  let sum = 0;
  for (const it of items) {
    const lvl = getRiskLevel(it);
    if (byLevel[lvl] === undefined) byLevel[lvl] = 0;
    byLevel[lvl] += 1;
    if (getNeedsReview(it)) review += 1;
    sum += getRiskScore(it);
  }

  $("kpiRepos").textContent = String(items.length);
  $("kpiAsOf").textContent = meta.as_of_month ? `as_of ${meta.as_of_month}` : "—";
  $("kpiHigh").textContent = String(byLevel.High || 0);
  $("kpiMid").textContent = String(byLevel.Medium || 0);
  $("kpiLow").textContent = String(byLevel.Low || 0);
  $("kpiReview").textContent = String(review);
  $("kpiAvg").textContent = fmt(sum / Math.max(1, items.length), 3);

  const modelLine = meta.model?.type ? `${meta.model.type}/${meta.model.version || ""}` : "unknown";
  $("metaLine").textContent = `source=${DATA_URL} · as_of=${meta.as_of_month || "—"} · model=${modelLine}`;

  // charts
  const segments = [
    { label: "High", value: byLevel.High || 0, color: "rgba(255,90,122,.92)" },
    { label: "Medium", value: byLevel.Medium || 0, color: "rgba(255,180,84,.92)" },
    { label: "Low", value: byLevel.Low || 0, color: "rgba(68,209,158,.92)" },
  ];
  drawDonut($("donutRisk"), segments);
  makeLegend($("legendRisk"), segments);

  const dims = computeDims(items);
  drawBars($("barDims"), dims);

  const sigs = computeSignals(items);
  drawBars($("barSignals"), sigs);

  const hist = computeRiskHist(items, 12);
  drawBars($("histRisk"), hist);

  // table
  const sorted = [...items].sort((a, b) => getRiskScore(b) - getRiskScore(a));
  const filtered = applyFilters(sorted);
  renderTable(filtered);
  setStatus(`已加载 ${items.length} 个仓库`, true);
}

function setupInteractions(state) {
  const rerender = () => render(state.meta, state.items);
  $("searchInput").addEventListener("input", rerender);
  $("levelFilter").addEventListener("change", rerender);
  $("reviewOnly").addEventListener("change", rerender);
  window.addEventListener("resize", rerender);

  $("fullscreenBtn").addEventListener("click", () => {
    if (document.fullscreenElement) {
      document.exitFullscreen?.();
    } else {
      document.documentElement.requestFullscreen?.();
    }
  });

  $("refreshBtn").addEventListener("click", async () => {
    try {
      const { meta, items } = await loadData();
      state.meta = meta;
      state.items = items;
      rerender();
    } catch (e) {
      console.error(e);
      setStatus(`加载失败：${e.message}`, false);
    }
  });

  $("exportBtn").addEventListener("click", () => {
    const payload = JSON.stringify({ meta: state.meta, items: state.items }, null, 2);
    const blob = new Blob([payload], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "dashboard_export.json";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  });
}

(async function main() {
  const state = { meta: {}, items: [] };
  try {
    const { meta, items } = await loadData();
    state.meta = meta;
    state.items = items;
    setupInteractions(state);
    render(meta, items);
  } catch (e) {
    console.error(e);
    setStatus(`加载失败：${e.message}`, false);
    $("metaLine").textContent = "请用本地 HTTP 服务打开（不要直接 file://）";
  }
})();
