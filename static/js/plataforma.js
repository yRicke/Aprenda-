document.querySelectorAll('[data-auto-submit]').forEach((form) => {
  const selects = form.querySelectorAll('select');
  const fallback = form.querySelector('[data-submit-fallback]');
  if (selects.length && typeof form.requestSubmit === 'function') {
    selects.forEach((select) => select.addEventListener('change', () => form.requestSubmit()));
    if (fallback) fallback.hidden = true;
  }
});

function readPreference(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function savePreference(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // As preferências continuam funcionando durante esta visita.
  }
}

const searchInput = document.getElementById('busca-global');
if (searchInput) {
  const shortcutLabel = document.querySelector('.search-shortcut');
  if (shortcutLabel) shortcutLabel.hidden = false;
  document.addEventListener('keydown', (event) => {
    const editing = event.target instanceof Element && event.target.closest('input, textarea, select, [contenteditable="true"]');
    if (event.isComposing || event.altKey || editing || document.body.classList.contains('focus-mode')) return;
    if (event.key === '/' || ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k')) {
      event.preventDefault();
      searchInput.focus();
      searchInput.select();
    }
  });
}

const catalog = document.querySelector('[data-catalog]');
const viewControls = document.querySelector('[data-view-controls]');
if (catalog && viewControls) {
  const layoutButtons = viewControls.querySelectorAll('[data-layout]');
  function setCatalogLayout(layout) {
    catalog.dataset.layout = layout === 'lista' ? 'lista' : 'grade';
    layoutButtons.forEach((button) => {
      button.setAttribute('aria-pressed', String(button.dataset.layout === catalog.dataset.layout));
    });
  }
  setCatalogLayout(readPreference('aprenda:catalog-layout'));
  viewControls.hidden = false;
  layoutButtons.forEach((button) => {
    button.addEventListener('click', () => {
      setCatalogLayout(button.dataset.layout);
      savePreference('aprenda:catalog-layout', catalog.dataset.layout);
    });
  });
}

const courseDialog = document.querySelector('[data-course-dialog]');
if (courseDialog && typeof courseDialog.showModal === 'function') {
  const dialogContent = courseDialog.querySelector('[data-dialog-content]');
  document.querySelectorAll('[data-course-preview]').forEach((button) => {
    const source = document.getElementById(button.dataset.coursePreview);
    if (!(source instanceof HTMLTemplateElement)) return;
    button.hidden = false;
    button.addEventListener('click', () => {
      if (courseDialog.open) return;
      dialogContent.replaceChildren(source.content.cloneNode(true));
      const title = dialogContent.querySelector('[data-preview-title]');
      title.id = 'titulo-previa';
      courseDialog.setAttribute('aria-labelledby', title.id);
      courseDialog.showModal();
    });
  });
  courseDialog.querySelector('[data-close-dialog]').addEventListener('click', () => courseDialog.close());
  courseDialog.addEventListener('click', (event) => {
    if (event.target !== courseDialog) return;
    const rect = courseDialog.getBoundingClientRect();
    const outside = event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom;
    if (outside) courseDialog.close();
  });
}

document.querySelectorAll('[data-expand-modules]').forEach((button) => {
  const section = document.getElementById(button.dataset.expandModules);
  if (!section) return;
  const modules = section.querySelectorAll('.module-accordion');
  button.hidden = false;
  function updateModuleButton() {
    const allOpen = Array.from(modules).every((module) => module.open);
    button.setAttribute('aria-expanded', String(allOpen));
    button.textContent = allOpen ? 'Recolher todos os módulos −' : 'Abrir todos os módulos +';
  }
  button.addEventListener('click', () => {
    const open = button.getAttribute('aria-expanded') !== 'true';
    modules.forEach((module) => { module.open = open; });
    updateModuleButton();
  });
  modules.forEach((module) => module.addEventListener('toggle', updateModuleButton));
  updateModuleButton();
});

const focusButton = document.querySelector('[data-focus-toggle]');
if (focusButton) {
  const classroomTools = document.querySelector('[data-classroom-tools]');
  const focusLabel = focusButton.querySelector('[data-focus-label]');
  function setFocusMode(enabled) {
    document.body.classList.toggle('focus-mode', enabled);
    focusButton.setAttribute('aria-pressed', String(enabled));
    focusLabel.textContent = enabled ? 'Sair do foco' : 'Modo foco';
  }
  classroomTools.hidden = false;
  setFocusMode(readPreference('aprenda:focus-mode') === 'true');
  focusButton.addEventListener('click', () => {
    const enabled = !document.body.classList.contains('focus-mode');
    setFocusMode(enabled);
    savePreference('aprenda:focus-mode', String(enabled));
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && document.body.classList.contains('focus-mode')) {
      setFocusMode(false);
      savePreference('aprenda:focus-mode', 'false');
      focusButton.focus();
    }
  });
}

const readingText = document.getElementById('texto-aula');
if (readingText) {
  const sizes = [16, 18, 20, 22];
  const savedSize = Number(readPreference('aprenda:reading-size'));
  let sizeIndex = sizes.includes(savedSize) ? sizes.indexOf(savedSize) : 1;
  const readingButtons = document.querySelectorAll('[data-reading-adjust]');
  function applyReadingSize() {
    readingText.style.setProperty('--reading-size', `${sizes[sizeIndex]}px`);
    readingButtons.forEach((button) => {
      const nextIndex = sizeIndex + Number(button.dataset.readingAdjust);
      button.disabled = nextIndex < 0 || nextIndex >= sizes.length;
    });
  }
  applyReadingSize();
  readingButtons.forEach((button) => {
    button.addEventListener('click', () => {
      sizeIndex = Math.max(0, Math.min(sizes.length - 1, sizeIndex + Number(button.dataset.readingAdjust)));
      applyReadingSize();
      savePreference('aprenda:reading-size', String(sizes[sizeIndex]));
    });
  });
}

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
if ('IntersectionObserver' in window && !reducedMotion.matches) {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.remove('reveal-pending');
      entry.target.classList.add('reveal-visible');
      observer.unobserve(entry.target);
    });
  }, { threshold: 0, rootMargin: '0px 0px -30px 0px' });
  document.querySelectorAll('[data-reveal]').forEach((element) => {
    if (element.getBoundingClientRect().top < window.innerHeight || element.parentElement.closest('.reveal-pending')) return;
    element.classList.add('reveal-pending');
    observer.observe(element);
  });
  reducedMotion.addEventListener('change', (event) => {
    if (!event.matches) return;
    document.querySelectorAll('.reveal-pending').forEach((element) => element.classList.remove('reveal-pending'));
    observer.disconnect();
  });
}

document.querySelectorAll('[data-password-toggle]').forEach((button) => {
  const input = document.getElementById(button.dataset.passwordToggle);
  if (!input) return;
  button.addEventListener('click', () => {
    const mostrar = input.type === 'password';
    input.type = mostrar ? 'text' : 'password';
    button.textContent = mostrar ? 'Ocultar' : 'Mostrar';
    button.setAttribute('aria-pressed', String(mostrar));
  });
});

const menus = document.querySelectorAll('[data-menu]');
document.addEventListener('click', (event) => {
  menus.forEach((menu) => {
    if (!menu.contains(event.target)) menu.open = false;
  });
});
document.addEventListener('keydown', (event) => {
  if (event.key !== 'Escape') return;
  menus.forEach((menu) => {
    if (menu.open) {
      menu.open = false;
      menu.querySelector('summary').focus();
    }
  });
});
