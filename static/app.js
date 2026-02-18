const loginModal = document.getElementById('loginModal');
const loginBtn = document.getElementById('loginBtn');
const loginError = document.getElementById('loginError');
const searchInput = document.getElementById('searchInput');
const mediaType = document.getElementById('mediaType');
const results = document.getElementById('results');
const welcome = document.getElementById('welcome');
const toast = document.getElementById('toast');
const emptyState = document.getElementById('emptyState');

let authToken = '';
let debounceTimer;

function showToast(message, isError = false) {
  toast.textContent = message;
  toast.style.background = isError ? '#7f1d1d' : '#064e3b';
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2600);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

async function parseApiResponse(response) {
  const raw = await response.text();
  if (!raw) {
    return {};
  }

  try {
    return JSON.parse(raw);
  } catch {
    return { error: raw };
  }
}

async function login() {
  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value;

  if (!username || !password) {
    loginError.textContent = 'Username and password are required.';
    return;
  }

  loginBtn.disabled = true;
  loginError.textContent = '';

  try {
    const response = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    const data = await parseApiResponse(response);
    if (!response.ok) {
      throw new Error(data.error || 'Login failed');
    }

    authToken = data.token;
    welcome.textContent = `Signed in as ${data.user}`;
    loginModal.classList.add('hidden');
    loginModal.style.display = 'none';
    loginModal.setAttribute('aria-hidden', 'true');
    searchInput.disabled = false;
    searchInput.focus();
  } catch (error) {
    loginError.textContent = error.message;
  } finally {
    loginBtn.disabled = false;
  }
}

function cardTemplate(item) {
  const title = escapeHtml(item.title || 'Untitled');
  const year = escapeHtml(item.year || '');
  const overview = escapeHtml(item.overview || 'No description available.');
  const poster = escapeHtml(item.poster || '');
  const encodedItem = encodeURIComponent(JSON.stringify(item));

  return `
    <article class="card">
      <img class="poster" src="${poster}" alt="${title}" loading="lazy" onerror="this.style.display='none'" />
      <div class="card-content">
        <h4>${title} ${year ? `(${year})` : ''}</h4>
        <p>${overview}</p>
        <button data-item="${encodedItem}">Add Request</button>
      </div>
    </article>
  `;
}

function updateEmptyState(message = 'No results found.') {
  emptyState.textContent = message;
  emptyState.classList.toggle('hidden', false);
}

async function runSearch() {
  const q = searchInput.value.trim();
  if (q.length < 2) {
    results.innerHTML = '';
    updateEmptyState('Start typing to search.');
    return;
  }

  const type = mediaType.value;

  try {
    const response = await fetch(`/api/search?type=${encodeURIComponent(type)}&q=${encodeURIComponent(q)}`);
    if (!response.ok) {
      throw new Error('Search failed');
    }

    const items = await response.json();

    if (!items.length) {
      results.innerHTML = '';
      updateEmptyState('No results found.');
      return;
    }

    emptyState.classList.add('hidden');
    results.innerHTML = items.map(cardTemplate).join('');

    results.querySelectorAll('button[data-item]').forEach((btn) => {
      btn.addEventListener('click', () => submitRequest(btn.dataset.item));
    });
  } catch (error) {
    results.innerHTML = '';
    updateEmptyState('Search unavailable right now.');
    showToast(error.message, true);
  }
}

async function submitRequest(encodedItem) {
  const item = JSON.parse(decodeURIComponent(encodedItem));

  try {
    const response = await fetch('/api/request', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(item),
    });

    const data = await parseApiResponse(response);
    if (!response.ok) {
      throw new Error(data.error || 'Request failed');
    }

    showToast(`Added to ${data.target}`);
  } catch (error) {
    showToast(error.message, true);
  }
}

loginBtn.addEventListener('click', login);

searchInput.addEventListener('input', () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(runSearch, 260);
});

mediaType.addEventListener('change', runSearch);

window.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !loginModal.classList.contains('hidden')) {
    login();
  }
});
