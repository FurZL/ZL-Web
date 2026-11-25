(() => {
  function sendToPage(pending) {
    if (!pending || location.pathname.startsWith('/login')) return;
    window.postMessage({
      source: 'furzl-schedule-extension',
      type: 'SCHEDULE_IMPORT',
      payload: pending,
    }, location.origin);
  }

  async function deliverPending() {
    try {
      const result = await chrome.runtime.sendMessage({ type: 'GET_PENDING' });
      if (result?.ok && result.pending) sendToPage(result.pending);
    } catch {
      // The app requests again when its schedule view mounts.
    }
  }

  window.addEventListener('message', (event) => {
    if (event.source !== window || event.origin !== location.origin) return;
    const message = event.data;
    if (!message || message.source !== 'furzl-schedule-page') return;
    if (message.type === 'READY') void deliverPending();
    if (message.type === 'ACK_IMPORT' && typeof message.id === 'string') {
      void chrome.runtime.sendMessage({ type: 'ACK_IMPORT', id: message.id });
    }
  });

  chrome.runtime.onMessage.addListener((message) => {
    if (message?.type === 'DELIVER_PENDING') void deliverPending();
  });
})();
