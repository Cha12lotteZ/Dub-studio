// From a web page or Node 18+. A page on another origin needs the server started
// with DUB_CORS_ORIGINS=https://your-site.example
const BASE = "http://localhost:8000";

export async function speak(text, opts = {}) {
  const r = await fetch(`${BASE}/api/v1/speak`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, character: "me", mood: "normal", atmosphere: "none", ...opts }),
  });
  if (!r.ok) throw new Error((await r.json()).detail);
  return await r.blob(); // audio/wav
}

export async function processAudio(fileOrBlob, opts = {}) {
  const fd = new FormData();
  fd.append("audio", fileOrBlob, "line.wav");
  for (const [k, v] of Object.entries(opts)) fd.append(k, String(v));
  const r = await fetch(`${BASE}/api/v1/process`, { method: "POST", body: fd });
  if (!r.ok) throw new Error((await r.json()).detail);
  return await r.blob();
}

// const wav = await speak("หยุดอยู่ตรงนั้น!", { character: "giant", atmosphere: "cave" });
// new Audio(URL.createObjectURL(wav)).play();
