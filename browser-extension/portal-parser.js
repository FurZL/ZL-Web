(() => {
  const NAME_FIELDS = ['kcmc', 'courseName', 'course_name', 'name', 'kc'];
  const DAY_FIELDS = ['xqj', 'weekday', 'dayOfWeek', 'day', 'weekDay'];
  const PERIOD_FIELDS = ['jcs', 'periods', 'lessonRange', 'lesson_range', 'period', 'jcdm'];
  const WEEK_FIELDS = ['zcd', 'weeks', 'weekText', 'week_range', 'zc'];
  const ROOM_FIELDS = ['cdmc', 'jxcdmc', 'location', 'classroom', 'room', 'cd'];
  const CAMPUS_FIELDS = ['xqmc', 'campus', 'campusName'];
  const DAY_NAMES = new Map([
    ['周一', 0], ['星期一', 0], ['周二', 1], ['星期二', 1],
    ['周三', 2], ['星期三', 2], ['周四', 3], ['星期四', 3],
    ['周五', 4], ['星期五', 4], ['周六', 5], ['星期六', 5],
    ['周日', 6], ['星期日', 6], ['星期天', 6], ['周天', 6],
  ]);

  function field(record, names) {
    for (const name of names) {
      if (Object.hasOwn(record, name) && record[name] !== null && record[name] !== undefined) {
        return { name, value: record[name] };
      }
    }
    return null;
  }

  function text(value) {
    if (typeof value === 'string' || typeof value === 'number') {
      return String(value).replace(/<[^>]*>/g, ' ').replace(/&nbsp;/gi, ' ').replace(/\s+/g, ' ').trim();
    }
    return '';
  }

  function periodRange(value) {
    const source = text(value);
    const range = source.match(/(\d{1,2})\s*(?:-|~|～|—|至|到)\s*(\d{1,2})/);
    if (range) return [Number(range[1]), Number(range[2])];
    const one = source.match(/\d{1,2}/);
    return one ? [Number(one[0]), Number(one[0])] : null;
  }

  function weekList(value) {
    if (Array.isArray(value)) {
      const items = value.flatMap((item) => weekList(item));
      return [...new Set(items)].sort((a, b) => a - b);
    }
    if (typeof value === 'number' && Number.isInteger(value)) {
      return value >= 1 && value <= 53 ? [value] : [];
    }
    const source = text(value);
    if (!source) return [];
    const weeks = new Set();
    const ranges = [...source.matchAll(/(\d{1,2})\s*[-~～—至到]\s*(\d{1,2})/g)];
    for (const match of ranges) {
      const start = Number(match[1]);
      const end = Number(match[2]);
      if (start >= 1 && end <= 53 && end >= start) {
        for (let week = start; week <= end; week += 1) weeks.add(week);
      }
    }
    const remainder = source.replace(/\d{1,2}\s*[-~～—至到]\s*\d{1,2}/g, ' ');
    for (const match of remainder.matchAll(/\d{1,2}/g)) {
      const week = Number(match[0]);
      if (week >= 1 && week <= 53) weeks.add(week);
    }
    const parity = /单周|奇数周/.test(source) ? 'odd' : /双周|偶数周/.test(source) ? 'even' : null;
    return [...weeks].filter((week) => !parity || (parity === 'odd' ? week % 2 === 1 : week % 2 === 0)).sort((a, b) => a - b);
  }

  function weekday(value, fieldName) {
    const source = text(value);
    for (const [label, day] of DAY_NAMES) {
      if (source.includes(label)) return day;
    }
    const number = Number(source);
    if (!Number.isInteger(number)) return null;
    if (fieldName === 'xqj') return number >= 1 && number <= 7 ? number - 1 : null;
    return number >= 0 && number <= 6 ? number : null;
  }

  function findArrays(root) {
    const results = [];
    const seen = new Set();
    const stack = [{ value: root, depth: 0 }];
    let visited = 0;
    while (stack.length && visited < 20000) {
      const { value, depth } = stack.pop();
      visited += 1;
      if (!value || typeof value !== 'object' || depth > 8 || seen.has(value)) continue;
      seen.add(value);
      if (Array.isArray(value)) {
        if (value.length && value.some((item) => item && typeof item === 'object' && !Array.isArray(item)
          && field(item, NAME_FIELDS) && field(item, DAY_FIELDS) && field(item, PERIOD_FIELDS))) {
          results.push(value);
        }
        for (const item of value) stack.push({ value: item, depth: depth + 1 });
      } else {
        for (const item of Object.values(value)) stack.push({ value: item, depth: depth + 1 });
      }
    }
    return results;
  }

  function parseRecord(record) {
    const courseName = field(record, NAME_FIELDS);
    const dayField = field(record, DAY_FIELDS);
    const periods = field(record, PERIOD_FIELDS);
    if (!courseName || !dayField || !periods) return null;
    const name = text(courseName.value);
    const day = weekday(dayField.value, dayField.name);
    const [lessonStart, lessonEnd] = periodRange(periods.value) || [];
    const weeksField = field(record, WEEK_FIELDS);
    const weeks = weeksField ? weekList(weeksField.value) : [];
    if (!name || day === null || !lessonStart || !lessonEnd || lessonStart > lessonEnd
      || lessonEnd > 24 || !weeks.length) return null;
    const room = field(record, ROOM_FIELDS);
    const campus = field(record, CAMPUS_FIELDS);
    return {
      kind: 'course',
      name: name.slice(0, 255),
      location: room ? text(room.value).slice(0, 255) : '',
      weekday: day,
      lesson_start: lessonStart,
      lesson_end: lessonEnd,
      weeks,
      campus: campus ? (text(campus.value).slice(0, 128) || null) : null,
    };
  }

  function parsePortalResponse(response) {
    let root = response;
    if (typeof root === 'string') {
      try { root = JSON.parse(root); } catch { return null; }
    }
    const slots = [];
    for (const list of findArrays(root)) {
      for (const record of list) {
        const slot = parseRecord(record);
        if (slot) slots.push(slot);
      }
      if (slots.length) break;
    }
    if (!slots.length || slots.length > 500) return null;
    const unique = new Map();
    for (const slot of slots) {
      const key = JSON.stringify(slot);
      unique.set(key, slot);
    }
    return [...unique.values()];
  }

  const api = { parsePortalResponse, weekList };
  globalThis.SchedulePortalParser = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
