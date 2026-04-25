const DATA_URL = 'catalog.json';

const state = {
  items: [],
  filtered: [],
  group: 'Todos',
  q: '',
  category: 'Todos',
  featured: [],
  pendingAdult: null,
  currentItem: null,
};

async function load() {
  try {
    const res = await fetch(DATA_URL, { cache: 'no-store' });
    const data = await res.json();

    state.items = data.sort((a, b) => (b.score || 0) - (a.score || 0));

    buildCategories();
    pickFeatured();
    renderStats();
    renderRails();
    applyFilters();
  } catch (e) {
    document.getElementById('catalogGrid').innerHTML =
      '<p>Não foi possível carregar o catálogo.</p>';
  }
}

function byScore(items) {
  return [...items].sort((a, b) => (b.score || 0) - (a.score || 0));
}

function buildCategories() {
  const select = document.getElementById('categorySelect');
  const cats = [...new Set(state.items.map(i => i.category).filter(Boolean))].sort();

  cats.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c;
    opt.textContent = c;
    select.appendChild(opt);
  });
}

function pickFeatured() {
  state.featured = byScore(state.items).slice(0, 12);
  renderRail('featuredRail', state.featured);

  document.getElementById('featuredBadge').textContent =
    state.featured.length + ' itens';

  setHero(state.featured[0]);
}

function setHero(item) {
  if (!