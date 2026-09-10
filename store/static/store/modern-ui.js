
/* ShopVibe modern UI enhancements.
   Browser-local features intentionally require no database/API changes. */
(function(){
  'use strict';
  const KEY='shopvibe_saved_products_v1', RECENT='shopvibe_recent_products_v1';
  const read=(key)=>{ try{return JSON.parse(localStorage.getItem(key)||'[]')}catch(e){return[]} };
  const write=(key,v)=>localStorage.setItem(key,JSON.stringify(v));

  function saved(){return read(KEY)}
  function updateCounts(){
    const count=saved().length;
    document.querySelectorAll('[data-sv-saved-count]').forEach(el=>{
      el.textContent=count; el.hidden=count===0;
    });
    document.querySelectorAll('[data-sv-saved-icon]').forEach(el=>{
      const id=String(el.closest('[data-product-id]')?.dataset.productId||'');
      el.classList.toggle('saved', !!id && saved().some(p=>String(p.id)===id));
      const i=el.querySelector('i'); if(i) i.className=el.classList.contains('saved')?'bi bi-heart-fill':'bi bi-heart';
      el.setAttribute('aria-pressed',el.classList.contains('saved'));
    });
  }
  function toggleSave(data){
    let list=saved(), idx=list.findIndex(p=>String(p.id)===String(data.id));
    if(idx>=0){list.splice(idx,1); toast('Removed from saved');}
    else {list.unshift(data); list=list.slice(0,50); toast('Saved for later');}
    write(KEY,list); updateCounts(); renderDrawer();
  }
  function toast(msg){
    let t=document.getElementById('sv-toast');
    if(!t){t=document.createElement('div');t.id='sv-toast';t.style.cssText='position:fixed;left:50%;bottom:28px;transform:translateX(-50%);z-index:1400;background:var(--card);color:var(--tx);border:1px solid var(--border);padding:10px 16px;border-radius:999px;box-shadow:0 8px 24px rgba(0,0,0,.18);font-size:13px';document.body.appendChild(t)}
    t.textContent=msg;t.style.opacity='1';clearTimeout(t._timer);t._timer=setTimeout(()=>t.style.opacity='0',1800);
  }
  function renderDrawer(){
    const box=document.querySelector('[data-sv-saved-list]'); if(!box)return;
    const list=saved();
    if(!list.length){box.innerHTML='<div class="sv-empty"><i class="bi bi-heart fs-2 d-block mb-2"></i><div>No saved products yet</div><small>Tap the heart on any product to save it.</small></div>';return}
    box.innerHTML=list.map(p=>{
      const url = p.url || p.product_url || '';
      const image = p.image || '';
      const content = `
        <img src="${esc(image)}" alt="${esc(p.name || 'Saved product')}" loading="lazy" onerror="this.style.display='none'">
        <div class="grow"><div class="name">${esc(p.name || 'Saved product')}</div><div class="price">${esc(p.price || '')}</div></div>`;
      return `<div class="sv-saved-item">
        ${url ? `<a class="sv-saved-product" href="${esc(url)}" aria-label="Open ${esc(p.name || 'saved product')}">${content}</a>` : content}
        ${url ? `<a class="btn btn-sm btn-primary" href="${esc(url)}" aria-label="View ${esc(p.name || 'saved product')}"><i class="bi bi-arrow-right"></i></a>` : ''}
        <button class="sv-remove" type="button" data-sv-remove="${esc(p.id)}" aria-label="Remove"><i class="bi bi-x-lg"></i></button>
      </div>`;
    }).join('');
    box.querySelectorAll('[data-sv-remove]').forEach(b=>b.addEventListener('click',()=>{
      write(KEY,saved().filter(p=>String(p.id)!==String(b.dataset.svRemove)));updateCounts();renderDrawer();
    }));
  }
  function esc(v){return String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]))}
  // Make the entire saved product (image + name + price) clickable.
  // Keep the existing action buttons independent.
  if (!document.getElementById('sv-saved-product-style')) {
    const style=document.createElement('style');
    style.id='sv-saved-product-style';
    style.textContent='.sv-saved-product{display:flex;align-items:center;gap:12px;flex:1;min-width:0;color:inherit;text-decoration:none}.sv-saved-product:hover .name{text-decoration:underline}.sv-saved-product img{width:58px;height:58px;object-fit:contain;border-radius:10px;flex:0 0 58px;background:var(--surface,#f5f5f5)}';
    document.head.appendChild(style);
  }

  function initSavedButtons(){
    document.querySelectorAll('[data-sv-save]').forEach(btn=>{
      if(btn.dataset.svBound)return; btn.dataset.svBound='1';
      btn.addEventListener('click',e=>{
        e.preventDefault();e.stopPropagation();
        const card=btn.closest('[data-product-id]'); if(!card)return;
        toggleSave({id:card.dataset.productId,name:card.dataset.productName,image:card.dataset.productImage,url:card.dataset.productUrl,price:card.dataset.productPrice});
      });
    });
    updateCounts();
  }

  function recordCurrentProduct(){
    const el=document.querySelector('[data-sv-current-product]'); if(!el)return;
    const p={id:el.dataset.id,name:el.dataset.name,image:el.dataset.image,url:location.href,price:el.dataset.price};
    let list=read(RECENT).filter(x=>String(x.id)!==String(p.id)); list.unshift(p);write(RECENT,list.slice(0,12));
  }
  function renderRecent(){
    const box=document.querySelector('[data-sv-recent-list]'); if(!box)return;
    const list=read(RECENT);
    if(!list.length){box.closest('[data-sv-recent-section]')?.remove();return}
    box.innerHTML=list.map(p=>`<a class="sv-recent-card" href="${esc(p.url)}"><img src="${esc(p.image)}" alt="${esc(p.name)}" loading="lazy"><div class="info"><div class="name">${esc(p.name)}</div><div class="price">${esc(p.price)}</div></div></a>`).join('');
  }

  function initDrawer(){
    const drawer=document.querySelector('[data-sv-drawer]');if(!drawer)return;
    const open=()=>{drawer.classList.add('open');drawer.setAttribute('aria-hidden','false');renderDrawer();document.body.style.overflow='hidden'};
    const close=()=>{drawer.classList.remove('open');drawer.setAttribute('aria-hidden','true');document.body.style.overflow=''};
    document.querySelectorAll('[data-sv-open-saved]').forEach(b=>b.addEventListener('click',open));
    drawer.querySelectorAll('[data-sv-close]').forEach(b=>b.addEventListener('click',close));
    document.addEventListener('keydown',e=>{if(e.key==='Escape')close()});
  }

  function initBackTop(){
    const b=document.getElementById('sv-back-top');if(!b)return;
    window.addEventListener('scroll',()=>b.classList.toggle('show',scrollY>500),{passive:true});
    b.addEventListener('click',()=>scrollTo({top:0,behavior:'smooth'}));
  }

  document.addEventListener('DOMContentLoaded',()=>{
    initSavedButtons();recordCurrentProduct();renderRecent();initDrawer();initBackTop();
    document.querySelectorAll('img').forEach(img=>img.addEventListener('error',()=>img.classList.add('sv-img-error'),{once:true}));
  });
  window.ShopVibeUI={toggleSave,refresh:()=>{updateCounts();renderDrawer()}};
})();
