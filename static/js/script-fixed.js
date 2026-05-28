// Clean ATS JS - Fixed filter toggle (no duplicates)
function showAlert(message, type = 'info') {
  document.querySelectorAll('.alert.client-alert').forEach(existing => existing.remove());
  const alert = document.createElement('div');
  alert.className = `alert alert-${type} client-alert`;
  alert.textContent = message;
  document.body.appendChild(alert);
  setTimeout(() => alert.remove(), 2000);
}

document.addEventListener('DOMContentLoaded', () => {
  let announcements = [];

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (char) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    }[char]));
  }

  function formatAnnouncementTime(value) {
    return value ? new Date(value).toLocaleString() : '';
  }

  function renderAnnouncements(unreadCount = 0) {
    const list = document.querySelector('#announcementList');
    const count = document.querySelector('#announcementCount');
    if (!list || !count) return;

    count.textContent = unreadCount > 9 ? '9+' : String(unreadCount);
    count.classList.toggle('hidden', unreadCount === 0);

    if (!announcements.length) {
      list.innerHTML = '<div class="announcement-empty">No notifications.</div>';
      return;
    }

    list.innerHTML = announcements.map((announcement) => `
      <button type="button" class="announcement-item ${announcement.is_read ? '' : 'unread'}" data-announcement-id="${announcement.id}">
        <span class="announcement-item-title">${escapeHtml(announcement.title)}</span>
        <span class="announcement-item-meta">${escapeHtml(announcement.created_by)} - ${escapeHtml(formatAnnouncementTime(announcement.created_at))}</span>
      </button>
    `).join('');
  }

  async function loadAnnouncements() {
    const list = document.querySelector('#announcementList');
    if (!list) return;
    try {
      const response = await fetch('/api/announcements', { headers: { 'Accept': 'application/json' } });
      if (!response.ok) return;
      const data = await response.json();
      announcements = data.announcements || [];
      renderAnnouncements(data.unread_count || 0);
    } catch (error) {
      // Keep the header usable if announcements are temporarily unavailable.
    }
  }

  async function markAnnouncementRead(announcementId) {
    await fetch(`/api/announcements/${announcementId}/read`, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-CSRFToken': window.ATS_CSRF_TOKEN || ''
      },
      body: '{}'
    });
  }

  function showAnnouncementModal(announcement) {
    const modal = document.querySelector('#announcementModal');
    const title = document.querySelector('#announcementModalTitle');
    const message = document.querySelector('#announcementModalMessage');
    const meta = document.querySelector('#announcementModalMeta');
    if (!modal || !title || !message || !meta) return;

    title.textContent = announcement.title;
    message.textContent = announcement.message;
    meta.textContent = `${announcement.created_by} - ${formatAnnouncementTime(announcement.created_at)}`;
    modal.classList.remove('hidden');
  }

  function closeAnnouncementModal() {
    const modal = document.querySelector('#announcementModal');
    if (modal) modal.classList.add('hidden');
  }

  // Announcement menu
  const announcementBell = document.querySelector('#announcementBell');
  const announcementMenu = document.querySelector('#announcementMenu');
  if (announcementBell && announcementMenu) {
    loadAnnouncements();
    window.setInterval(loadAnnouncements, 30000);

    announcementBell.addEventListener('click', (e) => {
      e.stopPropagation();
      const isHidden = announcementMenu.classList.toggle('hidden');
      announcementBell.setAttribute('aria-expanded', String(!isHidden));
    });

    document.addEventListener('click', (e) => {
      if (!announcementMenu.contains(e.target) && !announcementBell.contains(e.target)) {
        announcementMenu.classList.add('hidden');
        announcementBell.setAttribute('aria-expanded', 'false');
      }
    });

    announcementMenu.addEventListener('click', (event) => {
      const item = event.target.closest('[data-announcement-id]');
      if (!item) return;
      const announcementId = Number(item.dataset.announcementId);
      const announcement = announcements.find((entry) => entry.id === announcementId);
      if (!announcement) return;

      showAnnouncementModal(announcement);
      announcement.is_read = true;
      renderAnnouncements(announcements.filter((entry) => !entry.is_read).length);
      markAnnouncementRead(announcementId).catch(() => {});
    });
  }

  const announcementClose = document.querySelector('#announcementModalClose');
  const announcementModal = document.querySelector('#announcementModal');
  if (announcementClose) announcementClose.addEventListener('click', closeAnnouncementModal);
  if (announcementModal) {
    announcementModal.addEventListener('click', (event) => {
      if (event.target === announcementModal) closeAnnouncementModal();
    });
  }

  // Filter toggle - FIXED
  const filterToggle = document.querySelector('#toggle-filters');
  const filterDropdown = document.querySelector('#filter-dropdown');
  if (filterToggle && filterDropdown) {
    filterToggle.addEventListener('click', (e) => {
      e.stopPropagation();
      filterDropdown.classList.toggle('hidden');
    });
    document.addEventListener('click', (e) => {
      if (!filterDropdown.contains(e.target) && !filterToggle.contains(e.target)) {
        filterDropdown.classList.add('hidden');
      }
    });
  }

  // User menu toggle
  const userToggle = document.querySelector('#user-menu-toggle');
  const userMenu = document.querySelector('#user-menu');
  if (userToggle && userMenu) {
    userToggle.addEventListener('click', () => {
      userMenu.classList.toggle('hidden');
    });
    document.addEventListener('click', (e) => {
      if (!userMenu.contains(e.target) && !userToggle.contains(e.target)) {
        userMenu.classList.add('hidden');
      }
    });
  }

  // Batch checkboxes
  const selectAll = document.querySelector('#select-all');
  const selectAllTable = document.querySelector('#select-all-table');
  const checkboxes = document.querySelectorAll('input[name=\"applicant_ids\"]');
  
  function updateAllCheckboxes(checked) {
    checkboxes.forEach(box => box.checked = checked);
    if (selectAll) selectAll.checked = checked;
    if (selectAllTable) selectAllTable.checked = checked;
  }
  
  if (selectAll) selectAll.addEventListener('change', () => updateAllCheckboxes(selectAll.checked));
  if (selectAllTable) selectAllTable.addEventListener('change', () => updateAllCheckboxes(selectAllTable.checked));
  
  checkboxes.forEach(box => box.addEventListener('change', () => {
    const allChecked = Array.from(checkboxes).every(b => b.checked);
    if (selectAll) selectAll.checked = allChecked;
    if (selectAllTable) selectAllTable.checked = allChecked;
  }));

  // Refresh
  const refreshBtn = document.querySelector('#refresh-list');
  if (refreshBtn) refreshBtn.addEventListener('click', () => location.reload());

  // Search clear/back control
  const quickSearchInput = document.querySelector('#quick-search-input');
  const quickSearchClear = document.querySelector('#quick-search-clear');
  if (quickSearchInput && quickSearchClear) {
    const toggleSearchClear = () => {
      quickSearchClear.classList.toggle('hidden', quickSearchInput.value.trim() === '');
    };
    toggleSearchClear();
    quickSearchInput.addEventListener('input', toggleSearchClear);
  }

  // Applicant status dropdown
  document.querySelectorAll('.applicant-status-select').forEach(select => {
    select.addEventListener('change', () => {
      const action = select.dataset.statusAction;
      const csrfInput = document.querySelector('input[name="csrf_token"]');
      if (!action || !csrfInput) return;

      const form = document.createElement('form');
      form.method = 'POST';
      form.action = action;
      form.style.display = 'none';

      const csrf = document.createElement('input');
      csrf.type = 'hidden';
      csrf.name = 'csrf_token';
      csrf.value = csrfInput.value;
      form.appendChild(csrf);

      const status = document.createElement('input');
      status.type = 'hidden';
      status.name = 'status';
      status.value = select.value;
      form.appendChild(status);

      document.body.appendChild(form);
      form.submit();
    });
  });

  // Batch actions
  const batchForm = document.querySelector('#batch-form');
  const batchActionButtons = document.querySelectorAll('[data-batch-action]');
  const forwardBtn = document.querySelector('.forward-btn');
  const forwardUserSelect = document.querySelector('.forward-user-select');
  
  function selectedApplicants() {
    return document.querySelectorAll('input[name=\"applicant_ids\"]:checked');
  }

  batchActionButtons.forEach(button => {
    button.addEventListener('click', (e) => {
      e.preventDefault();
      const action = button.dataset.batchAction || 'continue';
      const checked = selectedApplicants();
      if (checked.length === 0) {
        showAlert(`Please select applicant to ${action}.`, 'error');
        return;
      }
      if (action === 'delete' && !confirm(`Delete ${checked.length} applicant(s)?`)) return;
      if (batchForm) {
        batchForm.method = 'POST';
        batchForm.action = button.formAction;
        batchForm.submit();
      }
    });
  });

  if (forwardBtn) {
    forwardBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const checked = selectedApplicants();
      if (checked.length === 0) return showAlert('Please select applicant to forward.', 'error');
      if (!forwardUserSelect || !forwardUserSelect.value) return showAlert('Select a user to forward to.', 'error');
      if (batchForm) {
        batchForm.method = 'POST';
        batchForm.action = forwardBtn.formAction;
        batchForm.submit();
      }
    });
  }

  // Logout confirm
  document.querySelectorAll('a[href=\"/logout\"]').forEach(link => {
    link.addEventListener('click', (e) => {
      if (!confirm('Logout?')) e.preventDefault();
    });
  });
});
