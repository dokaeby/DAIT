/* Serialize writes so an older request cannot overwrite the last selection. */
window.createInterestAutosave = ({ read, write, status, delay = 300 }) => {
  let revision = 0, saved = 0, timer, running;
  const dirty = () => revision !== saved;
  function flush() {
    clearTimeout(timer);
    if (running) return running;
    if (!dirty()) return Promise.resolve();
    running = (async () => {
      try {
        while (dirty()) {
          const current = revision;
          status('saving');
          await write(read());
          saved = current;
        }
        status('saved');
      } catch (error) {
        status('error', error);
        throw error;
      }
    })().finally(() => { running = null; });
    return running;
  }
  function change() {
    revision++;
    status('saving');
    clearTimeout(timer);
    timer = setTimeout(() => flush().catch(() => {}), delay);
  }
  return { change, flush, dirty };
};
