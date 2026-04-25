const RAW_PLAYLIST = 'https://raw.githubusercontent.com/kaykewf13/animeout/main/valid_links.m3u';

const state = { items: [], filtered: [], group: 'Todos', q: '' };

function parseM3U(text){
  const lines = text.split(/\r?\n/);
  const items = [];
  let current = null;
  for(const line of lines){
    if(line.startsWith('#EXTINF')){
      const title = line.split(',').slice(1).join(',').trim() || 'Sem título';
      let group = 'Geral';
      const g = line.match(/group-title="([^"]+)"/);
      if(g) group = g[1];
      current = { title, group };
    } else if(line.startsWith('http') && current){
      items.push({ ...current, url: line.trim() });
      current = null;
    }
  }
  return items;
}

async function load(){
  const res = await fetch(RAW_PLAYLIST, { cache: 'no-store' });
  const txt = await res.text();
  state.items = parseM3U(txt);
  applyFilters();
}

function applyFilters(){
  const q = state.q.toLowerCase();
  state.filtered = state.items.filter(i => {
    const inGroup = state.group === 'Todos' || i.group.startsWith(state.group);
    const match = !q || (i.title + ' ' + i.group).toLowerCase().includes(q);
    return inGroup && match;
  });
  render();
}

function render(){
  const grid = document.getElementById('catalogGrid');
  const count = document.getElementById('countBadge');
  grid.innerHTML = '';
  count.textContent = state.filtered.length + ' itens';

  for(const item of state.filtered){
    const el = document.createElement('div');
    el.className = 'card';
    el.innerHTML = `
      <div class="meta">${item.group}</div>
      <div class="title">${item.title}</div>
    `;
    el.onclick = () => play(item);
    grid.appendChild(el);
  }
}

function play(item){
  const video = document.getElementById('videoPlayer');
  const nowTitle = document.getElementById('nowTitle');
  const nowMeta = document.getElementById('nowMeta');

  nowTitle.textContent = item.title;
  nowMeta.textContent = item.group;

  if (window.Hls && item.url.endsWith('.m3u8')){
    if (window.hls) window.hls.destroy();
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
  document.getElementById('searchInput').addEventListener('input', (e)=>{
    state.q = e.target.value || '';
    applyFilters();
  });

  document.querySelectorAll('.tab').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      state.group = btn.dataset.group;
      applyFilters();
    });
  });
}

setup();
load();
