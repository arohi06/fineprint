/* fineprint. - frontend logic */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const HL = /\b(sell|sold|selling|share[sd]?|sharing|track\w*|indefinitely|biometric|location|arbitration|class action|without notice|retain\w*|partners|advertis\w+|third[- ]part\w+|waive\w*|affiliates|profile)\b/gi;

const state = { token: localStorage.getItem('fp_token'), user: null, mode: 'login' };

/* ---------- API ---------- */
async function api(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (state.token) headers.Authorization = 'Bearer ' + state.token;
  const res = await fetch(path, { ...opts, headers });
  if (!res.ok) {
    let msg = 'Something went wrong.';
    try { msg = (await res.json()).detail || msg; } catch (_) {}
    throw new Error(typeof msg === 'string' ? msg : 'Please check your input.');
  }
  return res;
}

/* ---------- cursor: spotlight, ring, tilt + shadow ---------- */
const spot = $('.spot'), ring = $('.ring');
let mx = innerWidth / 2, my = innerHeight / 3, rx = mx, ry = my, hovered = null;
addEventListener('pointermove', e => {
  if (e.pointerType === 'touch') return;
  mx = e.clientX; my = e.clientY;
  spot.style.setProperty('--mx', mx + 'px'); spot.style.setProperty('--my', my + 'px');
  ring.classList.add('on');
  const t = e.target.closest ? e.target.closest('.tilt') : null;
  if (hovered && hovered !== t) resetTilt(hovered);
  hovered = t;
  if (t) tilt(t, e);
  const b = e.target.closest && e.target.closest('.btn');
  if (b) { const r = b.getBoundingClientRect(); b.style.setProperty('--gx', e.clientX - r.left + 'px'); b.style.setProperty('--gy', e.clientY - r.top + 'px'); }
  ring.classList.toggle('big', !!(e.target.closest && e.target.closest('a,button,.hist,.chip')));
});
document.addEventListener('pointerleave', () => { ring.classList.remove('on'); if (hovered) resetTilt(hovered); });
function tilt(el, e) {
  const r = el.getBoundingClientRect();
  const dx = (e.clientX - r.left) / r.width - .5, dy = (e.clientY - r.top) / r.height - .5;
  const big = Math.min(1, 420 / Math.max(r.width, r.height));           // gentler tilt on large cards
  el.style.setProperty('--rx', (-dy * 7 * big).toFixed(2) + 'deg');
  el.style.setProperty('--ry', (dx * 7 * big).toFixed(2) + 'deg');
  el.style.setProperty('--sx', (-dx * 38).toFixed(1) + 'px');           // shadow slides away from the cursor
  el.style.setProperty('--sy', (22 - dy * 30).toFixed(1) + 'px');
  el.style.setProperty('--gx', e.clientX - r.left + 'px');
  el.style.setProperty('--gy', e.clientY - r.top + 'px');
}
function resetTilt(el) { ['--rx', '--ry', '--sx', '--sy'].forEach(p => el.style.removeProperty(p)); }
(function loop() { rx += (mx - rx) * .16; ry += (my - ry) * .16; ring.style.transform = `translate(${rx}px,${ry}px)`; requestAnimationFrame(loop); })();

/* ---------- scroll reveal ---------- */
const io = new IntersectionObserver(es => es.forEach(x => { if (x.isIntersecting) { x.target.classList.add('in'); io.unobserve(x.target); } }), { threshold: .12 });
const observeReveals = () => $$('.reveal:not(.in)').forEach(el => io.observe(el));
observeReveals();

/* ---------- scanning ---------- */
const form = $('#scanForm'), input = $('#urlInput'), errBox = $('#error'), loader = $('#loader'), loaderText = $('#loaderText');
$$('.chip').forEach(c => c.addEventListener('click', () => { input.value = c.dataset.url; form.requestSubmit(); }));

form.addEventListener('submit', async e => {
  e.preventDefault();
  errBox.hidden = true; $('#result').hidden = true;
  loader.hidden = false; $('#scanBtn').disabled = true;
  const msgs = ['Fetching the homepage…', 'Hunting for the privacy policy…', 'Reading every clause…', 'Counting trackers…', 'Doing the maths…'];
  let i = 0; loaderText.textContent = msgs[0];
  const timer = setInterval(() => loaderText.textContent = msgs[Math.min(++i, msgs.length - 1)], 2500);
  try {
    const res = await api('/api/scan', { method: 'POST', body: JSON.stringify({ url: input.value }) });
    renderResult(await res.json());
    if (state.user) loadHistory();
  } catch (err) { errBox.textContent = err.message; errBox.hidden = false; }
  finally { clearInterval(timer); loader.hidden = true; $('#scanBtn').disabled = false; }
});

/* ---------- rendering ---------- */
const tone = s => s >= 70 ? ['g-good', 'var(--moss)'] : s >= 45 ? ['g-mid', 'var(--amber)'] : ['g-bad', 'var(--clay)'];
const hl = t => esc(t).replace(HL, '<mark>$1</mark>');

function renderResult(r) {
  const [cls, col] = tone(r.score), C = 2 * Math.PI * 70;
  const cmp = r.comparison, rows = [{ name: r.domain, score: r.score, me: true }, ...cmp.benchmarks];
  if (cmp.average != null) rows.splice(1, 0, { name: 'Fineprint average', score: cmp.average });
  const risky = r.clauses.filter(c => c.risk !== 'positive' && c.risk !== 'info');
  const good = r.clauses.filter(c => c.risk === 'positive');
  const clauseHTML = c => `<div class="clause"><span class="pill r-${c.risk}">${esc(c.label_name)}</span>
      <q class="r-${c.risk}">${hl(c.text)}</q><p class="why">${esc(c.plain)} <span>· ${Math.round(c.confidence * 100)}% sure</span></p></div>`;

  $('#result').innerHTML = `
  <div class="card tilt score-card">
    <div class="gauge"><svg viewBox="0 0 160 160"><circle class="track" cx="80" cy="80" r="70" fill="none" stroke-width="12"/>
      <circle class="bar" cx="80" cy="80" r="70" fill="none" style="stroke:${col}" stroke-width="12" stroke-linecap="round"
        stroke-dasharray="${C}" stroke-dashoffset="${C}" data-target="${C * (1 - r.score / 100)}"/></svg><b>${r.score}</b></div>
    <div><span class="grade ${cls}">${esc(r.grade)}</span><h2>${esc(r.domain)}</h2><p class="muted">${esc(r.verdict)}</p>
      <div class="actions"><button class="btn primary" id="dlBtn">Download report</button>
      <a class="btn ghost" href="${esc(r.url)}" target="_blank" rel="noopener noreferrer" style="text-decoration:none">Visit site ↗</a></div></div>
  </div>

  <div class="card tilt half"><h3>In plain English</h3><ul class="plain">${r.summary.map(s => `<li>${esc(s)}</li>`).join('')}</ul></div>
  <div class="card tilt half"><h3>What you can do</h3><ul class="plain recs">${r.recommendations.map(s => `<li>${esc(s)}</li>`).join('')}</ul></div>

  <div class="card tilt"><h3>Clauses worth a second look <small class="muted">(${risky.length})</small></h3>
    ${risky.length ? risky.slice(0, 6).map(clauseHTML).join('') : '<p class="muted">No risky clauses were detected in the text we could read.</p>'}
    ${risky.length > 6 ? `<div id="moreClauses" hidden>${risky.slice(6).map(clauseHTML).join('')}</div><button class="btn ghost more" id="moreBtn">Show ${risky.length - 6} more</button>` : ''}
    ${good.length ? `<h3 style="margin-top:1.6rem">The good parts</h3>${good.slice(0, 3).map(clauseHTML).join('')}` : ''}
    ${r.policy_chars ? '' : '<p class="muted">We could not read a policy page, so the score leans on trackers and site checks.</p>'}
  </div>

  <div class="card tilt half"><h3>Trackers &amp; cookies</h3>
    <div class="tags">${r.trackers.length ? r.trackers.map(t => `<span class="tag">${esc(t.name)} <small>${esc(t.category)}</small></span>`).join('') : '<span class="muted">No known trackers on the homepage.</span>'}</div>
    <div style="margin-top:1.2rem">
      <div class="kv"><span>Cookies set on first visit</span><b>${r.cookies.count}</b></div>
      <div class="kv"><span>Without Secure flag</span><b>${r.cookies.insecure}</b></div>
      <div class="kv"><span>Consent banner</span><b>${r.cookies.banner_detected ? 'Detected' : 'Not detected'}</b></div>
      <div class="kv"><span>HTTPS</span><b>${r.checks.https ? 'Yes' : 'No'}</b></div>
    </div></div>

  <div class="card tilt half"><h3>Data they say they touch</h3>
    <div class="tags">${r.permissions.length ? r.permissions.map(p => `<span class="tag">${esc(p)}</span>`).join('') : '<span class="muted">Nothing specific detected.</span>'}</div>
    <h3 style="margin-top:1.6rem">Where the points went</h3>
    ${r.breakdown.map(b => `<div class="bd"><span>${esc(b.name)}</span><b class="${b.points < 0 ? 'neg' : 'pos'}">${b.points > 0 ? '+' : ''}${b.points}</b></div>`).join('') || '<p class="muted">No deductions.</p>'}</div>

  <div class="card tilt"><h3>How it compares</h3><div class="bars">
    ${rows.map(x => `<div class="bar-row ${x.me ? 'me' : ''}"><span>${esc(x.name)}</span><div class="b"><i style="background:${tone(x.score)[1]}" data-w="${x.score}"></i></div><b>${Math.round(x.score)}</b></div>`).join('')}</div>
    <p class="note">${cmp.percentile != null ? `Safer than ${cmp.percentile}% of the ${cmp.sample_size} sites scanned so far. ` : 'Scan a few more sites to unlock a live percentile. '}Category benchmarks are illustrative ranges, not scans of specific companies.</p></div>`;

  const box = $('#result'); box.hidden = false;
  $$('.tilt', box).forEach(el => el.classList.add('reveal')); observeReveals();
  requestAnimationFrame(() => setTimeout(() => {
    const bar = $('.gauge .bar'); bar.style.strokeDashoffset = bar.dataset.target;
    $$('.bar-row i').forEach(i => i.style.width = i.dataset.w + '%');
  }, 80));
  const mb = $('#moreBtn'); if (mb) mb.onclick = () => { $('#moreClauses').hidden = false; mb.remove(); };
  $('#dlBtn').onclick = () => downloadReport(r.id, r.domain);
  box.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function downloadReport(id, domain) {
  try {
    const res = await api('/api/report/' + id);
    const url = URL.createObjectURL(await res.blob());
    const a = Object.assign(document.createElement('a'), { href: url, download: `fineprint-${domain}.html` });
    a.click(); URL.revokeObjectURL(url);
  } catch (e) { alert(e.message); }
}

/* ---------- history + admin ---------- */
async function loadHistory() {
  const list = await (await api('/api/history')).json();
  $('#history').hidden = false; $('#navHistory').style.display = 'inline';
  $('#historyList').innerHTML = list.length ? list.map(s => `<div class="card tilt hist" data-id="${s.id}">
      <div><b>${esc(s.domain)}</b><br><small class="muted">${new Date(s.created_at * 1000).toLocaleString()}</small></div>
      <span style="color:${tone(s.score)[1]}">${s.score}</span></div>`).join('') : '<p class="muted">Nothing yet. Analyze a site above.</p>';
  $$('.hist').forEach(h => h.onclick = async () => renderResult(await (await api('/api/scan/' + h.dataset.id)).json()));
  if (state.user && state.user.is_admin) loadAdmin();
}
async function loadAdmin() {
  try {
    const s = await (await api('/api/admin/stats')).json();
    const list = a => a.map(x => `${esc(x.name)} (${x.count})`).join(', ') || '-';
    $('#adminBox').innerHTML = `<h2 style="margin-top:3rem">System insights</h2><div class="stat-grid">
      <div class="card tilt stat"><b>${s.total_scans}</b>scans</div><div class="card tilt stat"><b>${s.total_users}</b>users</div>
      <div class="card tilt stat"><b>${s.average_score ?? '-'}</b>average score</div></div>
      <div class="card" style="margin-top:1rem"><p><b>Top trackers:</b> ${list(s.top_trackers)}</p><p><b>Most common risks:</b> ${list(s.top_risks)}</p></div>`;
  } catch (_) {}
}

/* ---------- auth ---------- */
const dlg = $('#authDialog'), authErr = $('#authErr');
function setMode(m) {
  state.mode = m; const reg = m === 'register';
  $('#aName').hidden = !reg; $('#aName').required = reg;
  $('#authTitle').textContent = reg ? 'Create your account' : 'Welcome back';
  $('#authSub').textContent = reg ? 'Save every scan and revisit reports any time.' : 'Log in to keep a history of your scans.';
  $('#authSubmit').textContent = reg ? 'Sign up' : 'Log in';
  $('#authSwitchText').textContent = reg ? 'Already have an account?' : 'New here?';
  $('#authSwitch').textContent = reg ? 'Log in' : 'Create an account';
  authErr.hidden = true;
}
$('#authSwitch').onclick = e => { e.preventDefault(); setMode(state.mode === 'login' ? 'register' : 'login'); };
$('#authClose').onclick = () => dlg.close();
$('#authBtn').onclick = () => { if (state.user) logout(); else { setMode('login'); dlg.showModal(); } };
$('#authForm').addEventListener('submit', async e => {
  e.preventDefault(); authErr.hidden = true;
  const body = { email: $('#aEmail').value, password: $('#aPass').value };
  if (state.mode === 'register') body.name = $('#aName').value;
  try {
    const data = await (await api('/api/' + state.mode, { method: 'POST', body: JSON.stringify(body) })).json();
    state.token = data.token; localStorage.setItem('fp_token', data.token);
    dlg.close(); await initUser();
  } catch (err) { authErr.textContent = err.message; authErr.hidden = false; }
});
function logout() {
  localStorage.removeItem('fp_token'); state.token = null; state.user = null;
  $('#authBtn').textContent = 'Log in'; $('#history').hidden = true; $('#navHistory').style.display = 'none';
}
async function initUser() {
  if (!state.token) return;
  try {
    state.user = await (await api('/api/me')).json();
    $('#authBtn').textContent = 'Log out · ' + state.user.name.split(' ')[0];
    await loadHistory();
  } catch (_) { logout(); }
}
initUser();

/* ---------- light / dark toggle ---------- */
$('#themeBtn').onclick = () => {
  const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = next;
  localStorage.setItem('fp_theme', next);
};
