# =============================================
# 📝 INFORMAÇÕES SOBRE O DESENVOLVIMENTO DO CÓDIGO
# Data de início: 17/06/2025
# Tempo dedicado: 4h30
# =============================================

import os
import json
import uuid
import io
import mimetypes
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
from werkzeug.utils import secure_filename
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
FOLDER_ID = "1ZszcUwO1IXnf_pZpOS4X0YWi2iQ2DaJz"

app = Flask(__name__)

app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = "uploads"

# Garante que a pasta de uploads exista (tanto local quanto no volume Fly.io)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


def allowed_file(filename: str) -> bool:
    """Verifica se a extensão do arquivo é permitida."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


def get_credentials():
    """Obtém credenciais do Google a partir de variável de ambiente ou arquivo."""

    json_str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if json_str:
        info = json.loads(json_str)
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)

    json_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.path.join(os.getcwd(), "service-account.json")
    if not os.path.isfile(json_path):
        raise FileNotFoundError(
            "Credenciais não encontradas. Defina GOOGLE_SERVICE_ACCOUNT_JSON ou coloque service-account.json no diretório raiz."
        )

    return service_account.Credentials.from_service_account_file(json_path, scopes=SCOPES)


def get_drive_service():
    """Constrói e devolve o cliente do Google Drive."""
    creds = get_credentials()
    return build("drive", "v3", credentials=creds, cache_discovery=False)


@app.route("/")
def home():
    return "API de upload está funcionando! Use /upload para enviar imagens."


# ------------------------------
# 📤 Upload para o Google Drive
# ------------------------------
@app.route("/upload", methods=["POST"])
def upload():
    if "imagem" not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado."}), 400

    imagens = request.files.getlist("imagem")
    if not imagens or all(im.filename == "" for im in imagens):
        return jsonify({"erro": "Nenhum arquivo selecionado."}), 400

    try:
        drive = get_drive_service()
    except Exception as e:
        app.logger.exception("Falha ao autenticar Google API")
        return jsonify({"erro": f"Falha na autenticação: {e}"}), 500

    resultados = []
    for imagem in imagens:
        if imagem.filename == "":
            resultados.append({"arquivo": None, "status": "Arquivo vazio ignorado"})
            continue

        if not allowed_file(imagem.filename):
            resultados.append({"arquivo": imagem.filename, "status": "Extensão não permitida"})
            continue

        ext = imagem.filename.rsplit(".", 1)[1].lower()
        unique_name = secure_filename(f"{uuid.uuid4().hex}.{ext}")
        local_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
        imagem.save(local_path)

        metadata = {"name": unique_name, "parents": [FOLDER_ID]}
        media = MediaFileUpload(local_path, resumable=False)

        try:
            drive.files().create(body=metadata, media_body=media, fields="id").execute()
            resultados.append({"arquivo": unique_name, "status": "Upload realizado com sucesso"})
        except Exception as e:
            app.logger.exception("Falha ao enviar para o Drive")
            resultados.append({"arquivo": imagem.filename, "status": f"Erro: {e}"})

    return jsonify({"resultados": resultados}), 200


# ------------------------------
# 📥 Proxy de download (evita CORS)
# ------------------------------
@app.route("/download/<file_id>")
def download_file(file_id):
    """Faz streaming do arquivo do Google Drive para o cliente mantendo mesma origem."""
    try:
        drive = get_drive_service()
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


# ------------------------------
# 🌐 Páginas e arquivos estáticos
# ------------------------------
@app.route("/enviar")
def upload_page():
    return render_template("index.html")


@app.route("/galeria")
def galeria():
    return render_template("galeria.html")


@app.route("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# ------------------------------
# 🖼️ API listagem de fotos
# ------------------------------
@app.route("/api/fotos")
def api_fotos():
    try:
        drive = get_drive_service()

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
            nome = f["name"]
            visualizar = f.get("thumbnailLink") or f"https://drive.google.com/uc?export=view&id={f['id']}"
            # download via proxy para evitar CORS
            download = url_for("download_file", file_id=f["id"], _external=False)
            imagens.append({
                "nome": nome,
                "id": f["id"],
                "visualizar": visualizar,
                "download": download,
            })

        return jsonify(imagens)

    except Exception as e:
        app.logger.exception("Falha em /api/fotos")
        return jsonify({"erro": str(e)}), 500


# ------------------------------
# 🚀 Execução
# ------------------------------
if __name__ == "__main__":
    # Ajuste host/port conforme necessidade do PaaS (ex.: Render, Fly.io)
    app.run(host="0.0.0.0", port=8000, debug=True)
