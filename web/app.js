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

async function load(){
  try{
    const res = await fetch(DATA_URL, { cache: 'no-store' });
    const data = await res.json();
    state.items = data.sort((a,b)=>(b.score || 0) - (a.score || 0));
    buildCategories();
    pickFeatured();
    renderStats();
    renderRails();
    applyFilters();
  }catch(e){
    document.getElementById('catalogGrid').innerHTML = '<p>Não foi possível carregar o catálogo.</p>';
  }
}

function byScore(items){
  return [...items].sort((a,b)=>(b.score || 0) - (a.score || 0));
}

function buildCategories(){
  const select = document.getElementById('categorySelect');
  const cats = [...new Set(state.items.map(i=>i.category).filter(Boolean))].sort();
  cats.forEach(c=>{
    const opt = document.createElement('option');
    opt.value = c;
    opt.textContent = c;
    select.appendChild(opt);
  });
}

function pickFeatured(){
  state.featured = byScore(state.items).slice(0, 12);
  renderRail('featuredRail', state.featured);
  document.getElementById('featuredBadge').textContent = state.featured.length + ' itens';
  setHero(state.featured[0]);
}

function setHero(item){
  if(!item) return;
  document.getElementById('heroTitle').textContent = item.title;
  document.getElementById('heroGroup').textContent = item.groupTitle;
  document.getElementById('heroSubtitle').textContent = item.description || 'Conteúdo selecionado automaticamente pelo ranking do catálogo.';
  const hero = document.getElementById('hero');
  if(item.logo){
    hero.style.backgroundImage = `linear-gradient(90deg, rgba(11,12,16,.96), rgba(11,12,16,.72), rgba(11,12,16,.96)), url('${item.logo}')`;
  }
  const btn = document.getElementById('heroPlay');
  if(btn) btn.onclick = () => handlePlay(item);
}

function renderStats(){
  const stats = document.getElementById('stats');
  const total = state.items.length;
  const canais = state.items.filter(i=>i.group === 'Canais').length;
  const series = state.items.filter(i=>i.group === 'Series').length;
  const filmes = state.items.filter(i=>i.group === 'Filmes').length;
  const anime = state.items.filter(i=>i.isAnime).length;
  stats.innerHTML = `
    <div class="stat"><b>${total}</b><span>Total</span></div>
    <div class="stat"><b>${canais}</b><span>Canais</span></div>
    <div class="stat"><b>${series}</b><span>Séries</span></div>
    <div class="stat"><b>${filmes}</b><span>Filmes</span></div>
    <div class="stat"><b>${anime}</b><span>Animes</span></div>
  `;
}

function renderRails(){
  const anime = byScore(state.items.filter(i=>i.isAnime));
  const adult = byScore(state.items.filter(i=>i.isAdult));
  const top = byScore(state.items).slice(0, 20);

  document.getElementById('animeBadge').textContent = anime.length + ' itens';
  document.getElementById('adultBadge').textContent = adult.length + ' itens';

  renderRail('animeRail', anime.slice(0, 30));
  renderRail('adultRail', adult.slice(0, 30));

  const featured = document.getElementById('featuredRail');
  featured.innerHTML = '';
  top.forEach(i=>featured.appendChild(card(i)));
}

function renderRail(id, items){
  const rail = document.getElementById(id);
  if(!rail) return;
  rail.innerHTML = '';
  items.forEach(i=>rail.appendChild(card(i)));
}

function card(item){
  const el = document.createElement('div');
  el.className = 'card';
  const img = item.logo || '';
  const rating = item.rating ? `⭐ ${item.rating}` : '';
  const score = item.score ? `Q${item.score}` : '';
  const adult = item.isAdult ? '<span class="badge adultBadge">18+</span>' : '';
  const anime = item.isAnime ? '<span class="badge">Anime</span>' : '';

  el.innerHTML = `
    <div class="poster" style="background-image:${img ? `url('${img}')` : 'none'}">
      ${!img ? `<span class="posterFallback">${escapeHtml(item.title).slice(0,2)}</span>` : ''}
      <div class="badges">${anime}${adult}</div>
    </div>
    <div class="meta">${escapeHtml(item.groupTitle || '')}</div>
    <div class="title">${escapeHtml(item.title || 'Sem título')}</div>
    <div class="rating"><span>${rating}</span><span>${score}</span></div>
  `;

  el.onclick = ()=> handlePlay(item);
  return el;
}

function escapeHtml(value){
  return String(value || '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}

function handlePlay(item){
  if(item.isAdult){
    state.pendingAdult = item;
    document.getElementById('adultModal').classList.remove('hidden');
    return;
  }
  play(item);
}

function clearTracks(video){
  [...video.querySelectorAll('track')].forEach(t=>t.remove());
}

function addSubtitle(video, subtitleUrl){
  if(!subtitleUrl) return;
  const track = document.createElement('track');
  track.kind = 'subtitles';
  track.label = 'Português';
  track.srclang = 'pt';
  track.src = subtitleUrl;
  track.default = true;
  video.appendChild(track);
}

function play(item){
  state.currentItem = item;
  setHero(item);
  const video = document.getElementById('videoPlayer');
  clearTracks(video);
  document.getElementById('nowTitle').textContent = item.title;
  document.getElementById('nowMeta').textContent = item.groupTitle;
  document.getElementById('nowDescription').textContent = item.description || '';
  document.getElementById('nowSource').textContent = `${item.source || ''} ${item.sourcesCount ? '• fontes: ' + item.sourcesCount : ''}`;
  addSubtitle(video, item.subtitle);

  if(window.Hls && item.url && item.url.endsWith('.m3u8')){
    if(window.hls) window.hls.destroy();
    const hls = new Hls({ enableWorker: true, lowLatencyMode: true });
    window.hls = hls;
    hls.loadSource(item.url);
    hls.attachMedia(video);
  } else {
    video.src = item.url;
  }
  video.play().catch(()=>{});
  renderRecommendations(item);
}

function renderRecommendations(item){
  const related = byScore(state.items.filter(i =>
    i.title !== item.title &&
    (i.category === item.category || i.group === item.group || (item.isAnime && i.isAnime))
  )).slice(0, 12);

  let block = document.getElementById('recommendationBlock');
  if(!block){
    block = document.createElement('section');
    block.id = 'recommendationBlock';
    block.className = 'railBlock';
    block.innerHTML = '<div class="sectionTitle"><h2>✨ Mais como isso</h2><span id="recommendationBadge"></span></div><div id="recommendationRail" class="rail"></div>';
    document.getElementById('playerPanel').after(block);
  }
  document.getElementById('recommendationBadge').textContent = related.length + ' itens';
  renderRail('recommendationRail', related);
}

function applyFilters(){
  const q = state.q.toLowerCase();
  state.filtered = state.items.filter(i=>{
    const g = state.group === 'Todos' || i.group === state.group;
    const c = state.category === 'Todos' || i.category === state.category;
    const m = !q || `${i.title} ${i.category} ${i.group} ${i.source}`.toLowerCase().includes(q);
    return g && c && m;
  });
  render();
}

function render(){
  const grid = document.getElementById('catalogGrid');
  grid.innerHTML = '';
  document.getElementById('countBadge').textContent = state.filtered.length + ' itens';
  byScore(state.filtered).forEach(i=> grid.appendChild(card(i)));
}

function setup(){
  document.getElementById('searchInput').oninput = e=>{ state.q = e.target.value; applyFilters(); };
  document.getElementById('categorySelect').onchange = e=>{ state.category = e.target.value; applyFilters(); };

  document.querySelectorAll('.tab').forEach(btn=>{
    btn.onclick = ()=>{
      document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      if(btn.dataset.filter === 'anime'){
        state.filtered = byScore(state.items.filter(i=>i.isAnime));
        render(); return;
      }
      if(btn.dataset.filter === 'adult'){
        document.getElementById('adultRailBlock').classList.remove('hidden');
        state.filtered = byScore(state.items.filter(i=>i.isAdult));
        render(); return;
      }
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
