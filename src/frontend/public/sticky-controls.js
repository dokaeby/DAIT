/* Shared header measurements keep sticky controls and section anchors aligned. */
(() => {
  'use strict';
  const controls = document.querySelector('[data-sticky-controls]');
  const header = document.querySelector('.app-header');
  if (!controls || !header) return;
  // Main-page search lives in the header; its content must scroll normally.
  if (controls.classList.contains('page-controls')) return;
  const root = document.documentElement;
  const menu = document.querySelector('.settings-menu');
  let pending = false;
  let expandedHeight = 0;
  function measure() {
    pending = false;
    const headerHeight = Math.ceil(header.getBoundingClientRect().height);
    const controlsHeight = Math.ceil(controls.getBoundingClientRect().height);
    if (controls.classList.contains('is-compact')) {
      controls.style.setProperty('--controls-space', Math.max(0, expandedHeight - controlsHeight) + 'px');
    } else {
      expandedHeight = controlsHeight;
      controls.style.setProperty('--controls-space', '0px');
    }
    const menuHeight = menu && window.innerWidth <= 1100 ? Math.ceil(menu.getBoundingClientRect().height) : 0;
    const gap = controls.classList.contains('page-controls') && controls.classList.contains('is-compact') ? 12 : 0;
    root.style.setProperty('--app-header-height', headerHeight + 'px');
    root.style.setProperty('--page-controls-height', controlsHeight + 'px');
    root.style.setProperty('--section-offset', (headerHeight + gap + controlsHeight + menuHeight + 24) + 'px');
  }
  function queueMeasure() {
    if (!pending) { pending = true; requestAnimationFrame(measure); }
  }
  function onScroll() {
    // Separate thresholds prevent shrinking the title from toggling it repeatedly.
    if (window.scrollY > 160) controls.classList.add('is-compact');
    else if (window.scrollY < 24) controls.classList.remove('is-compact');
    queueMeasure();
  }
  const observer = new ResizeObserver(queueMeasure);
  [header, controls, menu].filter(Boolean).forEach(el => observer.observe(el));
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', queueMeasure);
  if (menu) menu.addEventListener('click', event => {
    const link = event.target.closest('a[href^="#"]');
    const section = link && document.getElementById(link.hash.slice(1));
    if (!section) return;
    event.preventDefault();
    controls.classList.add('is-compact');
    measure();
    history.pushState(null, '', link.hash);
    window.dispatchEvent(new Event('hashchange'));
    section.scrollIntoView({ block: 'start', behavior: 'instant' });
  });
  onScroll();
})();
