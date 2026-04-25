const DATA_URL = 'catalog.json';

const state = { items: [], filtered: [], group: 'Todos', q: '', category: 'Todos', featured: [] };

async function load(){
  const res = await fetch(DATA_URL);
  const data = await res.json();
  state.items = data;
  buildCategories();
  pickFeatured();
  applyFilters();
}

function buildCategories(){
  const select = document.getElementById('categorySelect');
  const cats = [...new Set(state.items.map(i=>i.category))].sort();
  cats.forEach(c=>{
    const opt = document.createElement('option');
    opt.value = c; opt.textContent = c;
    select.appendChild(opt);
  });
}

function pickFeatured(){
  state.featured = state.items.sort(()=>0.5 - Math.random()).slice(0, 10);
  renderFeatured();
  setHero(state.featured[0]);
}

function setHero(item){
  if(!item) return;
  document.getElementById('heroTitle').textContent = item.title;
  document.getElementById('heroGroup').textContent = item.groupTitle;
}

function renderFeatured(){
  const rail = document.getElementById('featuredRail');
  rail.innerHTML = '';
  state.featured.forEach(i=>{
    const el = document.createElement('div');
    el.className = 'card';
    el.innerHTML = `<div class="meta">${i.groupTitle}</div><div>${i.title}</div>`;
    el.onclick = ()=>play(i);
    rail.appendChild(el);
  });
}

function applyFilters(){
  const q = state.q.toLowerCase();
  state.filtered = state.items.filter(i=>{
    const g = state.group === 'Todos' || i.group === state.group;
    const c = state.category === 'Todos' || i.category === state.category;
    const m = !q || (i.title + i.category + i.group).toLowerCase().includes(q);
    return g && c && m;
  });
  render();
}

function render(){
  const grid = document.getElementById('catalogGrid');
  grid.innerHTML = '';
  document.getElementById('countBadge').textContent = state.filtered.length + ' itens';

  state.filtered.forEach(item=>{
    const el = document.createElement('div');
    el.className = 'card';
    el.innerHTML = `<div class="meta">${item.groupTitle}</div><div>${item.title}</div>`;
    el.onclick = ()=>play(item);
    grid.appendChild(el);
  });
}

function play(item){
  const video = document.getElementById('videoPlayer');
  document.getElementById('nowTitle').textContent = item.title;
  document.getElementById('nowMeta').textContent = item.groupTitle;
  document.getElementById('nowSource').textContent = item.source;

  if(window.Hls && item.url.endsWith('.m3u8')){
    if(window.hls) window.hls.destroy();
    const hls = new Hls();
    window.hls = hls;
    hls.loadSource(item.url);
    hls.attachMedia(video);
  } else {
    video.src = item.url;
  }
  video.play().catch(()=>{});
}

function setup(){
  document.getElementById('searchInput').addEventListener('input', e=>{
    state.q = e.target.value;
    applyFilters();
  });

  document.getElementById('categorySelect').addEventListener('change', e=>{
    state.category = e.target.value;
    applyFilters();
  });

  document.querySelectorAll('.tab').forEach(btn=>{
    btn.onclick = ()=>{
      document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      state.group = btn.dataset.group;
      applyFilters();
    };
  });
}

setup();
load();
