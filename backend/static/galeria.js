async function carregarFotos() {
  const resp  = await fetch("/api/fotos");
  const fotos = await resp.json();   
  const galeria = document.getElementById("gallery");
  galeria.innerHTML = "";

  fotos.forEach(f => {
    const col = document.createElement("div");
    col.className = "col";

    col.innerHTML = `
      <div class="card shadow-sm text-center">
        <img src="${f.visualizar}" class="card-img-top" style="object-fit:cover;height:225px" alt="${f.nome}">
        <div class="card-body">
          <button class="btn btn-primary btn-sm">Baixar</button>
        </div>
      </div>
    `;

    col.querySelector("button").addEventListener("click", () => baixar(f.download, f.nome));
    galeria.appendChild(col);
  });
}

function baixar(url, nome) {
  fetch(url)
    .then(r => r.blob())
    .then(b => {
      const blobUrl = URL.createObjectURL(b);
      const a = Object.assign(document.createElement("a"), { href: blobUrl, download: nome });
      document.body.appendChild(a).click();
      a.remove();
      URL.revokeObjectURL(blobUrl);
    })
    .catch(() => alert("Erro ao baixar."));
}

carregarFotos();
