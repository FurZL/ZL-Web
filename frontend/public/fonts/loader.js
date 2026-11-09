/**
 * 字体加载器：Google Fonts (Noto Sans SC) 优先，本地鸿蒙字体回退。
 *
 * 1. 尝试从 Google Fonts 加载 Noto Sans SC（3 秒超时）
 * 2. 成功 → 使用 Noto Sans SC（CSS 字体栈中排第一位）
 * 3. 失败/超时 → 注入本地 /fonts/fonts.css（HarmonyOS Sans SC）
 *
 * CSS 字体栈：'Noto Sans SC', 'HarmonyOS Sans SC', 系统字体
 * 两种来源共存，浏览器自动选择第一个可用的。
 */
;(function () {
  var TIMEOUT = 3000
  var localLoaded = false
  var gfSuccess = false

  function loadLocalFallback() {
    if (localLoaded || gfSuccess) return
    localLoaded = true
    var link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = '/fonts/fonts.css'
    document.head.appendChild(link)
    console.info('[fonts] Google Fonts 不可用，回退到本地鸿蒙字体')
  }

  function tryGoogleFonts() {
    return new Promise(function (resolve, reject) {
      var link = document.createElement('link')
      link.rel = 'stylesheet'
      link.href = 'https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap'

      var timer = setTimeout(function () {
        reject(new Error('timeout'))
      }, TIMEOUT)

      link.onload = function () {
        clearTimeout(timer)
        // 等字体文件实际可用后才算成功
        if (document.fonts && document.fonts.load) {
          document.fonts.load('400 16px "Noto Sans SC"').then(function () {
            resolve()
          }).catch(function () {
            reject(new Error('font load failed'))
          })
        } else {
          resolve()
        }
      }
      link.onerror = function () {
        clearTimeout(timer)
        reject(new Error('css load failed'))
      }

      document.head.appendChild(link)
    })
  }

  tryGoogleFonts().then(
    function () {
      gfSuccess = true
      console.info('[fonts] 使用 Google Fonts (Noto Sans SC)')
    },
    function () {
      loadLocalFallback()
    },
  )

  // 安全兜底：极端情况下强制加载本地
  setTimeout(loadLocalFallback, TIMEOUT + 1500)
})()
