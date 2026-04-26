function renderSourceSelector(){
  const container = document.getElementById("sourceSelector");
  if(!container) return;

  container.innerHTML = "";

  state.currentSources.forEach((s, i) => {
    const btn = document.createElement("button");

    const quality = s.score > 90 ? "🟢 Alta"
                  : s.score > 70 ? "🟡 Média"
                  : "🔴 Baixa";

    btn.textContent = `Fonte ${i+1} - ${quality}`;
    
    btn.onclick = () => {
      state.currentSourceIndex = i;
      playSource(
        getEpisodes(state.currentItem)[state.currentEpisodeIndex],
        s
      );
    };

    container.appendChild(btn);
  });
}