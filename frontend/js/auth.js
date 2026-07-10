(function(){
  const API = '/api';
  const tabs = document.querySelectorAll('.auth-tab');
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');
  const errorBox = document.getElementById('authError');

  tabs.forEach(tab => tab.addEventListener('click', () => {
    tabs.forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    const isLogin = tab.dataset.tab === 'login';
    loginForm.style.display = isLogin ? 'flex' : 'none';
    registerForm.style.display = isLogin ? 'none' : 'flex';
    errorBox.style.display = 'none';
  }));

  function showError(msg){
    errorBox.textContent = msg;
    errorBox.style.display = 'block';
  }

  async function submit(url, form){
    const data = {};
    new FormData(form).forEach((v,k) => data[k] = v);
    try{
      const res = await fetch(`${API}/auth/${url}`, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        credentials: 'include',
        body: JSON.stringify(data),
      });
      const body = await res.json();
      if(!res.ok){
        showError(body.detail || 'Erreur inconnue');
        return;
      }
      window.location.href = '/index.html';
    }catch(err){
      showError('Impossible de contacter le serveur : ' + err.message);
    }
  }

  loginForm.addEventListener('submit', (e) => { e.preventDefault(); submit('login', loginForm); });
  registerForm.addEventListener('submit', (e) => { e.preventDefault(); submit('register', registerForm); });

  // Si déjà connecté, redirige direct vers l'app
  fetch(`${API}/auth/me`, {credentials:'include'})
    .then(res => { if(res.ok) window.location.href = '/index.html'; })
    .catch(() => {});
})();
