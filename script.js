// Shared JS for Applicant Tracking System
// localStorage keys
const APPLICANTS_KEY = 'ats_applicants';
const EMPLOYEES_KEY = 'ats_employees';
const CURRENT_EMPLOYEE_KEY = 'ats_current_employee';

// Load applicants from localStorage
function loadApplicants() {
  const applicants = localStorage.getItem(APPLICANTS_KEY);
  return applicants ? JSON.parse(applicants) : [];
}

// Save applicant to localStorage
function saveApplicant(applicant) {
  const applicants = loadApplicants();
  applicants.push({
    id: Date.now(),
    name: applicant.name,
    email: applicant.email,
    resume: applicant.resume,
    timestamp: new Date().toISOString()
  });
  localStorage.setItem(APPLICANTS_KEY, JSON.stringify(applicants));
  return applicants;
}

// Load employees
function loadEmployees() {
  const employees = localStorage.getItem(EMPLOYEES_KEY);
  return employees ? JSON.parse(employees) : [];
}

// Save employee
function saveEmployee(employee) {
  const employees = loadEmployees();
  employees.push(employee);
  localStorage.setItem(EMPLOYEES_KEY, JSON.stringify(employees));
}

// Check if employee is logged in
function isLoggedIn() {
  const current = localStorage.getItem(CURRENT_EMPLOYEE_KEY);
  return !!current;
}

// Login employee
function loginEmployee(username, password) {
  const employees = loadEmployees();
  const employee = employees.find(e => e.username === username && e.password === password);
  if (employee) {
    localStorage.setItem(CURRENT_EMPLOYEE_KEY, JSON.stringify(employee));
    return true;
  }
  return false;
}

// Logout
function logoutEmployee() {
  localStorage.removeItem(CURRENT_EMPLOYEE_KEY);
}

// Form validation
function validateForm(formData) {
  for (let key in formData) {
    if (!formData[key].trim()) {
      return { valid: false, message: `${key.charAt(0).toUpperCase() + key.slice(1)} is required.` };
    }
  }
  if (formData.email && !/\S+@\S+\.\S+/.test(formData.email)) {
    return { valid: false, message: 'Invalid email.' };
  }
  return { valid: true };
}

// Generic form handler
function handleFormSubmit(formId, handler) {
  const form = document.getElementById(formId);
  if (!form) return;
  
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = Object.fromEntries(new FormData(form));
    const validation = validateForm(formData);
    
    if (!validation.valid) {
      showAlert(validation.message, 'error');
      return;
    }
    
    try {
      await handler(formData);
      showAlert('Success! Redirecting...', 'success');
      setTimeout(() => {
        if (formId === 'applicant-form') window.location.href = 'dashboard.html';
        else if (formId === 'employee-register-form') loginEmployee(formData.username, formData.password);
        else if (formId === 'employee-login-form') window.location.href = 'dashboard.html';
      }, 1500);
    } catch (err) {
      showAlert('Error: ' + err.message, 'error');
    }
  });
}

// Show alert
function showAlert(message, type) {
  const alert = document.createElement('div');
  alert.className = `alert alert-${type}`;
  alert.textContent = message;
  const container = document.querySelector('.container') || document.body;
  container.insertBefore(alert, container.firstChild);
  setTimeout(() => alert.remove(), 5000);
}

// Initialize page
function initPage() {
  // Nav links
  const nav = document.querySelector('.nav-links');
  if (nav) {
    nav.innerHTML = `
      <a href="index.html">Applicant Register</a>
      <a href="employee-register.html">Employee Register</a>
      <a href="employee-login.html">Employee Login</a>
      <a href="dashboard.html">Dashboard</a>
    `;
  }
  
  // Check auth for dashboard-relevant pages
  if (window.location.pathname.includes('dashboard')) {
    if (!isLoggedIn()) {
      const employeeSection = document.getElementById('employee-section');
      if (employeeSection) employeeSection.classList.add('hidden');
    } else {
      loadDashboardData();
    }
  }
}

// Dashboard data load
function loadDashboardData() {
  const applicants = loadApplicants();
  const tbody = document.querySelector('#applicants-table tbody');
  if (tbody) {
    tbody.innerHTML = applicants.map(app => `
      <tr>
        <td>${app.name}</td>
        <td>${app.email}</td>
        <td>${new Date(app.timestamp).toLocaleString()}</td>
        <td>${app.resume.substring(0, 100)}...</td>
      </tr>
    `).join('');
  }
}

// Applicant handler
function handleApplicantSubmit(data) {
  saveApplicant(data);
}

// Employee register handler
function handleEmployeeRegister(data) {
  saveEmployee({
    id: Date.now(),
    username: data.username,
    password: data.password,
    timestamp: new Date().toISOString()
  });
}

// Document ready
document.addEventListener('DOMContentLoaded', () => {
  initPage();
  
  // Setup forms
  handleFormSubmit('applicant-form', handleApplicantSubmit);
  handleFormSubmit('employee-register-form', handleEmployeeRegister);
  
  // Login form (separate as it checks existing)
  const loginForm = document.getElementById('employee-login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const formData = Object.fromEntries(new FormData(loginForm));
      if (loginEmployee(formData.username, formData.password)) {
        showAlert('Logged in!', 'success');
        setTimeout(() => window.location.href = 'dashboard.html', 1000);
      } else {
        showAlert('Invalid credentials.', 'error');
      }
    });
  }
  
  // Logout button
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      logoutEmployee();
      showAlert('Logged out.', 'success');
      setTimeout(() => window.location.href = 'employee-login.html', 1000);
    });
  }
});
