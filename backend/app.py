# =============================================
# 📝 INFORMAÇÕES SOBRE O DESENVOLVIMENTO DO CÓDIGO
# Data de início........: 17/06/2025
# Última atualização....: 03/07/2025
# Tempo dedicado........: 4h30 + otimizações
# Descrição.............: API Flask para upload de imagens
#                         otimizada para Fly.io
#                         • Upload direto da RAM → Google Drive
#                         • Sem escrita em disco
#                         • Uploads paralelos
#                         • Respostas JSON compactadas
# =============================================

import os
import json
import uuid
import io
import mimetypes
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import (
    Flask,
    request,
    jsonify,
    send_from_directory,
    render_template,
    url_for,
    Response,
    abort,
)
from flask_compress import Compress              # pip install flask-compress
from werkzeug.utils import secure_filename

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

# ---------- 🔧 Configurações ----------
SCOPES     = ["https://www.googleapis.com/auth/drive.file"]
FOLDER_ID  = "1ZszcUwO1IXnf_pZpOS4X0YWi2iQ2DaJz"

app = Flask(__name__)
Compress(app)                                    # gzip nas respostas

app.config["ALLOWED_EXTENSIONS"]  = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"]       = "uploads"    # ainda usado p/ send_from_directory
app.config["MAX_CONTENT_LENGTH"]  = 10 * 1024 * 1024   # 10 MB por imagem

# Pasta local só para downloads proxyados/galeria (não mais para upload)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


# ---------- 🔐 Credenciais Google ----------
def get_credentials():
    """Obtém credenciais do Google a partir de variável de ambiente ou arquivo."""
    json_str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if json_str:
        info = json.loads(json_str)
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)

    json_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.path.join(os.getcwd(), "service-account.json")
    if not os.path.isfile(json_path):
        raise FileNotFoundError(
            "Credenciais não encontradas. Defina GOOGLE_SERVICE_ACCOUNT_JSON "
            "ou coloque service-account.json no diretório raiz."
        )
    return service_account.Credentials.from_service_account_file(json_path, scopes=SCOPES)


def build_drive_service():
    """Cria um cliente Google Drive isolado (thread‑safe)."""
    creds = get_credentials()
    return build("drive", "v3", credentials=creds, cache_discovery=False)


# ---------- 🛠️ Utilidades ----------
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


def _upload_single(file_name: str, mime_type: str, data: bytes) -> dict:
    """
    Função isolada para subir UMA imagem.
    É executada em threads paralelas.
    """
    drive = build_drive_service()                # cada thread cria o seu
    buffer = io.BytesIO(data)
    buffer.seek(0)

    unique_name = secure_filename(f"{uuid.uuid4().hex}.{file_name.rsplit('.', 1)[1].lower()}")
    metadata = {"name": unique_name, "parents": [FOLDER_ID]}
    media    = MediaIoBaseUpload(buffer, mimetype=mime_type or "application/octet-stream",
                                 resumable=False, chunksize=256 * 1024)

    try:
        drive.files().create(body=metadata, media_body=media, fields="id").execute()
        return {"arquivo": unique_name, "status": "Upload ok"}
    except Exception as e:
        app.logger.exception("Falha no Drive")
        return {"arquivo": file_name, "status": f"Erro: {e}"}


# ---------- 🌐 Rotas ----------
@app.route("/")
def home():
    return "API de upload otimizada! Use /upload para enviar imagens."


# 📤 Novo endpoint de upload
@app.route("/upload", methods=["POST"])
def upload():
    if "imagem" not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado."}), 400

    imagens = [im for im in request.files.getlist("imagem") if im.filename]
    if not imagens:
        return jsonify({"erro": "Nenhum arquivo selecionado."}), 400

    # Pré‑validação + leitura para RAM
    files_data = []
    for imagem in imagens:
        if not allowed_file(imagem.filename):
            files_data.append((imagem.filename, imagem.mimetype, None, "Extensão não permitida"))
            continue
        try:
            data = imagem.read()                 # bytes em memória
            files_data.append((imagem.filename, imagem.mimetype, data, None))
        except Exception as e:
            files_data.append((imagem.filename, imagem.mimetype, None, f"Falha ao ler: {e}"))

    resultados = []

    # Uploads paralelos (somente os arquivos válidos com data != None)
    valid_files = [f for f in files_data if f[2] is not None]
    if valid_files:
        max_threads = min(4, len(valid_files))
        with ThreadPoolExecutor(max_workers=max_threads) as pool:
            futures = [pool.submit(_upload_single, name, mime, data) for name, mime, data, _ in valid_files]
            for fut in as_completed(futures):
                resultados.append(fut.result())

    # Anexar erros de leitura/extensão
    resultados.extend(
        {"arquivo": name, "status": status or "Erro inesperado"} 
        for name, _, _, status in files_data if status
    )

    return jsonify({"resultados": resultados}), 200


# 📥 Proxy de download (evita CORS)
@app.route("/download/<file_id>")
def download_file(file_id):
    try:
        drive = build_drive_service()
        request_drive = drive.files().get_media(fileId=file_id)

        def generate():
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request_drive, chunksize=256 * 1024)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                fh.seek(0)
                data = fh.read()
                fh.truncate(0)
                fh.seek(0)
                if data:
                    yield data

        mime = mimetypes.guess_type(file_id)[0] or "application/octet-stream"
        headers = {"Content-Disposition": f'attachment; filename="{file_id}"'}
        return Response(generate(), mimetype=mime, headers=headers)

    except Exception as e:
        app.logger.exception("Falha no proxy de download")
        abort(500, description=str(e))


# Páginas estáticas
@app.route("/enviar")
def upload_page():
    return render_template("index.html")


@app.route("/galeria")
def galeria():
    return render_template("galeria.html")


@app.route("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# 🔎 API listagem de fotos
@app.route("/api/fotos")
def api_fotos():
    try:
        drive = build_drive_service()
        res = (
            drive.files()
            .list(
                q=f"'{FOLDER_ID}' in parents and mimeType contains 'image/' and trashed=false",
                fields="files(id,name,webContentLink,thumbnailLink)",
            )
            .execute()
        )

        imagens = []
        for f in res.get("files", []):
            visualizar = f.get("thumbnailLink") or f"https://drive.google.com/uc?export=view&id={f['id']}"
            download   = url_for("download_file", file_id=f["id"], _external=False)
            imagens.append({
                "nome": f["name"],
                "id": f["id"],
                "visualizar": visualizar,
                "download": download,
            })

        return jsonify(imagens)

    except Exception as e:
        app.logger.exception("Falha em /api/fotos")
        return jsonify({"erro": str(e)}), 500


# ---------- 🚀 Execução local ----------
if __name__ == "__main__":
    # Em produção (Fly.io) use:
    #   gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=False)
