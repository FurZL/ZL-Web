/**
 * 开发期 mock：个人主页客制化契约的可执行版本。
 * 只在 `vite` dev server 里生效（生产构建不含），开关见 vite.config.ts。
 * 后端落地后删掉 vite.config.ts 里的 profileMock() 一行即可，业务代码无需改动。
 */
import type { Plugin } from 'vite'
import type { IncomingMessage, ServerResponse } from 'node:http'

type Block = { id: string; type: string; span: number; props: Record<string, unknown> }
type Media = { thumb_url: string | null; display_url: string | null; width: number | null; height: number | null }

interface MockImage {
  id: string
  object_key: string
  title: string
  created_at: string
  is_displayable: boolean
  width: number
  height: number
}

const ALLOWED_SPANS: Record<string, number[]> = {
  bio: [4, 6, 8, 12],
  quote: [4, 6, 12],
  featured_photo: [12],
  photo_wall: [6, 8, 12],
  gallery_link: [3, 4, 6, 12],
  links: [3, 4, 6],
  stats: [3, 4, 6, 12],
  html_block: [12],
}

const TEN_MINUTES = 600

function svg(label: string, from: string, to: string): string {
  const s = `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${from}"/><stop offset="1" stop-color="${to}"/></linearGradient></defs><rect width="400" height="400" fill="url(#g)"/><text x="200" y="210" font-size="28" font-family="sans-serif" fill="rgba(255,255,255,0.9)" text-anchor="middle">${label}</text></svg>`
  return `data:image/svg+xml;utf8,${encodeURIComponent(s)}`
}

const IMAGES: MockImage[] = [
  { id: 'img-1', object_key: 'private/profiles/demo/a1', title: '夏日漫展', created_at: '2026-08-03', is_displayable: true, width: 400, height: 400 },
  { id: 'img-2', object_key: 'private/profiles/demo/a2', title: '社团合影', created_at: '2026-07-19', is_displayable: true, width: 400, height: 400 },
  { id: 'img-3', object_key: 'private/profiles/demo/a3', title: '毛绒玩偶', created_at: '2026-06-30', is_displayable: false, width: 400, height: 400 },
  { id: 'img-4', object_key: 'private/profiles/demo/a4', title: '夜景练习', created_at: '2026-06-12', is_displayable: false, width: 400, height: 400 },
]

const MEDIA: Record<string, Media> = {
  'private/profiles/demo/a1': { thumb_url: svg('夏日漫展', '#6B5CE7', '#B8AEEF'), display_url: svg('夏日漫展', '#6B5CE7', '#B8AEEF'), width: 400, height: 400 },
  'private/profiles/demo/a2': { thumb_url: svg('社团合影', '#F0A6C8', '#F5C7DD'), display_url: svg('社团合影', '#F0A6C8', '#F5C7DD'), width: 400, height: 400 },
  'private/profiles/demo/a3': { thumb_url: svg('毛绒玩偶', '#5BC0BE', '#A8E6CF'), display_url: svg('毛绒玩偶', '#5BC0BE', '#A8E6CF'), width: 400, height: 400 },
  'private/profiles/demo/a4': { thumb_url: svg('夜景练习', '#F4A261', '#FAD2A6'), display_url: svg('夜景练习', '#F4A261', '#FAD2A6'), width: 400, height: 400 },
}

const DEFAULT_THEME = {
  primary: '#6B5CE7',
  accent: '#F0A6C8',
  background_type: 'gradient',
  background_key: null as string | null,
  background_blur: 0,
  card_style: 'glass',
}

const state = {
  theme: { ...DEFAULT_THEME },
  draft: [] as Block[],
  published: null as Block[] | null,
  isPublic: true,
  maxBlocks: 16,
}

function seed() {
  const blocks: Block[] = [
    { id: 'seed-bio', type: 'bio', span: 8, props: { text: '在杭州念书的毛茸茸爱好者，喜欢画图、拍照、听 Live。\n周末一般在社团活动室出没。' } },
    { id: 'seed-stats', type: 'stats', span: 4, props: { items: ['joined_days', 'gallery_image_count'] } },
    { id: 'seed-featured', type: 'featured_photo', span: 12, props: { object_key: 'private/profiles/demo/a1', caption: '今年夏天的第一场漫展' } },
    { id: 'seed-wall', type: 'photo_wall', span: 8, props: { object_keys: ['private/profiles/demo/a2', 'private/profiles/demo/a1'], columns: 2 } },
    { id: 'seed-links', type: 'links', span: 4, props: { items: [{ label: '社团公告', url: 'https://example.com/notices' }, { label: '我的 Pixiv', url: 'https://example.com/pixiv' }] } },
    { id: 'seed-quote', type: 'quote', span: 6, props: { text: '毛好，人也好。', author: '某位圈友' } },
    { id: 'seed-gallery', type: 'gallery_link', span: 6, props: { tag: '漫展', label: '看看现场照片' } },
  ]
  state.draft = blocks.map((b) => ({ ...b, props: { ...b.props } }))
  state.published = blocks.map((b) => ({ ...b, props: { ...b.props } }))
}

seed()

function mediaFor(keys: string[]): Record<string, Media> {
  const out: Record<string, Media> = {}
  for (const key of keys) {
    const img = IMAGES.find((i) => i.object_key === key)
    if (!img || !img.is_displayable) continue // 不可展示的一律剔除，模拟后端硬约束
    if (MEDIA[key]) out[key] = MEDIA[key]
  }
  return out
}

function collectKeys(blocks: Block[], theme: typeof state.theme): string[] {
  const keys = new Set<string>()
  for (const b of blocks) {
    if (b.type === 'featured_photo' && typeof b.props.object_key === 'string') keys.add(b.props.object_key)
    if (b.type === 'photo_wall' && Array.isArray(b.props.object_keys)) {
      for (const k of b.props.object_keys) if (typeof k === 'string') keys.add(k)
    }
  }
  if (theme.background_key) keys.add(theme.background_key)
  return [...keys]
}

function validateBlocks(raw: unknown): { blocks: Block[] } | { error: string } {
  if (!Array.isArray(raw)) return { error: 'blocks 必须是数组' }
  if (raw.length > state.maxBlocks) return { error: `模块数超过上限 ${state.maxBlocks}` }
  const seen = new Set<string>()
  const blocks: Block[] = []
  for (const item of raw) {
    if (typeof item !== 'object' || item === null) return { error: 'block 必须是对象' }
    const b = item as Record<string, unknown>
    const id = String(b.id ?? '')
    if (!/^[A-Za-z0-9_-]{1,32}$/.test(id)) return { error: `块 id 非法：${id}` }
    if (seen.has(id)) return { error: `块 id 重复：${id}` }
    seen.add(id)
    const type = String(b.type ?? '')
    const spans = ALLOWED_SPANS[type]
    if (!spans) return { error: `未知模块类型：${id}.type=${type}` }
    const span = Number(b.span)
    if (!spans.includes(span)) return { error: `块 ${id} 的宽度 ${span} 不被允许` }
    const props = typeof b.props === 'object' && b.props !== null ? (b.props as Record<string, unknown>) : {}
    blocks.push({ id, type, span, props })
  }
  return { blocks }
}

function stats() {
  return { joined_days: 268, gallery_image_count: 12 }
}

function send(res: ServerResponse, status: number, body: unknown) {
  const json = JSON.stringify(body)
  res.statusCode = status
  res.setHeader('Content-Type', 'application/json; charset=utf-8')
  res.setHeader('Cache-Control', 'no-store')
  res.end(json)
}

function ok(res: ServerResponse, data: unknown) {
  send(res, 200, { success: true, data, error: null, request_id: 'mock' })
}

function fail(res: ServerResponse, status: number, code: string, message: string) {
  send(res, status, { success: false, data: null, error: { code, message }, request_id: 'mock' })
}

function readBody(req: IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    let raw = ''
    req.on('data', (chunk) => {
      raw += chunk
      if (raw.length > 512 * 1024) reject(new Error('payload too large'))
    })
    req.on('end', () => resolve(raw))
    req.on('error', reject)
  })
}

function parseJson(raw: string): Record<string, unknown> {
  if (!raw) return {}
  try {
    const v = JSON.parse(raw)
    return typeof v === 'object' && v !== null ? (v as Record<string, unknown>) : {}
  } catch {
    return {}
  }
}

function layoutPayload() {
  return {
    theme: state.theme,
    draft_blocks: state.draft,
    published_blocks: state.published,
    is_public: state.isPublic,
    max_blocks: state.maxBlocks,
    media: mediaFor(collectKeys([...state.draft, ...(state.published ?? [])], state.theme)),
    media_expires_in: TEN_MINUTES,
    stats: stats(),
  }
}

function pagePayload(username: string) {
  return {
    user: { username, display_name: '示例成员', avatar_url: null },
    theme: state.theme,
    blocks: state.published ?? [],
    media: mediaFor(collectKeys(state.published ?? [], state.theme)),
    media_expires_in: TEN_MINUTES,
    stats: stats(),
    published_at: state.published ? '2026-11-01T10:00:00Z' : null,
  }
}

async function handle(req: IncomingMessage, res: ServerResponse, url: URL): Promise<boolean> {
  const path = url.pathname.replace(/^\/api\/v1/, '')
  const method = (req.method ?? 'GET').toUpperCase()

  // 会话相关：让 /profile/me/edit 的登录守卫在 mock 模式下放行
  if (path === '/auth/refresh' && method === 'POST') {
    ok(res, { access_token: 'mock-access', refresh_token: 'mock-refresh' })
    return true
  }
  if (path === '/auth/me' && method === 'GET') {
    ok(res, {
      id: 'demo',
      username: 'demo',
      display_name: '示例成员',
      role: 'member',
      avatar_url: null,
      bio: '在杭州念书的毛茸茸爱好者',
    })
    return true
  }

  if (path === '/profile/me/layout' && method === 'GET') {
    ok(res, layoutPayload())
    return true
  }

  if (path === '/profile/me/layout' && method === 'PUT') {
    const body = parseJson(await readBody(req))
    const result = validateBlocks(body.blocks)
    if ('error' in result) {
      fail(res, 422, 'PROFILE_LAYOUT_INVALID', result.error)
      return true
    }
    state.draft = result.blocks
    if (typeof body.is_public === 'boolean') state.isPublic = body.is_public
    ok(res, layoutPayload())
    return true
  }

  if (path === '/profile/me/layout/publish' && method === 'POST') {
    if (!state.draft.length) {
      fail(res, 422, 'PROFILE_LAYOUT_EMPTY', '草稿为空，无法发布')
      return true
    }
    state.published = state.draft.map((b) => ({ ...b, props: { ...b.props } }))
    ok(res, { published_at: new Date().toISOString() })
    return true
  }

  if (path === '/profile/me/layout/discard' && method === 'POST') {
    state.draft = (state.published ?? []).map((b) => ({ ...b, props: { ...b.props } }))
    ok(res, layoutPayload())
    return true
  }

  if (path === '/profile/me/theme' && method === 'PUT') {
    const body = parseJson(await readBody(req))
    const merged = { ...DEFAULT_THEME, ...body } as typeof state.theme
    if (!/^#[0-9a-fA-F]{6}$/.test(merged.primary) || !/^#[0-9a-fA-F]{6}$/.test(merged.accent)) {
      fail(res, 422, 'PROFILE_THEME_INVALID', '颜色需为 #RRGGBB')
      return true
    }
    state.theme = merged
    ok(res, { theme: state.theme })
    return true
  }

  if (path === '/profile/me/media' && method === 'GET') {
    ok(res, {
      items: IMAGES.map((img) => ({
        id: img.id,
        object_key: img.object_key,
        title: img.title,
        created_at: img.created_at,
        is_displayable: img.is_displayable,
        ...MEDIA[img.object_key],
      })),
    })
    return true
  }

  const patchMatch = /^\/profile\/me\/images\/([^/]+)$/.exec(path)
  if (patchMatch && method === 'PATCH') {
    const body = parseJson(await readBody(req))
    const target = IMAGES.find((i) => i.id === patchMatch[1])
    if (!target) {
      fail(res, 404, 'PROFILE_IMAGE_NOT_FOUND', '图片不存在')
      return true
    }
    if (typeof body.is_displayable === 'boolean') target.is_displayable = body.is_displayable
    ok(res, { id: target.id, is_displayable: target.is_displayable })
    return true
  }

  if (path === '/profile/me/images' && method === 'GET') {
    ok(res, {
      items: IMAGES.map((img) => ({
        id: img.id,
        original_name: `${img.title}.jpg`,
        title: img.title,
        description: null,
        width: img.width,
        height: img.height,
        created_at: img.created_at,
        processing_status: 'ready',
        thumb_url: MEDIA[img.object_key].thumb_url,
      })),
    })
    return true
  }

  const urlMatch = /^\/profile\/me\/images\/([^/]+)\/url$/.exec(path)
  if (urlMatch && method === 'GET') {
    const img = IMAGES.find((i) => i.id === urlMatch[1])
    if (!img) {
      fail(res, 404, 'PROFILE_IMAGE_NOT_FOUND', '图片不存在')
      return true
    }
    ok(res, { url: MEDIA[img.object_key].display_url })
    return true
  }

  const pageMatch = /^\/profile\/([^/]+)\/page$/.exec(path)
  if (pageMatch && method === 'GET') {
    if (!state.isPublic || !state.published || !state.published.length) {
      fail(res, 404, 'PROFILE_PAGE_NOT_FOUND', '该用户还没有公开主页')
      return true
    }
    ok(res, pagePayload(decodeURIComponent(pageMatch[1])))
    return true
  }

  return false
}

export function profileMock(): Plugin {
  return {
    name: 'profile-mock',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const raw = req.url ?? ''
        if (!raw.startsWith('/api/v1/')) return next()
        // 只管本功能的路径，其余照常转发给真实后端
        if (!/^\/api\/v1\/(profile|auth\/(me|refresh))/.test(raw)) return next()
        const url = new URL(raw, 'http://localhost')
        handle(req, res, url)
          .then((handled) => {
            if (!handled) next()
          })
          .catch(() => {
            fail(res, 500, 'MOCK_ERROR', 'mock 处理失败')
          })
      })
    },
  }
}
