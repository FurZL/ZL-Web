const assert = require('node:assert/strict')
const { readFileSync } = require('node:fs')
const path = require('node:path')
const { test } = require('node:test')
const vm = require('node:vm')

const schoolUrl = 'https://jwglxt-443.webvpn.zstu.edu.cn/jwglxt/kbcx/xskbcx_cxXskbcxIndex.html'
const popupSender = { id: 'test-extension-id', url: 'chrome-extension://test-extension-id/popup.html' }

function createWorkerHarness() {
  const values = new Map()
  let messageListener
  const chrome = {
    runtime: {
      id: 'test-extension-id',
      onMessage: { addListener(listener) { messageListener = listener } },
    },
    storage: {
      session: {
        async get(key) { return { [key]: values.get(key) } },
        async set(items) { for (const [key, value] of Object.entries(items)) values.set(key, value) },
        async remove(key) { values.delete(key) },
      },
    },
    tabs: { async get(id) { return { id, url: schoolUrl } } },
  }
  const source = readFileSync(path.join(__dirname, '..', 'service-worker.js'), 'utf8')
  vm.runInNewContext(source, { chrome, URL, Date })

  return {
    values,
    send(message, sender) {
      return new Promise((resolve) => messageListener(message, sender, resolve))
    },
  }
}

test('capture requires a popup authorization and can be consumed only once', async () => {
  const worker = createWorkerHarness()
  const sender = { id: 'test-extension-id', tab: { id: 17, url: schoolUrl } }
  const slots = [{ name: '课程', weekday: 0, lesson_start: 1, lesson_end: 2, weeks: [1] }]

  const rejected = await worker.send({ type: 'PORTAL_CAPTURED', payload: { slots } }, sender)
  assert.equal(rejected.ok, false)
  assert.equal(rejected.error, 'NOT_ARMED')
  assert.equal(worker.values.has('portalCapture'), false)

  const unauthorizedArm = await worker.send({ type: 'ARM_CAPTURE', tabId: 17 }, sender)
  assert.equal(unauthorizedArm.error, 'INVALID_REQUEST')
  const authorizedArm = await worker.send({ type: 'ARM_CAPTURE', tabId: 17 }, popupSender)
  assert.equal(authorizedArm.ok, true)
  const accepted = await worker.send({ type: 'PORTAL_CAPTURED', payload: { slots } }, sender)
  assert.equal(accepted.ok, true)
  assert.equal(worker.values.get('portalCapture').slots.length, 1)
  assert.equal(worker.values.has('captureArm'), false)

  const repeated = await worker.send({ type: 'PORTAL_CAPTURED', payload: { slots } }, sender)
  assert.equal(repeated.ok, false)
  assert.equal(repeated.error, 'NOT_ARMED')
})

test('the page hook observes course responses only while explicitly armed', async () => {
  const listeners = new Map()
  const posted = []
  const location = {
    hostname: 'jwglxt-443.webvpn.zstu.edu.cn',
    pathname: '/jwglxt/kbcx/xskbcx_cxXskbcxIndex.html',
    origin: 'https://jwglxt-443.webvpn.zstu.edu.cn',
    href: schoolUrl,
  }
  const window = {
    addEventListener(type, listener) { listeners.set(type, listener) },
    postMessage(message) { posted.push(message) },
  }
  const XMLHttpRequest = function XMLHttpRequest() {}
  XMLHttpRequest.prototype.open = function open() {}
  XMLHttpRequest.prototype.send = function send() {}
  const body = JSON.stringify({ kcmc: '课程', xqj: '1', jcs: '1-2', zcd: '1-16' })
  const context = {
    window,
    location,
    URL,
    XMLHttpRequest,
    fetch: async () => ({ ok: true, clone: () => ({ text: async () => body }) }),
  }
  const source = readFileSync(path.join(__dirname, '..', 'portal-hook.js'), 'utf8')
  vm.runInNewContext(source, context)

  async function querySchedule() {
    await context.fetch('/jwglxt/kbcx/xskbcx_cxXskbcxIndex.html')
    await new Promise((resolve) => setImmediate(resolve))
  }

  await querySchedule()
  assert.equal(posted.length, 0)

  listeners.get('message')({
    source: window,
    origin: location.origin,
    data: { source: 'furzl-schedule-reader', type: 'ARM_CAPTURE' },
  })
  await querySchedule()
  await querySchedule()

  assert.equal(posted.filter((message) => message.type === 'PORTAL_RESPONSE').length, 1)
})
