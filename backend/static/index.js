document.getElementById("uploadForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const formData = new FormData(e.target);

  const resp = await fetch("/upload", { method: "POST", body: formData });
  if (resp.ok) {
    alert("Foto(s) enviada(s) com sucesso!");
    window.location = "/galeria";          // vai direto para a galeria
  } else {
    alert("Erro ao enviar.");
  }
});

