document.getElementById('uploadForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const formData = new FormData(e.target);
  await fetch('http://localhost:5000/upload', {
    method: 'POST',
    body: formData
  });
  alert('Foto enviada!');
});