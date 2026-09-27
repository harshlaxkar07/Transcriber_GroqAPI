/* Call Transcriber — front end for the Groq transcription and extraction API. */
(function () {
  "use strict";

  const { $, $$, el, esc, icon, http, toast, modal, bytes, duration, relative } = UI;

  http.base = "";

  let config = null;
  let transcripts = [];
  let lastTranscript = "";

  const LANG_NAMES = {
    en: "English", hi: "Hindi", es: "Spanish", fr: "French", de: "German",
    pt: "Portuguese", it: "Italian", ru: "Russian", ja: "Japanese",
    zh: "Chinese", ar: "Arabic", ta: "Tamil", te: "Telugu", mr: "Marathi",
    bn: "Bengali", gu: "Gujarati", pa: "Punjabi", ur: "Urdu",
  };

  const langName = (code) =>
    !code ? "Unknown" : LANG_NAMES[String(code).toLowerCase()] || String(code).toUpperCase();

  /* ---------------- connection ---------------- */
  async function ping() {
    const node = $("#conn");
    const text = $(".conn-text", node);
    try {
      config = await http.get("/api/health");
      node.className = "conn online";
      text.textContent = "API connected";
      renderConfig();
      if (config.formats && config.formats.length) {
        $("#formatHint").textContent = config.formats
          .map((f) => f.toUpperCase())
          .join(", ");
      }
    } catch (_) {
      node.className = "conn offline";
      text.textContent = "API unreachable";
    }
  }

  function renderConfig() {
    if (!config) return;
    $("#configCards").innerHTML = [
      { label: "Transcription model", value: config.transcription_model, hint: "speech to text", ic: "mic" },
      { label: "Extraction model", value: config.extraction_model, hint: "structured output", ic: "brain" },
      { label: "Chunk length", value: `${config.chunk_minutes} min`, hint: "per request", ic: "clock" },
      { label: "Stored transcripts", value: config.transcripts, hint: "in the output directory", ic: "list" },
    ]
      .map(
        (t) => `<div class="stat">
        <div class="stat-icon">${icon(t.ic, 16)}</div>
        <div class="stat-label">${esc(t.label)}</div>
        <div class="stat-value" style="font-size:${String(t.value).length > 14 ? "1rem" : "1.7rem"}">${esc(t.value)}</div>
        <div class="stat-hint">${esc(t.hint)}</div></div>`
      )
      .join("");
  }

  /* ---------------- library ---------------- */
  async function loadTranscripts() {
    try {
      transcripts = await http.get("/api/transcripts");
      if (!Array.isArray(transcripts)) transcripts = [];
    } catch (_) {
      transcripts = [];
    }
    $("[data-count='tx']").textContent = transcripts.length;
    $("#txBadge").textContent = `${transcripts.length} file${transcripts.length === 1 ? "" : "s"}`;

    const host = $("#txList");
    if (!transcripts.length) {
      host.innerHTML = `<div class="empty">
        <div class="empty-icon">${icon("inbox", 24)}</div>
        <h3>No transcripts yet</h3>
        <p>Transcribe a recording and the text file will be listed here.</p></div>`;
      return;
    }

    host.innerHTML = transcripts
      .slice()
      .sort((a, b) => b.modified - a.modified)
      .map(
        (t) => `
      <div class="tx-row">
        <div class="tx-icon">${icon("fileText", 16)}</div>
        <div class="tx-body">
          <div class="tx-name truncate">${esc(t.name)}</div>
          <div class="tx-sub">${t.characters.toLocaleString()} characters · ${esc(
          relative(new Date(t.modified * 1000).toISOString())
        )}</div>
        </div>
        <button class="btn btn-sm btn-ghost" data-read="${esc(t.name)}" title="Read">${icon("eye", 13)}</button>
      </div>`
      )
      .join("");

    $$("#txList [data-read]").forEach((b) =>
      b.addEventListener("click", () => openTranscript(b.dataset.read))
    );
  }

  async function openTranscript(name) {
    const m = modal({
      title: name,
      size: "lg",
      body: `<div class="skeleton skeleton-line"></div><div class="skeleton skeleton-line"></div>`,
      actions: [{ label: "Close", onClick: (close) => close() }],
    });

    try {
      const data = await http.get(`/api/transcripts/${encodeURIComponent(name)}`);
      m.body.innerHTML = `
        <div class="row mb-2">
          <span class="badge">${data.transcript.length.toLocaleString()} characters</span>
          <span class="badge">${data.transcript.split(/\s+/).filter(Boolean).length.toLocaleString()} words</span>
          <div class="spacer"></div>
          <button class="btn btn-sm" data-copy>${icon("copy", 13)} Copy</button>
          <button class="btn btn-sm btn-primary" data-extract>${icon("sparkles", 13)} Extract details</button>
        </div>
        <div class="transcript">${esc(data.transcript)}</div>
        <div id="modalReport"></div>`;

      $("[data-copy]", m.body).addEventListener("click", () => UI.copy(data.transcript));
      $("[data-extract]", m.body).addEventListener("click", (e) =>
        runExtraction(data.transcript, $("#modalReport", m.body), e.currentTarget)
      );
    } catch (err) {
      m.body.innerHTML = `<p class="muted">${esc(err.message)}</p>`;
    }
  }

  /* ---------------- transcribe ---------------- */
  async function transcribe(file) {
    const url = URL.createObjectURL(file);
    $("#player").innerHTML = `
      <div class="file-chip">
        <div class="fi">${icon("audio", 16)}</div>
        <div class="fbody">
          <div class="fname">${esc(file.name)}</div>
          <div class="fmeta">${esc(bytes(file.size))}</div>
        </div>
      </div>
      <div class="mt-1"><audio controls src="${url}"></audio></div>`;

    const host = $("#result");
    host.innerHTML = `
      <div class="card"><div class="card-body">
        <div class="row" style="gap:12px"><span class="spinner"></span>
        <span class="muted">Splitting the recording and transcribing each chunk…</span></div>
        <div class="progress-bar indeterminate mt-2"><span></span></div>
        <p class="xs dim mt-1">Long recordings take a while — one request is made per chunk.</p>
      </div></div>`;

    const form = new FormData();
    form.append("file", file);

    try {
      const data = await http.post("/api/transcribe", form);
      lastTranscript = data.transcript || "";
      renderResult(data);
      toast(`${file.name} transcribed`, "success");
      loadTranscripts();
      ping();
    } catch (err) {
      host.innerHTML = `<div class="card"><div class="empty">
        <div class="empty-icon" style="background:var(--danger-soft);color:var(--danger)">${icon("alert", 24)}</div>
        <h3>Transcription could not complete</h3><p>${esc(err.message)}</p>
      </div></div>`;
      toast(err.message, "error");
    }
  }

  function renderResult(data) {
    const chunks = data.chunks || [];

    $("#result").innerHTML = `
      <div class="stack">
        <div class="grid cols-4">
          ${[
            { label: "Language", value: langName(data.language), hint: "detected", ic: "globe" },
            { label: "Duration", value: duration(data.duration), hint: "of audio", ic: "clock" },
            { label: "Chunks", value: chunks.length, hint: "transcribed", ic: "layers" },
            { label: "Words", value: (data.words || 0).toLocaleString(), hint: `${(data.characters || 0).toLocaleString()} characters`, ic: "fileText" },
          ]
            .map(
              (t) => `<div class="stat">
              <div class="stat-icon">${icon(t.ic, 16)}</div>
              <div class="stat-label">${esc(t.label)}</div>
              <div class="stat-value" style="font-size:1.4rem">${esc(t.value)}</div>
              <div class="stat-hint">${esc(t.hint)}</div></div>`
            )
            .join("")}
        </div>

        <div class="card">
          <div class="card-head">
            <h3>Transcript</h3>
            <div class="spacer"></div>
            <button class="btn btn-sm btn-ghost" id="copyTx">${icon("copy", 13)} Copy</button>
            <button class="btn btn-sm btn-ghost" id="dlTx">${icon("download", 13)} Download</button>
            <button class="btn btn-sm btn-primary" id="extractTx">${icon("sparkles", 13)} Extract details</button>
          </div>
          <div class="card-body">
            <div class="transcript">${esc(data.transcript || "No speech was detected.")}</div>
          </div>
        </div>

        <div id="report"></div>

        ${
          chunks.length > 1
            ? `<div class="card">
                <div class="card-head">
                  <h3>Per-chunk transcripts</h3>
                  <p>Each piece the recording was split into, in order.</p>
                </div>
                <div class="card-body stack" style="gap:8px">
                  ${chunks
                    .map(
                      (c) => `
                    <div class="chunk">
                      <button class="chunk-head" type="button">
                        <span class="chunk-n">${c.index}</span>
                        <span class="chunk-name">${esc(c.name)}</span>
                        ${c.duration ? `<span class="badge">${esc(duration(c.duration))}</span>` : ""}
                        <span class="chunk-chev">${icon("chevronRight", 15)}</span>
                      </button>
                      <div class="chunk-body"><div class="chunk-text">${esc(c.transcript || "—")}</div></div>
                    </div>`
                    )
                    .join("")}
                </div>
              </div>`
            : ""
        }
      </div>`;

    $("#copyTx").addEventListener("click", () => UI.copy(data.transcript || ""));
    $("#dlTx").addEventListener("click", () => download(data.transcript_file || "transcript.txt", data.transcript || ""));
    $("#extractTx").addEventListener("click", (e) =>
      runExtraction(data.transcript, $("#report"), e.currentTarget)
    );
    $$("#result .chunk-head").forEach((b) =>
      b.addEventListener("click", () => b.closest(".chunk").classList.toggle("open"))
    );
  }

  /* ---------------- extraction ---------------- */
  async function runExtraction(transcript, host, btn) {
    if (!transcript || !transcript.trim()) {
      toast("There is nothing to extract from", "warn");
      return;
    }

    btn.classList.add("loading");
    host.innerHTML = `
      <div class="card"><div class="card-body">
        <div class="row" style="gap:12px"><span class="spinner"></span>
        <span class="muted">Reading the transcript and pulling out the details…</span></div>
      </div></div>`;

    try {
      const data = await http.post("/api/extract", { transcript });
      host.innerHTML = `
        <div class="card">
          <div class="card-head">
            <h3>Extracted information</h3>
            <div class="spacer"></div>
            <button class="btn btn-sm btn-ghost" data-copy-report>${icon("copy", 13)} Copy</button>
          </div>
          <div class="card-body"><div class="report">${esc(data.report || "")}</div></div>
        </div>`;
      $("[data-copy-report]", host).addEventListener("click", () => UI.copy(data.report || ""));
      toast("Details extracted", "success");
    } catch (err) {
      host.innerHTML = `<div class="card"><div class="card-body">
        <div class="row" style="gap:10px;color:var(--warn)">${icon("info", 17)}
        <span class="small">${esc(err.message)}</span></div>
      </div></div>`;
    } finally {
      btn.classList.remove("loading");
    }
  }

  function download(name, text) {
    const url = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
    const a = el("a", { href: url, download: name });
    document.body.append(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    toast("Transcript downloaded", "success");
  }

  /* ---------------- boot ---------------- */
  function init() {
    UI.shell({ start: "transcribe" });

    UI.dropzone($("#dropzone"), transcribe, { accept: "audio/*" });

    $("#refresh").addEventListener("click", async (e) => {
      e.currentTarget.classList.add("loading");
      await Promise.all([ping(), loadTranscripts()]);
      e.currentTarget.classList.remove("loading");
      toast("Reloaded", "success");
    });

    void lastTranscript;
    ping();
    loadTranscripts();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
