const DATA_URL = 'catalog.json';
const FALLBACK_URL = 'https://raw.githubusercontent.com/kaykewf13/animeout/main/web/catalog.json';

const state = {
  items: [],
  filtered: [],
};

function showSkeleton() {
  const grid = document.getElementById('catalogGrid');
  grid.innerHTML = '';

  for (let i = 0; i < 12; i++) {
    const el = document.createElement('div');
    el.className = 'card';
    el.innerHTML = `
      <div class="poster"></div>
      <div class="title">Carregando...</div>
    `;
    grid.appendChild(el);
  }
}

async function fetchCatalog() {
  try {
    const res = await fetch(DATA_URL, { cache: 'no-store' });
    const data = await res.json();

    if (!data || data.length === 0) throw new Error('vazio');

    return data;
  } catch (e) {
    console.log('Fallback ativado');
    const res = await fetch(FALLBACK_URL);
    return await res.json();
  }
}

async function load() {
  showSkeleton();

  try {
    const data = await fetchCatalog();

    if (!data || data.length === 0) {
      showError('⚠️ Catálogo vazio (pipeline ainda rodando)');
      return;
    }

    state.items = data.sort((a, b) => (b.score || 0) - (a.score || 0));

    render();
    renderHero();

  } catch (e) {
    showError('❌ Erro ao carregar catálogo');
  }
}

function showError(msg) {
  document.getElementById('catalogGrid').innerHTML = `<p>${msg}</p>`;
}

function render() {
  const grid = document.getElementById('catalogGrid');
  grid.innerHTML = '';

  state.items.forEach(item => {
    grid.appendChild(createCard(item));
  });
}

function renderHero() {
  const item = state.items[0];
  if (!item) return;

  document.getElementById('heroTitle').innerText = item.title;
  document.getElementById('heroSubtitle').innerText = item.description || '';

  const hero = document.getElementById('hero');
  if (item.logo) {
    hero.style.backgroundImage = `
      linear-gradient(90deg, rgba(0,0,0,.9), rgba(0,0,0,.6)),
      url('${item.logo}')
    `;
  }

  document.getElementById('heroPlay').onclick = () => play(item);
}

function createCard(item) {
  const el = document.createElement('div');
  el.className = 'card';

  el.innerHTML = `
    <div class="poster" style="background-image:url('${item.logo || ''}')"></div>
    <div class="title">${item.title}</div>
  `;

  el.onclick = () => play(item);

  return el;
}

function play(item) {
  const video = document.getElementById('videoPlayer');

  if (window.Hls && item.url.includes('.m3u8')) {
    const hls = new Hls();
    hls.loadSource(item.url);
    hls.attachMedia(video);
  } else {
    video.src = item.url;
  }

  video.play().catch(() => {});
}

load();