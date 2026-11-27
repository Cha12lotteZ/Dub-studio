// Dub Studio front end. Talks to the FastAPI server in app/main.py.
const $ = (id) => document.getElementById(id);
const S = { catalog: null, project: null, lineId: null, audio: null, raw: null, fx: null, src: null, rec: null };

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  const body = res.headers.get("content-type")?.includes("json") ? await res.json() : null;
  if (!res.ok) throw new Error(body?.detail || `HTTP ${res.status}`);
  return body;
}
const json = (method, data) => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(data ?? {}) });
const fmt = (t) => { const m = Math.floor(t / 60), s = (t % 60).toFixed(1).padStart(4, "0"); return `${String(m).padStart(2, "0")}:${s}`; };
const line = () => S.project?.lines.find((l) => l.id === S.lineId);
const file = (rel) => `/api/projects/${encodeURIComponent(S.project.id)}/files/${rel}`;
const nameOf = (list, id) => (S.catalog[list].find((x) => x.id === id) || {}).name || id;
function busy(el, text) { el.textContent = text; el.dataset.busy = "1"; }
function done(el, text = "") { el.textContent = text; delete el.dataset.busy; }

// ---------- boot ----------
async function boot() {
  S.catalog = await api("/api/catalog");
  renderCatalog();
  const projects = await api("/api/projects");
  renderProjectSelect(projects);
  if (projects.length) await openProject(projects[0].id);
  else { $("empty").hidden = false; $("studio").hidden = true; }
}

function renderCatalog() {
  const c = S.catalog;
  const ms = $("modelSelect");
  ms.innerHTML = `<option value="">ไม่ใช้โมเดล (ใช้เสียงที่อัดตรงๆ)</option>` +
    c.models.map((m) => `<option value="${m.id}">${m.name}</option>`).join("");
  $("modelNote").textContent = !c.ai.voice_model ? "ยังไม่ได้ตั้งค่า Applio สำหรับแปลงเสียง (ดู README) ตอนนี้ใช้ได้เฉพาะเอฟเฟกต์"
    : c.models.length ? "โมเดลจะเปลี่ยนเนื้อเสียง แล้วตัวละคร อารมณ์ บรรยากาศจะปรับต่อ" : "ยังไม่มีโมเดล อัปโหลดได้ที่ช่อง \"สอนเสียงของคุณ\"";
  $("datasetNote").textContent = `เก็บไว้แล้ว ${c.dataset.takes} เทค (${c.dataset.minutes} นาที) แนะนำอย่างน้อย 10 นาทีสำหรับเทรนรอบแรก`;
  $("separateBtn").disabled = !c.ai.separate;
  $("transcribeBtn").disabled = !c.ai.transcribe;
  $("ttsBtn").disabled = !c.ai.tts;
  const missing = [!c.ai.separate && "แยกเสียง", !c.ai.transcribe && "ถอดบท", !c.ai.tts && "พิมพ์บทให้พูด"].filter(Boolean);
  $("aiStatus").textContent = missing.length ? `ยังใช้ไม่ได้: ${missing.join(", ")} (ติดตั้ง requirements-ai.txt)` : "";
  if (!c.ai.ffmpeg) $("aiStatus").textContent = "ไม่พบ ffmpeg ในเครื่อง กรุณาติดตั้งก่อน";
}

function renderProjectSelect(projects) {
  $("projectSelect").innerHTML = projects.map((p) => `<option value="${p.id}">${p.name}</option>`).join("");
  $("deleteProjectBtn").hidden = !projects.length;
}

async function openProject(id) {
  S.project = await api(`/api/projects/${encodeURIComponent(id)}`);
  $("projectSelect").value = id;
  $("empty").hidden = true; $("studio").hidden = false;
  const v = $("video");
  if (S.project.video) { v.src = file(S.project.video); v.hidden = false; $("noVideo").hidden = true; }
  else { v.removeAttribute("src"); v.hidden = true; $("noVideo").hidden = false; }
  $("separateBtn").textContent = S.project.original_voice ? "แยกเสียงแล้ว ✓" : "แยกเสียงพูดเดิมออก";
  S.lineId = S.project.lines[0]?.id || null;
  renderExport();
  renderLines(); await loadLine();
}

// ---------- lines ----------
function renderLines() {
  const L = $("lines");
  if (!S.project.lines.length) {
    L.innerHTML = `<p class="note">ยังไม่มีบท กด "ถอดบทอัตโนมัติ" หรือเล่นวิดีโอไปถึงจุดที่ต้องการแล้วกด "+ เพิ่มบรรทัด"</p>`;
    return;
  }
  L.innerHTML = "";
  for (const l of S.project.lines) {
    const b = document.createElement("button");
    b.className = "line"; b.setAttribute("aria-current", l.id === S.lineId);
    const s = l.settings;
    const tag = l.fx ? (l.kept ? `<span class="tag ok">เก็บแล้ว</span>` : `<span class="tag ok">พากแล้ว</span>`) : `<span class="tag todo">ยังไม่พาก</span>`;
    b.innerHTML = `<time>${fmt(l.start)}</time><span class="txt"><span class="who">${esc(l.who || "—")} · ${nameOf("characters", s.character)} · ${nameOf("moods", s.mood)} · ${nameOf("atmospheres", s.atmosphere)}${l.model ? " · " + esc(l.model) : ""}</span><br>${esc(l.text) || "<em>(ยังไม่มีบท)</em>"}</span>${tag}`;
    b.onclick = async () => { S.lineId = l.id; renderLines(); await loadLine(); seek(l.start); };
    L.appendChild(b);
  }
}
const esc = (t) => String(t ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

async function loadLine() {
  const l = line();
  $("editor").hidden = !l;
  if (!l) return;
  $("lStart").value = l.start; $("lEnd").value = l.end; $("lWho").value = l.who; $("lText").value = l.text;
  $("modelSelect").value = l.model || "";
  renderControls();
  $("subLine").textContent = l.text;
  S.raw = l.raw ? await decode(file(l.raw)) : null;
  S.fx = l.fx ? await decode(file(l.fx)) : null;
  draw(S.fx || S.raw);
  $("playFx").disabled = !S.fx; $("playRaw").disabled = !S.raw;
  $("keepBtn").disabled = !l.raw || l.kept || l.source === "tts";
  $("keepBtn").textContent = l.kept ? "เก็บแล้ว ✓" : "👍 เก็บเทคนี้ไว้สอนเสียง";
  $("fxStatus").textContent = S.fx ? `พร้อมฟัง · ${S.fx.duration.toFixed(1)} วินาที` : "ยังไม่มีเสียง อัดเสียงหรือพิมพ์บทให้พูด";
}

function renderControls() {
  const l = line(); if (!l) return;
  const s = l.settings;
  chips($("chars"), S.catalog.characters, "character", s.character);
  chips($("moods"), S.catalog.moods, "mood", s.mood);
  chips($("ambs"), S.catalog.atmospheres, "atmosphere", s.atmosphere);
  const p = s.pitch ?? S.catalog.characters.find((c) => c.id === s.character).pitch;
  $("pitch").value = p; $("pitchOut").textContent = p > 0 ? `+${p}` : p;
  $("mix").value = Math.round(s.mix * 100); $("mixOut").textContent = `${Math.round(s.mix * 100)}%`;
}

function chips(el, list, key, current) {
  el.innerHTML = "";
  for (const o of list) {
    const b = document.createElement("button");
    b.className = "chip"; b.textContent = o.name; b.setAttribute("aria-pressed", o.id === current);
    b.onclick = () => changeSettings(key === "character" ? { character: o.id, pitch: null } : { [key]: o.id });
    el.appendChild(b);
  }
}

let renderTimer = null;
async function changeSettings(patch, delay = 0) {
  const l = line(); if (!l) return;
  Object.assign(l.settings, patch); renderControls(); renderLines();
  clearTimeout(renderTimer);
  renderTimer = setTimeout(async () => {
    const updated = await api(`/api/projects/${S.project.id}/lines/${l.id}`, json("PATCH", { settings: patch }));
    Object.assign(l, updated);
    if (l.raw) await rerender();
  }, delay);
}

async function rerender() {
  const l = line();
  busy($("fxStatus"), "กำลังปรับเสียง…");
  try {
    Object.assign(l, await api(`/api/projects/${S.project.id}/lines/${l.id}/render`, { method: "POST" }));
    await loadLine(); renderLines();
  } catch (e) { done($("fxStatus"), e.message); }
}

async function saveLineFields() {
  const l = line(); if (!l) return;
  const body = { start: +$("lStart").value, end: +$("lEnd").value, who: $("lWho").value, text: $("lText").value };
  Object.assign(l, await api(`/api/projects/${S.project.id}/lines/${l.id}`, json("PATCH", body)));
  S.project.lines.sort((a, b) => a.start - b.start);
  renderLines(); $("subLine").textContent = l.text;
}
["lStart", "lEnd", "lWho", "lText"].forEach((id) => $(id).addEventListener("change", saveLineFields));

$("pitch").oninput = (e) => { $("pitchOut").textContent = e.target.value; changeSettings({ pitch: +e.target.value }, 400); };
$("mix").oninput = (e) => { $("mixOut").textContent = e.target.value + "%"; changeSettings({ mix: e.target.value / 100 }, 400); };
$("modelSelect").onchange = async (e) => {
  const l = line(); if (!l) return;
  Object.assign(l, await api(`/api/projects/${S.project.id}/lines/${l.id}`, json("PATCH", { model: e.target.value || null })));
  renderLines(); if (l.raw) await rerender();
};

$("addLineBtn").onclick = async () => {
  const t = $("video").currentTime || (S.project.lines.at(-1)?.end ?? 0);
  const l = await api(`/api/projects/${S.project.id}/lines`, json("POST", { start: +t.toFixed(2), end: +(t + 2).toFixed(2) }));
  S.project.lines.push(l); S.project.lines.sort((a, b) => a.start - b.start);
  S.lineId = l.id; renderLines(); await loadLine(); $("lText").focus();
};
$("lDelete").onclick = async () => {
  const l = line(); if (!l) return;
  await api(`/api/projects/${S.project.id}/lines/${l.id}`, { method: "DELETE" });
  S.project.lines = S.project.lines.filter((x) => x.id !== l.id);
  S.lineId = S.project.lines[0]?.id || null; renderLines(); await loadLine();
};

// ---------- takes: record / upload / tts ----------
async function sendTake(blob, filename) {
  const l = line();
  busy($("recStatus"), "กำลังแปลงเสียง…");
  const fd = new FormData(); fd.append("audio", blob, filename);
  try {
    Object.assign(l, await api(`/api/projects/${S.project.id}/lines/${l.id}/take`, { method: "POST", body: fd }));
    done($("recStatus")); await loadLine(); renderLines();
  } catch (e) { done($("recStatus"), e.message); }
}

$("recBtn").onclick = async () => {
  if (S.rec) { S.rec.stop(); return; }
  let stream;
  try { stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: true } }); }
  catch { $("recStatus").textContent = "เปิดไมค์ไม่ได้ ตรวจสอบการอนุญาตไมค์ในเบราว์เซอร์"; return; }
  const chunks = []; const rec = new MediaRecorder(stream);
  rec.ondataavailable = (e) => chunks.push(e.data);
  rec.onstop = () => {
    stream.getTracks().forEach((t) => t.stop()); S.rec = null;
    $("recBtn").classList.remove("on"); $("recBtn").textContent = "● อัดเสียง";
    sendTake(new Blob(chunks, { type: rec.mimeType }), "take.webm");
  };
  S.rec = rec; rec.start();
  $("recBtn").classList.add("on"); $("recBtn").textContent = "■ หยุดอัด";
  $("recStatus").textContent = "กำลังอัด… ดูวิดีโอแล้วพูดตามจังหวะ";
  const l = line(); if (l) { seek(l.start); playVideo(); }
};
$("takeFile").onchange = (e) => { const f = e.target.files[0]; if (f) sendTake(f, f.name); e.target.value = ""; };

$("ttsBtn").onclick = async () => {
  const l = line(); const text = $("lText").value.trim();
  if (!text) { $("fxStatus").textContent = "พิมพ์บทในช่อง \"บท\" ก่อน"; return; }
  busy($("fxStatus"), "กำลังสร้างเสียงจากบท (บน CPU อาจใช้เวลา 10–30 วินาที)…");
  try {
    Object.assign(l, await api(`/api/projects/${S.project.id}/lines/${l.id}/tts`, json("POST", { text })));
    await loadLine(); renderLines();
  } catch (e) { done($("fxStatus"), e.message); }
};

$("keepBtn").onclick = async () => {
  const l = line();
  const r = await api(`/api/projects/${S.project.id}/lines/${l.id}/keep`, { method: "POST" });
  Object.assign(l, r.line); S.catalog.dataset = r.dataset; renderCatalog(); await loadLine(); renderLines();
  $("fxStatus").textContent = "เก็บแล้ว เทคนี้จะใช้เทรนโมเดลเสียงรุ่นถัดไป";
};

$("tabSpeak").onclick = () => tab(true); $("tabType").onclick = () => tab(false);
function tab(speak) {
  $("tabSpeak").setAttribute("aria-selected", speak); $("tabType").setAttribute("aria-selected", !speak);
  $("paneSpeak").hidden = !speak; $("paneType").hidden = speak;
}

// ---------- playback ----------
function ctx() { return (S.audio ||= new (window.AudioContext || window.webkitAudioContext)()); }
async function decode(url) {
  try { return await ctx().decodeAudioData(await (await fetch(url)).arrayBuffer()); } catch { return null; }
}
function seek(t) { const v = $("video"); if (S.project.video) v.currentTime = t; }
function playVideo() { const v = $("video"); if (!S.project.video) return; v.muted = $("muteOriginal").checked; v.play(); }
function play(buf) {
  stop(); if (!buf) return;
  const c = ctx(); c.resume();
  S.src = c.createBufferSource(); S.src.buffer = buf; S.src.connect(c.destination);
  const l = line(); if (l) seek(l.start);
  S.src.start(); playVideo();
  S.src.onended = () => $("video").pause();
}
function stop() { try { S.src?.stop(); } catch {} S.src = null; $("video").pause(); }
$("playFx").onclick = () => play(S.fx); $("playRaw").onclick = () => play(S.raw); $("stopBtn").onclick = stop;

$("video").addEventListener("timeupdate", () => {
  const t = $("video").currentTime;
  const cur = S.project?.lines.find((l) => t >= l.start && t <= l.end);
  $("subLine").textContent = cur ? cur.text : "";
});

function draw(buf) {
  const cv = $("wave"), g = cv.getContext("2d"), W = cv.width, H = cv.height;
  const css = getComputedStyle(document.documentElement);
  g.clearRect(0, 0, W, H);
  if (!buf) { g.fillStyle = css.getPropertyValue("--line"); g.fillRect(0, H / 2, W, 1); return; }
  const d = buf.getChannelData(0), step = Math.ceil(d.length / W);
  g.fillStyle = css.getPropertyValue("--wave").trim();
  for (let x = 0; x < W; x++) {
    let mn = 1, mx = -1;
    for (let j = 0; j < step; j++) { const v = d[x * step + j] || 0; if (v < mn) mn = v; if (v > mx) mx = v; }
    g.fillRect(x, (1 + mn) * H / 2, 1, Math.max(1, (mx - mn) * H / 2));
  }
}

// ---------- AI steps ----------
$("separateBtn").onclick = async () => {
  busy($("aiStatus"), "กำลังแยกเสียงพูดเดิมออกจากดนตรีและเอฟเฟกต์ (บน CPU ใช้เวลาประมาณเท่าความยาววิดีโอ)…");
  try { S.project = await api(`/api/projects/${S.project.id}/separate`, { method: "POST" }); done($("aiStatus"), "แยกเสียงแล้ว ตอนส่งออกจะใช้เฉพาะดนตรีและเอฟเฟกต์เป็นพื้นหลัง"); $("separateBtn").textContent = "แยกเสียงแล้ว ✓"; }
  catch (e) { done($("aiStatus"), e.message); }
};
$("transcribeBtn").onclick = async () => {
  if (S.project.lines.length && !(await confirmInline("ถอดบทใหม่จะแทนที่บทเดิมทั้งหมด กดอีกครั้งเพื่อยืนยัน"))) return;
  busy($("aiStatus"), "กำลังถอดบท…");
  try { S.project = await api(`/api/projects/${S.project.id}/transcribe`, { method: "POST" }); S.lineId = S.project.lines[0]?.id; renderLines(); await loadLine(); done($("aiStatus"), `ถอดบทได้ ${S.project.lines.length} บรรทัด`); }
  catch (e) { done($("aiStatus"), e.message); }
};
let armed = null;
function confirmInline(msg) {
  if (armed && Date.now() - armed < 5000) { armed = null; return Promise.resolve(true); }
  armed = Date.now(); $("aiStatus").textContent = msg; return Promise.resolve(false);
}

// ---------- export ----------
function renderExport() {
  const p = S.project, out = $("exportOut");
  if (!p.export) { out.innerHTML = ""; return; }
  const url = file(p.export) + `?t=${p.exported_at}`;
  out.innerHTML = p.export.endsWith(".mp4")
    ? `<video class="export-video" controls src="${url}"></video><a class="btn ghost" href="${url}" download>ดาวน์โหลดวิดีโอ</a>`
    : `<audio controls src="${url}"></audio> <a class="btn ghost" href="${url}" download>ดาวน์โหลดเสียง</a>`;
}
$("exportBtn").onclick = async () => {
  busy($("exportStatus"), "กำลังรวมเสียง…");
  try { S.project = await api(`/api/projects/${S.project.id}/export`, { method: "POST" }); renderExport(); done($("exportStatus"), "เสร็จแล้ว"); }
  catch (e) { done($("exportStatus"), e.message); }
};

// ---------- projects & models ----------
const dlg = $("newProjectDlg");
$("newProjectBtn").onclick = $("emptyNew").onclick = () => dlg.showModal();
$("newProjectForm").addEventListener("submit", async (e) => {
  if (e.submitter?.value !== "create") return;
  e.preventDefault();
  const fd = new FormData(); fd.append("name", $("npName").value);
  if ($("npVideo").files[0]) fd.append("video", $("npVideo").files[0]);
  busy($("npStatus"), "กำลังอัปโหลด…");
  try {
    const p = await api("/api/projects", { method: "POST", body: fd });
    done($("npStatus")); dlg.close();
    renderProjectSelect(await api("/api/projects")); await openProject(p.id);
  } catch (err) { done($("npStatus"), err.message); }
});
$("projectSelect").onchange = (e) => openProject(e.target.value);
$("deleteProjectBtn").onclick = async () => {
  if (!S.project) return;
  const b = $("deleteProjectBtn");
  if (b.dataset.armed) {
    await api(`/api/projects/${S.project.id}`, { method: "DELETE" });
    delete b.dataset.armed; b.textContent = "ลบ";
    const ps = await api("/api/projects"); renderProjectSelect(ps);
    if (ps.length) await openProject(ps[0].id); else { S.project = null; $("empty").hidden = false; $("studio").hidden = true; }
  } else { b.dataset.armed = "1"; b.textContent = "กดอีกครั้งเพื่อลบ"; setTimeout(() => { delete b.dataset.armed; b.textContent = "ลบ"; }, 4000); }
};
$("modelForm").onsubmit = async (e) => {
  e.preventDefault();
  const fd = new FormData(); fd.append("name", $("mName").value); fd.append("pth", $("mPth").files[0]);
  if ($("mIndex").files[0]) fd.append("index", $("mIndex").files[0]);
  busy($("modelStatus"), "กำลังอัปโหลด…");
  try { await api("/api/models", { method: "POST", body: fd }); S.catalog = await api("/api/catalog"); renderCatalog(); await loadLine(); done($("modelStatus"), "อัปโหลดแล้ว เลือกใช้ได้ที่ \"โมเดลเสียง\""); e.target.reset(); }
  catch (err) { done($("modelStatus"), err.message); }
};

boot().catch((e) => { document.body.insertAdjacentHTML("afterbegin", `<p class="status" style="color:var(--tally)">เชื่อมต่อเซิร์ฟเวอร์ไม่ได้: ${esc(e.message)}</p>`); });
