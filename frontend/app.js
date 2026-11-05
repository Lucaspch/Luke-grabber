/**
 * Luke-Grabber — Script Frontend
 * Identidade Visual e Experiência inspiradas no Luke-Share (Midnight Ocean & Electric Cyan)
 * Versão: 1.1.0
 */

// Estado da Aplicação
const state = {
  currentUrl: "",
  videoData: null,
  formatType: "video", // "video" | "audio" | "image" | "carousel"
  mediaType: "video",
  isCarousel: false,
  quality: "best",
  downloadDir: "",
  isDownloading: false,
  pollTimer: null,
  lastCompletedFile: "",
  updateInfo: null,
  isUpdatingApp: false
};

// Elementos DOM
const dom = {
  urlInput: document.getElementById("url-input"),
  btnPaste: document.getElementById("btn-paste-clipboard"),
  btnFetch: document.getElementById("btn-fetch-info"),
  btnOpenDir: document.getElementById("btn-open-downloads-dir"),
  brandLogo: document.getElementById("brand-logo"),

  // Palco
  emptyState: document.getElementById("empty-state"),
  loadingState: document.getElementById("loading-state"),
  videoStage: document.getElementById("video-stage"),

  // Detalhes da Mídia
  videoThumb: document.getElementById("video-thumbnail"),
  platformBadge: document.getElementById("platform-badge"),
  platformIcon: document.getElementById("platform-icon"),
  platformName: document.getElementById("platform-name"),
  durationBadge: document.getElementById("duration-badge"),
  carouselBadge: document.getElementById("carousel-badge"),
  carouselBadgeText: document.getElementById("carousel-badge-text"),
  videoTitle: document.getElementById("video-title"),
  videoUploader: document.getElementById("video-uploader"),
  videoViews: document.getElementById("video-views"),
  metaViewsWrapper: document.getElementById("meta-views-wrapper"),

  // Controles de Download
  tabVideo: document.getElementById("tab-video"),
  tabAudio: document.getElementById("tab-audio"),
  tabImage: document.getElementById("tab-image"),
  qualitySelect: document.getElementById("quality-select"),
  chkEmbedThumb: document.getElementById("chk-embed-thumb"),
  chkEmbedSubs: document.getElementById("chk-embed-subs"),
  thumbToggleWrapper: document.getElementById("thumb-toggle-wrapper"),
  subsToggleWrapper: document.getElementById("subs-toggle-wrapper"),
  destinationDisplay: document.getElementById("destination-path-display"),
  btnChangeFolder: document.getElementById("btn-change-folder"),
  btnStartDownload: document.getElementById("btn-start-download"),
  btnStartDownloadText: document.getElementById("btn-start-download-text"),

  // Card de Progresso
  activeDownloadCard: document.getElementById("active-download-card"),
  progressStatusText: document.getElementById("progress-status-text"),
  progressPercentage: document.getElementById("progress-percentage"),
  progressFill: document.getElementById("progress-fill"),
  progressDownloaded: document.getElementById("progress-downloaded"),
  progressSpeed: document.getElementById("progress-speed"),
  progressEta: document.getElementById("progress-eta"),
  progressSpinner: document.getElementById("progress-spinner"),
  downloadCompletedActions: document.getElementById("download-completed-actions"),
  btnPlayFile: document.getElementById("btn-play-file"),
  btnViewInFolder: document.getElementById("btn-view-in-folder"),

  // Histórico
  historyList: document.getElementById("history-list"),
  btnClearHistory: document.getElementById("btn-clear-history"),

  // Modal de Atualização
  btnCheckUpdates: document.getElementById("btn-check-updates"),
  updateBadge: document.getElementById("update-badge"),
  updateModal: document.getElementById("update-modal"),
  btnCloseUpdateModal: document.getElementById("btn-close-update-modal"),
  btnCloseUpdateModalSecondary: document.getElementById("btn-close-update-modal-secondary"),
  updateCurrVersion: document.getElementById("update-curr-version"),
  updateNewVersion: document.getElementById("update-new-version"),
  updateNotes: document.getElementById("update-notes"),
  btnStartUpdate: document.getElementById("btn-start-update"),
  updateProgressContainer: document.getElementById("update-progress-container"),
  updateStatusText: document.getElementById("update-status-text"),
  updateProgressText: document.getElementById("update-progress-text"),
  updateProgressBar: document.getElementById("update-progress-bar"),
  updateActionButtons: document.getElementById("update-action-buttons"),
  engineVersionSub: document.getElementById("engine-version-sub"),
  btnUpdateEngine: document.getElementById("btn-update-engine"),

  // Modal WhatsApp Status
  btnOpenWaModal: document.getElementById("btn-open-wa-modal"),
  whatsappModal: document.getElementById("whatsapp-modal"),
  btnCloseWaModal: document.getElementById("btn-close-whatsapp-modal"),
  btnCloseWaFooter: document.getElementById("btn-close-wa-footer"),
  btnCopyBookmarklet: document.getElementById("btn-copy-bookmarklet"),
  waBookmarkletCode: document.getElementById("wa-bookmarklet-code"),

  // Toasts
  toastContainer: document.getElementById("toast-container")
};

// ============================================================================
// 1. INICIALIZAÇÃO
// ============================================================================
async function initApp() {
  try {
    const res = await fetch("/api/config");
    const config = await res.json();
    state.downloadDir = config.download_dir;
    dom.destinationDisplay.textContent = state.downloadDir;
    dom.destinationDisplay.title = state.downloadDir;

    if (dom.engineVersionSub && config.engine) {
      dom.engineVersionSub.textContent = `Motor: ${config.engine}`;
    }
  } catch (e) {
    console.error("Erro ao carregar configurações:", e);
  }

  loadHistory();
  setupEventListeners();
  checkInitialClipboard();

  // Verificação automática silenciosa de atualizações após 3.5 segundos (igual ao Luke-Share)
  setTimeout(() => {
    checkForUpdates(false).catch((e) => console.debug("Checagem automática de update:", e));
  }, 3500);
}

// ============================================================================
// 2. CONFIGURAÇÃO DE EVENTOS
// ============================================================================
function setupEventListeners() {
  // Input de URL e tecla Enter
  dom.urlInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      fetchVideoInfo();
    }
  });

  dom.btnFetch.addEventListener("click", fetchVideoInfo);

  // Botão Colar
  dom.btnPaste.addEventListener("click", pasteFromClipboard);

  // Tabs de Formato
  dom.tabVideo.addEventListener("click", () => setFormatType("video"));
  dom.tabAudio.addEventListener("click", () => setFormatType("audio"));
  dom.tabImage.addEventListener("click", () => setFormatType("image"));

  // Alterar Pasta
  dom.btnChangeFolder.addEventListener("click", chooseFolder);

  // Abrir pasta de downloads
  dom.btnOpenDir.addEventListener("click", () => {
    fetch("/api/open-folder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder: state.downloadDir })
    });
  });

  // Iniciar Download
  dom.btnStartDownload.addEventListener("click", startDownload);

  // Ações de Conclusão
  dom.btnPlayFile.addEventListener("click", () => {
    if (state.lastCompletedFile) {
      fetch("/api/open-file", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_path: state.lastCompletedFile })
      });
    }
  });

  dom.btnViewInFolder.addEventListener("click", () => {
    if (state.lastCompletedFile) {
      fetch("/api/open-folder", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_path: state.lastCompletedFile })
      });
    }
  });

  // Limpar Histórico
  dom.btnClearHistory.addEventListener("click", async () => {
    if (confirm("Deseja realmente limpar o histórico de downloads recentes?")) {
      await fetch("/api/history/clear", { method: "POST" });
      loadHistory();
      showToast("Histórico limpo com sucesso", "info");
    }
  });

  // Eventos do Sistema de Atualização (Luke-Share)
  if (dom.btnCheckUpdates) {
    dom.btnCheckUpdates.addEventListener("click", () => checkForUpdates(true));
  }
  if (dom.btnCloseUpdateModal) {
    dom.btnCloseUpdateModal.addEventListener("click", closeUpdateModal);
  }
  if (dom.btnCloseUpdateModalSecondary) {
    dom.btnCloseUpdateModalSecondary.addEventListener("click", closeUpdateModal);
  }
  if (dom.btnStartUpdate) {
    dom.btnStartUpdate.addEventListener("click", startApplicationUpdate);
  }
  if (dom.btnUpdateEngine) {
    dom.btnUpdateEngine.addEventListener("click", updateDownloadEngine);
  }

  // Eventos do Modal WhatsApp Status
  if (dom.btnOpenWaModal) {
    dom.btnOpenWaModal.addEventListener("click", () => {
      dom.whatsappModal.classList.remove("hidden");
    });
  }
  if (dom.btnCloseWaModal) {
    dom.btnCloseWaModal.addEventListener("click", () => {
      dom.whatsappModal.classList.add("hidden");
    });
  }
  if (dom.btnCloseWaFooter) {
    dom.btnCloseWaFooter.addEventListener("click", () => {
      dom.whatsappModal.classList.add("hidden");
    });
  }
  if (dom.btnCopyBookmarklet) {
    dom.btnCopyBookmarklet.addEventListener("click", copyWaBookmarklet);
  }

  // Auto-detecção ao focar na janela
  window.addEventListener("focus", () => {
    checkInitialClipboard();
  });
}

// ============================================================================
// 3. ANÁLISE DE LINK DO VÍDEO / FOTO / CARROSSEL (API INFO)
// ============================================================================
async function fetchVideoInfo() {
  const url = dom.urlInput.value.trim();
  if (!url) {
    showToast("Por favor, cole o link de um vídeo ou post primeiro.", "warning");
    dom.urlInput.focus();
    return;
  }

  state.currentUrl = url;

  // Atualiza visual para Carregando
  dom.emptyState.classList.add("hidden");
  dom.videoStage.classList.add("hidden");
  dom.loadingState.classList.remove("hidden");
  dom.btnFetch.disabled = true;

  try {
    const res = await fetch("/api/info", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });
    const data = await res.json();

    if (data.error) {
      throw new Error(data.error);
    }

    state.videoData = data;
    renderMediaCard(data);
    showToast("Mídia analisada com sucesso!", "success");
  } catch (err) {
    console.error("Erro na extração:", err);
    dom.loadingState.classList.add("hidden");
    dom.emptyState.classList.remove("hidden");
    showToast("Não foi possível analisar o link: " + err.message, "danger");
  } finally {
    dom.btnFetch.disabled = false;
  }
}

function renderMediaCard(data) {
  dom.loadingState.classList.add("hidden");
  dom.emptyState.classList.add("hidden");
  dom.videoStage.classList.remove("hidden");

  // Miniatura e Metadados
  dom.videoThumb.src = data.thumbnail || "logo.svg";
  dom.videoTitle.textContent = data.title;
  dom.videoTitle.title = data.title;
  dom.videoUploader.textContent = data.uploader;

  if (data.views && data.views !== "-") {
    dom.videoViews.textContent = `${data.views} visualizações`;
    dom.metaViewsWrapper.style.display = "flex";
  } else {
    dom.metaViewsWrapper.style.display = "none";
  }

  dom.durationBadge.textContent = data.duration;

  // Plataforma (YouTube / X / Instagram / TikTok)
  const plat = data.platform || { name: "Web Multimídia", icon: "play_circle" };
  dom.platformIcon.textContent = plat.icon;
  dom.platformName.textContent = plat.name;

  // Trata Carrossel
  if (data.is_carousel) {
    state.isCarousel = true;
    state.mediaType = "carousel";
    dom.carouselBadge.classList.remove("hidden");
    dom.carouselBadgeText.textContent = `Carrossel (${data.carousel_count} mídias)`;
    setFormatType("carousel");
  } else if (data.media_type === "image") {
    state.isCarousel = false;
    state.mediaType = "image";
    dom.carouselBadge.classList.add("hidden");
    setFormatType("image");
  } else {
    state.isCarousel = false;
    state.mediaType = "video";
    dom.carouselBadge.classList.add("hidden");
    setFormatType("video");
  }
}

function setFormatType(type) {
  state.formatType = type;

  // Reset visual das tabs
  dom.tabVideo.classList.remove("active");
  dom.tabAudio.classList.remove("active");
  dom.tabImage.classList.remove("active");

  if (type === "video") {
    dom.tabVideo.classList.add("active");
    dom.subsToggleWrapper.classList.remove("hidden");
    dom.thumbToggleWrapper.classList.remove("hidden");
    dom.btnStartDownloadText.textContent = "BAIXAR VÍDEO (MP4)";
  } else if (type === "audio") {
    dom.tabAudio.classList.add("active");
    dom.subsToggleWrapper.classList.add("hidden");
    dom.thumbToggleWrapper.classList.remove("hidden");
    dom.btnStartDownloadText.textContent = "BAIXAR ÁUDIO (MP3)";
  } else if (type === "image") {
    dom.tabImage.classList.add("active");
    dom.subsToggleWrapper.classList.add("hidden");
    dom.thumbToggleWrapper.classList.add("hidden");
    dom.btnStartDownloadText.textContent = "BAIXAR FOTO ORIGINAL";
  } else if (type === "carousel") {
    dom.tabImage.classList.add("active");
    dom.subsToggleWrapper.classList.add("hidden");
    dom.thumbToggleWrapper.classList.add("hidden");
    dom.btnStartDownloadText.textContent = "BAIXAR CARROSSEL COMPLETO";
  }

  updateQualityOptions();
}

function updateQualityOptions() {
  dom.qualitySelect.innerHTML = "";

  if (state.formatType === "video") {
    const qualities = [
      { val: "best", label: "Melhor Disponível (Original / 4K / 1080p)" },
      { val: "1080", label: "1080p FHD (Alta Definição)" },
      { val: "720", label: "720p HD (Padrão Rápido)" },
      { val: "480", label: "480p SD (Leve)" }
    ];
    qualities.forEach(q => {
      const opt = document.createElement("option");
      opt.value = q.val;
      opt.textContent = q.label;
      dom.qualitySelect.appendChild(opt);
    });
  } else if (state.formatType === "audio") {
    const audioOptions = [
      { val: "mp3_320", label: "MP3 — 320 kbps (Máxima Fidelidade)" },
      { val: "mp3_192", label: "MP3 — 192 kbps (Padrão)" },
      { val: "m4a", label: "M4A — Áudio Nativo AAC" },
      { val: "wav", label: "WAV — Sem Compressão (Lossless)" }
    ];
    audioOptions.forEach(a => {
      const opt = document.createElement("option");
      opt.value = a.val;
      opt.textContent = a.label;
      dom.qualitySelect.appendChild(opt);
    });
  } else if (state.formatType === "image") {
    const imgOptions = [
      { val: "best", label: "Imagem Original (Melhor Resolução JPG/WEBP)" }
    ];
    imgOptions.forEach(i => {
      const opt = document.createElement("option");
      opt.value = i.val;
      opt.textContent = i.label;
      dom.qualitySelect.appendChild(opt);
    });
  } else if (state.formatType === "carousel") {
    const carOptions = [
      { val: "all", label: "Todas as Mídias (Fotos e Vídeos do Carrossel)" },
      { val: "images_only", label: "Apenas Imagens / Fotos" },
      { val: "videos_only", label: "Apenas Vídeos" }
    ];
    carOptions.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.val;
      opt.textContent = c.label;
      dom.qualitySelect.appendChild(opt);
    });
  }
}

// ============================================================================
// 4. SELEÇÃO DE PASTA
// ============================================================================
async function chooseFolder() {
  try {
    const res = await fetch("/api/select-folder", { method: "POST" });
    const data = await res.json();
    if (!data.canceled && data.folder) {
      state.downloadDir = data.folder;
      dom.destinationDisplay.textContent = state.downloadDir;
      dom.destinationDisplay.title = state.downloadDir;
      showToast("Pasta de downloads alterada!", "info");
    }
  } catch (e) {
    console.error("Erro ao selecionar pasta:", e);
  }
}

// ============================================================================
// 5. INICIAR E ACOMPANHAR DOWNLOAD
// ============================================================================
async function startDownload() {
  if (!state.currentUrl || !state.videoData) return;

  const payload = {
    url: state.currentUrl,
    title: state.videoData.title,
    thumbnail: state.videoData.thumbnail,
    format_type: state.formatType,
    quality: dom.qualitySelect.value,
    out_dir: state.downloadDir,
    embed_thumb: dom.chkEmbedThumb.checked,
    embed_subs: dom.chkEmbedSubs.checked
  };

  dom.btnStartDownload.disabled = true;
  dom.activeDownloadCard.classList.remove("hidden");
  dom.downloadCompletedActions.classList.add("hidden");
  dom.progressPercentage.textContent = "0%";
  dom.progressFill.style.width = "0%";
  dom.progressStatusText.textContent = "Iniciando processamento...";
  dom.progressSpinner.style.display = "inline-flex";

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const resp = await res.json();
    if (resp.error) throw new Error(resp.error);

    state.isDownloading = true;
    startProgressPolling();
  } catch (err) {
    showToast("Erro ao iniciar download: " + err.message, "danger");
    dom.btnStartDownload.disabled = false;
  }
}

function startProgressPolling() {
  if (state.pollTimer) clearInterval(state.pollTimer);

  state.pollTimer = setInterval(async () => {
    try {
      const res = await fetch("/api/progress");
      const prog = await res.json();

      dom.progressPercentage.textContent = `${prog.progress}%`;
      dom.progressFill.style.width = `${prog.progress}%`;
      dom.progressDownloaded.textContent = `${prog.downloaded} / ${prog.total}`;
      dom.progressSpeed.textContent = prog.speed;
      dom.progressEta.textContent = `Restante: ${prog.eta}`;
      dom.progressStatusText.textContent = prog.message;

      if (prog.status === "completed") {
        clearInterval(state.pollTimer);
        state.isDownloading = false;
        state.lastCompletedFile = prog.file_path;
        dom.progressSpinner.style.display = "none";
        dom.downloadCompletedActions.classList.remove("hidden");
        dom.btnStartDownload.disabled = false;
        showToast("Download concluído com sucesso!", "success");
        loadHistory();
      } else if (prog.status === "error") {
        clearInterval(state.pollTimer);
        state.isDownloading = false;
        dom.progressSpinner.style.display = "none";
        dom.btnStartDownload.disabled = false;
        showToast("Falha no download: " + (prog.error || "Erro desconhecido"), "danger");
      }
    } catch (e) {
      console.warn("Falha no polling de progresso:", e);
    }
  }, 400);
}

// ============================================================================
// 6. HISTÓRICO DE DOWNLOADS
// ============================================================================
async function loadHistory() {
  try {
    const res = await fetch("/api/history");
    const history = await res.json();

    if (!history || history.length === 0) {
      dom.historyList.innerHTML = `
        <div class="empty-state" style="padding: 24px; font-size: 13px; color: var(--text-subtle);">
          Nenhum download registrado ainda.
        </div>
      `;
      return;
    }

    dom.historyList.innerHTML = history.map(item => {
      let formatLabel = "Vídeo MP4";
      if (item.format_type === "audio") formatLabel = "Áudio MP3";
      else if (item.format_type === "image") formatLabel = "Foto Original";
      else if (item.format_type === "carousel") formatLabel = "Carrossel";

      return `
        <div class="history-item-card">
          <img src="${item.thumbnail || 'logo.svg'}" class="history-thumb-mini" alt="" />
          <div class="history-info-group">
            <div class="history-item-title" title="${escapeHtml(item.title)}">${escapeHtml(item.title)}</div>
            <div class="history-item-sub">
              <span>${escapeHtml(item.uploader)}</span>
              <span>•</span>
              <span style="color: var(--accent-cyan); text-transform: uppercase; font-weight: 700;">${formatLabel}</span>
              <span>•</span>
              <span>${item.file_size || ''}</span>
            </div>
          </div>
          <div class="history-item-actions">
            <button class="btn-icon-action" title="Abrir Arquivo" onclick="playHistoryFile('${escapeJs(item.file_path)}')">
              <span class="material-symbols-rounded ms-sm">play_arrow</span>
            </button>
            <button class="btn-icon-action" title="Mostrar na Pasta" onclick="openHistoryFolder('${escapeJs(item.file_path)}')">
              <span class="material-symbols-rounded ms-sm">folder</span>
            </button>
          </div>
        </div>
      `;
    }).join("");
  } catch (e) {
    console.error("Erro ao carregar histórico:", e);
  }
}

window.playHistoryFile = (path) => {
  fetch("/api/open-file", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_path: path })
  });
};

window.openHistoryFolder = (path) => {
  fetch("/api/open-folder", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_path: path })
  });
};

// ============================================================================
// 7. SISTEMA DE ATUALIZAÇÃO AUTOMÁTICA (PADRÃO LUKE-SHARE)
// ============================================================================
async function checkForUpdates(manual = false) {
  if (state.isUpdatingApp) return;

  if (manual && dom.btnCheckUpdates) {
    dom.btnCheckUpdates.disabled = true;
    dom.btnCheckUpdates.innerHTML = `<span class="material-symbols-rounded ms-sm" style="animation: spin 1s linear infinite;">sync</span><span>Checando...</span>`;
  }

  try {
    const res = await fetch("/api/updates/check");
    const data = await res.json();
    state.updateInfo = data;

    if (data.available && data.latest_version) {
      // Notifica presença de nova versão
      if (dom.updateBadge) dom.updateBadge.classList.remove("hidden");
      showUpdateModal(data);
    } else {
      if (dom.updateBadge) dom.updateBadge.classList.add("hidden");
      if (manual) {
        showToast(`O Luke-Grabber já está na versão mais recente (v${data.current_version})!`, "success");
      }
    }
  } catch (err) {
    console.warn("Erro ao checar atualizações:", err);
    if (manual) {
      showToast("Não foi possível verificar atualizações no momento.", "warning");
    }
  } finally {
    if (manual && dom.btnCheckUpdates) {
      dom.btnCheckUpdates.disabled = false;
      dom.btnCheckUpdates.innerHTML = `
        <span class="material-symbols-rounded ms-sm">sync</span>
        <span>Atualizações</span>
        <span id="update-badge" class="update-badge-dot ${state.updateInfo?.available ? '' : 'hidden'}"></span>
      `;
    }
  }
}

function showUpdateModal(data) {
  dom.updateCurrVersion.textContent = `v${data.current_version}`;
  dom.updateNewVersion.textContent = `v${data.latest_version}`;
  dom.updateNotes.textContent = data.notes || "Melhorias gerais e compatibilidade com novas plataformas.";

  dom.updateProgressContainer.classList.add("hidden");
  dom.updateActionButtons.classList.remove("hidden");
  dom.updateModal.classList.remove("hidden");
}

function closeUpdateModal() {
  if (!state.isUpdatingApp) {
    dom.updateModal.classList.add("hidden");
  }
}

async function startApplicationUpdate() {
  if (state.isUpdatingApp || !state.updateInfo?.download_url) return;
  state.isUpdatingApp = true;

  dom.updateActionButtons.classList.add("hidden");
  dom.updateProgressContainer.classList.remove("hidden");
  dom.updateStatusText.textContent = "Baixando atualização oficial do Luke-Grabber...";

  try {
    await fetch("/api/updates/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ download_url: state.updateInfo.download_url })
    });

    // Inicia polling de progresso do update
    const updateTimer = setInterval(async () => {
      try {
        const res = await fetch("/api/updates/progress");
        const prog = await res.json();

        dom.updateProgressBar.style.width = `${prog.progress}%`;
        dom.updateProgressText.textContent = `${prog.progress}%`;
        dom.updateStatusText.textContent = prog.message;

        if (prog.status === "ready") {
          clearInterval(updateTimer);
          dom.updateStatusText.textContent = "Iniciando instalador da nova versão...";
          showToast("Atualização baixada! Reiniciando aplicativo...", "success");
        } else if (prog.status === "error") {
          clearInterval(updateTimer);
          state.isUpdatingApp = false;
          dom.updateStatusText.textContent = prog.message;
          dom.updateStatusText.style.color = "#f43f5e";
          dom.updateActionButtons.classList.remove("hidden");
        }
      } catch (e) {
        console.warn("Polling de update:", e);
      }
    }, 500);

  } catch (err) {
    state.isUpdatingApp = false;
    dom.updateStatusText.textContent = "Falha ao iniciar atualização.";
    dom.updateActionButtons.classList.remove("hidden");
    showToast("Erro: " + err.message, "danger");
  }
}

async function updateDownloadEngine() {
  if (dom.btnUpdateEngine) {
    dom.btnUpdateEngine.disabled = true;
    dom.btnUpdateEngine.innerHTML = `<span class="material-symbols-rounded ms-xs" style="animation: spin 1s linear infinite;">sync</span><span>Atualizando...</span>`;
  }

  try {
    const res = await fetch("/api/updates/engine", { method: "POST" });
    const data = await res.json();
    if (data.success) {
      if (dom.engineVersionSub) {
        dom.engineVersionSub.textContent = `Versão: yt-dlp ${data.version}`;
      }
      showToast(`Motor atualizado com sucesso para yt-dlp ${data.version}!`, "success");
    } else {
      showToast("Não foi possível atualizar o motor: " + (data.error || "Desconhecido"), "danger");
    }
  } catch (e) {
    showToast("Erro na requisição de atualização do motor.", "danger");
  } finally {
    if (dom.btnUpdateEngine) {
      dom.btnUpdateEngine.disabled = false;
      dom.btnUpdateEngine.innerHTML = `<span class="material-symbols-rounded ms-xs">refresh</span><span>Atualizar Motor</span>`;
    }
  }
}

// ============================================================================
// 8. HELPERS DE WHATSAPP STATUS & CLIPBOARD
// ============================================================================
async function copyWaBookmarklet() {
  const code = dom.waBookmarkletCode.textContent.trim();
  try {
    await navigator.clipboard.writeText(code);
    showToast("Código copiado! Cole na barra de favoritos do seu navegador.", "success");
  } catch (e) {
    showToast("Não foi possível copiar automaticamente. Selecione e copie o texto.", "warning");
  }
}

async function pasteFromClipboard() {
  try {
    const text = await navigator.clipboard.readText();
    if (text && (text.startsWith("http://") || text.startsWith("https://"))) {
      dom.urlInput.value = text.trim();
      fetchVideoInfo();
    } else {
      showToast("Nenhum link detectado na área de transferência.", "warning");
    }
  } catch (err) {
    showToast("Permissão negada para ler área de transferência.", "warning");
  }
}

async function checkInitialClipboard() {
  if (state.videoData || dom.urlInput.value.trim()) return;
  try {
    const text = await navigator.clipboard.readText();
    if (text && (
      text.includes("youtube.com") || text.includes("youtu.be") ||
      text.includes("x.com") || text.includes("twitter.com") ||
      text.includes("instagram.com") || text.includes("tiktok.com")
    )) {
      dom.urlInput.value = text.trim();
      showToast("Link detectado na área de transferência! Pressione Analisar.", "info");
    }
  } catch (e) {}
}

function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = "toast";

  let icon = "info";
  if (type === "success") icon = "check_circle";
  if (type === "danger") icon = "error";
  if (type === "warning") icon = "warning";

  toast.innerHTML = `
    <span class="material-symbols-rounded ms-sm" style="color: ${type === 'success' ? 'var(--accent-success)' : type === 'danger' ? 'var(--accent-danger)' : 'var(--accent-cyan)'}">${icon}</span>
    <span>${escapeHtml(message)}</span>
  `;

  dom.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(50px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function escapeJs(str) {
  if (!str) return "";
  return str.replace(/\\/g, "\\\\").replace(/'/g, "\\'");
}

// Inicia aplicação quando o DOM estiver pronto
document.addEventListener("DOMContentLoaded", initApp);
