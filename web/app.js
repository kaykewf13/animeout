const DATA_URL = 'catalog.json';
const FALLBACK_URL = 'https://raw.githubusercontent.com/kaykewf13/animeout/main/web/catalog.json';

const state = {
  items: [], filtered: [], group: 'Todos', q: '', category: 'Todos', pendingAdult: null,
  currentItem: null, currentEpisodeIndex: 0, currentSourceIndex: 0, currentSources: [], retryCount: 0, maxRetries: 2,
};

function $(id){ return document.getElementById(id); }
function byScore(items){ return [...items].sort((a,b)=>(b.score || 0) - (a.score || 0)); }
function escapeHtml(value){ return String(value || '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
function getEpisodes(item){ return Array.isArray(item?.episodes) ? item.episodes : []; }
function isPlayableUrl(url){ const clean = String(url || '').split('?')[0].toLowerCase(); return clean.endsWith('.m3u8') || clean.endsWith('.mp4') || clean.endsWith('.ts'); }
function isPlaylistOnly(url){ return String(url || '').split('?')[0].toLowerCase().endsWith('.m3u'); }
function getPlayable(item){ const eps = getEpisodes(item); return eps.length ? (eps.find(e => isPlayableUrl(e.url)) || eps[0]) : item; }
function buildSources(episode){
  const sources = [];
  if(episode?.url && isPlayableUrl(episode.url)) sources.push({url: episode.url, source: episode.source || 'principal', score: episode.score || 0, subtitle: episode.subtitle || ''});
  (episode?.alternatives || []).forEach(a => { if(a?.url && isPlayableUrl(a.url) && !sources.some(s => s.url === a.url)) sources.push({url: a.url, source: a.source || 'fallback', score: a.score || 0, subtitle: a.subtitle || ''}); });
  return sources.sort((a,b)=>(b.score || 0) - (a.score || 0));
}

function showSkeleton(){
  const grid = $('catalogGrid'); if(!grid) return; grid.innerHTML = '';
  for(let i=0;i<12;i++){ const el = document.createElement('div'); el.className = 'card'; el.innerHTML = '<div class="poster"></div><div class="meta">Carregando...</div><div class="title">Preparando catálogo</div>'; grid.appendChild(el); }
}
async function fetchCatalog(){
  try{ const res = await fetch(`${DATA_URL}?v=${Date.now()}`, { cache: 'no-store' }); if(!res.ok) throw new Error('local'); const data = await res.json(); if(!Array.isArray(data)||!data.length) throw new Error('vazio'); return data; }
  catch(e){ const res = await fetch(`${FALLBACK_URL}?v=${Date.now()}`, { cache:'no-store' }); if(!res.ok) throw new Error('fallback'); const data = await res.json(); if(!Array.isArray(data)) throw new Error('inválido'); return data; }
}
async function load(){ showSkeleton(); try{ const data = await fetchCatalog(); state.items = byScore(data); if(!state.items.length){ showEmpty('Catálogo vazio. Rode a Action para gerar web/catalog.json.'); return; } buildCategories(); renderStats(); renderFeatured(); renderRails(); applyFilters(); setHero(state.items[0]); }catch(e){ showEmpty('Erro ao carregar catálogo. Aguarde o GitHub Pages atualizar e tente ?v=novo.'); } }
function showEmpty(message){ $('catalogGrid').innerHTML = `<p>${escapeHtml(message)}</p>`; ['featuredBadge','animeBadge','adultBadge','countBadge'].forEach(id=>{ if($(id)) $(id).textContent='0 itens'; }); }
function buildCategories(){ const select=$('categorySelect'); if(!select) return; const current=select.value||'Todos'; select.innerHTML='<option value="Todos">Todas as categorias</option>'; [...new Set(state.items.map(i=>i.category).filter(Boolean))].sort().forEach(c=>{ const opt=document.createElement('option'); opt.value=c; opt.textContent=c; select.appendChild(opt); }); select.value=current; }
function renderStats(){ const stats=$('stats'); if(!stats) return; const total=state.items.length,canais=state.items.filter(i=>i.group==='Canais').length,series=state.items.filter(i=>i.group==='Series').length,filmes=state.items.filter(i=>i.group==='Filmes').length,anime=state.items.filter(i=>i.isAnime).length; stats.innerHTML=`<div class="stat"><b>${total}</b><span>Títulos</span></div><div class="stat"><b>${canais}</b><span>Canais</span></div><div class="stat"><b>${series}</b><span>Séries</span></div><div class="stat"><b>${filmes}</b><span>Filmes</span></div><div class="stat"><b>${anime}</b><span>Animes</span></div>`; }
function setHero(item){ if(!item) return; $('heroTitle').textContent=item.title||'AnimeOut Premium'; $('heroGroup').textContent=item.groupTitle||item.group||'Streaming IPTV'; const eps=getEpisodes(item).length; $('heroSubtitle').textContent=item.description||(eps?`${eps} episódio(s) disponíveis.`:'Catálogo atualizado automaticamente.'); const hero=$('hero'); if(item.logo) hero.style.backgroundImage=`linear-gradient(90deg, rgba(11,12,16,.96), rgba(11,12,16,.72), rgba(11,12,16,.96)), url('${item.logo}')`; const btn=$('heroPlay'); if(btn) btn.onclick=()=>handlePlay(item); }
function renderFeatured(){ const items=byScore(state.items).slice(0,20); renderRail('featuredRail',items); if($('featuredBadge')) $('featuredBadge').textContent=`${items.length} itens`; }
function renderRails(){ const anime=byScore(state.items.filter(i=>i.isAnime)); const adult=byScore(state.items.filter(i=>i.isAdult)); renderRail('animeRail',anime.slice(0,30)); renderRail('adultRail',adult.slice(0,30)); if($('animeBadge')) $('animeBadge').textContent=`${anime.length} itens`; if($('adultBadge')) $('adultBadge').textContent=`${adult.length} itens`; }
function renderRail(id,items){ const rail=$(id); if(!rail) return; rail.innerHTML=''; items.forEach(item=>rail.appendChild(card(item))); }
function card(item){ const el=document.createElement('div'); el.className='card'; const img=item.logo||'', rating=item.rating?`⭐ ${item.rating}`:'', score=item.score?`Q${item.score}`:''; const adult=item.isAdult?'<span class="badge adultBadge">18+</span>':'', anime=item.isAnime?'<span class="badge">Anime</span>':''; const eps=getEpisodes(item).length?`<span>${getEpisodes(item).length} eps</span>`:`<span>${score}</span>`; el.innerHTML=`<div class="poster" style="background-image:${img?`url('${img}')`:'none'}">${!img?`<span class="posterFallback">${escapeHtml(item.title||'AO').slice(0,2)}</span>`:''}<div class="badges">${anime}${adult}</div></div><div class="meta">${escapeHtml(item.groupTitle||item.category||'')}</div><div class="title">${escapeHtml(item.title||'Sem título')}</div><div class="rating"><span>${rating}</span>${eps}</div>`; el.onclick=()=>handlePlay(item); return el; }
function handlePlay(item){ if(item.isAdult){ state.pendingAdult=item; $('adultModal').classList.remove('hidden'); return; } play(item); }
function clearTracks(video){ [...video.querySelectorAll('track')].forEach(t=>t.remove()); }
function addSubtitle(video, subtitleUrl){ if(!subtitleUrl) return; const track=document.createElement('track'); track.kind='subtitles'; track.label='Português'; track.srclang='pt'; track.src=subtitleUrl; track.default=true; video.appendChild(track); }
function resetVideo(){ const video=$('videoPlayer'); clearTracks(video); if(window.hls){ window.hls.destroy(); window.hls=null; } video.removeAttribute('src'); video.load(); return video; }
function play(item, episodeIndex=0){
  state.currentItem=item; state.currentEpisodeIndex=episodeIndex; state.currentSourceIndex=0; state.retryCount=0; setHero(item); renderEpisodeList(item); renderRecommendations(item);
  const episodes=getEpisodes(item); const selected=episodes.length ? episodes[episodeIndex] : getPlayable(item); state.currentSources=buildSources(selected);
  if(!state.currentSources.length){ $('nowTitle').textContent=selected?.title||item.title||'Sem stream'; $('nowSource').textContent='Nenhuma URL direta reproduzível encontrada.'; return; }
  playSource(selected, state.currentSources[0]);
}
function playSource(episode, source){
  const video=resetVideo(); const url=source.url;
  $('nowTitle').textContent=episode.title||state.currentItem?.title||'Reproduzindo'; $('nowMeta').textContent=state.currentItem?.groupTitle||state.currentItem?.category||''; $('nowDescription').textContent=state.currentItem?.description||(getEpisodes(state.currentItem).length?`${getEpisodes(state.currentItem).length} episódio(s) disponíveis.`:''); $('nowSource').textContent=`Fonte: ${source.source||'principal'} • score ${source.score||0}`; addSubtitle(video, source.subtitle||episode.subtitle);
  if(!url){ return failover('URL indisponível'); } if(isPlaylistOnly(url)){ return failover('Playlist .m3u não roda no player web'); } if(!isPlayableUrl(url)){ return failover('Formato não suportado'); }
  const clean=url.split('?')[0].toLowerCase();
  video.onerror=()=>failover('Erro no vídeo'); video.onstalled=()=>setTimeout(()=>{ if(video.readyState<2) failover('Stream travado'); }, 8000); video.onended=()=>playNextEpisode();
  if(window.Hls && clean.endsWith('.m3u8')){
    if(Hls.isSupported()){
      const hls=new Hls({ enableWorker:true, lowLatencyMode:true, maxBufferLength:30 }); window.hls=hls;
      hls.on(Hls.Events.ERROR, function(_, data){ if(data?.fatal) failover(`Falha HLS: ${data.details||'erro'}`); });
      hls.loadSource(url); hls.attachMedia(video); hls.on(Hls.Events.MANIFEST_PARSED, ()=>video.play().catch(()=>{}));
    }else if(video.canPlayType('application/vnd.apple.mpegurl')){ video.src=url; video.play().catch(()=>{}); }
  }else{ video.src=url; video.play().catch(()=>{}); }
}
function failover(reason){
  if(state.retryCount < state.maxRetries){ state.retryCount++; $('nowSource').textContent=`${reason}. Tentando novamente (${state.retryCount}/${state.maxRetries})...`; const ep=getEpisodes(state.currentItem)[state.currentEpisodeIndex]||getPlayable(state.currentItem); const src=state.currentSources[state.currentSourceIndex]; setTimeout(()=>playSource(ep,src),1200); return; }
  state.currentSourceIndex++;
  if(state.currentSourceIndex < state.currentSources.length){ state.retryCount=0; const ep=getEpisodes(state.currentItem)[state.currentEpisodeIndex]||getPlayable(state.currentItem); $('nowSource').textContent=`${reason}. Trocando para backup ${state.currentSourceIndex+1}/${state.currentSources.length}...`; setTimeout(()=>playSource(ep,state.currentSources[state.currentSourceIndex]),900); return; }
  $('nowSource').textContent=`${reason}. Todas as fontes falharam para este episódio.`;
}
function playNextEpisode(){ const eps=getEpisodes(state.currentItem); const next=state.currentEpisodeIndex+1; if(eps.length && next<eps.length){ $('nowSource').textContent='Próximo episódio iniciando...'; setTimeout(()=>play(state.currentItem,next),1200); } }
function renderEpisodeList(item){ const panel=$('episodePanel'), list=$('episodeList'); if(!panel||!list) return; const eps=getEpisodes(item); if(!eps.length){ panel.classList.add('hidden'); list.innerHTML=''; return; } panel.classList.remove('hidden'); $('episodeBadge').textContent=`${eps.length} eps`; list.innerHTML=''; eps.forEach((ep,idx)=>{ const btn=document.createElement('button'); btn.className='episodeButton'; btn.textContent=`Ep ${ep.episode||idx+1} • ${ep.title||item.title}`; btn.onclick=()=>play(item,idx); list.appendChild(btn); }); }
function renderRecommendations(item){ const related=byScore(state.items.filter(i=>i.title!==item.title&&(i.category===item.category||i.group===item.group||(item.isAnime&&i.isAnime)))).slice(0,12); let block=$('recommendationBlock'); if(!block){ block=document.createElement('section'); block.id='recommendationBlock'; block.className='railBlock'; block.innerHTML='<div class="sectionTitle"><h2>✨ Mais como isso</h2><span id="recommendationBadge"></span></div><div id="recommendationRail" class="rail"></div>'; $('playerPanel').after(block); } $('recommendationBadge').textContent=`${related.length} itens`; renderRail('recommendationRail',related); }
function applyFilters(){ const q=state.q.toLowerCase(); state.filtered=state.items.filter(i=>{ const g=state.group==='Todos'||i.group===state.group; const c=state.category==='Todos'||i.category===state.category; const m=!q||`${i.title} ${i.category} ${i.group} ${i.source}`.toLowerCase().includes(q); return g&&c&&m; }); renderCatalog(); }
function renderCatalog(){ const grid=$('catalogGrid'); grid.innerHTML=''; if($('countBadge')) $('countBadge').textContent=`${state.filtered.length} itens`; byScore(state.filtered).forEach(item=>grid.appendChild(card(item))); }
function setup(){
  if($('searchInput')) $('searchInput').oninput=e=>{ state.q=e.target.value; applyFilters(); };
  if($('categorySelect')) $('categorySelect').onchange=e=>{ state.category=e.target.value; applyFilters(); };
  document.querySelectorAll('.tab').forEach(btn=>{ btn.onclick=()=>{ document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active')); btn.classList.add('active'); if(btn.dataset.filter==='anime'){ state.group='Todos'; state.filtered=byScore(state.items.filter(i=>i.isAnime)); renderCatalog(); return; } if(btn.dataset.filter==='adult'){ $('adultRailBlock').classList.remove('hidden'); state.group='Todos'; state.filtered=byScore(state.items.filter(i=>i.isAdult)); renderCatalog(); return; } state.group=btn.dataset.group||'Todos'; applyFilters(); }; });
  if($('confirmAdult')) $('confirmAdult').onclick=()=>{ play(state.pendingAdult); $('adultModal').classList.add('hidden'); };
  if($('cancelAdult')) $('cancelAdult').onclick=()=>$('adultModal').classList.add('hidden');
}
setup(); load();
