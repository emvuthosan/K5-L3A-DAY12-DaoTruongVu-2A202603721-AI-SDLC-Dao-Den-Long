import * as THREE from "./three.module.min.js";

// ---- palette (Ticket-02) ----
const PAL = { sky: 0x0E1430, mist: 0x1B2350, grass: 0x2F5D50, sand: 0xC9B48A, wood: 0x6B4A2F, sea: 0x12384A,
  lampOn: 0xFFB347, lampCore: 0xFFE9B0, lampOff: 0x5B5F6E, mote: 0xFFF6C2, halo: 0xFFE58A,
  shade: 0x120A1A, outline: 0x7A3CFF, stunned: 0x3A3450, coat: 0xE8E2D0, scarf: 0xC8102E,
  gold: 0xF2C14E, drifter: 0x8FA3B8 };
const NAMES = { 1: "Đêm 1 · Đảo Bến", 2: "Đêm 2 · Đảo Cau", 3: "Đêm 3 · Đảo Chuông" };
const INTRO = {
  1: "Ông Đăng: \"Sương đen đã nuốt hết ánh sáng của đảo, cháu ạ. Nhặt đom đóm, thắp năm Đèn Lồng Lớn, và đừng để Bóng Mực chạm vào.\"",
  2: "Ông Đăng: \"Hai hòn đảo nối nhau bằng cầu tre không lan can. Bục nhảy sẽ đưa cháu bay qua; coi chừng Gió Lạc tham đom đóm.\"",
  3: "Ông Đăng: \"Đảo Chuông có ba tầng, dốc và gió mạnh. Bảy ngọn đèn cuối cùng đang chờ cháu. Bình minh sắp tới rồi.\"" };
const $ = id => document.getElementById(id);

// ---- settings (persisted) ----
let settings = { vol: 60, sens: 40 };
try { Object.assign(settings, JSON.parse(localStorage.getItem("ddl-settings") || "{}")); } catch (e) {}
function saveSettings() { try { localStorage.setItem("ddl-settings", JSON.stringify(settings)); } catch (e) {} }
$("vol").value = settings.vol; $("sens").value = settings.sens;
const syncSet = () => { $("volV").textContent = settings.vol; $("sensV").textContent = settings.sens; };
syncSet();
$("vol").oninput = e => { settings.vol = +e.target.value; syncSet(); saveSettings(); applyVol(); };
$("sens").oninput = e => { settings.sens = +e.target.value; syncSet(); saveSettings(); };

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
  const notes = [220, 261.6, 329.6, 392, 329.6, 261.6, 196, 246.9];
  let i = 0;
  setInterval(() => { if (ac && ac.state === "running") tone(notes[i++ % notes.length] / 2, 1.6, "sine", .09); }, 1200);
}
for (const id of ["bStart", "bBegin"]) $(id).addEventListener("click", initAudio);
addEventListener("keydown", initAudio, { once: true });

// ---- scene ----
const scene = new THREE.Scene();
scene.background = new THREE.Color(PAL.sky);
scene.fog = new THREE.Fog(PAL.mist, 40, 160);
const camera = new THREE.PerspectiveCamera(60, innerWidth / innerHeight, 0.1, 400);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
renderer.setSize(innerWidth, innerHeight);
document.body.appendChild(renderer.domElement);
addEventListener("resize", () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });
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

const lanternObjs = {}, moteObjs = new Map(), shadeObjs = new Map(), drifterObjs = new Map(), charmObjs = new Map();
const moteGeo = new THREE.SphereGeometry(0.16, 8, 8), haloGeo = new THREE.SphereGeometry(0.34, 8, 8);
const moteMat = bas(PAL.mote), haloMat = bas(PAL.halo, { transparent: true, opacity: 0.35 });
const shadeGeo = new THREE.IcosahedronGeometry(0.62, 1), outlineGeo = new THREE.IcosahedronGeometry(0.74, 1);
const shadeMat = lam(PAL.shade, { emissive: 0x1a0d2a }), stunMat = lam(PAL.stunned);
const outlineMat = bas(PAL.outline, { side: THREE.BackSide });
const leaves = []; for (let i = 0; i < 40; i++) { const m = new THREE.Mesh(new THREE.PlaneGeometry(.4, .25), bas(0x6fae7a, { side: THREE.DoubleSide })); m.visible = false; scene.add(m); leaves.push(m); }

let builtNight = 0, cfg = null;
function clearWorld() {
  world.clear(); for (const k in lanternObjs) { scene.remove(lanternObjs[k].g); delete lanternObjs[k]; }
  for (const mp of [moteObjs, shadeObjs, drifterObjs, charmObjs]) { for (const m of mp.values()) scene.remove(m); mp.clear(); }
}
function disc(cx, cz, r, h, color) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, h, 56), lam(color)); m.position.set(cx, h / -2 + (h > 0.5 ? 0 : 0), cz);
  world.add(m); return m;
}
function island(cx, cz, r) {
  const g = disc(cx, cz, r, 1, PAL.grass); g.position.y = -0.5;
  const rim = new THREE.Mesh(new THREE.TorusGeometry(r, 0.35, 6, 64), lam(PAL.sand)); rim.rotation.x = Math.PI / 2; rim.position.set(cx, -0.05, cz); world.add(rim);
}
function pad(x, y, z) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(1, 1, 0.2, 24), lam(PAL.lampOn, { emissive: 0x6b3d00 })); m.position.set(x, y + 0.1, z); world.add(m);
  const r = new THREE.Mesh(new THREE.TorusGeometry(1.1, 0.08, 6, 24), bas(PAL.lampCore)); r.rotation.x = Math.PI / 2; r.position.set(x, y + 0.25, z); world.add(r);
}
function buildNight(n, snap) {
  clearWorld(); builtNight = n;
  if (n === 1) { island(0, 0, 40); }
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
  const light = new THREE.PointLight(PAL.lampOn, 0, 22); light.position.y = 3.4; g.add(light);
  const zone = new THREE.Mesh(new THREE.RingGeometry(5.85, 6, 64), bas(PAL.lampOn, { transparent: true, opacity: 0, side: THREE.DoubleSide }));
  zone.rotation.x = -Math.PI / 2; zone.position.y = 0.06; g.add(zone);
  scene.add(g); return { g, orb, core, light, zone };
}
function makeShade() {
  const g = new THREE.Group(); g.add(new THREE.Mesh(outlineGeo, outlineMat));
  const b = new THREE.Mesh(shadeGeo, shadeMat); g.add(b); g.userData.body = b; scene.add(g); return g;
}
function makeDrifter() {
  const g = new THREE.Group();
  for (let i = 0; i < 3; i++) { const m = new THREE.Mesh(new THREE.PlaneGeometry(1.6, 0.35), bas(PAL.drifter, { side: THREE.DoubleSide, transparent: true, opacity: 0.85 })); m.position.z = -i * 0.5; g.add(m); }
  scene.add(g); return g;
}
function makeCharm() {
  const g = new THREE.Group();
  g.add(new THREE.Mesh(new THREE.BoxGeometry(0.9, 1.2, 0.06), bas(PAL.gold)));
  const f = new THREE.Mesh(new THREE.BoxGeometry(0.72, 1.02, 0.08), bas(PAL.scarf)); g.add(f);
  scene.add(g); return g;
}
function sync(map, items, make, upd) {
  const seen = new Set();
  for (const it of items) { seen.add(it.id); let m = map.get(it.id); if (!m) { m = make(it); map.set(it.id, m); } upd(m, it); }
  for (const [id, m] of map) if (!seen.has(id)) { scene.remove(m); map.delete(id); }
}

// ---- input ----
const keys = new Set();
let yaw = 0, dragging = false;
const latch = { jump: 0, interact: 0, pulse: 0, dash: 0 };
let S = { phase: "menu" };
function post(path, body) { return fetch(path, { method: "POST", body: JSON.stringify(body || {}) }).catch(() => {}); }
const cmd = c => post("/cmd", { cmd: c });
addEventListener("keydown", e => {
  if (e.repeat) return;
  const k = e.key.toLowerCase(), now = performance.now();
  keys.add(k);
  if (k === " ") latch.jump = now + 90;
  if (k === "e") latch.interact = now + 90;
  if (k === "f") latch.pulse = now + 90;
  if (k === "shift") latch.dash = now + 90;
  if ((k === "escape" || k === "p") && S.phase === "playing") cmd("pause");
  if (k === "r" && S.phase === "result") cmd("retry");
  if (k.startsWith("arrow") || k === " ") e.preventDefault();
});
addEventListener("keyup", e => keys.delete(e.key.toLowerCase()));
addEventListener("mousedown", () => dragging = true);
addEventListener("mouseup", () => dragging = false);
addEventListener("mousemove", e => { if (dragging) yaw += e.movementX * settings.sens / 100; });
setInterval(() => {
  const now = performance.now();
  if (keys.has("arrowleft")) yaw -= 1.8; if (keys.has("arrowright")) yaw += 1.8;
  // the camera looks toward +Z at yaw 0, so screen-right is -X in the contract's input space
  const move = [(keys.has("a") ? 1 : 0) - (keys.has("d") ? 1 : 0), (keys.has("w") ? 1 : 0) - (keys.has("s") ? 1 : 0)];
  post("/input", { move, yaw, jump: now < latch.jump, interact: now < latch.interact, pulse: now < latch.pulse, dash: now < latch.dash });
}, 25);

// ---- screens ----
const screens = ["sMenu", "sIntro", "sResult", "sDawn", "sPause", "sSet"];
let settingsFrom = "sMenu", showSet = false;
function showScreen(id) { for (const s of screens) $(s).style.display = s === id ? "flex" : "none"; }
function openSettings(from) { settingsFrom = from; showSet = true; showScreen("sSet"); }
$("bStart").onclick = () => cmd("new_game");
$("bBegin").onclick = () => cmd("begin");
$("bNext").onclick = () => cmd("next");
$("bRetry").onclick = () => cmd("retry");
$("bRestart").onclick = () => cmd("retry");
$("bResume").onclick = () => cmd("pause");
for (const id of ["bMenu1", "bMenu2", "bMenu3"]) $(id).onclick = () => cmd("menu");
$("bSet1").onclick = () => openSettings("sMenu");
$("bSet2").onclick = () => openSettings("sPause");
$("bSetBack").onclick = () => { showSet = false; };

// ---- per-frame ----
let lastSeq = 0, lastTick = -1, msgs = [], pulseT = 0, shake = 0, lastSec = 999, wasGrounded = true, wasPhase = "";
const MSG = {
  deposit: d => `${d.lantern_id}: ${d.deposited}/10 ánh sáng`, lantern_lit: d => `${d.lantern_id} đã sáng!`,
  pulse: d => `Tỏa Sáng: ${d.stunned_ids.length} Bóng Mực choáng`, player_hit: d => d.by === "fall" ? `Rơi khỏi đảo! Còn ${d.flames} ngọn lửa` : `Bóng Mực chạm bạn! Còn ${d.flames} ngọn lửa`,
  shade_spawned: () => "Một Bóng Mực trườn ra từ sương...", drifter_steal: d => `Gió Lạc cướp ${d.amount} đom đóm!`,
  drifter_drop: d => `Lấy lại ${d.amount} đom đóm`, charm_picked: () => "Bùa Gió: chạy nhanh, lướt không hồi chiêu!", paused: () => null };
function sfxFor(e) {
  const n = e.name;
  if (n === "mote_picked") SFX.pick(); else if (n === "lantern_lit") SFX.light(); else if (n === "pulse") SFX.pulse();
  else if (n === "player_hit") SFX.hit(); else if (n === "dash") SFX.dash(); else if (n === "shade_spawned") SFX.spawn();
  else if (n === "drifter_steal") SFX.steal(); else if (n === "charm_picked") SFX.charm();
  else if (n === "game_over") (e.data.result === "won" ? SFX.win : SFX.lose)();
}
const fmt = s => { s = Math.max(0, Math.ceil(s)); return String(Math.floor(s / 60)).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0"); };

function updateScreens(s) {
  if (showSet) { showScreen("sSet"); return; }
  if (s.phase === "menu") showScreen("sMenu");
  else if (s.phase === "intro") { $("iName").textContent = NAMES[s.night]; $("iText").textContent = INTRO[s.night]; showScreen("sIntro"); }
  else if (s.phase === "result") {
    const won = s.result === "won";
    $("rTitle").textContent = won ? `${NAMES[s.night]} · Thắng!` : "Đêm này chưa qua...";
    $("rText").textContent = (won ? "Các Đèn Lồng đã sáng lại." : (s.time_left_s <= 0 ? "Bình minh đến khi đèn chưa sáng hết." : "Mây hết ngọn lửa.")) +
      ` Điểm đêm: ${s.score}. Tổng điểm: ${s.total}.`;
    $("bNext").style.display = won ? "" : "none"; $("bNext").textContent = s.night < 3 ? "Đêm kế tiếp" : "Đón bình minh";
    $("bRetry").style.display = ""; showScreen("sResult");
  } else if (s.phase === "dawn") { $("dText").textContent = `Ba hòn đảo đã sáng. Tổng điểm: ${s.total}.`; showScreen("sDawn"); }
  else if (s.phase === "playing" && s.state === "paused") showScreen("sPause");
  else showScreen("");
}

function apply(s) {
  if (s.phase !== "playing" && s.phase !== "result") return;
  if (s.night !== builtNight) { buildNight(s.night, s); lastSeq = 0; lastTick = -1; msgs = []; }
  if (s.tick < lastTick) { lastSeq = 0; msgs = []; }
  lastTick = s.tick;
  const [px, py, pz] = s.player.pos;
  may.position.set(px, py, pz);
  may.rotation.y = Math.atan2(s.player.facing[0], s.player.facing[1]);
  may.visible = !(s.player.invuln > 0 && Math.floor(s.tick / 5) % 2);
  const yr = yaw * Math.PI / 180;
  camera.position.set(px - Math.sin(yr) * 9, py + 5.5, pz - Math.cos(yr) * 9);
  if (shake > 0.01) { camera.position.x += (Math.random() - .5) * shake; camera.position.y += (Math.random() - .5) * shake; shake *= 0.9; }
  camera.lookAt(px, py + 1.2, pz);

  const total = s.lanterns.length, lit = s.lanterns.filter(l => l.lit).length;
  ambient.intensity = 0.15 + 0.55 * (lit / total);
  for (const l of s.lanterns) {
    let o = lanternObjs[l.id]; if (!o) { o = lanternObjs[l.id] = makeLantern(); o.g.position.set(l.pos[0], l.pos[1], l.pos[2]); }
    const f = l.lit ? 1 : l.deposited / s.lantern_cost;
    o.orb.material.color.setHex(l.lit ? PAL.lampOn : f > 0 ? 0x8a6d4a : PAL.lampOff);
    o.core.visible = l.lit; o.light.intensity = l.lit ? 5 : f * 1.5; o.zone.material.opacity = l.lit ? 0.5 : 0;
  }
  sync(moteObjs, s.motes, m => { const g = new THREE.Group(); g.add(new THREE.Mesh(moteGeo, moteMat), new THREE.Mesh(haloGeo, haloMat)); scene.add(g); return g; },
    (m, it) => { m.scale.setScalar(it.id[0] === "G" ? 1.8 : it.kind === "dropped" ? 0.85 : 1);
      m.position.set(it.pos[0], it.pos[1] + 0.8 + Math.sin(s.tick / 20 + it.pos[0]) * 0.15, it.pos[2]);
      m.visible = it.ttl_s === null || it.ttl_s > 1.5 || Math.floor(s.tick / 6) % 2 === 0; });
  sync(shadeObjs, s.shades, makeShade, (m, it) => {
    m.userData.body.material = it.state === "stunned" ? stunMat : shadeMat;
    m.position.set(it.pos[0], it.pos[1] + 0.2 + Math.sin(s.tick / 12) * 0.1, it.pos[2]); m.rotation.y = s.tick / 30;
    m.scale.setScalar(it.state === "spawning" ? 0.5 : 1); });
  sync(drifterObjs, s.drifters, makeDrifter, (m, it) => {
    m.position.set(it.pos[0], it.pos[1] + Math.sin(s.tick / 15) * 0.2, it.pos[2]);
    m.rotation.y = Math.atan2(px - it.pos[0], pz - it.pos[2]); m.children.forEach((c, i) => c.rotation.z = Math.sin(s.tick / 8 + i) * 0.5); });
  sync(charmObjs, s.charms.filter(c => c.available), makeCharm, (m, it) => { m.position.set(it.pos[0], it.pos[1] + 1.2, it.pos[2]); m.rotation.y = s.tick / 40; });

  // HUD
  $("flames").textContent = "♥".repeat(Math.max(0, s.player.flames));
  const clk = $("clock"); clk.textContent = fmt(s.time_left_s); clk.classList.toggle("low", s.time_left_s <= 30);
  $("right").innerHTML = `Đèn <b>${lit}/${total}</b><br>Điểm <b>${s.score}</b>` + (s.player.charm_s > 0 ? `<br>Bùa Gió <b>${Math.ceil(s.player.charm_s)}s</b>` : "");
  let bar = ""; for (let i = 0; i < s.capacity; i++) bar += `<i class="${i < s.player.carried ? "on" : ""}"></i>`; $("bar").innerHTML = bar;
  const dp = $("cdDash"), pp = $("cdPulse");
  dp.querySelector(".fill").style.height = (s.player.dash_cd_s / 1.5 * 100) + "%"; dp.classList.toggle("ready", s.player.dash_cd_s === 0);
  pp.querySelector(".fill").style.height = (s.player.pulse_cd_s / 3 * 100) + "%"; pp.classList.toggle("ready", s.pulse_ready);
  // prompt and arrow
  let near = null, nearest = null, nd = 1e9;
  for (const l of s.lanterns) if (!l.lit) {
    const d = Math.hypot(px - l.pos[0], pz - l.pos[2]);
    if (d < nd) { nd = d; nearest = l; }
  }
  const pr = $("prompt");
  if (nearest && nd <= 2.0) { pr.style.display = "block"; pr.textContent = `E — Nạp ánh sáng (${nearest.deposited}/${s.lantern_cost})`; } else pr.style.display = "none";
  const ar = $("arrow");
  if (nearest) {
    const v = new THREE.Vector3(nearest.pos[0], nearest.pos[1] + 3, nearest.pos[2]).project(camera);
    const off = v.z > 1 || Math.abs(v.x) > 0.95 || Math.abs(v.y) > 0.95;
    if (off && nd > 2) {
      let x = v.x, y = v.y; if (v.z > 1) { x = -x; y = -y; }
      const k = 0.85 / Math.max(Math.abs(x), Math.abs(y), 1e-6);
      const sx = (x * k * 0.5 + 0.5) * innerWidth, sy = (-y * k * 0.5 + 0.5) * innerHeight;
      ar.style.display = "block"; ar.style.left = (sx - 14) + "px"; ar.style.top = (sy - 17) + "px";
      ar.style.transform = `rotate(${Math.atan2(-y, x) * 180 / Math.PI + 90}deg)`;
    } else ar.style.display = "none";
  } else ar.style.display = "none";
  $("warn").style.display = s.wind_warn ? "block" : "none";
  // wind leaves
  const windOn = s.wind.active || s.wind_warn, wa = s.wind.dir_deg * Math.PI / 180;
  leaves.forEach((m, i) => {
    m.visible = windOn; if (!windOn) return;
    const t = (s.tick * 0.05 + i * 0.37) % 1, ox = Math.cos(wa), oz = Math.sin(wa);
    m.position.set(px - ox * 14 + ox * 28 * t + (i % 5 - 2) * 3, py + 1 + (i % 7) * 0.7, pz - oz * 14 + oz * 28 * t + (i % 3 - 1) * 4);
    m.rotation.set(t * 9, t * 7, i);
  });

  // events -> messages / sfx / effects
  for (const e of s.events) {
    if (e.seq <= lastSeq) continue; lastSeq = e.seq;
    const t = MSG[e.name] && MSG[e.name](e.data); if (t) { msgs.push(t); if (msgs.length > 4) msgs.shift(); }
    sfxFor(e);
    if (e.name === "player_hit") { $("flash").style.opacity = .55; setTimeout(() => $("flash").style.opacity = 0, 150); shake = 0.8; }
    if (e.name === "pulse") pulseT = 1;
  }
  $("msg").innerHTML = msgs.join("<br>");
  if (pulseT > 0) { pulseT -= 0.04; ring.visible = pulseT > 0; ring.position.set(px, py + 0.1, pz); ring.scale.setScalar(1 + (1 - pulseT) * 4.5); ring.material.opacity = Math.max(0, pulseT); }
  if (s.player.grounded === false && wasGrounded && s.player.vel[1] > 5 && s.player.vel[1] < 8) SFX.jump();
  wasGrounded = s.player.grounded;
  const sec = Math.ceil(s.time_left_s);
  if (s.state === "playing" && sec <= 10 && sec < lastSec && sec > 0) SFX.tick();
  lastSec = sec;
}

async function poll() {
  try {
    S = await (await fetch("/state")).json();
    window.__state = S;
    updateScreens(S);
    const hudOn = S.phase === "playing";
    for (const id of ["flames", "clock", "right", "bar", "cds", "msg"]) $(id).style.display = hudOn ? "" : "none";
    if (!hudOn) { $("prompt").style.display = "none"; $("arrow").style.display = "none"; $("warn").style.display = "none"; }
    apply(S);
  } catch (e) { await new Promise(r => setTimeout(r, 300)); }
  renderer.render(scene, camera);
  requestAnimationFrame(poll);
}
poll();
