/* Modal générique réutilisable */
window.ROSOModal = (function(){
  let overlay, panel, titleEl, bodyEl, closeBtn;

  function build(){
    overlay = document.createElement('div');
    overlay.className = 'roso-modal-overlay';
    overlay.innerHTML = `
      <div class="roso-modal" role="dialog" aria-modal="true">
        <div class="roso-modal-head">
          <h3 class="roso-modal-title"></h3>
          <button class="roso-modal-close" aria-label="Fermer">✕</button>
        </div>
        <div class="roso-modal-body"></div>
      </div>`;
    document.body.appendChild(overlay);
    panel = overlay.querySelector('.roso-modal');
    titleEl = overlay.querySelector('.roso-modal-title');
    bodyEl = overlay.querySelector('.roso-modal-body');
    closeBtn = overlay.querySelector('.roso-modal-close');

    closeBtn.addEventListener('click', close);
    overlay.addEventListener('click', (e) => { if(e.target === overlay) close(); });
    document.addEventListener('keydown', (e) => { if(e.key === 'Escape') close(); });
  }

  function open(title, contentNodeOrHTML){
    if(!overlay) build();
    titleEl.textContent = title;
    bodyEl.innerHTML = '';
    if(typeof contentNodeOrHTML === 'string'){
      bodyEl.innerHTML = contentNodeOrHTML;
    } else if (contentNodeOrHTML instanceof Node){
      bodyEl.appendChild(contentNodeOrHTML);
    }
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
    return bodyEl;
  }

  function close(){
    if(!overlay) return;
    overlay.classList.remove('open');
    document.body.style.overflow = '';
  }

  function setBusy(msg){
    if(!bodyEl) return;
    bodyEl.innerHTML = `<div class="roso-modal-loading"><span class="spinner"></span>${msg || 'Chargement…'}</div>`;
  }

  return { open, close, setBusy, get body(){ return bodyEl; } };
})();
