(() => {
  if (globalThis.__furzScheduleHookInstalled) return;
  globalThis.__furzScheduleHookInstalled = true;

  const MAX_RESPONSE_CHARS = 1_500_000;
  const endpointPattern = /\/jwglxt\/kbcx\/[^?#]*(?:xskbcx|xsgrkb|kb)/i;

  let captureArmed = false;

  window.addEventListener('message', (event) => {
    if (event.source !== window || event.origin !== location.origin) return;
    const message = event.data;
    if (message?.source === 'furzl-schedule-reader' && message.type === 'ARM_CAPTURE') {
      captureArmed = true;
    }
  });

  function report(url, body) {
    if (!captureArmed || typeof url !== 'string' || typeof body !== 'string' || body.length > MAX_RESPONSE_CHARS) return;
    let path;
    try { path = new URL(url, location.href).pathname; } catch { return; }
    if (!endpointPattern.test(path)) return;
    if (!/"(?:kbList|kcmc|xqj|jcs|courseName)"/i.test(body)) return;
    try {
      JSON.parse(body);
      captureArmed = false;
      window.postMessage({
        source: 'furzl-schedule-reader',
        type: 'PORTAL_RESPONSE',
        responseText: body,
      }, location.origin);
    } catch {
      // The schedule endpoint may return HTML during an expired login session.
    }
  }

  const originalFetch = globalThis.fetch;
  if (typeof originalFetch === 'function') {
    globalThis.fetch = async function (...args) {
      const response = await originalFetch.apply(this, args);
      const requestUrl = typeof args[0] === 'string' ? args[0] : args[0]?.url;
      if (captureArmed && response.ok && typeof requestUrl === 'string') {
        void response.clone().text().then((body) => report(requestUrl, body)).catch(() => {});
      }
      return response;
    };
  }

  const originalOpen = XMLHttpRequest.prototype.open;
  const originalSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function (method, url, ...rest) {
    this.__furzScheduleUrl = url;
    return originalOpen.call(this, method, url, ...rest);
  };
  XMLHttpRequest.prototype.send = function (...args) {
    this.addEventListener('load', () => {
      if (!captureArmed || this.status < 200 || this.status >= 300) return;
      try {
        if (typeof this.responseText === 'string') report(this.__furzScheduleUrl, this.responseText);
      } catch {
        // Binary and JSON response types do not expose responseText.
      }
    }, { once: true });
    return originalSend.apply(this, args);
  };
})();
