/**
 * RAG Generator Client Application Logic
 */

document.addEventListener("DOMContentLoaded", () => {
  // State
  let applications = [];
  let currentAppId = null;
  let currentAppData = null;
  let selectedFiles = [];
  let runtimeSelectedFiles = [];

  // DOM Elements
  const appSelect = document.getElementById("app-select-dropdown");
  const btnRefreshApps = document.getElementById("btn-refresh-apps");
  const navTabs = document.querySelectorAll(".nav-tab");
  const tabPanes = document.querySelectorAll(".tab-pane");

  // Query Tab Elements
  const bannerAppName = document.getElementById("banner-app-name");
  const bannerAppDesc = document.getElementById("banner-app-desc");
  const badgeDocCount = document.getElementById("badge-doc-count");
  const badgeChunkCount = document.getElementById("badge-chunk-count");
  const badgeHybridAlpha = document.getElementById("badge-hybrid-alpha");
  const chipsList = document.getElementById("chips-list");
  const queryInput = document.getElementById("query-input");
  const btnSubmitQuery = document.getElementById("btn-submit-query");
  const paramTopK = document.getElementById("param-top-k");
  const paramAlpha = document.getElementById("param-alpha");
  const paramProvider = document.getElementById("param-provider");
  const queryLoading = document.getElementById("query-loading");
  const responseCard = document.getElementById("response-card");
  const answerText = document.getElementById("answer-text");
  const responseMetrics = document.getElementById("response-metrics");
  const citationsGrid = document.getElementById("citations-grid");
  const statGroundednessVal = document.getElementById("stat-groundedness-val");
  const meterGroundedness = document.getElementById("meter-groundedness");
  const statConfidence = document.getElementById("stat-confidence");
  const statRetrievedChunks = document.getElementById("stat-retrieved-chunks");
  const statLatency = document.getElementById("stat-latency");
  const statRetrievalTime = document.getElementById("stat-retrieval-time");
  const statModel = document.getElementById("stat-model");
  const evidencePreviewList = document.getElementById("evidence-preview-list");

  // Create App Tab Elements
  const formCreateApp = document.getElementById("form-create-app");
  const createChunkSize = document.getElementById("create-chunk-size");
  const valChunkSize = document.getElementById("val-chunk-size");
  const createChunkOverlap = document.getElementById("create-chunk-overlap");
  const valChunkOverlap = document.getElementById("val-chunk-overlap");
  const createHybridAlpha = document.getElementById("create-hybrid-alpha");
  const valHybridAlpha = document.getElementById("val-hybrid-alpha");
  const fileDropzone = document.getElementById("file-dropzone");
  const fileInput = document.getElementById("file-input");
  const selectedFilesList = document.getElementById("selected-files-list");

  // Docs Tab Elements
  const docsTabAppName = document.getElementById("docs-tab-app-name");
  const documentsTableBody = document.getElementById("documents-table-body");
  const chunkSearchInput = document.getElementById("chunk-search-input");
  const chunksExplorerList = document.getElementById("chunks-explorer-list");
  const btnOpenAddDocs = document.getElementById("btn-open-add-docs");
  const modalAddDocs = document.getElementById("modal-add-docs");
  const btnCloseModal = document.getElementById("btn-close-modal");
  const btnCancelModal = document.getElementById("btn-cancel-modal");
  const runtimeDropzone = document.getElementById("runtime-dropzone");
  const runtimeFileInput = document.getElementById("runtime-file-input");
  const runtimeFilesList = document.getElementById("runtime-files-list");
  const formRuntimeIngest = document.getElementById("form-runtime-ingest");

  // Export Tab Elements
  const btnExportApp = document.getElementById("btn-export-app");
  const codeCurl = document.getElementById("code-curl");
  const codePython = document.getElementById("code-python");

  // Toast
  const toast = document.getElementById("toast");

  function showToast(msg, type = "success") {
    toast.textContent = msg;
    toast.className = `toast show ${type === "success" ? "toast-success" : "toast-error"}`;
    setTimeout(() => {
      toast.className = "toast";
    }, 3800);
  }

  // --- Tab Switching ---
  navTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const targetId = tab.getAttribute("data-tab");
      navTabs.forEach(t => {
        t.classList.remove("active");
        t.setAttribute("aria-selected", "false");
      });
      tabPanes.forEach(pane => pane.classList.remove("active"));

      tab.classList.add("active");
      tab.setAttribute("aria-selected", "true");
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add("active");

      if (targetId === "tab-documents") {
        loadDocumentsTab();
      } else if (targetId === "tab-export") {
        updateExportCodeSnippets();
      }
    });
  });

  // --- Fetch Applications ---
  async function loadApplications(preferredAppId = null) {
    try {
      const res = await fetch("/api/apps");
      applications = await res.json();
      appSelect.innerHTML = "";

      if (applications.length === 0) {
        appSelect.innerHTML = '<option value="">No applications found</option>';
        bannerAppName.textContent = "No Applications Available";
        bannerAppDesc.textContent = "Create an application in the 'Create App' tab to get started.";
        return;
      }

      applications.forEach(app => {
        const opt = document.createElement("option");
        opt.value = app.app_id;
        opt.textContent = `${app.name} (${app.document_count} docs)`;
        appSelect.appendChild(opt);
      });

      if (preferredAppId && applications.some(a => a.app_id === preferredAppId)) {
        currentAppId = preferredAppId;
      } else {
        currentAppId = applications[0].app_id;
      }

      appSelect.value = currentAppId;
      await selectApplication(currentAppId);
    } catch (err) {
      console.error("Error loading apps:", err);
      showToast("Failed to load applications list", "error");
    }
  }

  async function selectApplication(appId) {
    currentAppId = appId;
    try {
      const res = await fetch(`/api/apps/${appId}`);
      if (!res.ok) throw new Error("App not found");
      currentAppData = await res.json();

      bannerAppName.textContent = currentAppData.name;
      bannerAppDesc.textContent = currentAppData.description || "No description provided.";
      badgeDocCount.textContent = `${currentAppData.document_count} Docs`;
      badgeChunkCount.textContent = `${currentAppData.chunk_count} Chunks`;
      const alphaVal = currentAppData.config ? currentAppData.config.hybrid_alpha : 0.5;
      badgeHybridAlpha.textContent = `Hybrid RRF: ${alphaVal.toFixed(2)}`;
      paramAlpha.value = alphaVal;

      populateSuggestedPrompts(currentAppData);
      updateExportCodeSnippets();

      // Reset response card
      responseCard.style.display = "none";
      evidencePreviewList.innerHTML = '<p class="empty-hint">Submit a query to inspect the retrieved text passages.</p>';
      statGroundednessVal.textContent = "--%";
      meterGroundedness.style.width = "0%";
      statConfidence.textContent = "N/A";
      statConfidence.className = "stat-val badge";
      statRetrievedChunks.textContent = "0";
      statLatency.textContent = "-- ms";
      statRetrievalTime.textContent = "-- ms";
      statModel.textContent = "--";
    } catch (err) {
      console.error("Error selecting app:", err);
    }
  }

  function populateSuggestedPrompts(appData) {
    chipsList.innerHTML = "";
    const nameLower = (appData.name + " " + (appData.description || "")).toLowerCase();
    let prompts = [];

    if (nameLower.includes("quantum")) {
      prompts = [
        "What are the dilution refrigerator thermal cooling stages?",
        "What is the physical error threshold for the surface code?",
        "What is the measured average T1 coherence time across qubits?",
        "How is real-time syndrome decoding performed?",
      ];
    } else if (nameLower.includes("saas") || nameLower.includes("msa") || nameLower.includes("legal")) {
      prompts = [
        "What is the monthly uptime commitment under Section 7?",
        "What is the total aggregate liability cap?",
        "What are the payment terms and invoicing schedule?",
        "How many days notice is required for termination for convenience?",
        "What is the security incident notification window for GDPR?",
      ];
    } else if (nameLower.includes("oncology") || nameLower.includes("clinical") || nameLower.includes("trial")) {
      prompts = [
        "What is the standard dosage and infusion schedule for TX-409?",
        "What are the primary and secondary study endpoints?",
        "What are the key patient inclusion and exclusion criteria?",
        "What action is required for Grade 3 infusion-related reactions?",
      ];
    } else {
      prompts = [
        "What are the main points discussed in these documents?",
        "Summarize the key findings or clauses.",
        "What specific metrics, limits, or parameters are mentioned?",
      ];
    }

    prompts.forEach(p => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "prompt-chip";
      chip.textContent = p;
      chip.addEventListener("click", () => {
        queryInput.value = p;
        submitQuery();
      });
      chipsList.appendChild(chip);
    });
  }

  appSelect.addEventListener("change", () => {
    selectApplication(appSelect.value);
  });

  btnRefreshApps.addEventListener("click", () => {
    loadApplications(currentAppId);
    showToast("Applications refreshed");
  });

  // --- Query Execution ---
  async function submitQuery() {
    const q = queryInput.value.trim();
    if (!q) {
      showToast("Please enter a question", "error");
      return;
    }
    if (!currentAppId) {
      showToast("Please select a RAG application first", "error");
      return;
    }

    btnSubmitQuery.disabled = true;
    queryLoading.style.display = "flex";
    responseCard.style.display = "none";

    try {
      const payload = {
        question: q,
        top_k: parseInt(paramTopK.value) || 4,
        hybrid_alpha: parseFloat(paramAlpha.value) || 0.5,
        llm_provider: paramProvider.value,
      };

      const res = await fetch(`/api/apps/${currentAppId}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || "Query failed");
      }

      const answer = await res.json();
      renderAnswer(answer);
    } catch (err) {
      console.error("Query error:", err);
      showToast(err.message || "Query failed", "error");
    } finally {
      btnSubmitQuery.disabled = false;
      queryLoading.style.display = "none";
    }
  }

  function renderAnswer(data) {
    responseCard.style.display = "block";

    // Format Markdown-like text
    let formatted = data.answer
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/`([^`]+)`/g, "<code>$1</code>");

    // Replace lines starting with bullet
    const lines = formatted.split("\n");
    let inList = false;
    let htmlLines = [];
    for (let l of lines) {
      if (l.trim().startsWith("• ") || l.trim().startsWith("- ")) {
        if (!inList) { htmlLines.push("<ul>"); inList = true; }
        htmlLines.push(`<li>${l.trim().substring(2)}</li>`);
      } else {
        if (inList) { htmlLines.push("</ul>"); inList = false; }
        if (l.trim()) htmlLines.push(`<p>${l}</p>`);
      }
    }
    if (inList) htmlLines.push("</ul>");
    answerText.innerHTML = htmlLines.join("\n");

    // Metrics badges
    responseMetrics.innerHTML = "";
    const confBadge = document.createElement("span");
    const confColor = data.confidence === "High" ? "badge-emerald" :
                      data.confidence === "Medium" ? "badge-amber" : "badge-rose";
    confBadge.className = `badge ${confColor}`;
    confBadge.textContent = `${data.confidence} Confidence`;
    responseMetrics.appendChild(confBadge);

    const groundBadge = document.createElement("span");
    groundBadge.className = "badge badge-cyan";
    groundBadge.textContent = `${(data.groundedness_score * 100).toFixed(0)}% Grounded`;
    responseMetrics.appendChild(groundBadge);

    const latBadge = document.createElement("span");
    latBadge.className = "badge badge-purple";
    latBadge.textContent = `${data.latency_ms.toFixed(0)}ms`;
    responseMetrics.appendChild(latBadge);

    // Sidebar gauges
    statGroundednessVal.textContent = `${(data.groundedness_score * 100).toFixed(0)}%`;
    meterGroundedness.style.width = `${Math.min(100, Math.max(0, data.groundedness_score * 100))}%`;
    statConfidence.textContent = data.confidence;
    statConfidence.className = `stat-val badge ${confColor}`;
    statRetrievedChunks.textContent = data.retrieved_chunk_count;
    statLatency.textContent = `${data.latency_ms.toFixed(1)} ms`;
    statRetrievalTime.textContent = `${data.retrieval_latency_ms.toFixed(1)} ms`;
    statModel.textContent = data.model_used;

    // Render citations
    citationsGrid.innerHTML = "";
    if (data.citations && data.citations.length > 0) {
      data.citations.forEach((cit, idx) => {
        const card = document.createElement("div");
        card.className = "citation-card";
        card.setAttribute("data-chunk-id", cit.chunk_id);
        card.innerHTML = `
          <div class="citation-header">
            <span class="citation-source">[${idx + 1}] ${cit.source_name}</span>
            <span class="citation-score">Relevance: ${cit.relevance_score.toFixed(2)}</span>
          </div>
          <p class="citation-snippet">"${cit.snippet}"</p>
        `;
        card.addEventListener("click", () => {
          document.querySelectorAll(".citation-card").forEach(c => c.classList.remove("active"));
          card.classList.add("active");
          highlightEvidenceChunk(cit.chunk_id);
        });
        citationsGrid.appendChild(card);
      });
    } else {
      citationsGrid.innerHTML = '<p class="empty-hint">No specific citations generated for this response.</p>';
    }

    // Render Evidence list in sidebar
    evidencePreviewList.innerHTML = "";
    if (data.citations && data.citations.length > 0) {
      data.citations.forEach((cit, idx) => {
        const item = document.createElement("div");
        item.className = "evidence-chunk-item";
        item.id = `evidence-${cit.chunk_id}`;
        item.innerHTML = `
          <div class="evidence-item-header">
            <strong>[#${idx + 1}] ${cit.source_name} (Page ${cit.page_number || 1})</strong>
            <span>Score: ${cit.relevance_score.toFixed(2)}</span>
          </div>
          <p>${cit.snippet}</p>
        `;
        evidencePreviewList.appendChild(item);
      });
    }
  }

  function highlightEvidenceChunk(chunkId) {
    document.querySelectorAll(".evidence-chunk-item").forEach(item => item.classList.remove("highlighted"));
    const el = document.getElementById(`evidence-${chunkId}`);
    if (el) {
      el.classList.add("highlighted");
      el.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }

  btnSubmitQuery.addEventListener("click", submitQuery);
  queryInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitQuery();
    }
  });

  // --- Create App Form Controls ---
  createChunkSize.addEventListener("input", () => {
    valChunkSize.textContent = createChunkSize.value;
  });
  createChunkOverlap.addEventListener("input", () => {
    valChunkOverlap.textContent = createChunkOverlap.value;
  });
  createHybridAlpha.addEventListener("input", () => {
    valHybridAlpha.textContent = parseFloat(createHybridAlpha.value).toFixed(2);
  });

  // Drag and drop for Create App
  fileDropzone.addEventListener("click", () => fileInput.click());
  fileDropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    fileDropzone.classList.add("dragover");
  });
  fileDropzone.addEventListener("dragleave", () => {
    fileDropzone.classList.remove("dragover");
  });
  fileDropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    fileDropzone.classList.remove("dragover");
    if (e.dataTransfer.files) {
      addFiles(Array.from(e.dataTransfer.files));
    }
  });
  fileInput.addEventListener("change", () => {
    if (fileInput.files) {
      addFiles(Array.from(fileInput.files));
    }
  });

  function addFiles(files) {
    selectedFiles = selectedFiles.concat(files);
    renderSelectedFiles();
  }

  function renderSelectedFiles() {
    selectedFilesList.innerHTML = "";
    selectedFiles.forEach((file, index) => {
      const pill = document.createElement("div");
      pill.className = "selected-file-pill";
      const sizeKb = (file.size / 1024).toFixed(1);
      pill.innerHTML = `
        <span>📄 ${file.name} (${sizeKb} KB)</span>
        <button type="button" class="remove-file-btn" data-index="${index}">&times;</button>
      `;
      pill.querySelector(".remove-file-btn").addEventListener("click", () => {
        selectedFiles.splice(index, 1);
        renderSelectedFiles();
      });
      selectedFilesList.appendChild(pill);
    });
  }

  formCreateApp.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("create-name").value.trim();
    const desc = document.getElementById("create-desc").value.trim();
    const chunkSize = createChunkSize.value;
    const chunkOverlap = createChunkOverlap.value;
    const hybridAlpha = createHybridAlpha.value;
    const provider = document.getElementById("create-llm-provider").value;
    const rawText = document.getElementById("create-raw-text").value.trim();
    const textTitle = document.getElementById("create-text-title").value.trim() || "Uploaded_Note.txt";

    if (!name) {
      showToast("Application name is required", "error");
      return;
    }

    if (selectedFiles.length === 0 && !rawText) {
      showToast("Please select at least one document or paste raw text", "error");
      return;
    }

    const btn = document.getElementById("btn-create-app-submit");
    btn.disabled = true;
    btn.innerHTML = '<span>Creating Application & Indexing...</span>';

    try {
      const formData = new FormData();
      formData.append("name", name);
      formData.append("description", desc);
      formData.append("chunk_size", chunkSize);
      formData.append("chunk_overlap", chunkOverlap);
      formData.append("hybrid_alpha", hybridAlpha);
      formData.append("llm_provider", provider);

      selectedFiles.forEach(file => {
        formData.append("files", file);
      });

      if (rawText) {
        formData.append("raw_text", rawText);
        formData.append("text_title", textTitle);
      }

      const res = await fetch("/api/apps", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Failed to create application");
      }

      const result = await res.json();
      showToast(`RAG Application '${name}' created successfully!`);

      // Reset form
      formCreateApp.reset();
      selectedFiles = [];
      renderSelectedFiles();

      // Refresh applications and select new one
      await loadApplications(result.application.app_id);

      // Switch to Query tab
      document.getElementById("tab-btn-query").click();
    } catch (err) {
      console.error("Create app error:", err);
      showToast(err.message || "Failed to create application", "error");
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg><span>Generate RAG Application</span>';
    }
  });

  // --- Documents Tab ---
  async function loadDocumentsTab() {
    if (!currentAppId) return;
    try {
      docsTabAppName.textContent = `Documents in ${currentAppData ? currentAppData.name : currentAppId}`;
      const res = await fetch(`/api/apps/${currentAppId}`);
      if (!res.ok) return;
      const data = await res.json();

      documentsTableBody.innerHTML = "";
      if (!data.documents || data.documents.length === 0) {
        documentsTableBody.innerHTML = '<tr><td colspan="6" class="text-center">No documents in this application.</td></tr>';
      } else {
        data.documents.forEach(doc => {
          const row = document.createElement("tr");
          const dateStr = new Date(doc.created_at * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          row.innerHTML = `
            <td><strong>${doc.filename}</strong></td>
            <td><span class="badge badge-purple">${doc.file_type}</span></td>
            <td>${doc.page_count}</td>
            <td>${doc.char_count} chars</td>
            <td>~${doc.token_estimate} tokens</td>
            <td>${dateStr}</td>
          `;
          documentsTableBody.appendChild(row);
        });
      }

      // Load chunks
      loadChunksExplorer();
    } catch (err) {
      console.error("Error loading documents:", err);
    }
  }

  async function loadChunksExplorer(filterKw = "") {
    if (!currentAppId) return;
    try {
      let url = `/api/apps/${currentAppId}/chunks?limit=60`;
      if (filterKw) url += `&search=${encodeURIComponent(filterKw)}`;
      const res = await fetch(url);
      const data = await res.json();

      chunksExplorerList.innerHTML = "";
      if (!data.chunks || data.chunks.length === 0) {
        chunksExplorerList.innerHTML = '<p class="empty-hint">No chunks found matching filter.</p>';
        return;
      }

      data.chunks.forEach(c => {
        const card = document.createElement("div");
        card.className = "chunk-card";
        card.innerHTML = `
          <div class="chunk-card-header">
            <span>${c.source_name} (Page ${c.page_number || 1})</span>
            <span>Chunk #${c.chunk_index}</span>
          </div>
          <p class="chunk-content-text">${c.content}</p>
        `;
        chunksExplorerList.appendChild(card);
      });
    } catch (err) {
      console.error("Error loading chunks:", err);
    }
  }

  chunkSearchInput.addEventListener("input", (e) => {
    loadChunksExplorer(e.target.value.trim());
  });

  // Modal: Add Documents at Runtime
  btnOpenAddDocs.addEventListener("click", () => {
    modalAddDocs.style.display = "flex";
  });
  btnCloseModal.addEventListener("click", () => {
    modalAddDocs.style.display = "none";
  });
  btnCancelModal.addEventListener("click", () => {
    modalAddDocs.style.display = "none";
  });

  runtimeDropzone.addEventListener("click", () => runtimeFileInput.click());
  runtimeDropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    runtimeDropzone.classList.add("dragover");
  });
  runtimeDropzone.addEventListener("dragleave", () => runtimeDropzone.classList.remove("dragover"));
  runtimeDropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    runtimeDropzone.classList.remove("dragover");
    if (e.dataTransfer.files) {
      runtimeSelectedFiles = runtimeSelectedFiles.concat(Array.from(e.dataTransfer.files));
      renderRuntimeFiles();
    }
  });
  runtimeFileInput.addEventListener("change", () => {
    if (runtimeFileInput.files) {
      runtimeSelectedFiles = runtimeSelectedFiles.concat(Array.from(runtimeFileInput.files));
      renderRuntimeFiles();
    }
  });

  function renderRuntimeFiles() {
    runtimeFilesList.innerHTML = "";
    runtimeSelectedFiles.forEach((file, index) => {
      const pill = document.createElement("div");
      pill.className = "selected-file-pill";
      pill.innerHTML = `
        <span>📄 ${file.name}</span>
        <button type="button" class="remove-file-btn" data-index="${index}">&times;</button>
      `;
      pill.querySelector(".remove-file-btn").addEventListener("click", () => {
        runtimeSelectedFiles.splice(index, 1);
        renderRuntimeFiles();
      });
      runtimeFilesList.appendChild(pill);
    });
  }

  formRuntimeIngest.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!currentAppId) return;
    if (runtimeSelectedFiles.length === 0) {
      showToast("Select at least one document to ingest", "error");
      return;
    }

    const submitBtn = document.getElementById("btn-submit-runtime-ingest");
    submitBtn.disabled = true;
    submitBtn.textContent = "Ingesting...";

    try {
      const fd = new FormData();
      runtimeSelectedFiles.forEach(f => fd.append("files", f));

      const res = await fetch(`/api/apps/${currentAppId}/documents`, {
        method: "POST",
        body: fd,
      });

      if (!res.ok) throw new Error("Runtime ingestion failed");
      const result = await res.json();
      showToast(result.message || "Documents successfully ingested!");

      modalAddDocs.style.display = "none";
      runtimeSelectedFiles = [];
      renderRuntimeFiles();

      // Refresh app data and table
      await selectApplication(currentAppId);
      loadDocumentsTab();
    } catch (err) {
      console.error("Runtime ingest error:", err);
      showToast(err.message || "Ingestion failed", "error");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Ingest Documents";
    }
  });

  // --- Export Tab ---
  function updateExportCodeSnippets() {
    if (!currentAppId) return;
    const origin = window.location.origin;
    codeCurl.textContent = `curl -X POST ${origin}/api/apps/${currentAppId}/query \\
  -H "Content-Type: application/json" \\
  -d '{
    "question": "What is the primary policy or finding?",
    "top_k": 4,
    "hybrid_alpha": 0.5
  }'`;

    codePython.textContent = `import requests

res = requests.post(
    "${origin}/api/apps/${currentAppId}/query",
    json={
        "question": "What is the primary policy or finding?",
        "top_k": 4,
        "hybrid_alpha": 0.5
    }
)
data = res.json()
print("Answer:\\n", data["answer"])
print(f"Confidence: {data['confidence']} ({data['groundedness_score']*100:.1f}% Grounded)")
print("\\nCitations:")
for cit in data["citations"]:
    print(f"- [{cit['source_name']}] p.{cit['page_number']}: {cit['snippet']}")`;
  }

  btnExportApp.addEventListener("click", () => {
    if (!currentAppId) return;
    window.location.href = `/api/apps/${currentAppId}/export`;
    showToast("Downloading standalone RAG bundle (.zip)...");
  });

  // Copy code buttons
  document.querySelectorAll(".copy-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-target");
      const codeEl = document.getElementById(targetId);
      if (codeEl) {
        navigator.clipboard.writeText(codeEl.textContent);
        btn.textContent = "Copied!";
        setTimeout(() => btn.textContent = "Copy", 2000);
      }
    });
  });

  // Initial load
  loadApplications();
});
