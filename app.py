"""
Luke-Grabber — Extrator & Arquivador Multimídia Local e Aberto
Autor: Antigravity para Lucas
Identidade Visual: Baseada no Luke-Share (Midnight Ocean & Electric Cyan)
Motor: yt-dlp + FFmpeg (100% Local, Sem Telemetria, Sem Servidores de Terceiros)
Versão: 1.1.0
"""

import os
import sys
import json
import time
import shutil
import urllib.parse
import urllib.request
import threading
import subprocess
import re
import tkinter as tk
from tkinter import filedialog
from pathlib import Path

# Configura diretório base (compatível com execução normal e PyInstaller)
if getattr(sys, "frozen", False):
    BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    EXE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent
    EXE_DIR = BASE_DIR

FRONTEND_DIR = BASE_DIR / "frontend"
BIN_DIR = BASE_DIR / "bin"
if not BIN_DIR.exists() and (EXE_DIR / "bin").exists():
    BIN_DIR = EXE_DIR / "bin"

HISTORY_FILE = EXE_DIR / "history.json"
APP_VERSION = "1.1.1"
GITHUB_REPO = "Lucaspch/Luke-grabber"

# Garante que o FFmpeg local de bin/ seja prioridade no PATH
os.environ["PATH"] = str(BIN_DIR) + os.pathsep + os.environ.get("PATH", "")

# Importa yt_dlp
import yt_dlp
import yt_dlp.extractor.instagram as ig

# -----------------------------------------------------------------------------
# PATCH DO EXTRATOR DO INSTAGRAM NO YT-DLP
# -----------------------------------------------------------------------------
# Por padrão, o yt-dlp lança 'There is no video in this post' para posts de foto.
# Este patch injeta as fotos do post em 'formats' para que o yt-dlp retorne todas
# as resoluções originais e metadados com sucesso.
try:
    _orig_extract_product_media = ig.InstagramIE._extract_product_media
    def _patched_extract_product_media(self, product_media):
        res = _orig_extract_product_media(self, product_media)
        if not res.get("formats") and res.get("thumbnails"):
            res["formats"] = []
            for idx, t in enumerate(res["thumbnails"]):
                if t.get("url"):
                    res["formats"].append({
                        "format_id": f"img_{idx}",
                        "url": t["url"],
                        "ext": "jpg",
                        "vcodec": "none",
                        "acodec": "none",
                        "width": t.get("width"),
                        "height": t.get("height"),
                    })
        return res
    ig.InstagramIE._extract_product_media = _patched_extract_product_media

    _orig_extract_product = ig.InstagramIE._extract_product
    def _patched_extract_product(self, product_info, video_id=None, get_comments=True):
        res = _orig_extract_product(self, product_info, video_id=video_id, get_comments=get_comments)
        if not res.get("formats") and res.get("thumbnails"):
            res["formats"] = []
            for idx, t in enumerate(res["thumbnails"]):
                if t.get("url"):
                    res["formats"].append({
                        "format_id": f"img_{idx}",
                        "url": t["url"],
                        "ext": "jpg",
                        "vcodec": "none",
                        "acodec": "none",
                        "width": t.get("width"),
                        "height": t.get("height"),
                    })
        return res
    ig.InstagramIE._extract_product = _patched_extract_product
except Exception as _patch_err:
    print(f"Aviso ao aplicar patch do Instagram: {_patch_err}")

# Importa Bottle (WSGI micro-framework leve)
from bottle import Bottle, request, response, static_file, run

app = Bottle()

# Pasta padrão de downloads do usuário: Downloads/Luke-Grabber
DEFAULT_DOWNLOAD_DIR = Path.home() / "Downloads" / "Luke-Grabber"
DEFAULT_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Estado global da aplicação
current_download = {
    "is_active": False,
    "url": "",
    "title": "",
    "thumbnail": "",
    "format_type": "video",
    "quality": "best",
    "progress": 0.0,
    "speed": "0 MB/s",
    "downloaded": "0 MB",
    "total": "0 MB",
    "eta": "--:--",
    "status": "idle", # idle, analyzing, downloading, processing, completed, error
    "message": "Pronto para baixar",
    "file_path": "",
    "error": None
}

updater_state = {
    "is_updating": False,
    "progress": 0.0,
    "downloaded": "0 MB",
    "total": "0 MB",
    "status": "idle",
    "message": "",
    "target_file": ""
}

download_lock = threading.Lock()
updater_lock = threading.Lock()

# -----------------------------------------------------------------------------
# GERENCIAMENTO DE HISTÓRICO
# -----------------------------------------------------------------------------
def load_history():
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(entry):
    history = load_history()
    # Adiciona no topo e limita aos últimos 50 itens
    history = [h for h in history if h.get("id") != entry.get("id")]
    history.insert(0, entry)
    history = history[:50]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erro ao salvar histórico: {e}")

# -----------------------------------------------------------------------------
# HELPERS DE HIGIENIZAÇÃO E MÍDIA
# -----------------------------------------------------------------------------
def sanitize_filename(name: str, max_len: int = 120) -> str:
    """Higieniza o nome do arquivo para compatibilidade universal no Windows."""
    cleaned = re.sub(r'[<>:"/\\|?*\n\r\t]', '_', name or "download")
    cleaned = cleaned.strip(". ")
    return cleaned[:max_len] or "download"

def get_best_image_url(info: dict) -> str:
    """Extrai a URL da imagem de maior resolução disponível nos metadados."""
    if not info:
        return ""
    thumbs = info.get("thumbnails") or []
    if thumbs:
        valid = [t for t in thumbs if t.get("url")]
        if valid:
            valid.sort(key=lambda t: (t.get("width") or 0) * (t.get("height") or 0), reverse=True)
            return valid[0].get("url") or ""
    if info.get("thumbnail"):
        return info.get("thumbnail")
    if info.get("url") and any(info.get("url").lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
        return info.get("url")
    return ""

def detect_platform(url: str):
    u = url.lower()
    if "youtube.com" in u or "youtu.be" in u:
        return {"name": "YouTube", "icon": "smart_display", "color": "#ff0000", "chip": "yt"}
    elif "x.com" in u or "twitter.com" in u:
        return {"name": "X (Twitter)", "icon": "chat", "color": "#38bdf8", "chip": "x"}
    elif "instagram.com" in u:
        return {"name": "Instagram", "icon": "photo_camera", "color": "#e1306c", "chip": "ig"}
    elif "tiktok.com" in u:
        return {"name": "TikTok", "icon": "music_note", "color": "#00f2fe", "chip": "tk"}
    elif "whatsapp.com" in u:
        return {"name": "WhatsApp", "icon": "forum", "color": "#25d366", "chip": "wa"}
    return {"name": "Web Multimídia", "icon": "play_circle", "color": "#0ea5e9", "chip": "web"}

# -----------------------------------------------------------------------------
# ROTAS DA API REST
# -----------------------------------------------------------------------------
@app.route("/")
def index():
    return static_file("index.html", root=str(FRONTEND_DIR))

@app.route("/<filepath:path>")
def server_static(filepath):
    return static_file(filepath, root=str(FRONTEND_DIR))

@app.route("/api/config", method=["GET"])
def get_config():
    response.content_type = "application/json"
    ffmpeg_ok = (BIN_DIR / "ffmpeg.exe").exists() or bool(shutil.which("ffmpeg"))
    return json.dumps({
        "download_dir": str(DEFAULT_DOWNLOAD_DIR),
        "ffmpeg_installed": ffmpeg_ok,
        "version": APP_VERSION,
        "engine": "yt-dlp " + yt_dlp.version.__version__
    })

@app.route("/api/select-folder", method=["POST"])
def select_folder():
    response.content_type = "application/json"
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        folder = filedialog.askdirectory(initialdir=str(DEFAULT_DOWNLOAD_DIR), title="Selecione a Pasta de Downloads do Luke-Grabber")
        root.destroy()
        if folder:
            return json.dumps({"folder": folder, "canceled": False})
        return json.dumps({"folder": str(DEFAULT_DOWNLOAD_DIR), "canceled": True})
    except Exception as e:
        return json.dumps({"error": str(e), "folder": str(DEFAULT_DOWNLOAD_DIR)})

@app.route("/api/info", method=["POST"])
def get_info():
    response.content_type = "application/json"
    data = request.json or {}
    url = (data.get("url") or "").strip()
    if not url:
        return json.dumps({"error": "URL não fornecida"})

    try:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": False,
            "format": "all",
            "ffmpeg_location": str(BIN_DIR),
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            }
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return json.dumps({"error": "Não foi possível extrair dados desta URL"})

            platform = detect_platform(url)

            # Verifica se é um carrossel / playlist com múltiplas mídias
            entries = info.get("entries")
            is_carousel = False
            carousel_items = []
            media_type = "video" # "video", "image", "carousel"

            if entries and len(entries) > 1:
                is_carousel = True
                media_type = "carousel"
                first_entry = entries[0]
                uploader = info.get("uploader") or first_entry.get("uploader") or info.get("channel") or "Instagram"
                title = info.get("title") or first_entry.get("title") or f"Carrossel ({len(entries)} mídias)"
                main_thumbnail = get_best_image_url(first_entry) or info.get("thumbnail", "")

                for idx, entry in enumerate(entries):
                    formats_e = entry.get("formats", [])
                    has_v = any(f.get("vcodec") and f.get("vcodec") != "none" for f in formats_e)
                    thumb_e = get_best_image_url(entry) or entry.get("thumbnail", "")
                    carousel_items.append({
                        "index": idx + 1,
                        "type": "video" if has_v else "image",
                        "thumbnail": thumb_e,
                        "title": f"Mídia {idx + 1}"
                    })

                available_qualities = ["all", "images_only", "videos_only"]
                dur_str = f"{len(entries)} Mídias"
                views_str = "-"
            else:
                # Caso venha envelopado em entries com 1 item só
                if entries and len(entries) == 1:
                    info = entries[0]

                formats = info.get("formats", [])
                has_video = any(f.get("vcodec") and f.get("vcodec") != "none" for f in formats)
                best_img = get_best_image_url(info)

                if not has_video and (best_img or not formats):
                    media_type = "image"
                    main_thumbnail = best_img
                    dur_str = "Imagem Estática"
                    available_qualities = ["original"]
                else:
                    media_type = "video"
                    main_thumbnail = info.get("thumbnail") or best_img

                    duration_sec = info.get("duration", 0)
                    if duration_sec:
                        mins, secs = divmod(int(duration_sec), 60)
                        hrs, mins = divmod(mins, 60)
                        dur_str = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs else f"{mins:02d}:{secs:02d}"
                    else:
                        dur_str = "Ao Vivo / Padrão"

                    # Extrai resoluções de vídeo disponíveis
                    heights = set()
                    for f in formats:
                        h = f.get("height")
                        if h and isinstance(h, int):
                            heights.add(h)
                    available_qualities = sorted(list(heights), reverse=True)

                uploader = info.get("uploader") or info.get("channel") or info.get("uploader_id") or "Autor Desconhecido"
                title = info.get("title", "Sem título")
                views = info.get("view_count")
                views_str = f"{views:,}".replace(",", ".") if views else "-"

            return json.dumps({
                "id": info.get("id"),
                "url": url,
                "title": title,
                "uploader": uploader,
                "thumbnail": main_thumbnail,
                "duration": dur_str,
                "views": views_str,
                "platform": platform,
                "media_type": media_type,
                "is_carousel": is_carousel,
                "carousel_count": len(carousel_items) if is_carousel else 1,
                "carousel_items": carousel_items,
                "available_qualities": available_qualities,
                "description": (info.get("description") or "")[:300]
            })
    except Exception as e:
        return json.dumps({"error": f"Falha ao analisar link: {str(e)}"})

# -----------------------------------------------------------------------------
# PROCESSO DE DOWNLOAD EM BACKGROUND
# -----------------------------------------------------------------------------
def progress_hook(d):
    global current_download
    status = d.get("status")
    if status == "downloading":
        downloaded = d.get("downloaded_bytes", 0)
        total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
        
        if total > 0:
            pct = round((downloaded / total) * 100, 1)
        else:
            pct = 0.0

        speed = d.get("speed")
        if speed:
            speed_mb = speed / (1024 * 1024)
            speed_str = f"{speed_mb:.1f} MB/s"
        else:
            speed_str = "-- MB/s"

        eta = d.get("eta")
        if eta is not None:
            m, s = divmod(int(eta), 60)
            eta_str = f"{m:02d}:{s:02d}"
        else:
            eta_str = "--:--"

        dl_mb = downloaded / (1024 * 1024)
        tot_mb = total / (1024 * 1024) if total else 0
        total_str = f"{tot_mb:.1f} MB" if tot_mb else "calculando..."

        with download_lock:
            current_download["progress"] = pct
            current_download["speed"] = speed_str
            current_download["downloaded"] = f"{dl_mb:.1f} MB"
            current_download["total"] = total_str
            current_download["eta"] = eta_str
            current_download["status"] = "downloading"
            current_download["message"] = f"Baixando: {pct}% a {speed_str} (Restam {eta_str})"

    elif status == "finished":
        with download_lock:
            current_download["progress"] = 99.0
            current_download["status"] = "processing"
            current_download["message"] = "Processando áudio e vídeo com FFmpeg..."

def download_file_direct(url: str, dest_path: Path, status_label: str = "Baixando imagem"):
    """Download direto de fluxos HTTP (imagens / fotos) com reporte de progresso."""
    global current_download
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp, open(dest_path, "wb") as f:
        total_size = int(resp.headers.get("content-length", 0))
        downloaded = 0
        start_time = time.time()

        while True:
            chunk = resp.read(64 * 1024)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)

            elapsed = max(0.1, time.time() - start_time)
            speed_mb = (downloaded / elapsed) / (1024 * 1024)
            pct = round((downloaded / total_size) * 100, 1) if total_size > 0 else 50.0

            with download_lock:
                current_download["progress"] = pct
                current_download["speed"] = f"{speed_mb:.1f} MB/s"
                current_download["downloaded"] = f"{downloaded / (1024*1024):.1f} MB"
                current_download["total"] = f"{total_size / (1024*1024):.1f} MB" if total_size > 0 else "-"
                current_download["status"] = "downloading"
                current_download["message"] = f"{status_label}: {pct}%"

def run_download_thread(params):
    global current_download
    url = params["url"]
    format_type = params.get("format_type", "video") # "video", "audio", "image", "carousel"
    quality = params.get("quality", "best")
    out_dir = Path(params["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    embed_thumb = params.get("embed_thumb", True)
    embed_subs = params.get("embed_subs", False)

    try:
        # 1. Caso especial: Download de Imagem / Foto
        if format_type == "image":
            with download_lock:
                current_download["message"] = "Obtendo endereço da imagem original..."

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "format": "all",
                "ffmpeg_location": str(BIN_DIR),
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if "entries" in info and info["entries"]:
                    info = info["entries"][0]

                img_url = get_best_image_url(info)
                if not img_url:
                    raise Exception("Não foi possível localizar o fluxo de imagem de alta resolução.")

                clean_title = sanitize_filename(info.get("title") or "foto_instagram")
                item_id = info.get("id") or str(int(time.time()))
                dest_path = out_dir / f"{clean_title} [{item_id}].jpg"

                download_file_direct(img_url, dest_path, "Baixando imagem original")

                with download_lock:
                    current_download["progress"] = 100.0
                    current_download["status"] = "completed"
                    current_download["message"] = "Imagem salva com sucesso!"
                    current_download["file_path"] = str(dest_path)

                history_item = {
                    "id": item_id,
                    "title": info.get("title", "Imagem"),
                    "uploader": info.get("uploader") or info.get("channel") or "Luke-Grabber",
                    "thumbnail": img_url,
                    "format_type": "image",
                    "quality": "Original HD",
                    "file_path": str(dest_path),
                    "timestamp": int(time.time()),
                    "file_size": f"{os.path.getsize(dest_path) / (1024*1024):.2f} MB"
                }
                save_history(history_item)
                return

        # 2. Caso especial: Carrossel com Múltiplas Mídias
        if format_type == "carousel":
            with download_lock:
                current_download["message"] = "Analisando carrossel de mídias..."

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "format": "all",
                "ffmpeg_location": str(BIN_DIR),
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                entries = info.get("entries") or [info]
                total_items = len(entries)
                clean_title = sanitize_filename(info.get("title") or "carrossel_instagram")
                post_id = info.get("id") or str(int(time.time()))

                completed_files = []

                for idx, entry in enumerate(entries):
                    item_num = idx + 1
                    formats_e = entry.get("formats", [])
                    has_v = any(f.get("vcodec") and f.get("vcodec") != "none" for f in formats_e)

                    with download_lock:
                        current_download["message"] = f"Baixando item {item_num} de {total_items}..."

                    if has_v and quality != "images_only":
                        # Baixa o vídeo do carrossel
                        item_dest = str(out_dir / f"{clean_title} [{post_id}]_{item_num:02d}.%(ext)s")
                        item_opts = {
                            "outtmpl": item_dest,
                            "quiet": True,
                            "no_warnings": True,
                            "format": "bestvideo+bestaudio/best",
                            "merge_output_format": "mp4",
                            "ffmpeg_location": str(BIN_DIR),
                        }
                        with yt_dlp.YoutubeDL(item_opts) as item_ydl:
                            item_ydl.download([entry.get("webpage_url") or url])
                        expected_file = out_dir / f"{clean_title} [{post_id}]_{item_num:02d}.mp4"
                        if expected_file.exists():
                            completed_files.append(str(expected_file))

                    elif not has_v and quality != "videos_only":
                        # Baixa a foto do carrossel
                        img_url = get_best_image_url(entry)
                        if img_url:
                            item_dest = out_dir / f"{clean_title} [{post_id}]_{item_num:02d}.jpg"
                            download_file_direct(img_url, item_dest, f"Baixando foto {item_num}/{total_items}")
                            completed_files.append(str(item_dest))

                    pct_total = round((item_num / total_items) * 100, 1)
                    with download_lock:
                        current_download["progress"] = pct_total

                first_file = completed_files[0] if completed_files else str(out_dir)

                with download_lock:
                    current_download["progress"] = 100.0
                    current_download["status"] = "completed"
                    current_download["message"] = f"Carrossel completo: {len(completed_files)} mídias salvas!"
                    current_download["file_path"] = first_file

                history_item = {
                    "id": post_id,
                    "title": f"{info.get('title', 'Carrossel')} ({len(completed_files)} mídias)",
                    "uploader": info.get("uploader") or info.get("channel") or "Instagram",
                    "thumbnail": get_best_image_url(entries[0]) if entries else "",
                    "format_type": "carousel",
                    "quality": f"{len(completed_files)} Itens",
                    "file_path": first_file,
                    "timestamp": int(time.time()),
                    "file_size": f"{len(completed_files)} arquivos"
                }
                save_history(history_item)
                return

        # 3. Caso padrão: Vídeo ou Áudio via yt-dlp
        out_template = str(out_dir / "%(title).200B [%(id)s].%(ext)s")

        ydl_opts = {
            "outtmpl": out_template,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [progress_hook],
            "ffmpeg_location": str(BIN_DIR),
            "windowsfilenames": True,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            }
        }

        if format_type == "audio":
            codec = "mp3"
            q_rate = "320"
            if quality == "wav":
                codec = "wav"
            elif quality == "m4a":
                codec = "m4a"

            ydl_opts["format"] = "bestaudio/best"
            postprocessors = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": codec,
                    "preferredquality": q_rate if codec == "mp3" else None,
                },
                {"key": "FFmpegMetadata", "add_metadata": True}
            ]
            if embed_thumb and codec in ["mp3", "m4a"]:
                ydl_opts["writethumbnail"] = True
                postprocessors.append({"key": "EmbedThumbnail"})

            ydl_opts["postprocessors"] = postprocessors

        else: # Video
            if quality == "best":
                ydl_opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
            elif quality == "1080":
                ydl_opts["format"] = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
            elif quality == "720":
                ydl_opts["format"] = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best"
            elif quality == "480":
                ydl_opts["format"] = "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]/best"
            else:
                ydl_opts["format"] = "bestvideo+bestaudio/best"

            ydl_opts["merge_output_format"] = "mp4"
            postprocessors = [{"key": "FFmpegMetadata", "add_metadata": True}]
            
            if embed_subs:
                ydl_opts["writesubtitles"] = True
                ydl_opts["writeautomaticsub"] = True
                postprocessors.append({"key": "FFmpegEmbedSubtitle"})

            ydl_opts["postprocessors"] = postprocessors

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(url, download=True)
            if "entries" in meta and meta["entries"]:
                meta = meta["entries"][0]

            final_filename = ydl.prepare_filename(meta)
            if format_type == "audio":
                p = Path(final_filename)
                target_ext = f".{codec}"
                final_candidate = p.with_suffix(target_ext)
                if final_candidate.exists():
                    final_filename = str(final_candidate)

            with download_lock:
                current_download["progress"] = 100.0
                current_download["status"] = "completed"
                current_download["message"] = "Download concluído com sucesso!"
                current_download["file_path"] = final_filename

            # Salva no histórico local
            history_item = {
                "id": meta.get("id", str(time.time())),
                "title": meta.get("title", "Download"),
                "uploader": meta.get("uploader") or meta.get("channel") or "Luke-Grabber",
                "thumbnail": meta.get("thumbnail", ""),
                "format_type": format_type,
                "quality": quality,
                "file_path": final_filename,
                "timestamp": int(time.time()),
                "file_size": f"{os.path.getsize(final_filename) / (1024*1024):.1f} MB" if os.path.exists(final_filename) else "-"
            }
            save_history(history_item)

    except Exception as e:
        with download_lock:
            current_download["status"] = "error"
            current_download["error"] = str(e)
            current_download["message"] = f"Erro no download: {str(e)}"
    finally:
        with download_lock:
            current_download["is_active"] = False

@app.route("/api/download", method=["POST"])
def start_download():
    global current_download
    response.content_type = "application/json"
    data = request.json or {}

    with download_lock:
        if current_download["is_active"]:
            return json.dumps({"error": "Já existe um download em andamento"})

        current_download["is_active"] = True
        current_download["url"] = data.get("url")
        current_download["title"] = data.get("title", "Iniciando...")
        current_download["thumbnail"] = data.get("thumbnail", "")
        current_download["format_type"] = data.get("format_type", "video")
        current_download["quality"] = data.get("quality", "best")
        current_download["progress"] = 0.0
        current_download["status"] = "analyzing"
        current_download["message"] = "Conectando ao fluxo de mídia original..."
        current_download["file_path"] = ""
        current_download["error"] = None

    t = threading.Thread(target=run_download_thread, args=(data,), daemon=True)
    t.start()

    return json.dumps({"status": "started", "message": "Download iniciado"})

@app.route("/api/progress", method=["GET"])
def get_progress():
    response.content_type = "application/json"
    with download_lock:
        return json.dumps(current_download)

@app.route("/api/history", method=["GET"])
def get_history_route():
    response.content_type = "application/json"
    return json.dumps(load_history())

@app.route("/api/history/clear", method=["POST"])
def clear_history_route():
    response.content_type = "application/json"
    try:
        if HISTORY_FILE.exists():
            HISTORY_FILE.unlink()
        return json.dumps({"success": True})
    except Exception as e:
        return json.dumps({"error": str(e)})

@app.route("/api/open-folder", method=["POST"])
def open_folder():
    response.content_type = "application/json"
    data = request.json or {}
    folder_path = data.get("folder") or str(DEFAULT_DOWNLOAD_DIR)
    file_path = data.get("file_path")

    try:
        if file_path and os.path.exists(file_path):
            subprocess.Popen(f'explorer.exe /select,"{os.path.abspath(file_path)}"')
        elif os.path.exists(folder_path):
            os.startfile(folder_path)
        else:
            os.startfile(str(DEFAULT_DOWNLOAD_DIR))
        return json.dumps({"success": True})
    except Exception as e:
        return json.dumps({"error": str(e)})

@app.route("/api/open-file", method=["POST"])
def open_file():
    response.content_type = "application/json"
    data = request.json or {}
    file_path = data.get("file_path")
    if file_path and os.path.exists(file_path):
        try:
            os.startfile(file_path)
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"error": str(e)})
    return json.dumps({"error": "Arquivo não encontrado"})

# -----------------------------------------------------------------------------
# ROTAS DO SISTEMA DE ATUALIZAÇÃO AUTOMÁTICA (PADRÃO LUKE-SHARE)
# -----------------------------------------------------------------------------
@app.route("/api/updates/check", method=["GET"])
def check_updates():
    response.content_type = "application/json"
    try:
        # Consulta GitHub Releases da conta oficial
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(
            api_url,
            headers={
                "User-Agent": "Luke-Grabber",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                rel = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as he:
            if he.code == 404:
                # Repositório recém-criado sem releases publicadas ainda
                return json.dumps({
                    "available": False,
                    "current_version": APP_VERSION,
                    "latest_version": APP_VERSION,
                    "message": f"Você está na versão mais recente (v{APP_VERSION}).",
                    "engine_version": yt_dlp.version.__version__
                })
            raise

        tag_name = rel.get("tag_name", "").lstrip("v")
        curr_ver = APP_VERSION.lstrip("v")

        # Compara strings semânticas de versão
        def parse_ver(v):
            return [int(x) for x in re.findall(r"\d+", v)]

        is_newer = parse_ver(tag_name) > parse_ver(curr_ver) if tag_name else False

        download_url = ""
        assets = rel.get("assets", [])
        for asset in assets:
            aname = asset.get("name", "").lower()
            if aname.endswith(".exe") or aname.endswith(".zip"):
                download_url = asset.get("browser_download_url")
                break

        if not download_url:
            download_url = rel.get("html_url", "")

        return json.dumps({
            "available": is_newer,
            "current_version": APP_VERSION,
            "latest_version": tag_name or APP_VERSION,
            "notes": rel.get("body") or "Melhorias de desempenho e estabilidade de downloads.",
            "download_url": download_url,
            "html_url": rel.get("html_url", f"https://github.com/{GITHUB_REPO}"),
            "engine_version": yt_dlp.version.__version__
        })

    except Exception as e:
        return json.dumps({
            "available": False,
            "current_version": APP_VERSION,
            "latest_version": APP_VERSION,
            "error": str(e),
            "engine_version": yt_dlp.version.__version__
        })

def run_update_download(download_url):
    global updater_state
    try:
        with updater_lock:
            updater_state["is_updating"] = True
            updater_state["progress"] = 0.0
            updater_state["status"] = "downloading"
            updater_state["message"] = "Conectando aos servidores do GitHub..."

        filename = download_url.split("/")[-1].split("?")[0] or "Luke-Grabber_Setup.exe"
        target_path = Path.home() / "Downloads" / filename

        req = urllib.request.Request(download_url, headers={"User-Agent": "Luke-Grabber"})
        with urllib.request.urlopen(req, timeout=60) as resp, open(target_path, "wb") as f:
            total_size = int(resp.headers.get("content-length", 0))
            downloaded = 0
            while True:
                chunk = resp.read(128 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)

                pct = round((downloaded / total_size) * 100, 1) if total_size > 0 else 50.0
                dl_mb = f"{downloaded / (1024*1024):.1f} MB"
                tot_mb = f"{total_size / (1024*1024):.1f} MB" if total_size > 0 else "-"

                with updater_lock:
                    updater_state["progress"] = pct
                    updater_state["downloaded"] = dl_mb
                    updater_state["total"] = tot_mb
                    updater_state["message"] = f"Baixando: {pct}% ({dl_mb} de {tot_mb})"

        with updater_lock:
            updater_state["progress"] = 100.0
            updater_state["status"] = "ready"
            updater_state["message"] = "Download concluído! Iniciando instalador..."
            updater_state["target_file"] = str(target_path)

        # Executa o instalador baixado
        if str(target_path).lower().endswith(".exe"):
            subprocess.Popen([str(target_path)])
            time.sleep(1.5)
            # Fecha a aplicação atual para permitir a substituição
            os._exit(0)
        else:
            # Caso seja zip, abre no Windows Explorer
            os.startfile(str(target_path.parent))

    except Exception as e:
        with updater_lock:
            updater_state["status"] = "error"
            updater_state["message"] = f"Erro na atualização: {str(e)}"
    finally:
        with updater_lock:
            updater_state["is_updating"] = False

@app.route("/api/updates/start", method=["POST"])
def start_app_update():
    response.content_type = "application/json"
    data = request.json or {}
    download_url = data.get("download_url")
    if not download_url:
        return json.dumps({"error": "URL de download não informada"})

    with updater_lock:
        if updater_state["is_updating"]:
            return json.dumps({"error": "Já existe uma atualização sendo baixada"})

    t = threading.Thread(target=run_update_download, args=(download_url,), daemon=True)
    t.start()
    return json.dumps({"status": "started"})

@app.route("/api/updates/progress", method=["GET"])
def get_updater_progress():
    response.content_type = "application/json"
    with updater_lock:
        return json.dumps(updater_state)

@app.route("/api/updates/engine", method=["POST"])
def update_engine():
    """Atualiza o motor yt-dlp local para a versão mais recente."""
    response.content_type = "application/json"
    try:
        res = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
            capture_output=True,
            text=True,
            timeout=120
        )
        # Recarrega a versão
        import importlib
        importlib.reload(yt_dlp)
        return json.dumps({
            "success": True,
            "version": yt_dlp.version.__version__,
            "output": res.stdout[:200]
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

# -----------------------------------------------------------------------------
# INICIALIZAÇÃO STANDALONE
# -----------------------------------------------------------------------------
PORT = 5892
HOST = "127.0.0.1"

def start_server():
    run(app, host=HOST, port=PORT, quiet=True)

if __name__ == "__main__":
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    app_url = f"http://{HOST}:{PORT}"
    icon_path = str(FRONTEND_DIR / "app-icon.png")

    try:
        import webview
        window = webview.create_window(
            title="Luke-Grabber — Extrator Multimídia Universal",
            url=app_url,
            width=1120,
            height=760,
            min_size=(920, 620),
            background_color="#04121e"
        )
        webview.start(debug=False)
        sys.exit(0)
    except Exception as e:
        print(f"pywebview não inicializou ({e}). Abrindo em modo App nativo do Windows...")
        edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        if not os.path.exists(edge_path):
            edge_path = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

        if os.path.exists(edge_path):
            subprocess.Popen([edge_path, f"--app={app_url}", "--window-size=1120,760"])
        else:
            import webbrowser
            webbrowser.open(app_url)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
