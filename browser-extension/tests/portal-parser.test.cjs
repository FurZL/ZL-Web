const test = require('node:test')
const assert = require('node:assert/strict')
const { parsePortalResponse, weekList } = require('../portal-parser.js')

test('maps the academic timetable response to private schedule slots', () => {
  const slots = parsePortalResponse({
    success: true,
    data: {
      kbList: [
        {
          kcmc: '高等数学',
          xqj: '1',
          jcs: '3-4节',
          zcd: '1-16周',
          cdmc: '2-N130',
          xqmc: '下沙校区',
        },
        {
          kcmc: '摄影基础',
          xqj: 5,
          jcs: '10-11',
          zcd: '1-15周(单周)',
          cdmc: '艺术楼 202',
        },
      ],
    },
  })

  assert.equal(slots.length, 2)
  assert.deepEqual(slots[0], {
    kind: 'course',
    name: '高等数学',
    location: '2-N130',
    weekday: 0,
    lesson_start: 3,
    lesson_end: 4,
    weeks: Array.from({ length: 16 }, (_, index) => index + 1),
    campus: '下沙校区',
  })
  assert.deepEqual(slots[1].weeks, [1, 3, 5, 7, 9, 11, 13, 15])
  assert.equal(slots[1].weekday, 4)
})

test('rejects responses without recognized weeks or course time fields', () => {
  assert.equal(parsePortalResponse({ kbList: [{ kcmc: '课程', xqj: 1, jcs: '1-2', cdmc: '教室' }] }), null)
  assert.equal(parsePortalResponse('<html>login required</html>'), null)
})

test('parses separate week ranges and even-week markers', () => {
  assert.deepEqual(weekList('1-8周，10-16周(双周)'), [2, 4, 6, 8, 10, 12, 14, 16])
})
