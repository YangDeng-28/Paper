'use strict';
(() => {
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];
  const C = window.CATALOG;
  if (!C) { $('#results').textContent = '目录加载失败，请刷新页面；若仍失败，请检查 catalog.js 是否已部署。'; return; }
  const papers = new Map(C.papers.map(p => [p.id, p]));
  const venues = new Map(C.scope.venues.map(v => [v.id, v]));
  const figures = new Map(C.figures.map(f => [f.id, f]));
  const totals = C.totals || {papers:C.papers.length,figures:C.figures.length};
  const fileLoads = new Map();
  let indexLoaded = !C.paging, indexLoading = null, renderVersion = 0;
  async function loadIndex() {
    if(indexLoaded) return;
    if(!indexLoading) indexLoading = fetch(C.paging.index).then(r => {if(!r.ok) throw new Error('索引请求失败');return r.json();}).then(index => {
      C.papers=index.papers; C.figures=index.figures;
      for(const p of C.papers) if(!papers.has(p.id)) papers.set(p.id,p);
      indexLoaded=true;
    }).catch(e => {indexLoading=null;throw e;});
    return indexLoading;
  }
  async function loadRecords(items) {
    await Promise.all([...new Set(items.map(x=>x._file).filter(Boolean))].map(file => {
      if(!fileLoads.has(file)) fileLoads.set(file,fetch(file).then(r=>{if(!r.ok) throw new Error('分页请求失败');return r.json();}).then(data=>{
        for(const p of data.papers || []) papers.set(p.id,p);
        for(const f of data.figures || []) figures.set(f.id,f);
      }).catch(e=>{fileLoads.delete(file);throw e;}));
      return fileLoads.get(file);
    }));
  }
  const labels = {framework: '框架图', experiment: '实验图'};
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const safeURL = value => { try { const u = new URL(value); return u.protocol === 'https:' ? u.href : '#'; } catch { return '#'; } };
  const imageURL = value => /^assets\/[a-zA-Z0-9_./-]+$/.test(value) && !value.split('/').includes('..') ? value : safeURL(value);
  const link = (url, label, cls = '') => `<a class="${cls}" href="${esc(safeURL(url))}" target="_blank" rel="noopener noreferrer">${esc(label)}</a>`;
  let saved;
  try { const data = JSON.parse(localStorage.getItem('se-figure-atlas:saved') || '[]'); saved = new Set(Array.isArray(data) ? data.filter(x => typeof x === 'string') : []); } catch { saved = new Set(); }
  let state = {view: 'figures', kind: '', q: '', year: '', venue: '', chart: '', core: false, curated: false, sort: 'new'};
  let limit = 24, lastFocused = null, toastTimer;

  function toast(message) { $('#toast').textContent = message; $('#toast').classList.add('visible'); clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').classList.remove('visible'), 3000); }
  function save(id) {
    saved.has(id) ? saved.delete(id) : saved.add(id);
    try { localStorage.setItem('se-figure-atlas:saved', JSON.stringify([...saved])); } catch { toast('浏览器无法保存收藏；本次会话仍可使用，请导出备份。'); }
    $('#saved-count').textContent = saved.size;
    $$('[data-save]').filter(b => b.dataset.save === id).forEach(b => { b.setAttribute('aria-pressed', saved.has(id)); b.textContent = saved.has(id) ? '已收藏' : '收藏'; });
    if (state.view === 'saved') render();
  }
  function readURL() {
    const q = new URLSearchParams(location.search);
    for (const key of Object.keys(state)) state[key] = typeof state[key] === 'boolean' ? q.get(key) === '1' : (q.get(key) || ({view:'figures',sort:'new'}[key] || ''));
    if (!['figures','papers','saved','about'].includes(state.view)) state.view = 'figures';
    if (!['','framework','experiment'].includes(state.kind)) state.kind = '';
    if (!['new','year','title'].includes(state.sort)) state.sort = 'new';
    if (state.venue && !venues.has(state.venue)) state.venue = '';
    if (state.year && !C.scope.years.includes(Number(state.year))) state.year = '';
    syncInputs(); render();
    const id = q.get('figure');
    if (id) openDetail(id, false); else if ($('#detail').open) $('#detail').close();
  }
  function writeURL(figure = null) {
    const q = new URLSearchParams();
    for (const [k,v] of Object.entries(state)) if (v && !(k === 'view' && v === 'figures') && !(k === 'sort' && v === 'new')) q.set(k, v === true ? '1' : v);
    if (figure) q.set('figure', figure);
    history.replaceState(null, '', location.pathname + (q.size ? '?' + q : ''));
  }
  function syncInputs() {
    $('#search').value = state.q;
    for (const id of ['year','venue','chart','sort']) $('#'+id).value = state[id];
    for (const id of ['core','curated']) $('#'+id).checked = state[id];
  }
  function setState(changes) { state = {...state, ...changes}; limit = 24; syncInputs(); writeURL(); render(); }
  function matches(p, f) {
    if (state.year && p.year !== Number(state.year)) return false;
    if (state.venue && p.venue !== state.venue) return false;
    if (state.core && !venues.get(p.venue)?.core) return false;
    if (f && state.kind && f.kind !== state.kind) return false;
    if (f && state.chart && f.chart_type !== state.chart) return false;
    if (f && state.curated && !f.reviewed) return false;
    const haystack = [p.title, ...p.authors, ...(p.tags || []), f?.caption, f?.note, ...(f?.tags || [])].join(' ').toLocaleLowerCase();
    return state.q.trim().toLocaleLowerCase().split(/\s+/).every(word => haystack.includes(word));
  }
  function sortItems(items, getPaper = x => x) {
    return items.sort((a,b) => {
      const p = getPaper(a), q = getPaper(b);
      if (state.sort === 'title') return p.title.localeCompare(q.title);
      if (state.sort === 'year') return q.year - p.year || p.title.localeCompare(q.title);
      return String(b.added_at || q.added_at).localeCompare(String(a.added_at || p.added_at)) || p.title.localeCompare(q.title);
    });
  }
  function figureCard(f) {
    const p = papers.get(f.paper_id);
    return `<article class="figure-card"><button class="figure-open" data-open="${esc(f.id)}" aria-label="查看 ${esc(p.title)} 的${esc(f.number)}"><div class="figure-img"><img src="${esc(imageURL(f.thumbnail || f.image))}" alt="${esc(f.caption)}" loading="lazy" decoding="async"></div><div class="card-body"><div class="card-meta"><span class="pill">${labels[f.kind]}</span><span>${esc(p.venue)} · ${p.year}</span>${f.reviewed ? '<span>精选</span>' : '<span>待精选</span>'}</div><h3>${esc(p.title)}</h3><div class="card-caption">${esc(f.note || f.caption)}</div></div></button><div class="card-body" style="padding-top:0"><div class="card-bottom"><span>${esc(f.chart_type || '')} · ${esc(f.number)}</span><button class="save-button" data-save="${esc(f.id)}" aria-pressed="${saved.has(f.id)}">${saved.has(f.id) ? '已收藏' : '收藏'}</button></div></div></article>`;
  }
  function paperCard(p) {
    const count = C.figures.filter(f => f.paper_id === p.id).length;
    return `<article class="paper-row"><div class="card-meta"><span class="pill">${esc(p.venue)} ${p.year}</span><span class="status-label">${p.verification === 'research_track_verified' ? '来源已核实' : '待核验正式论文资格'}</span></div><h3>${esc(p.title)}</h3><p>${esc(p.authors.join(' · '))}</p><p>${count ? `${count} 张已收录图表` : '图表待提取 / 审核'}${p.preprint_year ? ` · 预印本 ${p.preprint_year} 年，按正式发表年份归档` : ''}</p><div class="links">${link(p.source_url,'论文来源')}${p.doi ? link('https://doi.org/'+p.doi,'DOI') : ''}${p.pdf_url ? link(p.pdf_url,'阅读 PDF') : ''}<button class="text-button" data-cite="${esc(p.id)}">复制引用</button></div></article>`;
  }
  function empty(title, message, action = '') { return `<div class="empty"><div class="empty-symbol" aria-hidden="true">◫</div><h2>${title}</h2><p>${message}</p>${action}</div>`; }
  function renderAbout() {
    $('#about').innerHTML = `<div class="eyebrow">SCOPE & PROVENANCE</div><h2>公开收录，透明记录。</h2><p>收录范围为 2025–2026 年正式发表的研究论文，按当前 CCF「软件工程 / 系统软件 / 程序设计语言」A 类目录配置。预印本年份单独保存。目录覆盖设置不代表已经完成图表收集。</p>${link(C.scope.ranking_source,'查看 CCF 官方目录')}<h3>来源覆盖</h3><div class="table-scroll"><table><thead><tr><th>来源</th><th>类型</th><th>2025 论文索引</th><th>2026 论文索引</th><th>已发布图表</th></tr></thead><tbody>${C.scope.venues.map(v => `<tr><td>${v.id}${v.core ? ' · 核心' : ''}</td><td>${v.type === 'journal' ? '期刊' : '会议'}</td>${C.scope.years.map(y => `<td>${(C.coverage || []).find(c=>c.venue===v.id && c.year===y)?.papers || 0}</td>`).join('')}<td>${(C.coverage || []).filter(c=>c.venue===v.id).reduce((n,c)=>n+c.figures,0)}</td></tr>`).join('')}</tbody></table></div><p>“核心”是本图库的便捷筛选，包括 ICSE、FSE、ASE、ISSTA、FM、TOSEM 和 TSE，不是另一种评级。正式研究论文资格由人工复核；短文、演示、Workshop 和 Journal-first 展示不直接计入会议研究论文。</p><h3>从发现到精选</h3><p>定时发现论文 → 获取可用全文 → 提取框架图与实验图 → 核验出处、图片与展示依据 → 发布参考 → 人工精选。精选理由关注信息层级、布局、颜色、可读性与比较表达，不使用引用量代替图表质量。</p><h3>采集状态</h3><p>最近尝试：${esc(C.status.last_attempt || '尚未运行')}<br>最近全部查询成功：${esc(C.status.last_success || '暂无')}<br>${esc(C.status.note || '')}</p>${C.status.errors?.length ? `<p>有 ${C.status.errors.length} 个查询失败，已保留此前数据；任务日志可在 GitHub Actions 查看。</p>` : ''}<h3>收藏与引用</h3><p>收藏保存在当前浏览器，可导出 JSON 备份；不跨设备同步。图表详情保留原文、作者、图号、来源版本、许可和修改说明。收藏或收录不等于获得再次发表许可。</p><h3>补充、纠错与撤下</h3><p>通过 GitHub Issue 提供论文链接、图号和需要修正的内容；请勿上传无法公开分享的全文或图片。</p>${link('https://github.com/YangDeng-28/Paper/issues','提交反馈','button secondary')}`;
  }
  async function render() {
    const version = ++renderVersion;
    $$('nav [data-view]').forEach(b => { b.classList.toggle('active', b.dataset.view === state.view); b.setAttribute('aria-current', b.dataset.view === state.view ? 'page' : 'false'); });
    $$('.tabs button').forEach(b => { b.classList.toggle('selected', b.dataset.kind === state.kind); b.setAttribute('aria-pressed', b.dataset.kind === state.kind); });
    $('#explore').hidden = state.view === 'about'; $('#about').hidden = state.view !== 'about';
    if (state.view === 'about') { renderAbout(); return; }
    const isPapers = state.view === 'papers';
    const needsIndex = state.view !== 'figures' || state.kind || state.q || state.year || state.venue || state.chart || state.core || state.curated || state.sort !== 'new' || limit > 24;
    try {
      if(needsIndex && !indexLoaded) { $('#result-count').textContent='正在加载搜索索引…'; await loadIndex(); }
      if(version !== renderVersion) return;
    } catch { $('#result-count').textContent='目录加载失败，请稍后重试。'; return; }
    $('.tabs').hidden = isPapers; $('#chart').disabled = isPapers; $('#curated').disabled = isPapers;
    $('#export').hidden = state.view !== 'saved';
    let items;
    if (isPapers) items = sortItems(C.papers.filter(p => matches(p)));
    else items = sortItems(C.figures.filter(f => papers.has(f.paper_id) && (state.view !== 'saved' || saved.has(f.id)) && matches(papers.get(f.paper_id), f)), f => papers.get(f.paper_id));
    const total = !indexLoaded && state.view==='figures' ? totals.figures : items.length;
    $('#result-count').textContent = `${state.view === 'saved' ? '当前浏览器收藏 · ' : ''}${total} ${isPapers ? '篇论文' : '张图表'}`;
    try { await loadRecords(items.slice(0,limit)); if(version !== renderVersion) return; }
    catch { $('#result-count').textContent='分页加载失败，请重新选择筛选条件重试。'; return; }
    $('#more').hidden = total <= limit;
    if (items.length) $('#results').innerHTML = `<div class="${isPapers ? 'paper-list' : 'grid'}">${items.slice(0,limit).map(x => isPapers ? paperCard(papers.get(x.id)) : figureCard(figures.get(x.id))).join('')}</div>`;
    else if (!isPapers && state.view !== 'saved' && !totals.figures) $('#results').innerHTML = empty('第一批图表，正在整理中','论文索引已经开始建立。图表将在提取并核验出处后显示；这里不会用示意图充当论文原图。','<button class="button" data-view="papers">浏览已索引论文</button>');
    else if (state.view === 'saved' && !saved.size) $('#results').innerHTML = empty('为下一张图，建立你的参考集','在图表卡片上点击“收藏”，即可在这里集中查看。收藏仅保存在当前浏览器。','<button class="button" data-view="figures">探索图表</button>');
    else $('#results').innerHTML = empty('没有找到匹配的结果','试试减少筛选条件，或使用更短的关键词。','<button class="button secondary" data-reset>清除筛选</button>');
    imageErrors($('#results'));
  }
  function imageErrors(root) { $$('img',root).forEach(img => img.addEventListener('error',() => { const p = document.createElement('p'); p.className = 'image-error'; p.textContent = '图片暂时无法加载，可在详情中查看原文。'; img.replaceWith(p); },{once:true})); }
  function citation(p) { return `${p.authors.join(', ')}. ${p.title}. ${p.venue}, ${p.year}. ${p.doi ? 'https://doi.org/' + p.doi : p.source_url}`; }
  async function copy(text) {
    try { await navigator.clipboard.writeText(text); toast('已复制'); }
    catch { const field = document.createElement('textarea'); field.value = text; field.setAttribute('readonly',''); document.body.append(field); field.select(); const ok = document.execCommand('copy'); field.remove(); toast(ok ? '已复制' : '复制失败，请从原文页面复制引用。'); }
  }
  async function openDetail(id, update = true) {
    try { if(!figures.has(id)) { await loadIndex(); const item=C.figures.find(x=>x.id===id); if(item) await loadRecords([item]); } }
    catch { toast('图表详情加载失败，请稍后重试。'); return; }
    const f = figures.get(id); if (!f) { toast('该图表不存在或已撤下。'); return; }
    const p = papers.get(f.paper_id); lastFocused = document.activeElement;
    $('#detail-content').innerHTML = `<div class="detail-image"><img src="${esc(imageURL(f.image))}" alt="${esc(f.caption)}"></div><div class="detail-body"><div class="card-meta"><span class="pill">${labels[f.kind]}</span>${esc(p.venue)} ${p.year} · ${esc(f.number)} · ${f.reviewed ? '人工精选' : '出处已核实 · 待精选'}</div><h2>${esc(p.title)}</h2><p class="caption">${esc(f.caption)}</p>${f.note ? `<p class="detail-note">${esc(f.note)}</p>` : ''}<label class="zoom-control">图片缩放 <input id="zoom" type="range" min="100" max="250" step="25" value="100"><output id="zoom-value">100%</output></label><div class="detail-actions"><button class="button" data-save="${esc(f.id)}" aria-pressed="${saved.has(f.id)}">${saved.has(f.id) ? '已收藏' : '收藏'}</button>${link(f.source_url,'查看原图出处','button secondary')}${link(p.source_url,'论文来源','button secondary')}<button class="button secondary" data-cite="${esc(p.id)}">复制引用</button><button class="button secondary" id="share">复制分享链接</button></div><p class="detail-meta">作者：${esc(p.authors.join(', '))}<br>版本：${esc(f.version)}${f.page ? ` · PDF 第 ${esc(f.page)} 页` : ''}<br>署名：${esc(f.attribution)}<br>许可：${esc(f.license)} · ${link(f.rights_url,'查看展示依据')}<br>处理：${esc(f.modifications || '未修改原图内容')}</p></div>`;
    imageErrors($('#detail-content'));
    $('#zoom').addEventListener('input', e => { const image = $('.detail-image img'); if(image) image.style.width = e.target.value + '%'; $('#zoom-value').textContent = e.target.value + '%'; });
    $('#share').onclick = () => { const url = new URL(location.href); url.searchParams.set('figure',f.id); copy(url.href); };
    if (!$('#detail').open) $('#detail').showModal();
    if (update) writeURL(f.id);
  }
  function reset() { setState({kind:'',q:'',year:'',venue:'',chart:'',core:false,curated:false,sort:'new'}); }
  $('#venue').insertAdjacentHTML('beforeend', C.scope.venues.map(v => `<option value="${v.id}">${v.id} · ${v.type === 'journal' ? '期刊' : '会议'}</option>`).join(''));
  $('#chart').insertAdjacentHTML('beforeend', (C.charts || [...new Set(C.figures.map(f => f.chart_type).filter(Boolean))].sort()).map(t => `<option value="${esc(t)}">${esc(t)}</option>`).join(''));
  $('#stat-figures').textContent = totals.figures; $('#stat-papers').textContent = totals.papers; $('#stat-venues').textContent = C.scope.venues.length; $('#saved-count').textContent = saved.size;
  $('#update-status').textContent = C.status.last_attempt ? `最近采集 ${C.status.last_attempt.slice(0,10)}${C.status.errors?.length ? ' · 部分来源失败' : ''} · 持续补充中` : '初始索引 · 定时采集尚未运行';
  document.addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    if (b.dataset.view) setState({view:b.dataset.view});
    if ('kind' in b.dataset) setState({kind:b.dataset.kind});
    if (b.dataset.open) openDetail(b.dataset.open);
    if (b.dataset.save) save(b.dataset.save);
    if (b.dataset.cite) copy(citation(papers.get(b.dataset.cite)));
    if ('reset' in b.dataset) reset();
  });
  for (const id of ['year','venue','chart','sort']) $('#'+id).addEventListener('change', e => setState({[id]:e.target.value}));
  for (const id of ['core','curated']) $('#'+id).addEventListener('change', e => setState({[id]:e.target.checked}));
  let searchTimer; $('#search').addEventListener('input', e => {clearTimeout(searchTimer);const value=e.target.value;searchTimer=setTimeout(()=>setState({q:value}),180);});
  $('#reset').onclick = reset;
  $('#more').onclick = () => { limit += 24; render(); };
  $('#close-detail').onclick = () => $('#detail').close();
  $('#detail').addEventListener('click', e => { if (e.target === $('#detail')) { const r = e.target.getBoundingClientRect(); if(e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) e.target.close(); } });
  $('#detail').addEventListener('close', () => { writeURL(); lastFocused?.focus(); });
  $('#export').onclick = async () => { let entries; try { await loadIndex(); const selected=C.figures.filter(f=>saved.has(f.id)); await loadRecords(selected); entries=selected.map(f=>({figure:figures.get(f.id),paper:papers.get(f.paper_id)})); } catch {toast('导出失败，请稍后重试。');return;} const blob = new Blob([JSON.stringify({exported_at:new Date().toISOString(),entries},null,2)],{type:'application/json'}); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href=url; a.download='se-figure-atlas-collection.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url),1000); };
  document.addEventListener('keydown', e => { if(e.key==='/' && !/INPUT|TEXTAREA|SELECT/.test(e.target.tagName) && !$('#detail').open) { e.preventDefault(); $('#search').focus(); } });
  window.addEventListener('popstate',readURL);
  readURL();
})();
