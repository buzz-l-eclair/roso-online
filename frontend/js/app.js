(function(){
  const API = '/api';

  // ---------- Garde d'authentification ----------
  // Toute page de l'app nécessite une session valide ; sinon redirection vers login.html.
  async function ensureAuth(){
    try{
      const res = await fetch(`${API}/auth/me`, { credentials: 'include' });
      if(!res.ok){ window.location.href = '/login.html'; return null; }
      return await res.json();
    }catch(err){
      window.location.href = '/login.html';
      return null;
    }
  }

  // ---------- Starfield (ambiance, identique au reste du site) ----------
  (function initStars(){
    const starsEl = document.getElementById('stars');
    const frag = document.createDocumentFragment();
    for(let i=0;i<100;i++){
      const s = document.createElement('div');
      s.className = 'star';
      const size = Math.random()*1.6+0.6;
      s.style.width = size+'px'; s.style.height = size+'px';
      s.style.left = Math.random()*100+'%'; s.style.top = Math.random()*140+'%';
      s.style.opacity = (Math.random()*0.6+0.3).toFixed(2);
      s.style.animation = `twinkle ${(Math.random()*4+3).toFixed(1)}s ease-in-out infinite`;
      s.style.animationDelay = (Math.random()*4)+'s';
      frag.appendChild(s);
    }
    starsEl.appendChild(frag);
    const style = document.createElement('style');
    style.textContent = `@keyframes twinkle{0%,100%{opacity:.25}50%{opacity:.9}}`;
    document.head.appendChild(style);
  })();

  const main = document.getElementById('main');

  function statusPill(t){
    if(t.mode === 'manual') return `<span class="status-pill manual"><span class="dot"></span>manuel</span>`;
    if(t.mode === 'api') return `<span class="status-pill ok"><span class="dot"></span>API tierce</span>`;
    if(t.mode === 'link') return `<span class="status-pill ok"><span class="dot"></span>lien direct</span>`;
    return t.available
      ? `<span class="status-pill ok"><span class="dot"></span>installé</span>`
      : `<span class="status-pill missing"><span class="dot"></span>non détecté</span>`;
  }

  function modeLabel(mode){
    return { oneshot:'▶ Lancer', background:'⏱ Fond continu', manual:'🔧 Manuel', cli:'▶ Lancer', api:'🔌 Interroger', link:'↗ Ouvrir' }[mode] || 'Ouvrir';
  }

  function cardHTML(t){
    const keyBadge = (t.mode === 'api' && t.requires_key)
      ? `<span class="key-badge ${t.keyConfigured ? 'set' : 'unset'}">${t.keyConfigured ? 'clé OK' : 'clé manquante'}</span>`
      : '';
    return `
      <div class="card" data-name="${t.name}">
        <span class="badge">${t.category}<span class="gh-tag">${t.repo && t.repo.includes('/') ? 'GitHub' : (t.mode === 'link' ? 'Lien' : t.mode === 'api' ? 'API' : 'Dépôt')}</span></span>
        <span class="tool-name" style="cursor:pointer" data-open="${t.id}">${t.name}</span>
        <p class="desc">${t.notes || ''}</p>
        <div class="card-actions">
          ${statusPill(t)}
          <div style="display:flex; gap:8px; align-items:center;">
            ${keyBadge}
            <button class="btn-chip" data-open="${t.id}">${modeLabel(t.mode)}</button>
          </div>
        </div>
      </div>`;
  }

  async function loadTools(){
    const user = await ensureAuth();
    if(!user) return;

    let res, tools;
    try{
      res = await fetch(`${API}/tools`, { credentials: 'include' });
      if(!res.ok) throw new Error(`HTTP ${res.status}`);
      tools = await res.json();
    }catch(err){
      main.innerHTML = `
        <div class="install-banner missing" style="max-width:640px;margin:60px auto;">
          ⚠️ Impossible de joindre le backend (${err.message}).<br><br>
          Vérifie que le serveur tourne et que tu es bien connecté.
        </div>`;
      return;
    }

    // Statut des clés API perso, pour afficher le badge "clé OK / manquante" sur les cartes api
    let keyStatus = {};
    try{
      const keysRes = await fetch(`${API}/keys`, { credentials: 'include' });
      if(keysRes.ok){
        const keys = await keysRes.json();
        keys.forEach(k => keyStatus[k.service] = k.configured);
      }
    }catch(err){ /* pas bloquant pour l'affichage */ }
    tools.forEach(t => { if(t.requires_key) t.keyConfigured = !!keyStatus[t.service]; });

    document.getElementById('toolCount').textContent = tools.length;
    document.getElementById('availCount').textContent = tools.filter(t => t.available).length;

    let topbar = document.getElementById('topbar');
    if(!topbar){
      topbar = document.createElement('div');
      topbar.id = 'topbar';
      topbar.className = 'topbar';
      topbar.innerHTML = `
        <button id="apiKeysBtn">🔑 Mes clés API</button>
        <button id="logoutBtn">Se déconnecter</button>`;
      document.body.insertBefore(topbar, document.getElementById('stars').nextSibling);
      topbar.querySelector('#apiKeysBtn').addEventListener('click', openApiKeysModal);
      topbar.querySelector('#logoutBtn').addEventListener('click', async () => {
        await fetch(`${API}/auth/logout`, { method:'POST', credentials:'include' });
        window.location.href = '/login.html';
      });
    }

    const byCat = {};
    tools.forEach(t => (byCat[t.category] = byCat[t.category] || []).push(t));

    let html = `<section class="zone"><div class="zone-head"><h2 class="zone-title">Outils câblés</h2></div>`;
    Object.keys(byCat).forEach(cat => {
      html += `<div class="cat"><div class="cat-title">${cat} <span class="count">(${byCat[cat].length})</span></div><div class="grid">`;
      html += byCat[cat].map(cardHTML).join('');
      html += `</div></div>`;
    });
    html += `</section>`;
    main.innerHTML = html;

    const map = {};
    tools.forEach(t => map[t.id] = t);

    main.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-open]');
      if(!btn) return;
      openTool(map[btn.dataset.open]);
    });
  }

  // ---------- Panneau outil : dispatch selon le mode ----------
  function openTool(t){
    const body = ROSOModal.open(t.name, '');
    if(t.mode === 'oneshot' || t.mode === 'cli') renderOneshot(body, t);
    else if(t.mode === 'background') renderBackground(body, t);
    else if(t.mode === 'api') renderApiTool(body, t);
    else if(t.mode === 'link') renderLinkTool(body, t);
    else renderManual(body, t);
  }

  function installBanner(t){
    if(t.available){
      return `<div class="install-banner ok">✅ Détecté sur ta machine.</div>`;
    }
    return `<div class="install-banner missing">⚠️ Non détecté. Installation :<code>${t.install}</code></div>`;
  }

  function renderOneshot(body, t){
    const fields = (t.params || []).map(p => `
      <div class="run-field">
        <label>${p.label}${p.required ? '' : ' (optionnel)'}</label>
        <input type="text" name="${p.key}" placeholder="${p.placeholder || ''}" ${p.required ? 'required' : ''}>
        ${p.help ? `<span class="help">${p.help}</span>` : ''}
      </div>`).join('');

    body.innerHTML = `
      ${installBanner(t)}
      ${t.requires_manual_setup ? `<div class="manual-box">⚠️ Configuration préalable requise, une seule fois, dans un terminal : <code>${t.requires_manual_setup}</code></div>` : ''}
      <form class="mt-form" style="flex-direction:column; align-items:stretch;" id="runForm">
        ${fields}
        <button class="btn-primary" type="submit" ${t.available ? '' : 'disabled'}>Exécuter</button>
      </form>
      <div class="term-holder"></div>`;

    const form = body.querySelector('#runForm');
    const holder = body.querySelector('.term-holder');
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const params = {};
      new FormData(form).forEach((v,k) => params[k] = v);
      holder.innerHTML = `<div class="roso-modal-loading"><span class="spinner"></span>Exécution de ${t.name}…</div>`;
      try{
        const res = await fetch(`${API}/tools/${t.id}/run`, {
          method:'POST', headers:{'Content-Type':'application/json'},
          credentials: 'include',
          body: JSON.stringify({ params })
        });
        const data = await res.json();
        if(!res.ok || data.detail){
          holder.innerHTML = `<div class="roso-modal-error">${data.detail || data.error || 'Erreur inconnue'}</div>`;
          return;
        }
        holder.innerHTML = `
          <div class="term">${(data.stdout || '(sortie vide)') + (data.stderr ? '\n\n[stderr]\n' + data.stderr : '')}</div>
          <div class="run-meta">
            <span>code retour : ${data.returncode}</span>
            <span>durée : ${data.duration}s</span>
          </div>`;
      }catch(err){
        holder.innerHTML = `<div class="roso-modal-error">Erreur de communication avec le backend local : ${err.message}</div>`;
      }
    });
  }

  function renderBackground(body, t){
    body.innerHTML = `
      ${installBanner(t)}
      <div class="bg-controls">
        <button class="btn-primary" id="startBtn" ${t.available ? '' : 'disabled'}>Démarrer</button>
        <button class="btn-secondary" id="stopBtn">Arrêter</button>
        <span class="bg-status" id="bgStatus"><span class="dot"></span><span id="bgStatusLabel">arrêté</span></span>
      </div>
      <div class="term empty" id="bgLog">Aucun log pour l'instant.</div>`;

    const statusEl = body.querySelector('#bgStatus');
    const statusLabel = body.querySelector('#bgStatusLabel');
    const logEl = body.querySelector('#bgLog');
    let poller = null;

    async function refresh(){
      const res = await fetch(`${API}/tools/${t.id}/logs`, { credentials: 'include' });
      const data = await res.json();
      statusEl.classList.toggle('running', data.status === 'running');
      statusLabel.textContent = data.status === 'running' ? 'en cours' : 'arrêté';
      if(data.lines && data.lines.length){
        logEl.classList.remove('empty');
        logEl.textContent = data.lines.join('\n');
        logEl.scrollTop = logEl.scrollHeight;
      }
    }

    body.querySelector('#startBtn').addEventListener('click', async () => {
      const res = await fetch(`${API}/tools/${t.id}/start`, { method:'POST', credentials: 'include' });
      const data = await res.json();
      if(data.error){ logEl.textContent = data.error; return; }
      poller = setInterval(refresh, 2000);
      refresh();
    });
    body.querySelector('#stopBtn').addEventListener('click', async () => {
      await fetch(`${API}/tools/${t.id}/stop`, { method:'POST', credentials: 'include' });
      if(poller) clearInterval(poller);
      refresh();
    });

    refresh();
    poller = setInterval(refresh, 3000);
  }

  function renderManual(body, t){
    body.innerHTML = `
      <div class="manual-box">${t.manual_instructions || "Cet outil nécessite un lancement manuel."}</div>
      <div class="install-banner ${t.available ? 'ok' : 'missing'}">
        ${t.available ? '✅ Détecté sur ta machine.' : '⚠️ Installation :'}
        ${t.available ? '' : `<code>${t.install}</code>`}
      </div>`;
  }

  function renderApiTool(body, t){
    const fields = (t.params || []).map(p => `
      <div class="run-field">
        <label>${p.label}${p.required ? '' : ' (optionnel)'}</label>
        <input type="text" name="${p.key}" placeholder="${p.placeholder || ''}" ${p.required ? 'required' : ''}>
      </div>`).join('');

    const keyWarning = (t.requires_key && !t.keyConfigured)
      ? `<div class="install-banner missing">⚠️ Aucune clé ${t.service} configurée. Ajoute-la via « 🔑 Mes clés API » en haut de page, puis relance.</div>`
      : '';

    body.innerHTML = `
      ${keyWarning}
      <form class="mt-form" style="flex-direction:column; align-items:stretch;" id="runForm">
        ${fields}
        <button class="btn-primary" type="submit">Interroger</button>
      </form>
      <div class="term-holder"></div>`;

    const form = body.querySelector('#runForm');
    const holder = body.querySelector('.term-holder');
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const params = {};
      new FormData(form).forEach((v,k) => params[k] = v);
      holder.innerHTML = `<div class="roso-modal-loading"><span class="spinner"></span>Interrogation de ${t.name}…</div>`;
      try{
        const res = await fetch(`${API}/tools/${t.id}/run`, {
          method:'POST', headers:{'Content-Type':'application/json'},
          credentials: 'include',
          body: JSON.stringify({ params })
        });
        const data = await res.json();
        if(!res.ok || data.detail){
          holder.innerHTML = `<div class="roso-modal-error">${data.detail || 'Erreur inconnue'}</div>`;
          return;
        }
        holder.innerHTML = `
          <div class="term">${data.body || '(réponse vide)'}</div>
          <div class="run-meta">
            <span>code HTTP : ${data.status_code}</span>
            <span>durée : ${data.duration}s</span>
          </div>`;
      }catch(err){
        holder.innerHTML = `<div class="roso-modal-error">Erreur de communication : ${err.message}</div>`;
      }
    });
  }

  function renderLinkTool(body, t){
    const fields = (t.params || []).map(p => `
      <div class="run-field">
        <label>${p.label}${p.required ? '' : ' (optionnel)'}</label>
        <input type="text" name="${p.key}" placeholder="${p.placeholder || ''}" ${p.required ? 'required' : ''}>
      </div>`).join('');

    body.innerHTML = `
      <div class="link-box">
        <p class="desc">${t.notes || ''}</p>
        <form class="mt-form" style="flex-direction:column; align-items:stretch;" id="runForm">
          ${fields}
          <button class="btn-primary" type="submit">↗ Ouvrir dans un nouvel onglet</button>
        </form>
      </div>`;

    const form = body.querySelector('#runForm');
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const params = {};
      new FormData(form).forEach((v,k) => params[k] = v);
      try{
        const res = await fetch(`${API}/tools/${t.id}/run`, {
          method:'POST', headers:{'Content-Type':'application/json'},
          credentials: 'include',
          body: JSON.stringify({ params })
        });
        const data = await res.json();
        if(!res.ok || data.detail){
          alert(data.detail || 'Erreur inconnue');
          return;
        }
        window.open(data.url, '_blank', 'noopener');
      }catch(err){
        alert('Erreur de communication : ' + err.message);
      }
    });
  }

  // ---------- Modal "Mes clés API" ----------
  async function openApiKeysModal(){
    const body = ROSOModal.open('Mes clés API', `<div class="roso-modal-loading"><span class="spinner"></span>Chargement…</div>`);
    let keys;
    try{
      const res = await fetch(`${API}/keys`, { credentials: 'include' });
      keys = await res.json();
    }catch(err){
      body.innerHTML = `<div class="roso-modal-error">Impossible de charger les clés : ${err.message}</div>`;
      return;
    }

    body.innerHTML = `
      <p class="desc" style="margin-bottom:14px;">Chaque clé est stockée chiffrée et n'est utilisée que pour tes propres requêtes. Elle n'est jamais partagée avec les autres comptes.</p>
      ${keys.map(k => `
        <div class="apikeys-row" data-service="${k.service}">
          <strong style="min-width:110px;">${k.service}</strong>
          <input type="password" placeholder="${k.configured ? '•••••••• (déjà configurée)' : 'Coller ta clé ici'}">
          <span class="apikeys-status">${k.configured ? '✅ configurée' : '— absente'}</span>
          <button class="btn-chip save-key">Enregistrer</button>
          ${k.configured ? '<button class="btn-chip delete-key">✕</button>' : ''}
        </div>`).join('')}`;

    body.querySelectorAll('.save-key').forEach(btn => {
      btn.addEventListener('click', async () => {
        const row = btn.closest('.apikeys-row');
        const service = row.dataset.service;
        const value = row.querySelector('input').value.trim();
        if(!value) return;
        await fetch(`${API}/keys`, {
          method:'POST', headers:{'Content-Type':'application/json'}, credentials:'include',
          body: JSON.stringify({ service, value })
        });
        openApiKeysModal();
      });
    });
    body.querySelectorAll('.delete-key').forEach(btn => {
      btn.addEventListener('click', async () => {
        const service = btn.closest('.apikeys-row').dataset.service;
        await fetch(`${API}/keys/${service}`, { method:'DELETE', credentials:'include' });
        openApiKeysModal();
      });
    });
  }

  loadTools();
})();
