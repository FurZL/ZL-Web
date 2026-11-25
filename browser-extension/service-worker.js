const CAPTURE_KEY = 'portalCapture';
const CAPTURE_ARM_KEY = 'captureArm';
const PENDING_KEY = 'pendingImport';
const CAPTURE_TTL_MS = 30 * 60 * 1000;
const CAPTURE_ARM_TTL_MS = 2 * 60 * 1000;
const PENDING_TTL_MS = 10 * 60 * 1000;
const APP_HOSTS = new Set(['www.furzl.cn', 'localhost', '127.0.0.1']);
const SCHOOL_HOST = 'jwglxt-443.webvpn.zstu.edu.cn';

function isSchoolUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && url.hostname === SCHOOL_HOST
      && url.pathname.startsWith('/jwglxt/kbcx/');
  } catch {
    return false;
  }
}

function isAppUrl(value) {
  try {
    const url = new URL(value);
    return APP_HOSTS.has(url.hostname)
      && (url.protocol === 'https:' || url.protocol === 'http:');
  } catch {
    return false;
  }
}

function isPopupSender(sender) {
  try {
    const url = new URL(sender.url);
    return sender.id === chrome.runtime.id && url.protocol === 'chrome-extension:' && url.pathname === '/popup.html';
  } catch {
    return false;
  }
}

function validSlots(slots) {
  return Array.isArray(slots) && slots.length > 0 && slots.length <= 500
    && slots.every((slot) => slot && typeof slot.name === 'string'
      && slot.name.trim().length > 0 && slot.name.length <= 255
      && Number.isInteger(slot.weekday) && slot.weekday >= 0 && slot.weekday <= 6
      && Number.isInteger(slot.lesson_start) && slot.lesson_start >= 1 && slot.lesson_start <= 24
      && Number.isInteger(slot.lesson_end) && slot.lesson_end >= slot.lesson_start && slot.lesson_end <= 24
      && Array.isArray(slot.weeks) && slot.weeks.length > 0 && slot.weeks.length <= 53
      && slot.weeks.every((week) => Number.isInteger(week) && week >= 1 && week <= 53));
}

async function getCapture(tabId) {
  const { [CAPTURE_KEY]: capture } = await chrome.storage.session.get(CAPTURE_KEY);
  if (!capture || Date.now() - capture.capturedAt > CAPTURE_TTL_MS) {
    await chrome.storage.session.remove(CAPTURE_KEY);
    return null;
  }
  return tabId === undefined || capture.tabId === tabId ? capture : null;
}

async function getCaptureArm(tabId) {
  const { [CAPTURE_ARM_KEY]: arm } = await chrome.storage.session.get(CAPTURE_ARM_KEY);
  if (!arm || Date.now() - arm.armedAt > CAPTURE_ARM_TTL_MS) {
    await chrome.storage.session.remove(CAPTURE_ARM_KEY);
    return null;
  }
  return tabId === undefined || arm.tabId === tabId ? arm : null;
}

async function getPending(sender) {
  const { [PENDING_KEY]: pending } = await chrome.storage.session.get(PENDING_KEY);
  if (!pending || Date.now() - pending.createdAt > PENDING_TTL_MS) {
    await chrome.storage.session.remove(PENDING_KEY);
    return null;
  }
  if (!sender.tab?.url || !isAppUrl(sender.tab.url)) return null;
  if (new URL(sender.tab.url).origin !== pending.targetOrigin) return null;
  return pending;
}

async function deliverToSite(targetUrl) {
  const target = new URL(targetUrl);
  const matchPattern = `${target.protocol}//${target.hostname}/*`;
  const tabs = await chrome.tabs.query({ url: matchPattern });
  const scheduleTab = tabs.find((tab) => {
    try {
      const url = new URL(tab.url);
      return url.origin === target.origin && url.pathname.startsWith('/schedule');
    } catch {
      return false;
    }
  });
  if (scheduleTab?.id !== undefined) {
    try { await chrome.tabs.sendMessage(scheduleTab.id, { type: 'DELIVER_PENDING' }); } catch { /* The SPA will request the pending import when it mounts. */ }
    await chrome.tabs.update(scheduleTab.id, { active: true });
    return;
  }
  await chrome.tabs.create({ url: target.href });
}

async function handleMessage(message, sender) {
  if (!message || typeof message.type !== 'string') return { ok: false, error: 'INVALID_MESSAGE' };

  if (message.type === 'PORTAL_CAPTURED') {
    if (!sender.tab?.id || !isSchoolUrl(sender.tab.url) || !validSlots(message.payload?.slots)) {
      return { ok: false, error: 'INVALID_CAPTURE' };
    }
    if (!await getCaptureArm(sender.tab.id)) return { ok: false, error: 'NOT_ARMED' };
    await chrome.storage.session.set({
      [CAPTURE_KEY]: {
        tabId: sender.tab.id,
        capturedAt: Date.now(),
        slots: message.payload.slots,
      },
    });
    await chrome.storage.session.remove(CAPTURE_ARM_KEY);
    return { ok: true };
  }

  if (message.type === 'PORTAL_UNSUPPORTED') {
    if (!sender.tab?.id || !isSchoolUrl(sender.tab.url)) return { ok: false, error: 'INVALID_CAPTURE' };
    if (!await getCaptureArm(sender.tab.id)) return { ok: false, error: 'NOT_ARMED' };
    await chrome.storage.session.set({
      [CAPTURE_KEY]: { tabId: sender.tab.id, capturedAt: Date.now(), status: 'unsupported' },
    });
    await chrome.storage.session.remove(CAPTURE_ARM_KEY);
    return { ok: true };
  }

  if (message.type === 'ARM_CAPTURE') {
    if (!isPopupSender(sender) || !Number.isInteger(message.tabId)) return { ok: false, error: 'INVALID_REQUEST' };
    const tab = await chrome.tabs.get(message.tabId);
    if (!isSchoolUrl(tab.url)) return { ok: false, error: 'INVALID_TAB' };
    await chrome.storage.session.set({ [CAPTURE_ARM_KEY]: { tabId: tab.id, armedAt: Date.now() } });
    return { ok: true };
  }

  if (message.type === 'GET_CAPTURE_ARM') {
    if (!sender.tab?.id || !isSchoolUrl(sender.tab.url)) return { ok: false, error: 'INVALID_TAB' };
    return { ok: true, armed: Boolean(await getCaptureArm(sender.tab.id)) };
  }

  if (message.type === 'GET_CAPTURE') {
    if (!isPopupSender(sender)) return { ok: false, error: 'INVALID_REQUEST' };
    if (message.tabId !== undefined && sender.tab?.id !== undefined && message.tabId !== sender.tab.id) {
      return { ok: false, error: 'TAB_MISMATCH' };
    }
    return { ok: true, capture: await getCapture(message.tabId) };
  }

  if (message.type === 'CLEAR_CAPTURE') {
    if (!isPopupSender(sender)) return { ok: false, error: 'INVALID_REQUEST' };
    const capture = await getCapture(message.tabId);
    if (capture) await chrome.storage.session.remove(CAPTURE_KEY);
    return { ok: true };
  }

  if (message.type === 'IMPORT_TO_SITE') {
    if (!isPopupSender(sender)) return { ok: false, error: 'INVALID_REQUEST' };
    const capture = await getCapture(message.sourceTabId);
    if (!capture || capture.status || !validSlots(capture.slots)) return { ok: false, error: 'NO_CAPTURE' };
    if (sender.tab?.id !== undefined && sender.tab.id !== capture.tabId) return { ok: false, error: 'TAB_MISMATCH' };
    let target;
    try { target = new URL(message.targetUrl); } catch { return { ok: false, error: 'INVALID_TARGET' }; }
    if (!isAppUrl(target.href) || !target.pathname.startsWith('/schedule')) return { ok: false, error: 'INVALID_TARGET' };
    const name = typeof message.name === 'string' ? message.name.trim().slice(0, 255) : '';
    if (!name) return { ok: false, error: 'INVALID_NAME' };
    const pending = {
      id: crypto.randomUUID(),
      createdAt: Date.now(),
      targetOrigin: target.origin,
      schedule: { name, slots: capture.slots },
    };
    await chrome.storage.session.set({ [PENDING_KEY]: pending });
    await chrome.storage.session.remove(CAPTURE_KEY);
    await deliverToSite(target.href);
    return { ok: true };
  }

  if (message.type === 'GET_PENDING') {
    return { ok: true, pending: await getPending(sender) };
  }

  if (message.type === 'ACK_IMPORT') {
    const pending = await getPending(sender);
    if (pending?.id === message.id) {
      await chrome.storage.session.remove(PENDING_KEY);
      return { ok: true };
    }
    return { ok: false, error: 'PENDING_NOT_FOUND' };
  }

  return { ok: false, error: 'UNKNOWN_MESSAGE' };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  void handleMessage(message, sender).then(sendResponse).catch(() => sendResponse({ ok: false, error: 'INTERNAL_ERROR' }));
  return true;
});
