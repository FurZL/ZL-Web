const SCHOOL_HOST = 'jwglxt-443.webvpn.zstu.edu.cn';
const DAY_NAMES = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];

const status = document.querySelector('#status');
const preview = document.querySelector('#preview');
const courseCount = document.querySelector('#course-count');
const courseList = document.querySelector('#course-list');
const moreCourses = document.querySelector('#more-courses');
const reloadButton = document.querySelector('#reload');
const importButton = document.querySelector('#import');
const scheduleName = document.querySelector('#schedule-name');
const targetSite = document.querySelector('#target-site');

let activeTab = null;
let captured = null;

function setStatus(message, error = false) {
  status.textContent = message;
  status.classList.toggle('error', error);
}

function renderCapture(value) {
  captured = value;
  if (!value || value.status === 'unsupported') {
    preview.hidden = true;
    importButton.hidden = true;
    reloadButton.hidden = false;
    setStatus(value?.status === 'unsupported'
      ? '教务系统返回的数据格式暂未识别。请确认当前是个人课表页；仍无法读取时请导出 TXT 文件。'
      : '尚未读取到课表。首次使用或切换学期后，点击下方按钮重新加载教务课表。', value?.status === 'unsupported');
    return;
  }

  preview.hidden = false;
  reloadButton.hidden = false;
  importButton.hidden = false;
  courseCount.textContent = String(value.slots.length);
  courseList.replaceChildren();
  for (const slot of value.slots.slice(0, 8)) {
    const row = document.createElement('li');
    const course = document.createElement('span');
    const detail = document.createElement('span');
    course.textContent = `${DAY_NAMES[slot.weekday]} · ${slot.name}`;
    detail.textContent = `第${slot.lesson_start}${slot.lesson_end === slot.lesson_start ? '' : `-${slot.lesson_end}`}节`;
    row.append(course, detail);
    courseList.append(row);
  }
  moreCourses.textContent = value.slots.length > 8 ? `以及另外 ${value.slots.length - 8} 门课程` : '';
  setStatus('已从当前登录的教务页面读取课程。检查课表后可继续到啫喱小站预览。');
}

async function initialize() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  activeTab = tab;
  let currentUrl;
  try { currentUrl = new URL(tab?.url); } catch { currentUrl = null; }
  if (!tab?.id || currentUrl?.hostname !== SCHOOL_HOST || !currentUrl.pathname.startsWith('/jwglxt/kbcx/')) {
    setStatus('请在同一个浏览器中登录浙江理工大学教务系统，并打开个人课表页面后再使用扩展。', true);
    reloadButton.hidden = true;
    importButton.hidden = true;
    preview.hidden = true;
    return;
  }

  const response = await chrome.runtime.sendMessage({ type: 'GET_CAPTURE', tabId: tab.id });
  renderCapture(response?.ok ? response.capture : null);
}

reloadButton.addEventListener('click', async () => {
  if (!activeTab?.id) return;
  reloadButton.disabled = true;
  setStatus('本次读取已授权，正在重新加载教务课表…');
  try {
    const cleared = await chrome.runtime.sendMessage({ type: 'CLEAR_CAPTURE', tabId: activeTab.id });
    const armed = await chrome.runtime.sendMessage({ type: 'ARM_CAPTURE', tabId: activeTab.id });
    if (!cleared?.ok || !armed?.ok) throw new Error('无法授权读取当前标签页，请确认它仍是教务个人课表。');
    await chrome.tabs.reload(activeTab.id);
    window.close();
  } catch (error) {
    setStatus(error instanceof Error ? error.message : '读取授权失败，请重试。', true);
    reloadButton.disabled = false;
  }
});

importButton.addEventListener('click', async () => {
  if (!activeTab?.id || !captured?.slots?.length) return;
  const name = scheduleName.value.trim();
  if (!name) {
    setStatus('请填写课表名称。', true);
    scheduleName.focus();
    return;
  }
  importButton.disabled = true;
  try {
    const result = await chrome.runtime.sendMessage({
      type: 'IMPORT_TO_SITE',
      sourceTabId: activeTab.id,
      targetUrl: targetSite.value,
      name,
    });
    if (!result?.ok) throw new Error('读取结果已失效，请重新读取课表后再试。');
    setStatus('课程已发送。请在啫喱小站页面检查预览并确认保存。');
    window.close();
  } catch (error) {
    setStatus(error instanceof Error ? error.message : '发送失败，请重新读取课表。', true);
    importButton.disabled = false;
  }
});

void initialize().catch(() => setStatus('扩展初始化失败，请重新打开扩展面板。', true));
