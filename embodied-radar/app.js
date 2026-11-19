const labels={news:'行业新闻',technology:'技术 / 论文',company:'企业 / 融资 / 订单',jobs:'招聘线索',events:'大会活动',interviews:'人物访谈',application:'真实应用',industry:'政策 / 产业'};
let allItems=[],filter='all',visibleLimit=25;
const $=s=>document.querySelector(s);
function esc(s=''){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function confidenceLabel(x){return x.confidence||x.evidence_type||'来源待核验';}
function render(){
 const q=$('#searchInput').value.trim().toLowerCase();
 let items=allItems.filter(x=>(filter==='all'||x.category===filter)&&(!q||[x.title,x.summary,x.source,x.tags?.join(' ')].join(' ').toLowerCase().includes(q)));
 items.sort((a,b)=>$('#sortSelect').value==='oldest'?a.date.localeCompare(b.date):b.date.localeCompare(a.date));
 $('#resultMeta').textContent=`当前显示 ${Math.min(visibleLimit,items.length)} / ${items.length} 条 · 分类：${filter==='all'?'全部动态':labels[filter]}`;
 $('#feed').innerHTML=items.slice(0,visibleLimit).map(x=>`<article class="story"><div class="story-top"><span class="tag">${esc(labels[x.category]||'行业动态')}</span><span class="date">${esc(x.date||'日期未提供')}</span></div><h3>${esc(x.title)}</h3><p>${esc(x.summary||'摘要未提供，请打开来源核实。')}</p><div class="story-foot"><span class="source">${esc(x.source||'来源待核实')} <span class="confidence">${esc(confidenceLabel(x))}</span></span><a href="${esc(x.url||'#')}" target="_blank" rel="noopener noreferrer">打开原始来源 ↗</a></div></article>`).join('');
 $('#empty').hidden=items.length>0;
 $('#loadMore').hidden=items.length<=visibleLimit;
 $('#metrics').innerHTML=[['动态条目',allItems.length],['技术 / 论文',allItems.filter(x=>x.category==='technology').length],['企业动态',allItems.filter(x=>x.category==='company').length],['招聘线索',allItems.filter(x=>x.category==='jobs').length]].map(x=>`<div class="metric"><strong>${x[1]}</strong><span>${x[0]}</span></div>`).join('');
 document.querySelectorAll('#tabs button').forEach(b=>b.classList.toggle('active',b.dataset.filter===filter));
}
async function load(){
 try{
  const r=await fetch('data/news.json?ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);
  const d=await r.json();allItems=d.items||[];visibleLimit=25;
  const updated=d.updated_at||'时间未提供';
  $('#updateStatus').textContent=`数据更新：${updated} · ${d.timezone||'来源时区'}`;
  render();
 }catch(e){$('#updateStatus').textContent='数据读取失败';$('#feed').innerHTML='<div class="empty">暂时无法读取数据，请稍后重试。</div>';}
}
$('#tabs').addEventListener('click',e=>{const b=e.target.closest('button[data-filter]');if(!b)return;filter=b.dataset.filter;visibleLimit=25;render();});
$('#searchInput').addEventListener('input',()=>{visibleLimit=25;render();});
$('#sortSelect').addEventListener('change',render);
$('#refreshBtn').addEventListener('click',load);
$('#loadMore').addEventListener('click',()=>{visibleLimit+=25;render();});
load();
