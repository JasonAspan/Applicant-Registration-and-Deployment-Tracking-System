// Client-side JS for ATS
// Keep validation/alerts, dashboard table enhance, applicant fetch

function showAlert(message, type = 'info') {
  const alert = document.createElement('div');
  alert.className = `alert alert-${type}`;
  alert.textContent = message;
  const container = document.querySelector('.container') || document.body;
  container.insertBefore(alert, container.firstChild);
  setTimeout(() => alert.remove(), 5000);
}

// Refresh button
document.addEventListener('DOMContentLoaded', () => {
  const refreshBtn = document.querySelector('#refresh-list');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      location.reload();
    });
  }
});

// Batch select helpers - handle both select-all checkboxes
document.addEventListener('DOMContentLoaded', () => {
  const selectAll = document.querySelector('#select-all');
  const selectAllTable = document.querySelector('#select-all-table');
  const checkboxes = document.querySelectorAll('input[name="applicant_ids"]');
  
  function updateAllCheckboxes(checked) {
    checkboxes.forEach(box => { box.checked = checked; });
    if (selectAll) selectAll.checked = checked;
    if (selectAllTable) selectAllTable.checked = checked;
  }
  
  if (selectAll) {
    selectAll.addEventListener('change', () => {
      updateAllCheckboxes(selectAll.checked);
    });
  }
  
  if (selectAllTable) {
    selectAllTable.addEventListener('change', () => {
      updateAllCheckboxes(selectAllTable.checked);
    });
  }
  
  // Update select-all checkboxes when individual checkboxes change
  checkboxes.forEach(box => {
    box.addEventListener('change', () => {
      const allChecked = Array.from(checkboxes).every(b => b.checked);
      const someChecked = Array.from(checkboxes).some(b => b.checked);
      if (selectAll) selectAll.checked = allChecked;
      if (selectAllTable) selectAllTable.checked = allChecked;
    });
  });
});

// Dashboard filter dropdown
document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('#toggle-filters');
  const dropdown = document.querySelector('#filter-dropdown');
  if (!toggle || !dropdown) return;

  toggle.addEventListener('click', () => {
    dropdown.classList.toggle('hidden');
  });

  document.addEventListener('click', (e) => {
    if (dropdown.classList.contains('hidden')) return;
    if (dropdown.contains(e.target) || toggle.contains(e.target)) return;
    dropdown.classList.add('hidden');
  });
});

// Dashboard user hamburger menu
document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('#user-menu-toggle');
  const menu = document.querySelector('#user-menu');
  if (!toggle || !menu) return;

  toggle.addEventListener('click', () => {
    const nextHidden = menu.classList.toggle('hidden');
    toggle.setAttribute('aria-expanded', (!nextHidden).toString());
  });

  document.addEventListener('click', (e) => {
    if (menu.classList.contains('hidden')) return;
    if (menu.contains(e.target) || toggle.contains(e.target)) return;
    menu.classList.add('hidden');
    toggle.setAttribute('aria-expanded', 'false');
  });
});

// Fix export and delete button functionality
document.addEventListener('DOMContentLoaded', () => {
  const batchForm = document.querySelector('#batch-form');
  const exportBtn = document.querySelector('.export-btn');
  const deleteBtn = document.querySelector('.delete-btn');
  
  if (exportBtn) {
    exportBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const checked = document.querySelectorAll('input[name="applicant_ids"]:checked');
      if (checked.length === 0) {
        alert('Please select at least one applicant to export.');
        return;
      }
      if (batchForm) {
        batchForm.method = 'POST';
        batchForm.action = exportBtn.getAttribute('formaction') || '';
        batchForm.submit();
      }
    });
  }
  
  if (deleteBtn) {
    deleteBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const checked = document.querySelectorAll('input[name="applicant_ids"]:checked');
      if (checked.length === 0) {
        alert('Please select at least one applicant to delete.');
        return;
      }
      if (!confirm('Are you sure you want to delete ' + checked.length + ' applicant(s)?')) {
        return;
      }
      if (batchForm) {
        batchForm.method = 'POST';
        batchForm.action = deleteBtn.getAttribute('formaction') || '';
        batchForm.submit();
      }
    });
  }
});

// Logout confirmation (if direct access)
document.addEventListener('DOMContentLoaded', () => {
  const logoutLinks = document.querySelectorAll('a[href="/logout"]');
  logoutLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      if (!confirm('Logout?')) e.preventDefault();
    });
  });
});

// Dashboard filter dropdown
document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('#toggle-filters');
  const dropdown = document.querySelector('#filter-dropdown');
  if (!toggle || !dropdown) return;

  toggle.addEventListener('click', () => {
    dropdown.classList.toggle('hidden');
  });

  document.addEventListener('click', (e) => {
    if (dropdown.classList.contains('hidden')) return;
    if (dropdown.contains(e.target) || toggle.contains(e.target)) return;
    dropdown.classList.add('hidden');
  });
});

// Logout confirmation (if direct access)
document.addEventListener('DOMContentLoaded', () => {
  const logoutLinks = document.querySelectorAll('a[href="/logout"]');
  logoutLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      if (!confirm('Logout?')) e.preventDefault();
    });
  });
});

