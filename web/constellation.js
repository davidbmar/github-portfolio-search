/* Portfolio Constellation — a 3D star atlas of every public repo.
   Adapted from ~/src/missionmap (constellation.js). Stellarium-style canvas
   renderer, custom 3D force layout, no dependencies. Data now comes from
   web/data/constellation.json (fetched) instead of a MISSION_DATA global;
   edges are embedding-similarity threads (not hand-authored dependencies);
   the time-lapse HUD is removed. Session: S-2026-07-12-1734-portfolio-constellation */
(function () {
  'use strict';

  fetch('data/constellation.json')
    .then((r) => r.json())
    .then(init)
    .catch((err) => {
      document.getElementById('counter').innerHTML =
        '<b style="color:#fb7185">failed to load constellation.json</b>';
      console.error('[constellation]', err);
    });

  function init(DATA) {
    const canvas = document.getElementById('sky');
    const ctx = canvas.getContext('2d');
    const tooltip = document.getElementById('tooltip');
    const panel = document.getElementById('panel');
    const panelBody = document.getElementById('panel-body');
    const searchEl = document.getElementById('search');
    const counterEl = document.getElementById('counter');
    const hintEl = document.getElementById('hint');

    const CATS = DATA.categories;
    const catKeys = Object.keys(CATS);

    let W = 0, H = 0, DPR = 1;
    function resize() {
      DPR = Math.min(window.devicePixelRatio || 1, 2);
      W = window.innerWidth; H = window.innerHeight;
      canvas.width = W * DPR; canvas.height = H * DPR;
      canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
    }
    resize();
    window.addEventListener('resize', resize);

    // ---------- color helpers ----------
    function hexToRgb(h) {
      return [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
    }
    function mix(hexA, hexB, t) {
      const a = hexToRgb(hexA), b = hexToRgb(hexB);
      return `#${a.map((v, i) => Math.round(v + (b[i] - v) * t).toString(16).padStart(2, '0')).join('')}`;
    }
    function rgba(hexC, alpha) {
      const [r, g, b] = hexToRgb(hexC);
      return `rgba(${r},${g},${b},${Math.max(0, Math.min(1, alpha))})`;
    }
    const techStr = (t) => Array.isArray(t) ? t.join(', ') : (t || '');
    // Descriptions/tags are LLM-generated from README text we don't fully
    // control, and this is a public page — escape before it touches innerHTML.
    const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g,
      (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
    const safeUrl = (u) => /^https?:\/\//i.test(u || '') ? u : '';

    // ---------- graph construction ----------
    let nodes = [], edges = [], byId = {};

    function starClassOf(r) {
      if (r >= 6.4) return 'supergiant';
      if (r >= 4.6) return 'giant';
      if (r >= 3.0) return 'star';
      return 'dwarf';
    }

    function anchorFor(i) {
      const n = catKeys.length;
      const t = (i + 0.5) / n;
      const phi = Math.acos(1 - 2 * t);
      const theta = Math.PI * (1 + Math.sqrt(5)) * i;
      const R = 320;
      return {
        x: R * Math.sin(phi) * Math.cos(theta),
        y: R * 0.62 * Math.cos(phi),
        z: R * Math.sin(phi) * Math.sin(theta),
      };
    }

    function buildGraph() {
      byId = {};
      nodes = DATA.projects.map((p) => {
        const r = Math.min(8.5, p.size || 2.2);
        const cls = starClassOf(r);
        const tint = { supergiant: 0.68, giant: 0.62, star: 0.55, dwarf: 0.5 }[cls];
        const a = anchorFor(catKeys.indexOf(p.cat));
        const n = {
          p, id: p.id, cat: p.cat, r, cls,
          color: mix(CATS[p.cat].color, '#ffffff', tint),
          lineColor: mix(CATS[p.cat].color, '#aab6d0', 0.35),
          x: a.x + (Math.random() - 0.5) * 150,
          y: a.y + (Math.random() - 0.5) * 150,
          z: a.z + (Math.random() - 0.5) * 150,
          vx: 0, vy: 0, vz: 0,
          phase: Math.random() * Math.PI * 2,
          tw: 0.5 + Math.random() * 1.1,
          sx: 0, sy: 0, ss: 0, sz: 1,
        };
        byId[p.id] = n;
        return n;
      });

      // undirected edges from directional similarity neighbors.
      // strong = either endpoint ranked the other in its top-2; score = the stronger view.
      const seen = new Map();
      DATA.projects.forEach((p) => (p.neighbors || []).forEach((c) => {
        if (!byId[c.to]) return;
        const key = [p.id, c.to].sort().join('|');
        const ex = seen.get(key);
        if (ex) {
          ex.strong = ex.strong || c.strong;
          ex.score = Math.max(ex.score, c.score);
          return;
        }
        const e = {
          a: byId[p.id], b: byId[c.to],
          cross: byId[p.id].cat !== byId[c.to].cat,
          strong: !!c.strong, score: c.score,
        };
        seen.set(key, e);
        edges.push(e);
      }));
    }

    // ---------- 3D physics ----------
    function tick() {
      const REPEL = 3200, SPRING = 0.02, DAMP = 0.84;
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i];
        for (let j = i + 1; j < nodes.length; j++) {
          const m = nodes[j];
          let dx = n.x - m.x, dy = n.y - m.y, dz = n.z - m.z;
          let d2 = dx * dx + dy * dy + dz * dz;
          if (d2 < 1) { dx = Math.random() - 0.5; dy = Math.random() - 0.5; dz = Math.random() - 0.5; d2 = 1; }
          if (d2 > 220000) continue;
          const d = Math.sqrt(d2);
          const f = REPEL / d2;
          const fx = (dx / d) * f, fy = (dy / d) * f, fz = (dz / d) * f;
          n.vx += fx; n.vy += fy; n.vz += fz;
          m.vx -= fx; m.vy -= fy; m.vz -= fz;
        }
        const a = anchorFor(catKeys.indexOf(n.cat));
        n.vx += (a.x - n.x) * 0.009;
        n.vy += (a.y - n.y) * 0.009;
        n.vz += (a.z - n.z) * 0.009;
      }
      edges.forEach((e) => {
        // stronger similarity pulls stars closer; cross-cluster springs are looser.
        const rest = e.cross ? 280 : (e.strong ? 60 : 96);
        const k = e.cross ? SPRING * 0.2 : SPRING * (e.strong ? 1.1 : 0.7);
        const dx = e.b.x - e.a.x, dy = e.b.y - e.a.y, dz = e.b.z - e.a.z;
        const d = Math.max(1, Math.hypot(dx, dy, dz));
        const f = (d - rest) * k;
        const fx = (dx / d) * f, fy = (dy / d) * f, fz = (dz / d) * f;
        e.a.vx += fx; e.a.vy += fy; e.a.vz += fz;
        e.b.vx -= fx; e.b.vy -= fy; e.b.vz -= fz;
      });
      nodes.forEach((n) => {
        n.vx *= DAMP; n.vy *= DAMP; n.vz *= DAMP;
        const sp = Math.hypot(n.vx, n.vy, n.vz);
        if (sp > 12) { const s = 12 / sp; n.vx *= s; n.vy *= s; n.vz *= s; }
        n.x += n.vx; n.y += n.vy; n.z += n.vz;
      });
    }

    // ---------- family MST (3D) — the constellation skeleton ----------
    function familyMST(fam) {
      const fn = nodes.filter((n) => n.cat === fam);
      if (fn.length < 2) return [];
      const inTree = [fn[0]], out = fn.slice(1), lines = [];
      while (out.length) {
        let best = null, bi = -1, bd = Infinity;
        for (let i = 0; i < out.length; i++) {
          for (const t of inTree) {
            const d = (out[i].x - t.x) ** 2 + (out[i].y - t.y) ** 2 + (out[i].z - t.z) ** 2;
            if (d < bd) { bd = d; best = t; bi = i; }
          }
        }
        lines.push([best, out[bi]]);
        inTree.push(out[bi]);
        out.splice(bi, 1);
      }
      return lines;
    }

    // ---------- camera (orbit) ----------
    const cam = { yaw: -0.4, pitch: 0.18, dist: 940, fov: 850, target: { x: 0, y: 0, z: 0 } };
    let lastInteract = 0;

    function basis() {
      const cy = Math.cos(cam.yaw), sy = Math.sin(cam.yaw);
      const cp = Math.cos(cam.pitch), sp = Math.sin(cam.pitch);
      return { right: { x: cy, y: 0, z: -sy }, up: { x: -sp * sy, y: cp, z: -sp * cy }, cy, sy, cp, sp };
    }

    function project(px, py, pz) {
      const { cy, sy, cp, sp } = basis();
      const x = px - cam.target.x, y = py - cam.target.y, z = pz - cam.target.z;
      const x1 = x * cy - z * sy;
      const z1 = x * sy + z * cy;
      const y2 = y * cp - z1 * sp;
      const z2 = y * sp + z1 * cp;
      const zc = z2 + cam.dist;
      if (zc < 60) return null;
      const s = cam.fov / zc;
      return { x: W / 2 + x1 * s, y: H / 2 + y2 * s, s, z: zc };
    }

    // ---------- background dust ----------
    const dust = [];
    for (let i = 0; i < 560; i++) {
      dust.push({
        ax: Math.random() * Math.PI * 2, ay: (Math.random() - 0.5) * Math.PI,
        depth: 0.3 + Math.random() * 0.7, s: Math.random() * 0.7 + 0.25,
        a: 0.04 + Math.random() * 0.22, warm: Math.random() < 0.25, ph: Math.random() * Math.PI * 2,
      });
    }

    // ---------- interaction ----------
    let hoverNode = null, orbiting = false, panningCam = false;
    let lastMouse = { x: 0, y: 0 }, mouseDownAt = null, spotlightIds = null;

    function nodeAt(sx, sy) {
      let best = null, bd = Infinity;
      nodes.forEach((n) => {
        if (!n.ss) return;
        const d = Math.hypot(n.sx - sx, n.sy - sy);
        const hit = Math.max(10, n.r * n.ss + 6);
        if (d < hit && d < bd) { bd = d; best = n; }
      });
      return best;
    }

    function neighborIds(id) {
      const s = new Set([id]);
      edges.forEach((e) => {
        if (e.a.id === id) s.add(e.b.id);
        if (e.b.id === id) s.add(e.a.id);
      });
      return s;
    }

    canvas.addEventListener('mousedown', (e) => {
      mouseDownAt = { x: e.clientX, y: e.clientY };
      if (e.shiftKey || e.button === 2) { panningCam = true; } else { orbiting = true; }
      canvas.classList.add('dragging');
      lastMouse = { x: e.clientX, y: e.clientY };
      lastInteract = performance.now();
    });
    canvas.addEventListener('contextmenu', (e) => e.preventDefault());

    window.addEventListener('mousemove', (e) => {
      const dx = e.clientX - lastMouse.x, dy = e.clientY - lastMouse.y;
      lastMouse = { x: e.clientX, y: e.clientY };
      if (orbiting) {
        cam.yaw += dx * 0.0042;
        cam.pitch = Math.max(-1.25, Math.min(1.25, cam.pitch + dy * 0.0036));
        hintEl.classList.add('faded');
        lastInteract = performance.now();
        return;
      }
      if (panningCam) {
        const { right, up } = basis();
        const k = cam.dist / cam.fov;
        cam.target.x -= (right.x * dx + up.x * dy) * k;
        cam.target.y -= (right.y * dx + up.y * dy) * k;
        cam.target.z -= (right.z * dx + up.z * dy) * k;
        lastInteract = performance.now();
        return;
      }
      hoverNode = nodeAt(e.clientX, e.clientY);
      canvas.classList.toggle('star-hover', !!hoverNode);
      if (hoverNode) {
        const c = CATS[hoverNode.cat];
        const deg = edges.filter((ed) => ed.a === hoverNode || ed.b === hoverNode).length;
        tooltip.innerHTML =
          `<div class="t-name">${esc(hoverNode.p.name)}</div>` +
          `<div class="t-cat" style="color:${c.color}">${hoverNode.cls.toUpperCase()} · ${esc(c.label)}</div>` +
          `<div class="t-desc">${esc(hoverNode.p.desc || '')}</div>` +
          `<div class="t-links">${deg} similar repo${deg === 1 ? '' : 's'} · click for details</div>`;
        tooltip.classList.remove('hidden');
        tooltip.style.left = Math.min(e.clientX, W - 310) + 'px';
        tooltip.style.top = Math.min(Math.max(e.clientY, 90), H - 130) + 'px';
      } else {
        tooltip.classList.add('hidden');
      }
    });

    window.addEventListener('mouseup', (e) => {
      const wasClick = mouseDownAt && Math.hypot(e.clientX - mouseDownAt.x, e.clientY - mouseDownAt.y) < 5;
      if (wasClick) {
        const n = nodeAt(e.clientX, e.clientY);
        if (n) showPanel(n.p);
        else panel.classList.add('hidden');
      }
      orbiting = false; panningCam = false; mouseDownAt = null;
      canvas.classList.remove('dragging');
    });

    function setDist(d) {
      cam.dist = Math.max(260, Math.min(2600, d));
      hintEl.classList.add('faded');
      lastInteract = performance.now();
    }

    canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const k = e.ctrlKey ? 0.0075 : 0.0011;
      setDist(cam.dist * Math.exp(e.deltaY * k));
    }, { passive: false });

    let gestureBase = 0;
    canvas.addEventListener('gesturestart', (e) => { e.preventDefault(); gestureBase = cam.dist; });
    canvas.addEventListener('gesturechange', (e) => { e.preventDefault(); if (gestureBase) setDist(gestureBase / e.scale); });
    canvas.addEventListener('gestureend', (e) => { e.preventDefault(); gestureBase = 0; });

    document.getElementById('zin').onclick = () => setDist(cam.dist * 0.74);
    document.getElementById('zout').onclick = () => setDist(cam.dist / 0.74);
    document.getElementById('zreset').onclick = () => {
      cam.yaw = -0.4; cam.pitch = 0.18; cam.target = { x: 0, y: 0, z: 0 };
      setDist(940);
    };
    document.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT') return;
      if (e.key === '+' || e.key === '=') setDist(cam.dist * 0.74);
      else if (e.key === '-' || e.key === '_') setDist(cam.dist / 0.74);
      else if (e.key === '0') document.getElementById('zreset').onclick();
    });

    let touchStart = null, pinchDist = 0;
    canvas.addEventListener('touchstart', (e) => {
      lastInteract = performance.now();
      if (e.touches.length === 1) {
        touchStart = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        lastMouse = { ...touchStart };
      } else if (e.touches.length === 2) {
        pinchDist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
      }
    }, { passive: true });
    canvas.addEventListener('touchmove', (e) => {
      lastInteract = performance.now();
      if (e.touches.length === 1) {
        const t = e.touches[0];
        cam.yaw += (t.clientX - lastMouse.x) * 0.0042;
        cam.pitch = Math.max(-1.25, Math.min(1.25, cam.pitch + (t.clientY - lastMouse.y) * 0.0036));
        lastMouse = { x: t.clientX, y: t.clientY };
      } else if (e.touches.length === 2) {
        const d = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
        if (pinchDist) cam.dist = Math.max(260, Math.min(2600, cam.dist * pinchDist / d));
        pinchDist = d;
      }
    }, { passive: true });
    canvas.addEventListener('touchend', (e) => {
      if (touchStart && e.changedTouches.length === 1 && e.touches.length === 0) {
        const t = e.changedTouches[0];
        if (Math.hypot(t.clientX - touchStart.x, t.clientY - touchStart.y) < 8) {
          const n = nodeAt(t.clientX, t.clientY);
          if (n) showPanel(n.p);
        }
      }
      touchStart = null; pinchDist = 0;
    });

    // ---------- search ----------
    searchEl.addEventListener('input', () => {
      tooltip.classList.add('hidden');
      hoverNode = null;
      const q = searchEl.value.trim().toLowerCase();
      if (!q) { spotlightIds = null; return; }
      spotlightIds = new Set(nodes.filter((n) => {
        const p = n.p;
        return (p.name || '').toLowerCase().includes(q) ||
          (p.desc || '').toLowerCase().includes(q) ||
          techStr(p.tech).toLowerCase().includes(q) ||
          (p.reuse && (p.reuse.reuse_tags || []).join(' ').toLowerCase().includes(q));
      }).map((n) => n.id));
    });
    searchEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && spotlightIds && spotlightIds.size) {
        const n = nodes.find((m) => spotlightIds.has(m.id));
        cam.target = { x: n.x, y: n.y, z: n.z };
        cam.dist = Math.min(cam.dist, 620);
        showPanel(n.p);
      }
    });

    // ---------- detail panel ----------
    function showPanel(p) {
      const c = CATS[p.cat];
      const node = byId[p.id];
      const reuse = p.reuse || {};
      const patterns = reuse.patterns || [];
      const tags = reuse.reuse_tags || [];
      const nb = (p.neighbors || []).slice().sort((a, b) => b.score - a.score);
      const byPid = Object.fromEntries(DATA.projects.map((q) => [q.id, q]));

      const nbLi = (n) => {
        const t = byPid[n.to];
        if (!t) return '';
        return `<li data-goto="${esc(n.to)}"><span class="arrow ${n.strong ? 'strong' : ''}">✦</span>` +
          `<span class="cname">${esc(t.name)}</span><span class="cscore">${n.score.toFixed(2)}</span></li>`;
      };
      const url = safeUrl(p.url);

      panelBody.innerHTML = `
        <div class="panel-cat"><span class="legend-dot" style="background:${c.color}"></span>${esc(c.label)}${node ? ' · ' + node.cls.toUpperCase() : ''}</div>
        <h2>${esc(p.name)}</h2>
        <div class="panel-badges">
          ${p.lang ? `<span class="badge b-lang">${esc(p.lang)}</span>` : ''}
          ${techStr(p.tech) ? `<span class="badge">${esc(techStr(p.tech))}</span>` : ''}
        </div>
        ${url ? `<a class="gh-link" href="${esc(url)}" target="_blank" rel="noopener">↗ View on GitHub</a>` : ''}
        <p class="desc">${esc(p.desc || '')}</p>
        ${reuse.how_to_apply ? `<h3>How to reuse it</h3><p class="reuse-apply">${esc(reuse.how_to_apply)}</p>` : ''}
        ${patterns.length ? `<h3>Patterns</h3><div class="chips">${patterns.map((x) => `<span class="chip">${esc(x)}</span>`).join('')}</div>` : ''}
        ${tags.length ? `<h3>Reuse tags</h3><div class="chips">${tags.map((x) => `<span class="chip tag">${esc(x)}</span>`).join('')}</div>` : ''}
        <h3>Nearest in the sky ← ${nb.length}</h3>
        ${nb.length ? `<ul class="conn-list">${nb.map(nbLi).join('')}</ul>` : '<p class="none-note">A lone star — no strong neighbors.</p>'}
      `;
      panelBody.querySelectorAll('[data-goto]').forEach((el) => {
        el.onclick = () => {
          const q = byPid[el.dataset.goto];
          if (!q) return;
          showPanel(q);
          const n = byId[q.id];
          if (n) { cam.target = { x: n.x, y: n.y, z: n.z }; cam.dist = Math.min(cam.dist, 700); }
        };
      });
      panel.classList.remove('hidden');
    }

    document.getElementById('panel-close').onclick = () => panel.classList.add('hidden');
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') panel.classList.add('hidden'); });

    // ---------- render ----------
    function depthFade(z) { return Math.max(0.3, Math.min(1, 1.5 - z / (cam.dist * 1.6))); }

    function draw(now) {
      ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
      ctx.clearRect(0, 0, W, H);

      ctx.fillStyle = '#05060c';
      ctx.fillRect(0, 0, W, H);
      const bg = ctx.createRadialGradient(W / 2, H / 2, 0, W / 2, H / 2, Math.max(W, H) * 0.7);
      bg.addColorStop(0, 'rgba(24,32,58,0.28)');
      bg.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, W, H);

      dust.forEach((d) => {
        const px = ((d.ax + cam.yaw * d.depth * 0.35) / (Math.PI * 2) % 1 + 1) % 1 * (W + 80) - 40;
        const py = ((d.ay + cam.pitch * d.depth * 0.5) / Math.PI % 1 + 1) % 1 * (H + 80) - 40;
        const tw = 0.8 + 0.2 * Math.sin(now * 0.001 * d.depth + d.ph);
        ctx.fillStyle = d.warm ? `rgba(235,220,195,${d.a * tw})` : `rgba(200,212,238,${d.a * tw})`;
        ctx.beginPath();
        ctx.arc(px, py, d.s, 0, Math.PI * 2);
        ctx.fill();
      });

      nodes.forEach((n) => {
        const pr = project(n.x, n.y, n.z);
        if (pr) { n.sx = pr.x; n.sy = pr.y; n.ss = pr.s; n.sz = pr.z; } else n.ss = 0;
      });

      const hood = hoverNode ? neighborIds(hoverNode.id) : null;
      const dimming = !!hood || !!spotlightIds;
      const visAlpha = (n) => {
        let a = 1;
        if (hood && !hood.has(n.id)) a *= 0.22;
        if (spotlightIds && !spotlightIds.has(n.id)) a *= 0.16;
        return a;
      };

      // cross-cluster threads — barely-there hairlines, lit on hover
      edges.filter((e) => e.cross).forEach((e) => {
        if (!e.a.ss || !e.b.ss) return;
        const a = Math.min(visAlpha(e.a), visAlpha(e.b));
        if (a <= 0.01) return;
        const hot = hoverNode && (e.a === hoverNode || e.b === hoverNode);
        const fade = Math.min(depthFade(e.a.sz), depthFade(e.b.sz));
        ctx.strokeStyle = hot ? 'rgba(200,215,240,0.5)' : `rgba(150,165,200,${0.05 * e.score * a * fade})`;
        ctx.lineWidth = hot ? 0.9 : 0.5;
        ctx.beginPath();
        ctx.moveTo(e.a.sx, e.a.sy);
        ctx.lineTo(e.b.sx, e.b.sy);
        ctx.stroke();
      });

      // constellation skeleton — faint MST per cluster
      catKeys.forEach((k) => {
        const lc = mix(CATS[k].color, '#96a4c4', 0.4);
        familyMST(k).forEach(([a, b]) => {
          if (!a.ss || !b.ss) return;
          const al = Math.min(visAlpha(a), visAlpha(b));
          if (al <= 0.01) return;
          const fade = Math.min(depthFade(a.sz), depthFade(b.sz));
          ctx.strokeStyle = rgba(lc, 0.11 * al * fade);
          ctx.lineWidth = 0.6;
          ctx.beginPath();
          ctx.moveTo(a.sx, a.sy);
          ctx.lineTo(b.sx, b.sy);
          ctx.stroke();
        });
      });

      // within-cluster similarity threads — strong ones brighter
      edges.filter((e) => !e.cross).forEach((e) => {
        if (!e.a.ss || !e.b.ss) return;
        const a = Math.min(visAlpha(e.a), visAlpha(e.b));
        if (a <= 0.01) return;
        const hot = hoverNode && (e.a === hoverNode || e.b === hoverNode);
        const fade = Math.min(depthFade(e.a.sz), depthFade(e.b.sz));
        const base = e.strong ? 0.28 : 0.12;
        ctx.strokeStyle = hot ? 'rgba(210,225,245,0.7)' : rgba(e.a.lineColor, base * e.score * a * fade);
        ctx.lineWidth = hot ? 1 : (e.strong ? 0.75 : 0.5);
        ctx.beginPath();
        ctx.moveTo(e.a.sx, e.a.sy);
        ctx.lineTo(e.b.sx, e.b.sy);
        ctx.stroke();
      });

      // stars — small, crisp, painter's order far→near
      const ordered = [...nodes].sort((a, b) => b.sz - a.sz);
      const labels = [];
      ordered.forEach((n) => {
        if (!n.ss) return;
        const a = visAlpha(n);
        if (a <= 0.005) return;
        if (n.sx < -40 || n.sx > W + 40 || n.sy < -40 || n.sy > H + 40) return;
        const fade = depthFade(n.sz);
        const tw = 1 + 0.07 * Math.sin(now * 0.001 * n.tw + n.phase);
        const r = Math.max(0.7, Math.min(6, n.r * n.ss * 0.62)) * tw;
        const A = a * fade;

        if (n.cls === 'supergiant' || n.cls === 'giant') {
          const gR = r * (n.cls === 'supergiant' ? 4 : 3);
          const gA = (n.cls === 'supergiant' ? 0.16 : 0.1) * A;
          const g = ctx.createRadialGradient(n.sx, n.sy, 0, n.sx, n.sy, gR);
          g.addColorStop(0, rgba(n.color, gA));
          g.addColorStop(1, rgba(n.color, 0));
          ctx.fillStyle = g;
          ctx.beginPath();
          ctx.arc(n.sx, n.sy, gR, 0, Math.PI * 2);
          ctx.fill();
        }

        const coreA = ({ supergiant: 1, giant: 0.95, star: 0.85, dwarf: 0.6 }[n.cls]) * A;
        ctx.fillStyle = rgba(n.color, Math.min(1, coreA));
        ctx.beginPath();
        ctx.arc(n.sx, n.sy, r, 0, Math.PI * 2);
        ctx.fill();
        if (n.cls === 'supergiant') {
          ctx.fillStyle = `rgba(255,255,255,${0.9 * A})`;
          ctx.beginPath();
          ctx.arc(n.sx, n.sy, r * 0.45, 0, Math.PI * 2);
          ctx.fill();
        }

        if (hoverNode === n) {
          ctx.strokeStyle = 'rgba(220,232,250,0.7)';
          ctx.lineWidth = 0.8;
          ctx.beginPath();
          ctx.arc(n.sx, n.sy, r + 4.5, 0, Math.PI * 2);
          ctx.stroke();
        }

        const named = n.cls === 'supergiant' ||
          (n.cls === 'giant' && n.ss > 0.85) ||
          (n.ss > 1.5 && n.cls !== 'dwarf');
        if ((hoverNode === n || (spotlightIds && spotlightIds.has(n.id)) || (named && !dimming)) && A > 0.2) {
          labels.push({ n, r, A });
        }
      });

      ctx.font = `10px 'JetBrains Mono', monospace`;
      ctx.textAlign = 'left';
      // Place labels by priority (hovered/spotlight, then biggest stars) and
      // greedily drop any that would overlap one already placed — keeps the
      // dense clusters legible instead of a pile-up. Long titles get truncated.
      const isHot = (n) => hoverNode === n || (spotlightIds && spotlightIds.has(n.id));
      labels.sort((p, q) => (isHot(q.n) - isHot(p.n)) || (q.n.r - p.n.r));
      const placed = [];
      labels.forEach(({ n, r, A }) => {
        const hot = isHot(n);
        const full = n.p.name || '';
        const text = full.length > 30 ? full.slice(0, 29) + '…' : full;
        const x = n.sx + r + 7, y = n.sy + 3.5;
        const box = { x: x - 2, y: y - 11, w: text.length * 6.0 + 4, h: 15 };
        const clash = !hot && placed.some((b) =>
          box.x < b.x + b.w && box.x + box.w > b.x && box.y < b.y + b.h && box.y + box.h > b.y);
        if (clash) return;
        placed.push(box);
        ctx.fillStyle = `rgba(196,208,232,${(hot ? 0.95 : 0.42) * A})`;
        ctx.fillText(text, x, y);
      });

      // constellation names
      catKeys.forEach((k) => {
        const fn = nodes.filter((n) => n.cat === k && n.ss);
        if (fn.length < 2) return;
        let cx = 0, topY = Infinity, cz = 0;
        fn.forEach((n) => { cx += n.sx; cz += n.sz; topY = Math.min(topY, n.sy); });
        cx /= fn.length; cz /= fn.length;
        const alpha = (dimming ? 0.08 : 0.3) * depthFade(cz);
        ctx.font = `500 10px 'JetBrains Mono', monospace`;
        ctx.textAlign = 'center';
        ctx.fillStyle = rgba(mix(CATS[k].color, '#c8d2e8', 0.3), alpha);
        ctx.fillText(CATS[k].label.toUpperCase().split('').join(' '), cx, topY - 22);
      });
    }

    // ---------- HUD ----------
    function updateHUD() {
      counterEl.innerHTML =
        `<b>${nodes.length}</b> STARS · <b>${catKeys.length}</b> CONSTELLATIONS · ` +
        `<b>${edges.length}</b> THREADS`;
    }

    // ---------- main loop ----------
    buildGraph();
    for (let i = 0; i < 420; i++) tick();
    updateHUD();

    function frame(now) {
      if (now - lastInteract > 4000 && !orbiting && !panningCam && panel.classList.contains('hidden')) {
        cam.yaw += 0.00038;
      }
      tick();
      draw(now);
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);

    setTimeout(() => hintEl.classList.add('faded'), 9000);
  }
})();
