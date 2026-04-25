const DATA_URL = 'catalog.json';
const FALLBACK_URL = 'https://raw.githubusercontent.com/kaykewf13/animeout/main/web/catalog.json';

const state = {
  items: [],
  filtered: [],
  group: 'Todos',
  q: '',
  category: 'Todos',
  pendingAdult: null,
};

function $(id){ return document.getElementById(id); }
function byScore(items){ return [...items].sort((a,b)=>(b.score || 0) - (a.score || 0)); }
function escapeHtml(value){ return String(value || '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
function getEpisodes(item){ return Array.isArray(item.episodes) ? item.episodes : []; }
function getPlayable(item){
  const episodes = getEpisodes(item);
  if(episodes.length){
    return episodes.find(e => isPlayableUrl(e.url)) || episodes[0];
  }
  return item;
}
function isPlayableUrl(url){
  const clean = String(url || '').split('?')[0].toLowerCase();
  return clean.endsWith('.m3u8') || clean.endsWith('.mp4') || clean.endsWith('.ts');
}
function isPlaylistOnly(url){ return String(url || '').split('?')[0].toLowerCase().endsWith('.m3u'); }

function showSkeleton(){
  const grid = $('catalogGrid');
  if(!grid) return;
  grid.innerHTML = '';
  for(let i=0;i<12;i++){
    const el = document.createElement('div');
    el.className = 'card';
    el.innerHTML = '<div class="poster"></div><div class="meta">Carregando...</div><div class="title">Preparando catálogo</div>';
    grid.appendChild(el);
  }
}

async function fetchCatalog(){
  try{
    const res = await fetch(`${DATA_URL}?v=${Date.now()}`, { cache: 'no-store' });
    if(!res.ok) throw new Error('catalog local indisponível');
    const data = await res.json();
    if(!Array.isArray(data) || data.length === 0) throw new Error('catalog local vazio');
    return data;
  }catch(e){
    const res = await fetch(`${FALLBACK_URL}?v=${Date.now()}`, { cache: 'no-store' });
    if(!res.ok) throw new Error('fallback indisponível');
    const data = await res.json();
    if(!Array.isArray(data)) throw new Error('fallback inválido');
    return data;
  }
}

async function load(){
  showSkeleton();
  try{
    const data = await fetchCatalog();
    state.items = byScore(data);
    if(state.items.length === 0){ showEmpty('Catálogo vazio. Rode a Action para gerar web/catalog.json.'); return; }
    buildCategories(); renderStats(); renderFeatured(); renderRails(); applyFilters(); setHero(state.items[0]);
  }catch(e){ showEmpty('Erro ao carregar catálogo. Aguarde o GitHub Pages atualizar e tente ?v=novo.'); }
}

function showEmpty(message){
  $('catalogGrid').innerHTML = `<p>${escapeHtml(message)}</p>`;
  ['featuredBadge','animeBadge','adultBadge','countBadge'].forEach(id => { if($(id)) $(id).textContent = '0 itens'; });
}

function buildCategories(){
  const select = $('categorySelect'); if(!select) return;
  const current = select.value || 'Todos';
  select.innerHTML = '<option value="Todos">Todas as categorias</option>';
  const cats = [...new Set(state.items.map(i=>i.category).filter(Boolean))].sort();
  cats.forEach(c=>{ const opt = document.createElement('option'); opt.value = c; opt.textContent = c; select.appendChild(opt); });
  select.value = current;
}

function renderStats(){
  const stats = $('stats'); if(!stats) return;
  const total = state.items.length;
  const canais = state.items.filter(i=>i.group === 'Canais').length;
  const series = state.items.filter(i=>i.group === 'Series').length;
  const filmes = state.items.filter(i=>i.group === 'Filmes').length;
  const anime = state.items.filter(i=>i.isAnime).length;
  stats.innerHTML = `<div class="stat"><b>${total}</b><span>Títulos</span></div><div class="stat"><b>${canais}</b><span>Canais</span></div><div class="stat"><b>${series}</b><span>Séries</span></div><div class="stat"><b>${filmes}</b><span>Filmes</span></div><div class="stat"><b>${anime}</b><span>Animes</span></div>`;
}

function setHero(item){
  if(!item) return;
  $('heroTitle').textContent = item.title || 'AnimeOut Premium';
  $('heroGroup').textContent = item.groupTitle || item.group || 'Streaming IPTV';
  const eps = getEpisodes(item).length;
  $('heroSubtitle').textContent = item.description || (eps ? `${eps} episódio(s) disponíveis.` : 'Catálogo atualizado automaticamente com listas M3U e experiência web premium.');
  const hero = $('hero');
  if(item.logo){ hero.style.backgroundImage = `linear-gradient(90deg, rgba(11,12,16,.96), rgba(11,12,16,.72), rgba(11,12,16,.96)), url('${item.logo}')`; }
  const btn = $('heroPlay'); if(btn) btn.onclick = () => handlePlay(item);
}

function renderFeatured(){ const items = byScore(state.items).slice(0,20); renderRail('featuredRail', items); if($('featuredBadge')) $('featuredBadge').textContent = `${items.length} itens`; }
function renderRails(){
  const anime = byScore(state.items.filter(i=>i.isAnime));
  const adult = byScore(state.items.filter(i=>i.isAdult));
  renderRail('animeRail', anime.slice(0,30)); renderRail('adultRail', adult.slice(0,30));
  if($('animeBadge')) $('animeBadge').textContent = `${anime.length} itens`; if($('adultBadge')) $('adultBadge').textContent = `${adult.length} itens`;
}
function renderRail(id, items){ const rail = $(id); if(!rail) return; rail.innerHTML = ''; items.forEach(item => rail.appendChild(card(item))); }

function card(item){
  const el = document.createElement('div'); el.className = 'card';
  const img = item.logo || ''; const rating = item.rating ? `⭐ ${item.rating}` : ''; const score = item.score ? `Q${item.score}` : '';
  const adult = item.isAdult ? '<span class="badge adultBadge">18+</span>' : ''; const anime = item.isAnime ? '<span class="badge">Anime</span>' : '';
  const eps = getEpisodes(item).length ? `<span>${getEpisodes(item).length} eps</span>` : `<span>${score}</span>`;
  el.innerHTML = `<div class="poster" style="background-image:${img ? `url('${img}')` : 'none'}">${!img ? `<span class="posterFallback">${escapeHtml(item.title || 'AO').slice(0,2)}</span>` : ''}<div class="badges">${anime}${adult}</div></div><div class="meta">${escapeHtml(item.groupTitle || item.category || '')}</div><div class="title">${escapeHtml(item.title || 'Sem título')}</div><div class="rating"><span>${rating}</span>${eps}</div>`;
  el.onclick = () => handlePlay(item); return el;
}

function handlePlay(item){
  if(item.isAdult){ state.pendingAdult = item; $('adultModal').classList.remove('hidden'); return; }
  play(item);
}
function clearTracks(video){ [...video.querySelectorAll('track')].forEach(t=>t.remove()); }
function addSubtitle(video, subtitleUrl){ if(!subtitleUrl) return; const track = document.createElement('track'); track.kind='subtitles'; track.label='Português'; track.srclang='pt'; track.src=subtitleUrl; track.default=true; video.appendChild(track); }

function play(item){
  setHero(item);
  const selected = getPlayable(item);
  const url = selected.url || item.url;
  const video = $('videoPlayer');
  clearTracks(video);
  if(window.hls){ window.hls.destroy(); window.hls = null; }
  video.removeAttribute('src'); video.load();
  $('nowTitle').textContent = selected.title || item.title || 'Reproduzindo';
  $('nowMeta').textContent = item.groupTitle || item.category || '';
  $('nowDescription').textContent = item.description || (getEpisodes(item).length ? `${getEpisodes(item).length} episódio(s) disponíveis.` : '');
  $('nowSource').textContent = `${selected.source || item.source || ''} ${item.sourcesCount ? '• fontes: ' + item.sourcesCount : ''}`;
  addSubtitle(video, selected.subtitle || item.subtitle);

  if(!url){ $('nowSource').textContent = 'URL indisponível para este item.'; return; }
  if(isPlaylistOnly(url)){ $('nowSource').textContent = 'Este item é uma playlist .m3u. Use no app IPTV ou aguarde expansão da playlist.'; return; }
  if(!isPlayableUrl(url)){ $('nowSource').textContent = 'Formato não suportado no player web. Tente pela lista IPTV.'; return; }

  const clean = url.split('?')[0].toLowerCase();
  if(window.Hls && clean.endsWith('.m3u8')){
    if(Hls.isSupported()){
      const hls = new Hls({ enableWorker: true, lowLatencyMode: true });
      window.hls = hls;
      hls.on(Hls.Events.ERROR, function(_, data){ $('nowSource').textContent = `Falha HLS: ${data.details || 'erro no stream'}`; });
      hls.loadSource(url); hls.attachMedia(video);
      hls.on(Hls.Events.MANIFEST_PARSED, function(){ video.play().catch(()=>{}); });
    }else if(video.canPlayType('application/vnd.apple.mpegurl')){
      video.src = url; video.play().catch(()=>{});
    }
  }else{
    video.src = url; video.play().catch(()=>{});
  }
  renderRecommendations(item);
}

function renderRecommendations(item){
  const related = byScore(state.items.filter(i => i.title !== item.title && (i.category === item.category || i.group === item.group || (item.isAnime && i.isAnime)))).slice(0,12);
  let block = $('recommendationBlock');
  if(!block){ block = document.createElement('section'); block.id='recommendationBlock'; block.className='railBlock'; block.innerHTML='<div class="sectionTitle"><h2>✨ Mais como isso</h2><span id="recommendationBadge"></span></div><div id="recommendationRail" class="rail"></div>'; $('playerPanel').after(block); }
  $('recommendationBadge').textContent = `${related.length} itens`; renderRail('recommendationRail', related);
}

function applyFilters(){
  const q = state.q.toLowerCase();
  state.filtered = state.items.filter(i=>{ const g = state.group === 'Todos' || i.group === state.group; const c = state.category === 'Todos' || i.category === state.category; const m = !q || `${i.title} ${i.category} ${i.group} ${i.source}`.toLowerCase().includes(q); return g && c && m; });
  renderCatalog();
}
function renderCatalog(){ const grid = $('catalogGrid'); grid.innerHTML=''; if($('countBadge')) $('countBadge').textContent = `${state.filtered.length} itens`; byScore(state.filtered).forEach(item => grid.appendChild(card(item))); }
function setup(){
  if($('searchInput')) $('searchInput').oninput = e => { state.q = e.target.value; applyFilters(); };
  if($('categorySelect')) $('categorySelect').onchange = e => { state.category = e.target.value; applyFilters(); };
  document.querySelectorAll('.tab').forEach(btn=>{ btn.onclick = () => { document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active')); btn.classList.add('active'); if(btn.dataset.filter === 'anime'){ state.group='Todos'; state.filtered=byScore(state.items.filter(i=>i.isAnime)); renderCatalog(); return; } if(btn.dataset.filter === 'adult'){ $('adultRailBlock').classList.remove('hidden'); state.group='Todos'; state.filtered=byScore(state.items.filter(i=>i.isAdult)); renderCatalog(); return; } state.group = btn.dataset.group || 'Todos'; applyFilters(); }; });
  if($('confirmAdult')) $('confirmAdult').onclick = () => { play(state.pendingAdult); $('adultModal').classList.add('hidden'); };
  if($('cancelAdult')) $('cancelAdult').onclick = () => $('adultModal').classList.add('hidden');
}
setup(); load();
