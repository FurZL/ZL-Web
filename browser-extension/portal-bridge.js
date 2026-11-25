(() => {
  const schoolHost = 'jwglxt-443.webvpn.zstu.edu.cn';
  if (location.hostname !== schoolHost || !location.pathname.startsWith('/jwglxt/kbcx/')) return;

  let captureArmed = false;
  void chrome.runtime.sendMessage({ type: 'GET_CAPTURE_ARM' }).then((result) => {
    if (!result?.ok || !result.armed) return;
    captureArmed = true;
    window.postMessage({ source: 'furzl-schedule-reader', type: 'ARM_CAPTURE' }, location.origin);
  }).catch(() => {});

  window.addEventListener('message', (event) => {
    if (event.source !== window || event.origin !== location.origin) return;
    const message = event.data;
    if (!message || message.source !== 'furzl-schedule-reader' || message.type !== 'PORTAL_RESPONSE') return;
    if (!captureArmed) return;
    const slots = globalThis.SchedulePortalParser?.parsePortalResponse(message.responseText);
    captureArmed = false;
    if (!slots) {
      void chrome.runtime.sendMessage({ type: 'PORTAL_UNSUPPORTED', tabId: null });
      return;
    }
    void chrome.runtime.sendMessage({
      type: 'PORTAL_CAPTURED',
      payload: { slots, capturedAt: Date.now() },
    });
  });
})();
