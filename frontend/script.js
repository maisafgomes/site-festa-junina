document.getElementById("uploadForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const formData = new FormData(e.target);

  const response = await fetch("http://localhost:8080/upload", {
    method: "POST",
    body: formData,
  });

  if (response.ok) {
    alert("Foto enviada!");
    await carregarFotos(); // aqui atualiza a galeria
  } else {
    alert("Erro ao enviar a foto.");
  }
});


const API_URL = "http://localhost:8080";

async function carregarFotos() {
  const resposta = await fetch(`${API_URL}/fotos`);
  const fotos = await resposta.json();

  const galeria = document.getElementById("gallery");
  galeria.innerHTML = "";

  fotos.forEach((url) => {
    const col = document.createElement("div");
    col.className = "col";

    col.innerHTML = `
            <div class="card shadow-sm text-center">
              <img src="${API_URL}${url}" class="card-img-top" style="object-fit: cover; height: 225px;">
              <div class="card-body">
                <button class="btn btn-custom-download">Baixar</button>
                <div class="text-muted mt-2" style="font-size: 0.875rem;">Agora mesmo</div>
              </div>
            </div>
          `;

    const btn = col.querySelector(".btn-custom-download");
    btn.addEventListener("click", () => {
      downloadImage(`${API_URL}${url}`);
    });

    galeria.appendChild(col);
  });
}

carregarFotos();
function downloadImage(url) {
  fetch(url)
    .then((response) => response.blob())
    .then((blob) => {
      const urlBlob = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = urlBlob;

      // Extrair nome do arquivo da URL ou definir um nome padrão
      const filename = url.split("/").pop() || "download.jpg";
      a.download = filename;

      document.body.appendChild(a);
      a.click();

      window.URL.revokeObjectURL(urlBlob);
      a.remove();
    })
    .catch(() => alert("Erro ao baixar o arquivo."));
}
