// gallery.js – versão compatível com o proxy /download/<id>
// ---------------------------------------------------------
// • Usa o endpoint /api/fotos que devolve: nome, visualizar, id, download
// • Botão "Baixar" dispara download no MESMO domínio (CORS‑safe)
// ---------------------------------------------------------

async function carregarFotos() {
  try {
    const resp = await fetch("/api/fotos");
    if (!resp.ok) {
      throw new Error(`Erro ${resp.status}: não foi possível carregar a galeria`);
    }

    const fotos = await resp.json();
    const galeria = document.getElementById("gallery");
    galeria.innerHTML = "";

    fotos.forEach((foto) => {
      // Cria a coluna responsiva (Bootstrap)
      const col = document.createElement("div");
      col.className = "col";

      // Monta o card da imagem
      col.innerHTML = `
        <div class="card shadow-sm text-center">
          <img src="${foto.visualizar}" class="card-img-top" style="object-fit: cover; height: 225px;" alt="${foto.nome}">
          <div class="card-body">
            <button class="btn btn-custom-download" data-url="${foto.download}" data-nome="${foto.nome}">
              Baixar
            </button>
          </div>
        </div>`;

      galeria.appendChild(col);
    });

    // Adiciona os listeners após inserir os cards no DOM
    galeria.querySelectorAll(".btn-custom-download").forEach((btn) => {
      btn.addEventListener("click", () => {
        const url = btn.dataset.url;
        const nome = btn.dataset.nome; // usa nome original p/ arquivo
        downloadImage(url, nome);
      });
    });
  } catch (err) {
    console.error(err);
    alert("Falha ao carregar a galeria. Tente novamente mais tarde.");
  }
}

async function downloadImage(url, filename = "imagem.jpg") {
  try {
    const resp = await fetch(url);
    if (!resp.ok) {
      throw new Error(`Erro ${resp.status}: download falhou`);
    }

    const blob = await resp.blob();
    const blobUrl = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();

    URL.revokeObjectURL(blobUrl);
  } catch (err) {
    console.error(err);
    alert("Erro ao baixar o arquivo.");
  }
}

// Carrega galeria assim que o DOM estiver pronto
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", carregarFotos);
} else {
  carregarFotos();
}
