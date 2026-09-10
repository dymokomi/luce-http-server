'use strict';

// Render server data as text, so the examples work with arbitrary user input.
function form(id, action) {
  const element = document.getElementById(id);
  const output = document.getElementById(`${id}-result`);
  element.addEventListener('submit', async event => {
    event.preventDefault();
    const button = element.querySelector('button');
    button.disabled = true;
    output.textContent = 'Working…';
    try { await action(new FormData(element), output); }
    catch (error) { output.textContent = error.message; }
    finally { button.disabled = false; }
  });
}

form('greeting', async (data, output) => {
  const response = await fetch(`/api/greet?${new URLSearchParams({name: data.get('name')})}`);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
  output.textContent = result.message;
});

form('upload', async (data, output) => {
  const file = data.get('file');
  const path = `/api/files/${encodeURIComponent(file.name)}`;
  const response = await fetch(path, {method: 'PUT', body: file});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
  const link = document.createElement('a');
  link.href = path;
  link.download = file.name;
  link.textContent = `Download ${file.name} (${file.size} bytes)`;
  output.replaceChildren(link);
});

form('message', (data, output) => new Promise((resolve, reject) => {
  const socket = new WebSocket(`${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws/echo`);
  const timer = setTimeout(() => finish(new Error('Message timed out')), 5000);
  let finished = false;
  function finish(error) {
    if (finished) return;
    finished = true;
    clearTimeout(timer);
    socket.close();
    if (error) reject(error); else resolve();
  }
  socket.onopen = () => socket.send(data.get('text'));
  socket.onmessage = event => { output.textContent = event.data; finish(); };
  socket.onerror = () => finish(new Error('WebSocket connection failed'));
  socket.onclose = () => finish(new Error('Connection closed before a reply'));
}));
