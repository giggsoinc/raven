/* Shared OKF graph viewer — one file for every trees/*.html */
(function () {
  const el = document.getElementById("okf");
  if (!el) return;
  const G = JSON.parse(el.textContent);
  window.G = G;
  const title = document.getElementById("title");
  if (title) title.textContent = G.repo || title.textContent;
  const head = document.getElementById("head");
  if (head) head.textContent = headLabel();
  const sum = document.getElementById("sum");
  if (sum) sum.textContent = G.summary || "No README summary yet.";
  let mode = "both";
  let POS = {};
  let flowTimer = 0;
  let focusCommit = null;
  let focusFile = null;

  function headLabel() {
    const baked = G.git_head || "";
    const live = G.live_head || "";
    if (live && baked && live !== baked) {
      return "live HEAD: " + live + " · graph baked at " + baked;
    }
    return live || baked || "";
  }
  function headMetaHtml() {
    const baked = G.git_head || "";
    const live = G.live_head || "";
    if (!baked && !live) return "";
    if (live && baked && live !== baked) {
      return "live HEAD: " + esc(live) + "<br>graph baked at: " + esc(baked) + "<br>";
    }
    return "HEAD: " + esc(live || baked) + "<br>";
  }

  function extractedNeighbors(id) {
    const ids = new Set();
    (G.edges || []).forEach((e) => {
      if (e.tag !== "EXTRACTED") return;
      if (e.from === id) ids.add(e.to);
      if (e.to === id) ids.add(e.from);
    });
    return ids;
  }

  function pickSet() {
    const files = G.nodes.filter((n) => n.type === "file").sort((a, b) => (b.churn_30d || 0) - (a.churn_30d || 0)).slice(0, 48);
    const commits = G.nodes.filter((n) => n.type === "commit").slice(0, 20);
    const byId = {};
    G.nodes.forEach((n) => { byId[n.id] = n; });
    if (mode === "file") {
      if (focusFile && byId[focusFile] && !files.some((n) => n.id === focusFile)) {
        return [byId[focusFile]].concat(files).slice(0, 48);
      }
      return files;
    }
    if (mode === "commit") {
      if (focusCommit && byId[focusCommit]) {
        const keep = new Set([focusCommit]);
        extractedNeighbors(focusCommit).forEach((id) => keep.add(id));
        Array.from(keep).forEach((id) => {
          extractedNeighbors(id).forEach((oid) => {
            const n = byId[oid];
            if (n && n.type !== "project") keep.add(oid);
          });
        });
        return G.nodes.filter((n) => keep.has(n.id));
      }
      const cids = new Set(commits.map((c) => c.id));
      const extra = new Set();
      (G.edges || []).forEach((e) => {
        if (e.tag !== "EXTRACTED") return;
        if (cids.has(e.from)) extra.add(e.to);
        if (cids.has(e.to)) extra.add(e.from);
      });
      const linked = G.nodes.filter((n) => extra.has(n.id) && n.type !== "commit").slice(0, 60);
      return commits.concat(linked);
    }
    return files.concat(commits);
  }
  function words(s, n) {
    const parts = String(s || "").replace(/\s+/g, " ").trim().split(" ").filter(Boolean);
    if (parts.length <= n) return parts.join(" ");
    return parts.slice(0, n).join(" ") + "…";
  }
  function esc(s) {
    return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function nodeSummary(n) {
    if (n.type === "commit") return n.summary || n.subject || "Commit with no message.";
    if (n.purpose) return n.purpose;
    const why = (n.history && n.history[0] && n.history[0].why) || "";
    if (why) return "Last change: " + why;
    return (n.type === "file" ? "Source file" : n.type) + " — no docstring yet.";
  }
  function fileChangeSummary(fileNode, commitNode) {
    const bits = [];
    if (commitNode) {
      bits.push((commitNode.short || "") + " " + (commitNode.subject || commitNode.summary || ""));
    }
    const hist = (fileNode && fileNode.history) || [];
    hist.slice(0, 3).forEach((h) => {
      bits.push((h.commit || "") + " " + (h.why || ""));
    });
    const text = bits.join(". ").trim();
    return text || "No commit message stored for this path in the graph.";
  }
  function fileLinks(n) {
    const files = n.files || [];
    if (!files.length) return "";
    return files.slice(0, 40).map((f) => {
      const safe = String(f).replace(/"/g, "");
      return '<a href="#" class="file-link" data-file="' + esc(safe) + '" data-commit="' + esc(n.id) + '">' + esc(f) + "</a>";
    }).join("<br>");
  }
  function folderTree(rel) {
    const parts = String(rel || "").split("/").filter(Boolean);
    if (!parts.length) return "";
    const lines = parts.map((p, i) => {
      const pad = "&nbsp;".repeat(i * 2);
      const last = i === parts.length - 1;
      return pad + (last ? "└─ " + esc(p) : "├─ " + esc(p) + "/");
    });
    return "<h3>Folder</h3><pre class='tree'>" + lines.join("\n") + "</pre>";
  }
  function fileAbs(rel) {
    const root = String(G.root || "").replace(/\\/g, "/").replace(/\/$/, "");
    const path = String(rel || "").replace(/^\/+/, "");
    if (!root || !path) return "";
    return root + "/" + path;
  }
  function fileHref(rel) {
    const abs = fileAbs(rel);
    if (!abs) return "";
    return "file://" + (abs.charAt(0) === "/" ? "" : "/") + abs.split("/").map(encodeURIComponent).join("/").replace(/%3A/g, ":");
  }
  function vscodeHref(rel) {
    const abs = fileAbs(rel);
    if (!abs) return "";
    return "vscode://file" + (abs.charAt(0) === "/" ? "" : "/") + abs;
  }
  function openButtons(rel) {
    if (!fileAbs(rel)) return "<p class='meta'>No local repo path — cannot open file</p>";
    return (
      '<p class="open-row">' +
      '<button type="button" class="open-btn" data-open="' + esc(rel) + '" data-app="">Open file</button> ' +
      '<button type="button" class="open-btn" data-open="' + esc(rel) + '" data-app="code">Open in VS Code</button> ' +
      '<button type="button" class="open-btn" data-open="' + esc(rel) + '" data-app="cursor">Open in Cursor</button>' +
      "</p><p class='meta' id='openMsg'></p><h3>Preview</h3><pre id='filePreview' class='tree'>Loading…</pre>"
    );
  }
  function loadPreview(rel) {
    const el = document.getElementById("filePreview");
    const root = G.root || "";
    if (!el) return;
    if (!root) { el.textContent = "No repo root on this graph page."; return; }
    fetch("http://127.0.0.1:9787/api/file?root=" + encodeURIComponent(root) + "&rel=" + encodeURIComponent(rel))
      .then((r) => r.json())
      .then((d) => {
        if (d.ok) el.textContent = d.text + (d.truncated ? "\n… (truncated)" : "");
        else el.textContent = d.error || "Could not read file";
      })
      .catch(() => {
        el.textContent = "Start: python3 scripts/ops/dashboard-server.py  — then Open file works and preview loads.";
      });
  }
  function bindOpenButtons() {
    document.querySelectorAll("button[data-open]").forEach((btn) => {
      btn.onclick = () => {
        const rel = btn.getAttribute("data-open");
        const app = btn.getAttribute("data-app") || "";
        const msg = document.getElementById("openMsg");
        const url = "http://127.0.0.1:9787/api/open?root=" + encodeURIComponent(G.root || "") +
          "&rel=" + encodeURIComponent(rel) + "&app=" + encodeURIComponent(app);
        fetch(url).then((r) => r.json()).then((d) => {
          if (msg) msg.textContent = d.ok ? "Opened " + (d.path || rel) : (d.error || "open failed");
          if (!d.ok && app === "code") window.location.href = vscodeHref(rel);
        }).catch(() => {
          if (msg) msg.textContent = "Start python3 scripts/ops/dashboard-server.py then click Open file again.";
          if (app === "code") window.location.href = vscodeHref(rel);
        });
      };
    });
  }
  function bindFileLinks() {
    document.querySelectorAll(".file-link").forEach((a) => {
      a.onclick = (ev) => {
        ev.preventDefault();
        openFileBrief(a.getAttribute("data-file"), a.getAttribute("data-commit"));
      };
    });
    document.querySelectorAll(".node-link").forEach((a) => {
      a.onclick = (ev) => {
        ev.preventDefault();
        const n = G.nodes.find((x) => x.id === a.getAttribute("data-id"));
        if (n) {
          if (n.type === "commit") { mode = "commit"; focusCommit = n.id; draw(); }
          if (n.type === "file") { mode = "file"; focusFile = n.id; draw(); }
          showPanel(n);
          animateFlow(n.id);
        }
      };
    });
  }
  function openFileBrief(rel, commitId) {
    const fileNode = G.nodes.find((x) => x.type === "file" && (x.label === rel || x.id === "file:" + rel))
      || { type: "file", id: "file:" + rel, label: rel, purpose: "", history: [] };
    const commitNode = G.nodes.find((x) => x.id === commitId) || null;
    const t = (fileNode.label || rel).split("/").pop();
    document.getElementById("out").innerHTML =
      "<p><a href='#' id='backCommit'>← back to commit</a></p>" +
      "<h2>" + (fileNode.icon_emoji || "📄") + " " + esc(t) + "</h2>" +
      '<div><span class="chip">file</span></div>' +
      openButtons(rel) +
      folderTree(rel) +
      "<h3>File summary</h3><p>" + esc(words(nodeSummary(fileNode), 100)) + "</p>" +
      "<h3>Changes (this commit)</h3><p>" + esc(words(fileChangeSummary(fileNode, commitNode), 100)) + "</p>" +
      "<h3>Metadata</h3><p>path: <a href='" + fileHref(rel) + "'>" + esc(rel) + "</a><br>repo: " + esc(G.repo || "") + "</p>";
    const back = document.getElementById("backCommit");
    bindOpenButtons();
    if (rel) loadPreview(rel);
    if (back && commitNode) {
      back.onclick = (ev) => { ev.preventDefault(); showPanel(commitNode); };
    }
  }
  function showPanel(n) {
    const ed = G.edges.filter((e) => (e.from === n.id || e.to === n.id) && e.tag === "EXTRACTED");
    // history[0] is recent file change — never treat as current checkout HEAD
    const last = (n.history && n.history[0]) || {};
    const t = (n.label || n.id).split("/").pop();
    const isFile = n.type === "file";
    const rel = isFile ? (n.label || "") : "";
    const summaryHtml = isFile
      ? "<h3>File summary</h3><p>" + esc(words(nodeSummary(n), 100)) + "</p>" +
        "<h3>Changes</h3><p>" + esc(words(fileChangeSummary(n, null), 100)) + "</p>"
      : "<h3>Summary</h3><p>" + esc(words(nodeSummary(n), 100)) + "</p>";
    const flowHtml = ed.slice(0, 16).map((e) => {
      const other = e.from === n.id ? e.to : e.from;
      const on = G.nodes.find((x) => x.id === other);
      const lab = on ? (on.label || on.id).split("/").pop() : other;
      const dir = e.from === n.id ? "→ " : "← ";
      return dir + esc(e.type) + " <a href='#' class='node-link' data-id='" + esc(other) + "'>" + esc(lab) + "</a>";
    }).join("<br>") || "no EXTRACTED edges on canvas";
    document.getElementById("out").innerHTML =
      "<h2>" + (n.icon_emoji || "") + " " + esc(t) + "</h2>" +
      '<div><span class="chip">' + esc(n.type) + "</span>" +
      (n.role ? '<span class="chip">' + esc(n.role) + "</span>" : "") + "</div>" +
      (isFile ? openButtons(rel) + folderTree(rel) : "") +
      summaryHtml +
      "<h3>Metadata</h3><p>" +
      "repo: " + esc(G.repo || "") + "<br>" +
      headMetaHtml() +
      (rel ? "path: <a href='" + fileHref(rel) + "'>" + esc(rel) + "</a><br>" : "") +
      (n.churn_30d != null ? "churn 30d: " + n.churn_30d + "<br>" : "") +
      (last.why ? "recent change: " + esc(last.commit || "") + " " + esc(last.why) + "<br>" : "") +
      (n.date ? "date: " + esc(n.date) + "<br>" : "") +
      (n.sha ? "sha: " + esc(n.sha) + "<br>" : "") +
      (n.files ? "files:<br>" + fileLinks(n) : "") +
      "</p><h3>How it connects</h3><p>" + flowHtml + "</p>";
    bindFileLinks();
    bindOpenButtons();
    if (isFile && rel) loadPreview(rel);
  }
  function okfSearch(q) {
    const box = document.getElementById("okfQ");
    const raw = (q != null ? q : (box && box.value) || "").trim();
    const err = document.getElementById("okfQmsg");
    if (!raw) {
      if (err) err.textContent = "Type a filename or keyword";
      return;
    }
    const parts = raw.split(/\s+/);
    let kind = (parts[0] || "").toLowerCase();
    let rest = parts.slice(1).join(" ");
    const known = { file: "file", files: "file", commit: "commit", commits: "commit", symbol: "symbol", fn: "symbol" };
    if (known[kind] && rest) {
      kind = known[kind];
    } else {
      kind = "any";
      rest = raw;
    }
    const needle = rest.toLowerCase();
    function rank(n) {
      if (kind !== "any" && n.type !== kind) return 0;
      const label = String(n.label || n.id || "").toLowerCase();
      const base = label.split("/").pop();
      const blob = (label + " " + (n.purpose || "") + " " + (n.summary || "") + " " + (n.subject || "") + " " + (n.name || "") + " " + (n.sha || "")).toLowerCase();
      if (base === needle || base.replace(/\.[^.]+$/, "") === needle) return 100;
      if (base.indexOf(needle) === 0) return 90;
      if (label.indexOf("/" + needle) >= 0 || label.indexOf(needle) >= 0) return 80;
      if (n.type === "file" && blob.indexOf(needle) >= 0) return 50;
      if (blob.indexOf(needle) >= 0) return 20;
      return 0;
    }
    const scored = G.nodes.map((n) => ({ n: n, s: rank(n) })).filter((x) => x.s > 0);
    scored.sort((a, b) => b.s - a.s || ((a.n.type === "file") ? 0 : 1) - ((b.n.type === "file") ? 0 : 1));
    const filesFirst = scored.filter((x) => x.n.type === "file").concat(scored.filter((x) => x.n.type !== "file"));
    const hits = (kind === "any" ? filesFirst : scored).slice(0, 20).map((x) => x.n);
    if (!hits.length) {
      if (err) err.textContent = "Not found: " + rest;
      return;
    }
    const n = hits[0];
    if (err) err.textContent = (hits.length === 1 ? "Found " : hits.length + " matches. Opening ") + (n.label || n.id);
    focusCommit = n.type === "commit" ? n.id : null;
    focusFile = n.type === "file" ? n.id : null;
    mode = n.type === "commit" ? "commit" : "file";
    draw();
    showPanel(n);
    animateFlow(n.id);
  }
  window.okfSearch = okfSearch;
  function animateFlow(startId) {
    if (flowTimer) {
      clearTimeout(flowTimer);
      flowTimer = 0;
    }
    function runOnce(thenLoop) {
      document.querySelectorAll("line.flow").forEach((l) => l.classList.remove("flow"));
      document.querySelectorAll("circle.pulse").forEach((c) => c.classList.remove("pulse"));
      const adj = {};
      G.edges.forEach((e) => {
        if (e.tag !== "EXTRACTED") return;
        (adj[e.from] = adj[e.from] || []).push(e);
      });
      const seen = new Set([startId]);
      let q = [startId], hop = 0;
      function step() {
        const next = [];
        q.forEach((id) => {
          (adj[id] || []).forEach((e) => {
            if (seen.has(e.to)) return;
            seen.add(e.to);
            next.push(e.to);
            const line = document.querySelector('line[data-eid="' + e.from + "__" + e.to + '"]');
            if (line) line.classList.add("flow");
            const c = document.querySelector('circle[data-nid="' + e.to + '"]');
            if (c) c.classList.add("pulse");
          });
        });
        q = next;
        hop++;
        if (q.length && hop < 8) flowTimer = setTimeout(step, 280);
        else if (thenLoop) flowTimer = setTimeout(function () { runOnce(true); }, 900);
      }
      const c0 = document.querySelector('circle[data-nid="' + startId + '"]');
      if (c0) c0.classList.add("pulse");
      flowTimer = setTimeout(step, 80);
    }
    runOnce(true);
  }
  window.setGraphMode = function (m) {
    mode = m;
    if (m !== "commit") focusCommit = null;
    if (m !== "file") focusFile = null;
    draw();
  };
  function draw() {
    ["bboth", "bfile", "bcommit"].forEach((id) => {
      const b = document.getElementById(id);
      if (b) b.className = id === "b" + mode || (id === "bboth" && mode === "both") ? "on" : "";
    });
    const svg = document.getElementById("canvas");
    if (!svg) return;
    const W = svg.clientWidth || 800, H = svg.clientHeight || 560;
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    const nodes = pickSet();
    const ids = new Set(nodes.map((n) => n.id));
    POS = {};
    const files = nodes.filter((n) => n.type !== "commit");
    const commits = nodes.filter((n) => n.type === "commit");
    if (mode === "commit" && focusCommit && commits.length === 1) {
      POS[commits[0].id] = { x: W * 0.16, y: H * 0.5 };
      files.forEach((n, i) => {
        const a = (i / Math.max(files.length, 1)) * Math.PI * 2 - Math.PI / 2;
        POS[n.id] = { x: W * 0.58 + Math.cos(a) * W * 0.28, y: H * 0.5 + Math.sin(a) * H * 0.38 };
      });
    } else {
      files.forEach((n, i) => {
        const a = (i / Math.max(files.length, 1)) * Math.PI * 2 - Math.PI / 2;
        POS[n.id] = { x: W * 0.52 + Math.cos(a) * W * 0.32, y: H * 0.5 + Math.sin(a) * H * 0.38 };
      });
      commits.forEach((n, i) => {
        POS[n.id] = { x: 70 + (i % 2) * 40, y: 40 + i * Math.min(28, (H - 80) / Math.max(commits.length, 1)) };
      });
    }
    const edges = G.edges.filter((e) => ids.has(e.from) && ids.has(e.to) && e.tag === "EXTRACTED");
    let html = "";
    edges.forEach((e) => {
      const a = POS[e.from], b = POS[e.to];
      if (!a || !b) return;
      const eid = e.from + "__" + e.to;
      html += '<line data-eid="' + eid + '" x1="' + a.x + '" y1="' + a.y + '" x2="' + b.x + '" y2="' + b.y + '" stroke="#334155" stroke-width="1"/>';
    });
    nodes.forEach((n) => {
      const p = POS[n.id];
      if (!p) return;
      const r = n.type === "commit" ? 8 : 11;
      const lab = (n.label || n.id).split("/").pop().slice(0, 22);
      const img = n.icon_uri
        ? '<image href="' + n.icon_uri + '" x="' + (p.x - 8) + '" y="' + (p.y - 8) + '" width="16" height="16"/>'
        : "";
      html +=
        '<g data-id="' + n.id.replace(/"/g, "") + '" style="cursor:pointer">' +
        '<circle data-nid="' + n.id.replace(/"/g, "") + '" cx="' + p.x + '" cy="' + p.y + '" r="' + r +
        '" fill="#1e293b" stroke="' + (n.type === "commit" ? "#a78bfa" : "#38bdf8") + '"/>' +
        img +
        '<text x="' + (p.x + 14) + '" y="' + (p.y + 4) + '" fill="#94a3b8" font-size="10">' +
        (n.icon_emoji || "") + " " + lab + "</text></g>";
    });
    svg.innerHTML = html;
    svg.querySelectorAll("g[data-id]").forEach((g) =>
      g.addEventListener("click", () => {
        const n = G.nodes.find((x) => x.id === g.getAttribute("data-id"));
        if (!n) return;
        if (mode === "commit" && n.type === "commit") {
          focusCommit = n.id;
          draw();
        }
        showPanel(n);
        animateFlow(n.id);
      })
    );
  }
  window.draw = draw;
  draw();
  window.addEventListener("resize", draw);
  const qbox = document.getElementById("okfQ");
  if (qbox) {
    qbox.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); okfSearch(); }
    });
  }
  const qbtn = document.getElementById("okfQgo");
  if (qbtn) qbtn.addEventListener("click", () => okfSearch());
})();
