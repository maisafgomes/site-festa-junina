import os
from flask import Flask, jsonify, send_from_directory

app = Flask(__name__)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}


#todos os formatos permitidos
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/upload', methods=['POST'])
def upload():
    if 'imagem' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400

    imagens = request.files.getlist('imagem')
    if not imagens or all(imagem.filename == '' for imagem in imagens):
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400

    resultados = []
    for imagem in imagens:
        if imagem.filename == '':
            resultados.append({'filename': None, 'status': 'Arquivo vazio ignorado'})
            continue

        if not allowed_file(imagem.filename):
            resultados.append({'filename': imagem.filename, 'status': 'Extensão não permitida'})
            continue

        ext = imagem.filename.rsplit('.', 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        filename = secure_filename(unique_name)

        caminho = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            imagem.save(caminho)
            resultados.append({'filename': filename, 'status': 'Upload realizado com sucesso'})
        except Exception as e:
            resultados.append({'filename': imagem.filename, 'status': f'Erro ao salvar arquivo: {str(e)}'})

    return jsonify({'resultados': resultados}), 200


@app.route('/api/fotos', methods=['GET'])
def api_fotos():
    pasta = app.config['UPLOAD_FOLDER']
    if not os.path.exists(pasta):
        return jsonify([])

    arquivos = os.listdir(pasta)
    imagens = [f for f in arquivos if f.lower().endswith(tuple(app.config['ALLOWED_EXTENSIONS']))]
    return jsonify(imagens)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)

