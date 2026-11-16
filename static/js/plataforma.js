document.querySelectorAll('[data-auto-submit]').forEach((form) => {
  const select = form.querySelector('select');
  const fallback = form.querySelector('[data-submit-fallback]');
  if (select && typeof form.requestSubmit === 'function') {
    select.addEventListener('change', () => form.requestSubmit());
    if (fallback) fallback.hidden = true;
  }
});

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
