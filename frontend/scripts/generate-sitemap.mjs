/**
 * 构建时生成 sitemap.xml 与 robots.txt。
 *
 * 只收录无需登录的静态公开页面；动态个人主页、动态活动页由后端数据驱动，
 * 不应在构建时猜测。站点地址可通过 SITE_URL 环境变量覆盖。
 */
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const siteUrl = (process.env.SITE_URL || 'https://www.furzl.cn').replace(/\/+$/, '')
const outDir = resolve(process.cwd(), 'dist')

const publicPaths = [
  { path: '/', changefreq: 'weekly', priority: '1.0' },
  { path: '/about', changefreq: 'monthly', priority: '0.8' },
  { path: '/gallery', changefreq: 'weekly', priority: '0.9' },
  { path: '/events', changefreq: 'weekly', priority: '0.8' },
  { path: '/legal/terms', changefreq: 'yearly', priority: '0.3' },
  { path: '/legal/privacy', changefreq: 'yearly', priority: '0.3' },
  { path: '/legal/copyright', changefreq: 'yearly', priority: '0.3' },
  { path: '/legal/contact', changefreq: 'yearly', priority: '0.3' },
]

const escapeXml = (value) =>
  value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&apos;')

const today = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Shanghai',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
}).format(new Date())
const urls = publicPaths
  .map(
    ({ path, changefreq, priority }) => `  <url>
    <loc>${escapeXml(`${siteUrl}${path}`)}</loc>
    <lastmod>${today}</lastmod>
    <changefreq>${changefreq}</changefreq>
    <priority>${priority}</priority>
  </url>`,
  )
  .join('\n')

const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`

const robots = `User-agent: *
Allow: /
Disallow: /admin/
Disallow: /profile/me/edit
Disallow: /oauth/qq

Sitemap: ${siteUrl}/sitemap.xml
`

await mkdir(outDir, { recursive: true })
await Promise.all([
  writeFile(resolve(outDir, 'sitemap.xml'), sitemap, 'utf8'),
  writeFile(resolve(outDir, 'robots.txt'), robots, 'utf8'),
])

console.log(`[sitemap] generated ${publicPaths.length} URLs for ${siteUrl}`)
