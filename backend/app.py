# =============================================
# 📝 INFORMAÇÕES SOBRE O DESENVOLVIMENTO DO CÓDIGO
# Data de início: 17/06/2025
# Tempo dedicado: 2h30
# =============================================

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
from flask import request, Flask, jsonify, send_from_directory,render_template
import uuid
from werkzeug.utils import secure_filename
from flask import url_for

# Configurações - ajuste aqui:
SERVICE_ACCOUNT_FILE = '/etc/secrets/credentials.json'
SCOPES = ['https://www.googleapis.com/auth/drive.file']
FOLDER_ID = '1ZszcUwO1IXnf_pZpOS4X0YWi2iQ2DaJz'

app = Flask(__name__)

app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = 'uploads'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def home():
    return "API de upload está funcionando! Use /upload para enviar imagens."

@app.route('/upload', methods=['POST'])
def upload():
    if 'imagem' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400

    imagens = request.files.getlist('imagem')
    if not imagens or all(imagem.filename == '' for imagem in imagens):
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)
    resultados = []
    for imagem in imagens:
        if imagem.filename == '':
            resultados.append({'filename': None, 'status': 'Arquivo vazio ignorado'})
            continue

        if not allowed_file(imagem.filename):
            resultados.append({'filename': imagem.filename, 'status': 'Extensão não permitida'})
            continue
        ext = imagem.filename.rsplit('.', 1)[1].lower()
        unique_name = secure_filename(f"{uuid.uuid4().hex}.{ext}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        imagem.save(filepath)

        file_metadata = {
            'name': unique_name,
            'parents': [FOLDER_ID]
        }

        try:
            media = MediaFileUpload(filepath, resumable=True)
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            os.remove(filepath)
            resultados.append({'filename': unique_name, 'status': 'Upload realizado com sucesso'})
        except Exception as e:
            resultados.append({'filename': imagem.filename, 'status': f'Erro: {str(e)}'})

    return jsonify({'resultados': resultados}), 200


@app.route('/enviar')        
def upload_page():
    return render_template('index.html')

@app.route('/galeria')
def galeria():
    return render_template('galeria.html')



@app.route('/uploads/<path:filename>')
def uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/api/fotos')
def api_fotos():
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)

        res = service.files().list(
            q=f"'{FOLDER_ID}' in parents and mimeType contains 'image/' and trashed=false",
            fields="files(id,name,webContentLink)"
        ).execute()

        imagens = []
        for f in res.get('files', []):
            nome = f['name']
            #visualizar = f"https://drive.google.com/uc?export=view&id={f['id']}"

            visualizar = url_for('uploads', filename=nome, _external=True)

            download = f.get('webContentLink') or \
                       f"https://drive.google.com/uc?export=download&id={f['id']}"
            print(visualizar)
            imagens.append({
                'nome': nome,
                'id': f['id'],
                'visualizar': visualizar,
                'download': download
            })

        return jsonify(imagens)

    except Exception as e:
        app.logger.exception('Falha em /api/fotos')
        return jsonify({'erro': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
