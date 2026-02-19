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

function showToast(message, isError = false, isWarning = false) {
  toast.textContent = message;
  
  if (isError) {
    toast.style.background = '#7f1d1d'; // Red for errors
  } else if (isWarning) {
    toast.style.background = '#854d0e'; // Amber/yellow for warnings (already exists)
  } else {
    toast.style.background = '#064e3b'; // Green for success
  }
  
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3000);
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

function resultCardTemplate(item) {
  const title = escapeHtml(item.title || 'Untitled');
  const year = escapeHtml(item.year || '');
  const overview = escapeHtml(item.overview || 'No description available.');
  const poster = escapeHtml(item.poster || '');
  const encodedItem = encodeURIComponent(JSON.stringify(item));

  return `
    <article class="result-card">
      <img class="poster" src="${poster}" alt="${title}" loading="lazy" onerror="this.style.display='none'" />
      <div class="card-content">
        <h4>${title} ${year ? `(${year})` : ''}</h4>
        <p>${overview}</p>
        <button data-item="${encodedItem}">➕ Add Request</button>
      </div>
    </article>
  `;
}

function updateEmptyState(message = 'No results found.') {
  emptyState.textContent = message;
  emptyState.classList.remove('hidden');
}

async function runSearch() {
  const q = searchInput.value.trim();
  if (q.length < 2) {
    results.innerHTML = '';
    updateEmptyState('🔍 Start typing to search for movies, TV shows, or books.');
    return;
  }

  const type = mediaType.value;
  const typeDisplay = {
    'movies': 'movies',
    'tv': 'TV shows',
    'books': 'books',
    'audiobooks': 'audiobooks'
  }[type] || 'media';

  try {
    results.innerHTML = '<div class="loading">Searching...</div>';
    emptyState.classList.add('hidden');
    
    const response = await fetch(`/api/search?type=${encodeURIComponent(type)}&q=${encodeURIComponent(q)}`);
    if (!response.ok) {
      throw new Error('Search failed');
    }

    const payload = await parseApiResponse(response);
    const items = Array.isArray(payload) ? payload : [];

    if (!items.length) {
      results.innerHTML = '';
      updateEmptyState(`😕 No ${typeDisplay} found matching "${escapeHtml(q)}".`);
      return;
    }

    emptyState.classList.add('hidden');
    results.innerHTML = items.map(resultCardTemplate).join('');

    results.querySelectorAll('button[data-item]').forEach((btn) => {
      btn.addEventListener('click', (event) => submitRequest(btn.dataset.item, event));
    });
  } catch (error) {
    results.innerHTML = '';
    updateEmptyState('⚠️ Search unavailable right now.');
    showToast(error.message, true);
  }
}

async function submitRequest(encodedItem, event) {
  let item;
  try {
    item = JSON.parse(decodeURIComponent(encodedItem));
  } catch {
    showToast('❌ Unable to parse selected item.', true);
    return;
  }

  // Disable the button temporarily to prevent double-clicks
  const button = event?.target;
  if (button) {
    button.disabled = true;
    button.textContent = '⏳ Adding...';
  }

  try {
    const response = await fetch('/api/request', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(item),
    });

    const data = await parseApiResponse(response);
    
    if (!response.ok) {
      // Check if it's a 409 (Conflict) which means already exists
      if (response.status === 409) {
        // Show a warning toast for existing items
        showToast(data.error || `⚠️ '${item.title}' already exists!`, false, true);
      } else {
        throw new Error(data.error || 'Request failed');
      }
    } else {
      // Success!
      showToast(data.message || `✅ Added to ${data.target}`);
    }
  } catch (error) {
    showToast(error.message, true);
  } finally {
    // Re-enable the button
    if (button) {
      button.disabled = false;
      button.textContent = '➕ Add Request';
    }
  }
}

loginBtn.addEventListener('click', login);

searchInput.addEventListener('input', () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(runSearch, 300);
});

mediaType.addEventListener('change', () => {
  results.innerHTML = '';
  if (searchInput.value.trim().length >= 2) {
    runSearch();
  } else {
    updateEmptyState(`🔍 Start typing to search for ${mediaType.value}.`);
  }
});

window.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !loginModal.classList.contains('hidden')) {
    login();
  }
});

// Initialize empty state
updateEmptyState('🔍 Login and start typing to search for movies, TV shows, or books.');
