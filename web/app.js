const DATA_URL = 'catalog.json';

const state = { items: [], filtered: [], group: 'Todos', q: '', category: 'Todos', featured: [], pendingAdult: null };

async function load(){
  const res = await fetch(DATA_URL);
  const data = await res.json();
  state.items = data;
  buildCategories();
  pickFeatured();
  renderRails();
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
  state.featured.forEach(i=> rail.appendChild(card(i)));
}

function renderRails(){
  const anime = state.items.filter(i=>i.isAnime);
  const adult = state.items.filter(i=>i.isAdult);

  document.getElementById('animeBadge').textContent = anime.length;
  document.getElementById('adultBadge').textContent = adult.length;

  anime.slice(0,20).forEach(i=> document.getElementById('animeRail').appendChild(card(i)));
  adult.slice(0,20).forEach(i=> document.getElementById('adultRail').appendChild(card(i)));
}

function card(item){
  const el = document.createElement('div');
  el.className = 'card';

  const img = item.logo || '';
  const rating = item.rating ? `⭐ ${item.rating}` : '';

  el.innerHTML = `
    <div class="poster" style="background-image:url('${img}')"></div>
    <div class="meta">${item.groupTitle}</div>
    <div class="title">${item.title}</div>
    <div class="rating">${rating}</div>
  `;

  el.onclick = ()=> handlePlay(item);
  return el;
}

function handlePlay(item){
  if(item.isAdult){
    state.pendingAdult = item;
    document.getElementById('adultModal').classList.remove('hidden');
    return;
  }
  play(item);
}

function play(item){
  const video = document.getElementById('videoPlayer');
  document.getElementById('nowTitle').textContent = item.title;
  document.getElementById('nowMeta').textContent = item.groupTitle;
  document.getElementById('nowDescription').textContent = item.description || '';
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
  state.filtered.forEach(i=> grid.appendChild(card(i)));
}

function setup(){
  document.getElementById('searchInput').oninput = e=>{ state.q = e.target.value; applyFilters(); };
  document.getElementById('categorySelect').onchange = e=>{ state.category = e.target.value; applyFilters(); };

  document.querySelectorAll('.tab').forEach(btn=>{
    btn.onclick = ()=>{
      if(btn.dataset.filter === 'anime'){
        state.filtered = state.items.filter(i=>i.isAnime);
        render(); return;
      }
      if(btn.dataset.filter === 'adult'){
        document.getElementById('adultRailBlock').classList.remove('hidden');
        return;
      }
      document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      state.group = btn.dataset.group;
      applyFilters();
    };
  });

  document.getElementById('confirmAdult').onclick = ()=>{
    play(state.pendingAdult);
    document.getElementById('adultModal').classList.add('hidden');
  };

  document.getElementById('cancelAdult').onclick = ()=>{
    document.getElementById('adultModal').classList.add('hidden');
  };
}

setup();
load();
