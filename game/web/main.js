import * as THREE from "./three.module.min.js";

// ---- palette (Ticket-02) ----
const PAL = { sky: 0x0E1430, mist: 0x1B2350, grass: 0x2F5D50, sand: 0xC9B48A, wood: 0x6B4A2F, sea: 0x12384A,
  lampOn: 0xFFB347, lampCore: 0xFFE9B0, lampOff: 0x5B5F6E, mote: 0xFFF6C2, halo: 0xFFE58A,
  shade: 0x120A1A, outline: 0x7A3CFF, stunned: 0x3A3450, coat: 0xE8E2D0, scarf: 0xC8102E,
  gold: 0xF2C14E, drifter: 0x8FA3B8 };
const NEED = { 1: 3, 2: 4, 3: 5 };
const NAMES = { 1: "Đêm 1 · Đảo Bến", 2: "Đêm 2 · Đảo Cau", 3: "Đêm 3 · Đảo Chuông" };
const INTRO = {
  1: "Ông Đăng: \"Đèn Lồng nào cũng cạn dầu, cháu ạ. Giữ ít nhất 3 trong 5 ngọn còn sáng tới bình minh; châm dầu bằng đom đóm, và coi chừng Bóng Mực hút dầu.\"",
  2: "Ông Đăng: \"Hai hòn đảo, sáu ngọn đèn: cần giữ sáng ít nhất 4. Bục nhảy đưa cháu qua cầu; Gió Lạc thì tham đom đóm lắm.\"",
  3: "Ông Đăng: \"Đảo Chuông có ba tầng, dốc và gió mạnh. Bảy ngọn đèn, cần giữ sáng ít nhất 5 tới bình minh.\"" };
const $ = id => document.getElementById(id);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const Q = new URLSearchParams(location.search);
const BENCH = Q.has("bench"), BENCH_DUR = +(Q.get("duration") || 30);

// ---- settings (persisted) ----
const ACTIONS = [["up", "Đi lên"], ["down", "Đi xuống"], ["left", "Sang trái"], ["right", "Sang phải"], ["jump", "Nhảy"],
  ["dash", "Lướt"], ["interact", "Tương tác"], ["pulse", "Tỏa Sáng"], ["pause", "Tạm dừng"]];
const DEFAULT_KEYS = { up: "KeyW", down: "KeyS", left: "KeyA", right: "KeyD", jump: "Space", dash: "Shift",
  interact: "KeyE", pulse: "KeyF", pause: "Escape" };
let settings = { vol: 60, sens: 40, cb: false, rm: false, big: false, keys: { ...DEFAULT_KEYS } };
try { const o = JSON.parse(localStorage.getItem("ddl-settings") || "{}"); Object.assign(settings, o); settings.keys = { ...DEFAULT_KEYS, ...(o.keys || {}) }; } catch (e) {}
function saveSettings() { try { localStorage.setItem("ddl-settings", JSON.stringify(settings)); } catch (e) {} }
const norm = c => c.startsWith("Shift") ? "Shift" : c.startsWith("Control") ? "Control" : c.startsWith("Alt") ? "Alt" : c;
function keyName(c) {
  if (c.startsWith("Key")) return c.slice(3); if (c.startsWith("Digit")) return c.slice(5);
  return ({ Space: "Space", Escape: "Esc", ArrowUp: "↑", ArrowDown: "↓", ArrowLeft: "←", ArrowRight: "→", Shift: "Shift", Control: "Ctrl", Alt: "Alt" })[c] || c;
}
$("vol").value = settings.vol; $("sens").value = settings.sens;
for (const k of ["cb", "rm", "big"]) $(k).checked = !!settings[k];
const syncSet = () => { $("volV").textContent = settings.vol; $("sensV").textContent = settings.sens; };
syncSet();
$("vol").oninput = e => { settings.vol = +e.target.value; syncSet(); saveSettings(); applyVol(); };
$("sens").oninput = e => { settings.sens = +e.target.value; syncSet(); saveSettings(); };
$("cb").onchange = e => { settings.cb = e.target.checked; saveSettings(); applyCB(); };
$("rm").onchange = e => { settings.rm = e.target.checked; saveSettings(); };
$("big").onchange = e => { settings.big = e.target.checked; saveSettings(); applyScale(); };
function applyScale() { document.documentElement.style.setProperty("--scale", settings.big ? "1.25" : "1"); }
applyScale();

// ---- audio (synthesised, no external assets) ----
let ac = null, master = null, musicOn = false;
function initAudio() {
  if (ac) { if (ac.state === "suspended") ac.resume(); return; }
  try { ac = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { return; }
  master = ac.createGain(); master.connect(ac.destination); applyVol(); startMusic();
}
function applyVol() { if (master) master.gain.value = settings.vol / 100 * 0.5; }
function tone(freq, dur, type = "sine", vol = 0.3, slide = 0, delay = 0) {
  if (!ac) return;
  const t0 = ac.currentTime + delay, o = ac.createOscillator(), g = ac.createGain();
  o.type = type; o.frequency.setValueAtTime(freq, t0);
  if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(30, freq + slide), t0 + dur);
  g.gain.setValueAtTime(vol, t0); g.gain.exponentialRampToValueAtTime(0.001, t0 + dur);
  o.connect(g); g.connect(master); o.start(t0); o.stop(t0 + dur + 0.02);
}
const SFX = {
  pick: () => tone(880, .12, "sine", .25, 600), light: () => { tone(523, .3, "triangle", .3); tone(784, .4, "triangle", .3, 0, .12); },
  pulse: () => tone(300, .5, "sine", .4, 500), hit: () => tone(140, .35, "sawtooth", .35, -90),
  jump: () => tone(300, .15, "square", .12, 250), dash: () => tone(500, .18, "sawtooth", .12, -300),
  win: () => [523, 659, 784, 1047].forEach((f, i) => tone(f, .35, "triangle", .3, 0, i * .15)),
  lose: () => [400, 330, 262, 196].forEach((f, i) => tone(f, .4, "sawtooth", .2, 0, i * .2)),
  spawn: () => tone(110, .6, "sawtooth", .18, -40), tick: () => tone(1000, .08, "square", .18),
  steal: () => tone(700, .25, "sawtooth", .2, -400), charm: () => { tone(660, .15, "sine", .3); tone(990, .25, "sine", .3, 0, .1); }
};
function startMusic() {
  if (musicOn) return; musicOn = true;
  const notes = [220, 261.6, 329.6, 392, 329.6, 261.6, 196, 246.9]; let i = 0;
  setInterval(() => { if (ac && ac.state === "running") tone(notes[i++ % notes.length] / 2, 1.6, "sine", .09); }, 1200);
}
addEventListener("pointerdown", initAudio, { once: true });
addEventListener("keydown", initAudio, { once: true });

// ---- scene ----
const scene = new THREE.Scene();
scene.background = new THREE.Color(PAL.sky);
scene.fog = new THREE.Fog(PAL.mist, 40, 160);
const camera = new THREE.PerspectiveCamera(60, innerWidth / innerHeight, 0.1, 400);
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
renderer.setPixelRatio(BENCH ? 1 : Math.min(devicePixelRatio, 1.5));
renderer.setSize(BENCH ? 1280 : innerWidth, BENCH ? 720 : innerHeight);     // the benchmark always renders 1280x720
if (BENCH) { camera.aspect = 1280 / 720; camera.updateProjectionMatrix(); }
document.body.appendChild(renderer.domElement);
addEventListener("resize", () => { if (BENCH) return; camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });
const ambient = new THREE.AmbientLight(0xffffff, 0.15); scene.add(ambient);
const moon = new THREE.DirectionalLight(0x9fb0ff, 0.8); moon.position.set(-30, 60, 20); scene.add(moon);
const lam = (c, o = {}) => new THREE.MeshLambertMaterial({ color: c, ...o });
const bas = (c, o = {}) => new THREE.MeshBasicMaterial({ color: c, ...o });

const world = new THREE.Group(); scene.add(world);
const sea = new THREE.Mesh(new THREE.PlaneGeometry(600, 600), lam(PAL.sea)); sea.rotation.x = -Math.PI / 2; sea.position.y = -6; scene.add(sea);

// Mây: coat, red scarf, conical hat with a small lantern
const may = new THREE.Group();
const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.4, 0.7, 4, 10), lam(PAL.coat)); body.position.y = 0.75; may.add(body);
const scarf = new THREE.Mesh(new THREE.TorusGeometry(0.38, 0.1, 6, 14), lam(PAL.scarf)); scarf.rotation.x = Math.PI / 2; scarf.position.y = 1.2; may.add(scarf);
const hat = new THREE.Mesh(new THREE.ConeGeometry(0.6, 0.8, 12), lam(PAL.wood)); hat.position.y = 1.7; may.add(hat);
const hatLamp = new THREE.Mesh(new THREE.SphereGeometry(0.13, 8, 8), bas(PAL.lampOn)); hatLamp.position.set(0.5, 1.4, 0); may.add(hatLamp);
const mayLight = new THREE.PointLight(PAL.lampOn, 1.4, 16); mayLight.position.y = 1.6; may.add(mayLight);
scene.add(may);
const ring = new THREE.Mesh(new THREE.RingGeometry(0.92, 1, 48), bas(PAL.halo, { transparent: true, side: THREE.DoubleSide }));
ring.rotation.x = -Math.PI / 2; ring.visible = false; scene.add(ring);

// shades and motes are instanced: 4 draw calls for any number of Bóng Mực, 2 for all fireflies
const MAXS = 256, MAXM = 192;
const shadeGeo = new THREE.IcosahedronGeometry(0.62, 1), outlineGeo = new THREE.IcosahedronGeometry(0.74, 1);
const outlineMat = bas(PAL.outline, { side: THREE.BackSide }), eyeMat = bas(PAL.outline);
const eyeGeo = new THREE.SphereGeometry(0.1, 8, 8);
const shadeBody = new THREE.InstancedMesh(shadeGeo, lam(0xffffff, { emissive: 0x1a0d2a }), MAXS);
const shadeOut = new THREE.InstancedMesh(outlineGeo, outlineMat, MAXS);
const shadeEyes = new THREE.InstancedMesh(eyeGeo, eyeMat, MAXS * 2);
const moteBody = new THREE.InstancedMesh(new THREE.SphereGeometry(0.16, 8, 8), bas(PAL.mote), MAXM);
const moteHalo = new THREE.InstancedMesh(new THREE.SphereGeometry(0.34, 8, 8), bas(PAL.halo, { transparent: true, opacity: 0.35 }), MAXM);
const cShade = new THREE.Color(PAL.shade), cStun = new THREE.Color(PAL.stunned);
for (const m of [shadeBody, shadeOut, shadeEyes, moteBody, moteHalo]) { m.frustumCulled = false; m.count = 0; scene.add(m); }
shadeBody.setColorAt(0, cShade);
const eyeL = new THREE.Matrix4().makeTranslation(-0.2, 0.15, 0.55), eyeR = new THREE.Matrix4().makeTranslation(0.2, 0.15, 0.55);
const _m = new THREE.Matrix4(), _e = new THREE.Matrix4(), _p = new THREE.Vector3(), _q = new THREE.Quaternion(), _s = new THREE.Vector3(), _up = new THREE.Vector3(0, 1, 0);

function applyCB() {
  const cb = !!settings.cb;
  outlineMat.color.setHex(cb ? 0x00B3FF : PAL.outline); eyeMat.color.setHex(cb ? 0x00B3FF : PAL.outline);
  document.documentElement.style.setProperty("--danger", cb ? "#FFFFFF" : "#FF5A5F");
}
applyCB();
const leaves = []; for (let i = 0; i < 40; i++) { const m = new THREE.Mesh(new THREE.PlaneGeometry(.4, .25), bas(0x6fae7a, { side: THREE.DoubleSide })); m.visible = false; scene.add(m); leaves.push(m); }

const lanternObjs = {}, drifterObjs = new Map(), charmObjs = new Map();
let builtNight = 0;
function clearWorld() {
  world.clear(); for (const k in lanternObjs) { scene.remove(lanternObjs[k].g); delete lanternObjs[k]; }
  for (const mp of [drifterObjs, charmObjs]) { for (const m of mp.values()) scene.remove(m); mp.clear(); }
}
function island(cx, cz, r) {
  const g = new THREE.Mesh(new THREE.CylinderGeometry(r, r, 1, 56), lam(PAL.grass)); g.position.set(cx, -0.5, cz); world.add(g);
  const rim = new THREE.Mesh(new THREE.TorusGeometry(r, 0.35, 6, 64), lam(PAL.sand)); rim.rotation.x = Math.PI / 2; rim.position.set(cx, -0.05, cz); world.add(rim);
}
function pad(x, y, z) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(1, 1, 0.2, 24), lam(PAL.lampOn, { emissive: 0x6b3d00 })); m.position.set(x, y + 0.1, z); world.add(m);
  const r = new THREE.Mesh(new THREE.TorusGeometry(1.1, 0.08, 6, 24), bas(PAL.lampCore)); r.rotation.x = Math.PI / 2; r.position.set(x, y + 0.25, z); world.add(r);
}
function buildNight(n) {
  clearWorld(); builtNight = n;
  if (n === 1) island(0, 0, 40);
  if (n === 2) {
    island(0, 0, 28); island(70, 0, 28);
    const b = new THREE.Mesh(new THREE.BoxGeometry(18, 0.3, 4), lam(PAL.wood)); b.position.set(35, -0.15, 0); world.add(b);
    pad(20, 0, 18); pad(50, 0, -18);
  }
  if (n === 3) {
    island(0, 0, 45);
    const sh = new THREE.Shape(); sh.absarc(0, 0, 24, 0, Math.PI, false); sh.absarc(0, 0, 12, Math.PI, 0, true);
    const t1 = new THREE.Mesh(new THREE.ExtrudeGeometry(sh, { depth: 3, bevelEnabled: false, curveSegments: 40 }), lam(PAL.grass));
    t1.rotation.x = Math.PI / 2; t1.position.y = 3; world.add(t1);
    const t2 = new THREE.Mesh(new THREE.CylinderGeometry(8, 8, 6, 40), lam(PAL.grass)); t2.position.y = 3; world.add(t2);
    const tower = new THREE.Mesh(new THREE.CylinderGeometry(2, 2, 8, 20), lam(PAL.wood)); tower.position.y = 10; world.add(tower);
    const bell = new THREE.Mesh(new THREE.ConeGeometry(1.2, 1.4, 16), lam(PAL.gold)); bell.position.y = 14.7; world.add(bell);
    for (const a of [30, 150]) {
      const r = a * Math.PI / 180, L = Math.hypot(6, 3);
      const piv = new THREE.Group(); piv.position.set(27 * Math.cos(r), 1.5, 27 * Math.sin(r)); piv.rotation.y = Math.PI / 2 - r;
      const m = new THREE.Mesh(new THREE.BoxGeometry(3, 0.3, L), lam(PAL.sand)); m.rotation.x = Math.atan2(3, 6); piv.add(m); world.add(piv);
    }
    pad(0, 3, 13);
  }
}
function makeLantern() {
  const g = new THREE.Group();
  const pillar = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.35, 2.6, 8), lam(PAL.wood)); pillar.position.y = 1.3; g.add(pillar);
  const orb = new THREE.Mesh(new THREE.SphereGeometry(0.7, 16, 16), bas(PAL.lampOff)); orb.position.y = 3.2; g.add(orb);
  const core = new THREE.Mesh(new THREE.SphereGeometry(0.35, 10, 10), bas(PAL.lampCore)); core.position.y = 3.2; core.visible = false; g.add(core);
  // torn paper: a dark notch that is visible only while the lantern is out (readable without colour)
  const tear = new THREE.Mesh(new THREE.ConeGeometry(0.28, 0.5, 3), bas(0x14141c)); tear.position.set(0.45, 3.1, 0.45); tear.rotation.set(0.4, 0, -0.9); g.add(tear);
  const light = new THREE.PointLight(PAL.lampOn, 0, 22); light.position.y = 3.4; g.add(light);
  const zone = new THREE.Mesh(new THREE.RingGeometry(5.85, 6, 64), bas(PAL.lampOn, { transparent: true, opacity: 0, side: THREE.DoubleSide }));
  zone.rotation.x = -Math.PI / 2; zone.position.y = 0.06; g.add(zone);
  const bar = new THREE.Group(); bar.position.y = 4.5;
  bar.add(new THREE.Mesh(new THREE.PlaneGeometry(1.6, 0.22), bas(0x14141c)));
  const fill = new THREE.Mesh(new THREE.PlaneGeometry(1.5, 0.14), bas(PAL.lampOn)); fill.position.z = 0.01; bar.add(fill);
  g.add(bar);
  scene.add(g); return { g, orb, core, light, zone, tear, bar, fill };
}
function makeDrifter() {
  const g = new THREE.Group();
  for (let i = 0; i < 3; i++) { const m = new THREE.Mesh(new THREE.PlaneGeometry(1.6, 0.35), bas(PAL.drifter, { side: THREE.DoubleSide, transparent: true, opacity: 0.85 })); m.position.z = -i * 0.5; g.add(m); }
  scene.add(g); return g;
}
function makeCharm() {
  const g = new THREE.Group();
  g.add(new THREE.Mesh(new THREE.BoxGeometry(0.9, 1.2, 0.06), bas(PAL.gold)));
  g.add(new THREE.Mesh(new THREE.BoxGeometry(0.72, 1.02, 0.08), bas(PAL.scarf)));
  scene.add(g); return g;
}
function sync(map, items, make, upd) {
  const seen = new Set();
  for (const it of items) { seen.add(it.id); let m = map.get(it.id); if (!m) { m = make(it); map.set(it.id, m); } upd(m, it); }
  for (const [id, m] of map) if (!seen.has(id)) { scene.remove(m); map.delete(id); }
}

// ---- input (rebindable) ----
const held = new Set();
let yaw = 0, dragging = false, capturing = null;
const latch = { jump: 0, interact: 0, pulse: 0, dash: 0 };
let S = { phase: "menu" }, seq = 0;
function post(path, body) { return fetch(path, { method: "POST", body: JSON.stringify(body || {}) }).catch(() => null); }
const cmd = c => post("/cmd", { cmd: c });
const K = () => settings.keys;
addEventListener("keydown", e => {
  if (e.target && (e.target.tagName === "INPUT" && e.target.type === "text")) return;
  if (capturing) { e.preventDefault(); captureKey(norm(e.code)); return; }
  if (e.repeat) return;
  const code = norm(e.code), now = performance.now();
  held.add(code);
  const k = K();
  if (code === k.jump) latch.jump = now + 90;
  if (code === k.interact) latch.interact = now + 90;
  if (code === k.pulse) latch.pulse = now + 90;
  if (code === k.dash) latch.dash = now + 90;
  if (code === k.pause && S.phase === "playing" && !BENCH) cmd("pause");
  if (code === "KeyR" && S.phase === "result" && !Object.values(k).includes("KeyR")) cmd("retry");
  if (code.startsWith("Arrow") || code === "Space") e.preventDefault();
});
addEventListener("keyup", e => held.delete(norm(e.code)));
addEventListener("mousedown", () => dragging = true);
addEventListener("mouseup", () => dragging = false);
addEventListener("mousemove", e => { if (dragging) yaw += e.movementX * settings.sens / 100; });
if (!BENCH) setInterval(() => {
  const now = performance.now(), k = K();
  if (held.has("ArrowLeft")) yaw -= 1.8; if (held.has("ArrowRight")) yaw += 1.8;
  // the camera looks toward +Z at yaw 0, so screen-right is -X in the contract's input space
  const move = [(held.has(k.left) ? 1 : 0) - (held.has(k.right) ? 1 : 0), (held.has(k.up) ? 1 : 0) - (held.has(k.down) ? 1 : 0)];
  post("/input", { move, yaw, jump: now < latch.jump, interact: now < latch.interact, pulse: now < latch.pulse, dash: now < latch.dash });
}, 25);

// ---- key binding screen ----
function renderKeys() {
  $("keyList").innerHTML = ACTIONS.map(([a, label]) =>
    `<div class="keyrow"><span>${label}</span><button class="alt" data-a="${a}">${capturing === a ? "Nhấn phím..." : keyName(K()[a])}</button></div>`).join("");
  for (const b of $("keyList").querySelectorAll("button")) b.onclick = () => { capturing = b.dataset.a; $("keyWarn").textContent = ""; renderKeys(); };
  $("kDash").textContent = keyName(K().dash); $("kPulse").textContent = keyName(K().pulse);
  $("menuHint").textContent = `${keyName(K().up)}${keyName(K().left)}${keyName(K().down)}${keyName(K().right)} di chuyển · ${keyName(K().jump)} nhảy · ${keyName(K().dash)} lướt · ${keyName(K().interact)} nạp/châm · ${keyName(K().pulse)} tỏa sáng · ${keyName(K().pause)} tạm dừng · kéo chuột xoay camera`;
}
function captureKey(code) {
  const a = capturing; capturing = null;
  const clash = ACTIONS.find(([o]) => o !== a && K()[o] === code);
  if (clash) $("keyWarn").textContent = `⚠ Phím ${keyName(code)} đã dùng cho "${clash[1]}". Hãy đổi phím đó trước.`;
  else { settings.keys[a] = code; saveSettings(); $("keyWarn").textContent = ""; }
  renderKeys();
}
$("bKeyReset").onclick = () => { settings.keys = { ...DEFAULT_KEYS }; saveSettings(); capturing = null; $("keyWarn").textContent = ""; renderKeys(); };
renderKeys();

// ---- screens ----
const screens = ["sMenu", "sIntro", "sResult", "sDawn", "sPause", "sSet", "sKeys", "sLb"];
let overlay = null, overlayFrom = null, lastScreenKey = "";
function showScreen(id) { for (const s of screens) $(s).style.display = s === id ? "flex" : "none"; }
async function loadLb() {
  try {
    const d = await (await fetch("/leaderboard")).json();
    const rows = d.entries.map((e, i) => `<tr><td>${i + 1}</td><td>${e.name.replace(/[<>&]/g, "")}</td><td>${e.score}</td><td>${e.nights_won}/3</td><td>${String(e.achieved_at).slice(0, 10)}</td></tr>`).join("");
    $("lbTable").innerHTML = `<table><tr><th>#</th><th>Tên</th><th>Điểm</th><th>Đêm thắng</th><th>Ngày</th></tr>${rows || '<tr><td colspan="5">Chưa có ai</td></tr>'}</table>`;
  } catch (e) { $("lbTable").textContent = "Không tải được bảng xếp hạng"; }
}
$("bStart").onclick = () => cmd("new_game");
$("bBegin").onclick = () => cmd("begin");
$("bNext").onclick = () => cmd("next");
$("bRetry").onclick = () => cmd("retry");
$("bRestart").onclick = () => cmd("retry");
$("bResume").onclick = () => cmd("pause");
for (const id of ["bMenu1", "bMenu2", "bMenu3"]) $(id).onclick = () => cmd("menu");
$("bSet1").onclick = () => { overlay = "sSet"; overlayFrom = "sMenu"; };
$("bSet2").onclick = () => { overlay = "sSet"; overlayFrom = "sPause"; };
$("bSetBack").onclick = () => { overlay = null; };
$("bKeys").onclick = () => { overlay = "sKeys"; renderKeys(); };
$("bKeysBack").onclick = () => { capturing = null; overlay = "sSet"; };
$("bLb").onclick = () => { overlay = "sLb"; loadLb(); };
$("bLbBack").onclick = () => { overlay = null; };
$("bSave").onclick = async () => {
  const r = await post("/leaderboard", { name: $("nameIn").value.trim() });
  if (r && r.ok) { $("saveMsg").textContent = "Đã lưu vào bảng xếp hạng!"; $("saveMsg").style.color = "var(--core)"; }
  else { $("saveMsg").style.color = ""; $("saveMsg").textContent = "⚠ Tên phải 3–12 ký tự: chữ, số hoặc _"; }
};
function placeSave(parentId, show) { const b = $("saveBox"); if (show) { $(parentId).insertBefore(b, $(parentId).querySelector("button")); b.style.display = "flex"; } else b.style.display = "none"; }

function updateScreens(s) {
  if (BENCH) { showScreen(""); return; }
  if (overlay) { showScreen(overlay); return; }
  if (s.phase === "menu") showScreen("sMenu");
  else if (s.phase === "intro") { $("iName").textContent = NAMES[s.night]; $("iText").textContent = INTRO[s.night]; showScreen("sIntro"); }
  else if (s.phase === "result") {
    const won = s.result === "won", need = NEED[s.night], lit = s.lanterns.filter(l => l.lit).length;
    $("rTitle").textContent = won ? `${NAMES[s.night]} · Thắng!` : "Đêm này chưa qua...";
    $("rText").textContent = (won ? `Bình minh! Bạn giữ được ${lit}/${s.lanterns.length} đèn sáng.` :
      s.reason === "no_flames" ? "Mây hết ngọn lửa." : `Bình minh đến khi chỉ còn ${lit} đèn sáng (cần ${need}).`) +
      ` Điểm đêm: ${s.score}. Tổng điểm: ${s.total}.`;
    $("bNext").style.display = won ? "" : "none"; $("bNext").textContent = s.night < 3 ? "Đêm kế tiếp" : "Đón bình minh";
    placeSave("sResult", s.can_save); showScreen("sResult");
  } else if (s.phase === "dawn") { $("dText").textContent = `Ba hòn đảo đã sáng. Tổng điểm: ${s.total}.`; placeSave("sDawn", s.can_save); showScreen("sDawn"); }
  else if (s.phase === "playing" && s.state === "paused") showScreen("sPause");
  else showScreen("");
}

// ---- per-frame state ----
let lastSeq = 0, lastTick = -1, msgs = [], timedCues = [], pulseT = 0, shake = 0, lastSec = 999, wasGrounded = true;
let spawnWatch = null, lastHud = 0, hudSeq = -1, lastTs = 0;
const MSG = {
  deposit: d => `${d.lantern_id}: ${d.deposited}/10 ánh sáng`, lantern_lit: d => d.relight ? `${d.lantern_id} thắp lại!` : `${d.lantern_id} đã sáng!`,
  pulse: d => `Tỏa Sáng: ${d.stunned_ids.length} Bóng Mực choáng`, player_hit: d => d.by === "fall" ? `Rơi khỏi đảo! Còn ${d.flames} ngọn lửa` : `Bóng Mực chạm bạn! Còn ${d.flames} ngọn lửa`,
  shade_spawned: () => "Một Bóng Mực trườn ra từ sương...", drifter_steal: d => `Gió Lạc cướp ${d.amount} đom đóm!`,
  refuel: d => `${d.lantern_id}: châm ${d.amount} đom đóm, dầu ${Math.round(d.fuel)}/100`,
  lantern_out: d => `${d.lantern_id} đã cạn dầu và tắt!`, fuel_drain: d => `Bóng Mực đang hút dầu ${d.lantern_id} (còn ${Math.round(d.fuel)})`,
  drifter_drop: d => `Lấy lại ${d.amount} đom đóm`, charm_picked: () => "Bùa Gió: chạy nhanh, lướt không hồi chiêu!" };
function sfxFor(e) {
  const n = e.name;
  if (n === "mote_picked") SFX.pick(); else if (n === "lantern_lit" || n === "refuel") SFX.light(); else if (n === "lantern_out") SFX.lose(); else if (n === "pulse") SFX.pulse();
  else if (n === "player_hit") SFX.hit(); else if (n === "dash") SFX.dash(); else if (n === "shade_spawned") SFX.spawn();
  else if (n === "drifter_steal") SFX.steal(); else if (n === "charm_picked") SFX.charm();
  else if (n === "game_over") (e.data.result === "won" ? SFX.win : SFX.lose)();
}
const fmt = s => { s = Math.max(0, Math.ceil(s)); return String(Math.floor(s / 60)).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0"); };

// project a world position to the screen edge; returns true if the arrow is shown
const _v = new THREE.Vector3();
function edgeArrow(el, x, y, z) {
  _v.set(x, y, z).project(camera);
  const off = _v.z > 1 || Math.abs(_v.x) > 0.95 || Math.abs(_v.y) > 0.95;
  if (!off) { el.style.display = "none"; return false; }
  let ax = _v.x, ay = _v.y; if (_v.z > 1) { ax = -ax; ay = -ay; }
  const k = 0.85 / Math.max(Math.abs(ax), Math.abs(ay), 1e-6);
  el.style.display = "block"; el.style.left = ((ax * k * 0.5 + 0.5) * innerWidth - 14) + "px"; el.style.top = ((-ay * k * 0.5 + 0.5) * innerHeight - 17) + "px";
  el.style.transform = `rotate(${Math.atan2(-ay, ax) * 180 / Math.PI + 90}deg)`;
  return true;
}

// ---- scene update (every rendered frame) ----
function applyScene(s, ts, dt) {
  if (s.night !== builtNight) { buildNight(s.night); lastSeq = 0; lastTick = -1; msgs = []; }
  const [px, py, pz] = s.player.pos;
  may.position.set(px, py, pz);
  may.rotation.y = Math.atan2(s.player.facing[0], s.player.facing[1]);
  may.visible = !(s.player.invuln > 0 && Math.floor(s.tick / 5) % 2);
  if (BENCH && s.bench) {
    const a = 2 * Math.PI * ((ts - bench.t0) / 15000);            // counter-clockwise seen from above, 15 s per turn
    camera.position.set(30 * Math.cos(a), 15, 30 * Math.sin(a)); camera.lookAt(0, 0, 0);
  } else {
    const yr = yaw * Math.PI / 180;
    camera.position.set(px - Math.sin(yr) * 9, py + 5.5, pz - Math.cos(yr) * 9);
    if (shake > 0.01 && !settings.rm) { camera.position.x += (Math.random() - .5) * shake; camera.position.y += (Math.random() - .5) * shake; shake *= 0.9; } else shake = 0;
    camera.lookAt(px, py + 1.2, pz);
  }
  const total = s.lanterns.length, lit = s.lanterns.filter(l => l.lit).length;
  ambient.intensity = 0.15 + 0.55 * (lit / total);
  const blink = Math.floor(s.tick / 30) % 2 === 0;                    // 1 Hz
  for (const l of s.lanterns) {
    let o = lanternObjs[l.id]; if (!o) { o = lanternObjs[l.id] = makeLantern(); o.g.position.set(l.pos[0], l.pos[1], l.pos[2]); }
    const low = l.lit && l.fuel < 30;
    const f = l.lit ? l.fuel / 100 : l.deposited / (l.ever_lit ? s.relight_cost : s.lantern_cost);
    o.orb.material.color.setHex(l.lit ? PAL.lampOn : f > 0 ? 0x8a6d4a : PAL.lampOff);
    o.orb.scale.y = l.lit ? 1 : 0.8;                                   // an unlit lantern is squashed by 20%
    o.tear.visible = !l.lit;
    o.core.visible = l.lit && (!low || blink); o.orb.visible = !low || blink || !l.lit;
    o.light.intensity = l.lit ? (low ? (blink ? 2 : 0.6) : 5) : f * 1.5;
    o.zone.material.opacity = l.lit && l.fuel >= 30 ? 0.5 : 0;
    o.bar.visible = l.lit && (!low || blink); o.bar.lookAt(camera.position);
    o.fill.scale.x = Math.max(0.01, l.fuel / 100); o.fill.position.x = -0.75 * (1 - l.fuel / 100);
    o.fill.material.color.setHex(low ? PAL.scarf : PAL.lampOn);
  }
  // fireflies (instanced)
  let n = 0;
  for (const it of s.motes) {
    if (n >= MAXM) break;
    const vis = it.ttl_s === null || it.ttl_s > 1.5 || Math.floor(s.tick / 6) % 2 === 0;
    const sc = vis ? (it.id[0] === "G" ? 1.8 : it.kind === "dropped" ? 0.85 : 1) : 0.0001;
    _p.set(it.pos[0], it.pos[1] + 0.8 + Math.sin(s.tick / 20 + it.pos[0]) * 0.15, it.pos[2]); _s.set(sc, sc, sc);
    _m.compose(_p, _q.identity(), _s); moteBody.setMatrixAt(n, _m); moteHalo.setMatrixAt(n, _m); n++;
  }
  moteBody.count = moteHalo.count = n; moteBody.instanceMatrix.needsUpdate = moteHalo.instanceMatrix.needsUpdate = true;
  // Bóng Mực (instanced)
  n = 0;
  for (const it of s.shades) {
    if (n >= MAXS) break;
    const sc = it.state === "spawning" ? 0.5 : it.state === "drain" ? 1 + Math.sin(s.tick / 5) * 0.12 : 1;
    _p.set(it.pos[0], it.pos[1] + 0.2 + Math.sin(s.tick / 12) * 0.1, it.pos[2]); _s.set(sc, sc, sc);
    _q.setFromAxisAngle(_up, s.tick / 30);
    _m.compose(_p, _q, _s); shadeBody.setMatrixAt(n, _m); shadeOut.setMatrixAt(n, _m);
    shadeBody.setColorAt(n, it.state === "stunned" ? cStun : cShade);
    shadeEyes.setMatrixAt(n * 2, _e.multiplyMatrices(_m, eyeL)); shadeEyes.setMatrixAt(n * 2 + 1, _e.multiplyMatrices(_m, eyeR)); n++;
  }
  shadeBody.count = shadeOut.count = n; shadeEyes.count = n * 2;
  shadeBody.instanceMatrix.needsUpdate = shadeOut.instanceMatrix.needsUpdate = shadeEyes.instanceMatrix.needsUpdate = true;
  if (shadeBody.instanceColor) shadeBody.instanceColor.needsUpdate = true;
  sync(drifterObjs, s.drifters, makeDrifter, (m, it) => {
    m.position.set(it.pos[0], it.pos[1] + Math.sin(s.tick / 15) * 0.2, it.pos[2]);
    m.rotation.y = Math.atan2(px - it.pos[0], pz - it.pos[2]); m.children.forEach((c, i) => c.rotation.z = Math.sin(s.tick / 8 + i) * 0.5); });
  sync(charmObjs, s.charms.filter(c => c.available), makeCharm, (m, it) => { m.position.set(it.pos[0], it.pos[1] + 1.2, it.pos[2]); m.rotation.y = s.tick / 40; });
  const windOn = s.wind.active || s.wind_warn, wa = s.wind.dir_deg * Math.PI / 180;
  leaves.forEach((m, i) => {
    m.visible = windOn; if (!windOn) return;
    const t = (s.tick * 0.05 + i * 0.37) % 1, ox = Math.cos(wa), oz = Math.sin(wa);
    m.position.set(px - ox * 14 + ox * 28 * t + (i % 5 - 2) * 3, py + 1 + (i % 7) * 0.7, pz - oz * 14 + oz * 28 * t + (i % 3 - 1) * 4);
    m.rotation.set(t * 9, t * 7, i);
  });
  if (pulseT > 0) { pulseT -= dt * 2.4; ring.visible = pulseT > 0; ring.position.set(px, py + 0.1, pz); ring.scale.setScalar(1 + (1 - pulseT) * 4.5); ring.material.opacity = Math.max(0, pulseT); }
  // arrows to the nearest lantern needing attention and to a freshly spawned shade
  let attn = null, ad = 1e9;
  for (const l of s.lanterns) { const d = Math.hypot(px - l.pos[0], pz - l.pos[2]); if ((!l.lit || l.fuel < 30) && d < ad) { ad = d; attn = l; } }
  if (attn && ad > 2 && !BENCH) edgeArrow($("arrow"), attn.pos[0], attn.pos[1] + 3, attn.pos[2]); else $("arrow").style.display = "none";
  const sa = $("sarrow");
  if (spawnWatch && performance.now() < spawnWatch.until) {
    const sh = s.shades.find(x => x.id === spawnWatch.id);
    if (sh) edgeArrow(sa, sh.pos[0], sh.pos[1], sh.pos[2]); else sa.style.display = "none";
  } else sa.style.display = "none";
}

// ---- HUD / events (when a new state arrives) ----
function applyHud(s) {
  if (s.tick < lastTick) { lastSeq = 0; msgs = []; }
  lastTick = s.tick;
  const [px, , pz] = s.player.pos;
  const need = NEED[s.night], cb = !!settings.cb, k = K();
  const total = s.lanterns.length, lit = s.lanterns.filter(l => l.lit).length;
  $("flames").textContent = (cb ? "⚠ " : "") + "♥".repeat(Math.max(0, s.player.flames));
  const clk = $("clock"); clk.textContent = (cb && s.time_left_s <= 30 ? "⚠ " : "") + fmt(s.time_left_s); clk.classList.toggle("low", s.time_left_s <= 30);
  $("right").innerHTML = `Đèn sáng <b>${lit}/${total}</b> (cần ${need})<br>Điểm <b>${s.score}</b>` + (s.player.charm_s > 0 ? `<br>Bùa Gió <b>${Math.ceil(s.player.charm_s)}s</b>` : "");
  const cap = s.player.capacity;
  let bar = ""; for (let i = 0; i < cap; i++) bar += `<i class="${i < s.player.carried ? "on" : ""}"></i>`;
  $("bar").innerHTML = bar + `<span style="margin-left:8px">${s.player.carried}/${cap}</span>`;
  const dp = $("cdDash"), pp = $("cdPulse");
  dp.querySelector(".fill").style.height = (s.player.dash_cd_s / 1.5 * 100) + "%"; dp.classList.toggle("ready", s.player.dash_cd_s === 0);
  pp.querySelector(".fill").style.height = (s.player.pulse_cd_s / 3 * 100) + "%"; pp.classList.toggle("ready", s.pulse_ready);
  let near = null, nd = 1e9;
  for (const l of s.lanterns) { const d = Math.hypot(px - l.pos[0], pz - l.pos[2]); if ((!l.lit || l.fuel < 100) && d < nd) { nd = d; near = l; } }
  const pr = $("prompt");
  if (near && nd <= 2.0) {
    pr.style.display = "block";
    pr.textContent = near.lit ? `${keyName(k.interact)} — Châm dầu (${Math.round(near.fuel)}/100)` : `${keyName(k.interact)} — Nạp ánh sáng (${near.deposited}/${near.ever_lit ? s.relight_cost : s.lantern_cost})`;
  } else pr.style.display = "none";
  for (const e of s.events) {
    if (e.seq <= lastSeq) continue; lastSeq = e.seq;
    const t = MSG[e.name] && MSG[e.name](e.data); if (t) { msgs.push(t); if (msgs.length > 4) msgs.shift(); }
    sfxFor(e);
    if (e.name === "shade_spawned") { spawnWatch = { id: e.data.id, until: performance.now() + 5000 }; timedCues.push({ text: "⚠ Bóng Mực xuất hiện (mũi tên tím chỉ hướng)", until: performance.now() + 4000 }); }
    if (e.name === "player_hit" && !settings.rm) { $("flash").style.opacity = .55; setTimeout(() => $("flash").style.opacity = 0, 150); shake = 0.8; }
    if (e.name === "pulse") pulseT = 1;
  }
  $("msg").innerHTML = msgs.join("<br>");
  // visual cues (subtitles) for sound-only events
  const now = performance.now(), cues = timedCues.filter(c => c.until > now).map(c => c.text);
  timedCues = timedCues.filter(c => c.until > now);
  if (s.wind_warn) cues.push("Gió sắp thổi (lá đang bay)"); else if (s.wind.active) cues.push("Gió đang thổi");
  if (s.state === "playing" && s.time_left_s <= 10 && s.time_left_s > 0) cues.push(`10 giây cuối: còn ${Math.ceil(s.time_left_s)} s`);
  for (const l of s.lanterns) if (l.lit && l.fuel < 30) cues.push(`${l.id} sắp cạn dầu (${Math.round(l.fuel)})`);
  $("cue").innerHTML = cues.map(c => `<div>${c}</div>`).join("");
  if (s.player.grounded === false && wasGrounded && s.player.vel[1] > 5 && s.player.vel[1] < 8) SFX.jump();
  wasGrounded = s.player.grounded;
  const sec = Math.ceil(s.time_left_s);
  if (s.state === "playing" && sec <= 10 && sec < lastSec && sec > 0) SFX.tick();
  lastSec = sec;
}

// ---- benchmark (Ticket-04): ?bench=1&duration=30 ----
const benchPx = new Uint8Array(4);
const bench = { t0: null, prev: null, dts: [], done: false, started: false };
function benchStep(ts) {
  if (!BENCH || bench.done || !S.bench) return;
  if (!bench.started) { bench.started = true; post("/bench_first_frame", {}); bench.prev = ts; return; }
  const el = ts - bench.t0;
  if (el >= 3000) {                                   // the first 3 s are warm-up and are not measured
    if (el < 3000 + BENCH_DUR * 1000) bench.dts.push(ts - bench.prev);
    else {
      bench.done = true;
      const gl = renderer.getContext(), dbg = gl.getExtension("WEBGL_debug_renderer_info");
      post("/bench_report", { dts: bench.dts, renderer: `three.js r${THREE.REVISION} / WebGL: ${dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER)}`,
        ua: navigator.userAgent, size: [innerWidth, innerHeight], dpr: devicePixelRatio });
    }
  }
  bench.prev = ts;
}

function frame(ts) {
  requestAnimationFrame(frame);
  const dt = Math.min(0.1, (ts - lastTs) / 1000); lastTs = ts;
  const live = S.phase === "playing" || S.phase === "result";
  if (live && (!BENCH || S.bench)) {
    if (BENCH && bench.t0 === null) bench.t0 = ts;     // camera angle starts at 0 degrees on the first scene frame
    applyScene(S, ts, dt);
    if (S._seq !== hudSeq && (performance.now() - lastHud > 40)) { hudSeq = S._seq; lastHud = performance.now(); applyHud(S); }
  }
  renderer.render(scene, camera);
  if (BENCH) { const gl = renderer.getContext(); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, benchPx); }   // wait for the GPU so dt is the real frame time
  if (live) benchStep(ts);
}

function onState(s) {
  updateScreens(s);
  const hudOn = s.phase === "playing";
  for (const id of ["flames", "clock", "right", "bar", "cds", "msg", "cue"]) $(id).style.display = hudOn ? "" : "none";
  if (!hudOn) { for (const id of ["prompt", "arrow", "sarrow"]) $(id).style.display = "none"; }
}
async function pollLoop() {
  for (;;) {
    try { S = await (await fetch("/state")).json(); S._seq = ++seq; window.__state = S; onState(S); }
    catch (e) { await sleep(300); }
    await sleep(8);
  }
}
pollLoop();
requestAnimationFrame(frame);
