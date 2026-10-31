/* HELPUP - progressive enhancement. Every form also works without JavaScript. */
(function () {
  'use strict';

  var MAX_IMAGE_BYTES = 5 * 1024 * 1024;
  var IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
  var csrfToken = (document.querySelector('meta[name="csrf-token"]') || {}).content || '';

  function qs(sel, root) { return (root || document).querySelector(sel); }
  function qsa(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  // POST helper: sends the CSRF token and flags the request as AJAX so Django answers with JSON.
  function post(url, formData) {
    return fetch(url, {
      method: 'POST',
      body: formData || new FormData(),
      headers: { 'X-CSRFToken': csrfToken, 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
      credentials: 'same-origin'
    }).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        if (!res.ok) { var err = new Error(data.error || 'Something went wrong. Please try again.'); err.status = res.status; throw err; }
        return data;
      });
    });
  }

  function toast(message, kind) {
    var wrap = qs('.messages');
    if (!wrap) { wrap = document.createElement('div'); wrap.className = 'messages'; wrap.setAttribute('role', 'status'); document.body.appendChild(wrap); }
    var el = document.createElement('div');
    el.className = 'message ' + (kind || 'success');
    var text = document.createElement('span'); text.textContent = message;
    var close = document.createElement('button'); close.type = 'button'; close.className = 'message-x'; close.setAttribute('aria-label', 'Dismiss'); close.textContent = '×';
    el.appendChild(text); el.appendChild(close);
    wrap.appendChild(el);
    setTimeout(function () { el.remove(); }, 4500);
  }

  // ---- theme ----------------------------------------------------------------
  function syncThemeIcon() {
    var dark = document.documentElement.dataset.theme === 'dark';
    qsa('[data-theme-toggle] use').forEach(function (u) { u.setAttribute('href', dark ? '#i-sun' : '#i-moon'); });
  }
  syncThemeIcon();
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-theme-toggle]');
    if (!btn) return;
    var next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('helpup-theme', next); } catch (err) { /* private mode */ }
    syncThemeIcon();
  });

  // ---- flash messages ---------------------------------------------------------
  document.addEventListener('click', function (e) {
    var x = e.target.closest('.message-x');
    if (x) x.parentElement.remove();
  });
  qsa('.messages .message').forEach(function (m) { setTimeout(function () { m.remove(); }, 6000); });

  // close open dropdown menus when clicking elsewhere
  document.addEventListener('click', function (e) {
    qsa('details.usermenu[open], details.kebab[open]').forEach(function (d) { if (!d.contains(e.target)) d.removeAttribute('open'); });
  });

  // ---- likes ------------------------------------------------------------------
  document.addEventListener('submit', function (e) {
    var form = e.target.closest('[data-like-form]');
    if (!form) return;
    e.preventDefault();
    var btn = qs('button', form);
    if (btn.disabled) return;
    btn.disabled = true;
    post(form.action).then(function (data) {
      btn.classList.toggle('on', data.liked);
      btn.setAttribute('aria-pressed', data.liked ? 'true' : 'false');
      qs('[data-like-count]', btn).textContent = data.count;
      if (data.liked) { btn.classList.add('pop'); setTimeout(function () { btn.classList.remove('pop'); }, 400); }
    }).catch(function (err) { toast(err.message, 'error'); }).then(function () { btn.disabled = false; });
  });

  // ---- follow / unfollow --------------------------------------------------------
  document.addEventListener('submit', function (e) {
    var form = e.target.closest('[data-follow-form]');
    if (!form) return;
    e.preventDefault();
    var btn = qs('[data-follow-btn]', form);
    btn.disabled = true;
    post(form.action).then(function (data) {
      btn.textContent = data.following ? 'Following' : 'Follow';
      btn.classList.toggle('btn-ghost', data.following);
      btn.classList.toggle('is-following', data.following);
      btn.classList.toggle('btn-accent', !data.following);
      qsa('[data-followers-count]').forEach(function (el) { el.textContent = data.followers_count; });
    }).catch(function (err) { toast(err.message, 'error'); }).then(function () { btn.disabled = false; });
  });

  // ---- comments -----------------------------------------------------------------
  document.addEventListener('click', function (e) {
    var toggle = e.target.closest('[data-toggle-comments]');
    if (!toggle) return;
    var card = toggle.closest('[data-post]');
    var section = qs('[data-comments]', card);
    var open = section.hidden;
    section.hidden = !open;
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open && !section.dataset.loaded) {
      fetch(toggle.dataset.url, { headers: { 'X-Requested-With': 'XMLHttpRequest' }, credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          qs('[data-comments-list]', section).innerHTML = data.html;
          section.dataset.loaded = '1';
          qs('input[name=text]', section).focus();
        }).catch(function () { toast('Could not load comments.', 'error'); });
    } else if (open) {
      qs('input[name=text]', section).focus();
    }
  });

  document.addEventListener('submit', function (e) {
    var form = e.target.closest('[data-comment-form]');
    if (!form) return;
    e.preventDefault();
    var input = qs('input[name=text]', form);
    if (!input.value.trim()) { input.focus(); return; }
    var btn = qs('button', form);
    btn.disabled = true;
    post(form.action, new FormData(form)).then(function (data) {
      var list = qs('[data-comments-list]', form.closest('[data-comments]'));
      var empty = qs('.empty-note', list); if (empty) empty.remove();
      list.insertAdjacentHTML('beforeend', data.html);
      var added = list.lastElementChild; if (added) added.classList.add('fresh');
      input.value = '';
      setCommentCount(form.closest('[data-post]'), data.count);
    }).catch(function (err) { toast(err.message, 'error'); }).then(function () { btn.disabled = false; });
  });

  document.addEventListener('submit', function (e) {
    var form = e.target.closest('[data-comment-delete]');
    if (!form) return;
    e.preventDefault();
    if (!confirm('Delete this comment?')) return;
    post(form.action).then(function (data) {
      var card = form.closest('[data-post]');
      var node = form.closest('.comment');
      var list = node.parentElement;
      node.remove();
      if (!list.children.length) list.innerHTML = '<p class="meta empty-note">No comments yet. Start the conversation.</p>';
      setCommentCount(card, data.count);
    }).catch(function (err) { toast(err.message, 'error'); });
  });

  function setCommentCount(card, count) {
    qsa('[data-comment-count]', card).forEach(function (el) { el.textContent = count; });
  }

  // ---- image inputs: validate + preview -------------------------------------------
  document.addEventListener('change', function (e) {
    var input = e.target.closest('[data-image-input]');
    if (!input) return;
    var scope = input.closest('form');
    var errorBox = qs('[data-file-error]', scope);
    var preview = qs('[data-preview]', scope);
    var avatarSlot = qs('[data-avatar-preview]', scope);
    var file = input.files && input.files[0];
    if (errorBox) { errorBox.hidden = true; errorBox.textContent = ''; }
    if (!file) { if (preview) preview.hidden = true; return; }

    var problem = null;
    if (IMAGE_TYPES.indexOf(file.type) === -1) problem = 'Unsupported image type. Please choose a JPG, PNG, GIF or WebP file.';
    else if (file.size > MAX_IMAGE_BYTES) problem = 'That image is too large. The maximum size is 5 MB.';
    if (problem) {
      input.value = '';
      if (preview) preview.hidden = true;
      if (errorBox) { errorBox.textContent = problem; errorBox.hidden = false; } else { toast(problem, 'error'); }
      return;
    }
    var url = URL.createObjectURL(file);
    if (preview) { qs('img', preview).src = url; preview.hidden = false; }
    if (avatarSlot) { avatarSlot.innerHTML = '<img class="avatar xl" alt="New profile picture preview">'; qs('img', avatarSlot).src = url; }
  });

  document.addEventListener('click', function (e) {
    var clear = e.target.closest('[data-preview-clear]');
    if (!clear) return;
    var scope = clear.closest('form');
    var input = qs('[data-image-input]', scope);
    if (input) input.value = '';
    qs('[data-preview]', scope).hidden = true;
  });

  // ---- textarea helpers: auto-grow + character counter ------------------------------
  document.addEventListener('input', function (e) {
    var ta = e.target.closest('textarea');
    if (!ta) return;
    if (ta.hasAttribute('data-autogrow')) { ta.style.height = 'auto'; ta.style.height = Math.min(ta.scrollHeight, 240) + 'px'; }
    var form = ta.closest('form');
    var counter = form && qs('[data-counter]', form);
    if (counter && ta.name === 'text') counter.textContent = ta.value.length + ' / ' + (ta.maxLength > 0 ? ta.maxLength : 1000);
  });
  qsa('form textarea[name=text]').forEach(function (ta) { ta.dispatchEvent(new Event('input', { bubbles: true })); });

  // ---- composer: block empty posts client-side (the server validates too) -------------
  document.addEventListener('submit', function (e) {
    var form = e.target.closest('[data-composer]');
    if (!form) return;
    var text = qs('textarea[name=text]', form);
    var file = qs('[data-image-input]', form);
    var hasImage = (file && file.files && file.files.length) || qs('.image-preview.current', form);
    if (text && !text.value.trim() && !hasImage) {
      e.preventDefault();
      text.focus();
      toast('Write something or attach an image first.', 'error');
    }
  });

  // ---- nearby filters: submit when a select changes ----------------------------------
  qsa('[data-autosubmit] select').forEach(function (sel) {
    sel.addEventListener('change', function () {
      // changing the city invalidates the neighbourhood / interest choices
      if (sel.name === 'city') { var n = qs('[name=neighbourhood]', sel.form); var i = qs('[name=interest]', sel.form); if (n) n.value = ''; if (i) i.value = ''; }
      sel.form.submit();
    });
  });

  // ---- notification badge: poll for new activity -------------------------------------
  var badge = qs('[data-notif-badge]');
  if (badge) {
    setInterval(function () {
      if (document.hidden) return;
      fetch('/notifications/count/', { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) { if (d) { badge.textContent = d.count; badge.hidden = !d.count; } })
        .catch(function () { /* offline */ });
    }, 45000);
  }
})();
