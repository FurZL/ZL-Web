<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useSiteConfig } from '@/composables/useSiteConfig'

const route = useRoute()
const { siteName } = useSiteConfig()

type LegalKind = 'terms' | 'privacy' | 'copyright' | 'contact'

type LegalLink = {
  label: string
  href: string
  note?: string
}

type LegalSection = {
  title: string
  body: string
  links?: LegalLink[]
}

const UPDATED_AT = '2026 年 11 月 19 日'

const kind = computed<LegalKind>(() => {
  const slug = String(route.params.slug ?? 'terms')
  if (['privacy', 'copyright', 'contact'].includes(slug)) return slug as LegalKind
  return 'terms'
})

const meta = computed(() => {
  switch (kind.value) {
    case 'privacy':
      return { title: '隐私政策', intro: '我们如何收集、使用和保护你的个人信息。' }
    case 'copyright':
      return { title: '版权声明', intro: '关于本站内容的权利、转载与投诉处理规则。' }
    case 'contact':
      return { title: '联系我们', intro: '反馈问题、内容申诉或运营合作，欢迎来信。' }
    default:
      return { title: '用户协议', intro: '使用本站前，请先阅读并理解以下约定。' }
  }
})

const sections = computed<LegalSection[]>(() => {
  if (kind.value === 'privacy') {
    return [
      {
        title: '引言',
        body: `本隐私政策说明${siteName.value}（以下简称“本站”）如何收集、使用、保存和共享你的个人信息。使用本站服务前，请仔细阅读本政策。你勾选同意并提交注册，即表示你已阅读并理解本政策。`,
      },
      {
        title: '我们收集哪些信息',
        body: '当你注册账号、登录、上传图片、编辑主页或报名活动时，我们会收集运行服务所必需的信息，包括：\n\n• 账号信息：用户名、昵称、密码哈希、邮箱、手机号、账号状态与角色。\n• 登录与安全信息：登录时间、会话有效期、设备与浏览器标识摘要、IP 地址或脱敏记录、人机验证结果、验证码发送与校验记录。\n• 内容信息：你主动上传的图片、文件、个人简介、主页布局、活动报名信息及你填写的其他内容。\n• 第三方登录信息：经你授权后，从 QQ 互联获取的 QQ 用户标识（OpenID / UnionID）、昵称、头像及授权范围信息。\n\n你上传到个人空间的图片默认仅自己可见；公开图库内容是否展示由审核状态和权限决定。',
      },
      {
        title: '信息如何使用',
        body: '我们仅在下列目的范围内使用你的信息：\n\n• 创建和审批账号、完成登录认证、维持登录会话与找回密码。\n• 提供图片展示、个人空间、课表工具、活动报名等本站功能。\n• 发送注册结果、账号审批、安全提醒等必要通知。\n• 进行人机验证、频率限制、异常登录识别、内容审核和故障排查。\n• 履行法律法规规定的义务，处理投诉、侵权申诉与安全事件。\n\n我们不会出售你的个人信息。除本政策列明的第三方服务、你明确授权或法律法规要求外，我们不会向无关第三方披露你的个人信息。',
      },
      {
        title: '内容与定位权限',
        body: '课表、个人空间和私密图片都属于敏感内容。默认情况下仅本人可见；只有当你主动开启公开分享、或将图片设置为允许展示后，相应内容才会对其他用户开放。你可以随时关闭相关授权。',
      },
      {
        title: '第三方服务与信息处理',
        body: '为实现网站托管、图片存储与分发、QQ 登录、短信与邮件验证码、人机验证背景图和字体加载，本站接入了下列第三方服务。第三方服务可能按其隐私政策处理必要的设备信息、网络信息、日志信息、授权信息或你主动提交的验证信息。我们会要求服务商仅在提供服务所必需的范围内处理相关信息。',
        links: [
          {
            label: '腾讯云 EdgeOne / EdgeOne Pages',
            href: 'https://edgeone.ai/zh/document/46315',
            note: '前端静态资源托管与加速；官方隐私条款',
          },
          {
            label: '腾讯云对象存储 COS',
            href: 'https://cloud.tencent.com/document/product/301/11470',
            note: '图片和文件对象存储；图片展示通过本站代理域访问',
          },
          {
            label: 'QQ 互联',
            href: 'https://privacy.qq.com/policy/pbd',
            note: '可选第三方登录；仅在你在登录页点击 QQ 登录并授权后处理',
          },
          {
            label: '阿里云短信',
            href: 'https://terms.aliyun.com/legal-agreement/terms/suit_bu1_ali_cloud/suit_bu1_ali_cloud202107091605_49213.html',
            note: '手机验证码与必要的安全短信通知',
          },
          {
            label: '飞书企业邮箱（SMTP）',
            href: 'https://www.feishu.cn/privacy',
            note: '邮箱验证码与账号通知邮件',
          },
          {
            label: 'Microsoft Bing',
            href: 'https://www.microsoft.com/zh-cn/privacy/privacystatement',
            note: '滑块验证的背景图片；浏览器会直接请求 Bing 图片地址',
          },
          {
            label: 'Google Fonts',
            href: 'https://policies.google.cn/privacy',
            note: '尝试加载 Noto Sans SC 字体；不可用时回退本站本地字体',
          },
        ],
      },
      {
        title: 'Cookie 与登录状态',
        body: '本站使用必要的 Cookie 和浏览器本地存储维持登录状态。登录后，后端会写入 HttpOnly、Secure（生产环境）的刷新令牌 Cookie，有效期默认为 7 天；前端仅保存一个不包含令牌的会话标记。你访问本站时，登录状态会在有效期内自动续期。若连续 7 天没有访问，刷新令牌到期后需要重新登录。退出登录或撤销会话后，相应 Cookie 将失效。\n\n我们不会使用第三方广告 Cookie 进行跨站广告追踪。你可以通过浏览器设置清除 Cookie 和本地存储，但这会使你退出登录。',
      },
      {
        title: '信息共享、委托处理与依法提供',
        body: '我们仅在以下情形共享或提供信息：\n\n• 为提供本政策列明的服务，向相应服务商委托处理必要的技术与业务信息。\n• 取得你的明确同意或授权。\n• 为履行法定义务、应对突发公共卫生事件、保护你或他人的生命健康和财产安全所必需。\n• 公安机关、人民检察院、人民法院、网信、市场监管等有权机关依法定程序提出要求时，依法保存并提供必要的账号信息、联系方式、登录日志、发布记录、上传文件元数据、交易或活动记录等。\n\n对涉嫌违法、侵权、危害网络安全或社区安全的内容和行为，本站可依法采取删除、下架、限制功能、暂停或终止服务、封禁账号等措施，并依法保存相关记录。除法律另有规定外，我们不会无故向无关第三方披露你的个人信息。',
      },
      {
        title: '数据安全与保留',
        body: '密码使用 Argon2id 等成熟算法哈希存储，刷新令牌仅保存哈希值，验证码按用途隔离并以哈希形式保存。我们采取访问控制、传输加密、最小权限、日志审计和频率限制等措施保护信息安全。\n\n我们仅在实现处理目的所需的最短期限内保留个人信息，法律法规另有规定或为处理争议、配合监管所需的除外。你提出删除、更正或撤回同意申请后，我们会在法律允许的范围内及时处理；依法必须保留的信息除外。',
      },
      {
        title: '你的权利',
        body: '你可以在个人主页查看和修改昵称、简介、头像等资料，管理个人图片和已绑定的第三方登录。你也可以通过联系邮箱申请查阅、更正、删除个人信息，撤回授权，注销账号或获取相关说明。我们会在核实身份后依法处理。\n\n撤回同意不影响撤回前基于同意已进行的处理。注销账号后，相关个人信息将按法律要求和运营必要期限删除或匿名化处理。',
      },
      {
        title: '未成年人保护',
        body: '本站主要面向成年人与高校社群成员。未成年人应在监护人同意和指导下使用本站，不应上传涉及本人或他人隐私的敏感内容。若我们发现未经监护人同意收集了未成年人个人信息，将依法删除或采取其他必要措施。',
      },
      {
        title: '政策更新与联系我们',
        body: '我们可能因服务调整、法律法规变化而更新本政策。重大变更会在站内提示；更新后的政策自页面标注的更新日期起生效。\n\n如对本政策或个人信息处理有疑问、投诉或请求，请联系：contact@furzl.cn。我们通常会在 15 个工作日内答复。',
      },
    ]
  }
  if (kind.value === 'copyright') {
    return [
      {
        title: '内容归属',
        body: '站内用户上传的图片、文案和主页内容的版权归原作者所有。上传者应当确保自己有权发布相关内容，并授权本站进行展示、分发和必要的内容处理。',
      },
      {
        title: '转载规则',
        body: '若需转载本站内容，请先取得原作者或运营团队授权，并清晰注明来源。未经授权批量抓取、去水印使用或用于商业用途都属于禁止行为。',
      },
      {
        title: '侵权投诉',
        body: '如果你认为本站内容侵犯了你的合法权益，请通过 contact@furzl.cn 提供被侵权内容链接、权属证明和初步说明。我们会在核实后及时处理；涉嫌违法的，本站将依法保存必要信息并配合有权机关调查。',
      },
    ]
  }
  if (kind.value === 'contact') {
    return [
      {
        title: '联系邮箱',
        body: 'contact@furzl.cn',
      },
      {
        title: '常见事项',
        body: '账号申诉、内容举报、侵权投诉、个人信息权利请求、运营合作与站点异常反馈都可以发送至上述邮箱。来信请尽量附上相关链接或截图，我们会在工作日尽快回复。\n\n涉及违法和不良信息的举报，请说明具体页面、内容和理由；本站会依法保存相关记录并配合有权机关处理。',
      },
    ]
  }
  return [
    {
      title: '协议的范围与接受',
      body: `本协议是你与${siteName.value}之间关于使用本站服务的约定。你勾选同意并提交注册，即表示你已阅读、理解并同意本协议和《隐私政策》。注册后需等待管理员审批通过方可登录。若你不同意本协议，请停止注册和使用本站服务。`,
      links: [
        { label: '隐私政策', href: '/legal/privacy', note: '了解个人信息如何被处理' },
      ],
    },
    {
      title: '账号与内容',
      body: '你应提供真实、准确、完整的注册信息，并妥善保管账号、密码和登录设备。账号仅限本人使用，不得出租、出借、转让或买卖。你对自己账号下发布、上传、传播的内容和行为负责，不得利用本站发布违法违规、侵权、虚假、恶意骚扰或危害网络安全的内容。',
    },
    {
      title: '图片与个人空间',
      body: '公开图库接受审核后展示；个人空间默认私有。请不要上传自己无权发布的内容，不要在私密内容中嵌入可追踪他人隐私的信息。',
    },
    {
      title: '活动与课表',
      body: '报名活动的信息请如实填写；付费或实名活动另有公告说明。课表工具仅用于辅助对比与规划，请以学校教务系统为准。',
    },
    {
      title: '违规处理',
      body: '对于违反本协议、干扰社区秩序或侵害他人权益的行为，我们会视情节采取警告、内容下架、限制功能、暂停服务、封禁账号等措施，并保留依法追究责任的权利。对涉嫌违法、侵权、危害网络安全或社区安全的内容和行为，本站可依法保存相关记录并配合有权机关调查。',
    },
    {
      title: '第三方登录与外部服务',
      body: '你可以选择使用 QQ 互联登录本站。选择第三方登录前，请阅读 QQ 互联的隐私保护指引；你授权后，本站会获取必要的第三方账号标识、昵称和头像，用于登录、绑定账号和展示。第三方服务由相应服务商独立提供，其信息处理行为适用其自身的隐私政策和服务条款。\n\n本站还使用腾讯云 EdgeOne、腾讯云对象存储、阿里云短信、飞书企业邮箱、Microsoft Bing 和 Google Fonts 等服务完成网站托管、图片存储、验证码、邮件通知、人机验证和字体加载。相关说明及官方隐私政策链接见《隐私政策》的“第三方服务与信息处理”章节。',
      links: [
        { label: 'QQ 互联隐私保护指引', href: 'https://privacy.qq.com/policy/pbd' },
        { label: '查看完整隐私政策', href: '/legal/privacy' },
      ],
    },
    {
      title: '违法违规信息与依法配合',
      body: '你不得利用本站制作、复制、发布、传播法律法规禁止的信息，不得从事网络诈骗、侵犯他人隐私、传播恶意程序、攻击系统、批量抓取数据或其他违法活动。\n\n对涉嫌违法、侵权、危害网络安全或社区安全的内容和行为，本站有权依法采取删除、屏蔽、下架、限制功能、暂停或终止服务、封禁账号等措施，并保存相关记录。公安机关、人民检察院、人民法院、网信、市场监管等有权机关依法定程序提出要求时，本站将依法保存并提供必要的账号信息、联系方式、登录日志、发布记录、上传文件元数据、活动报名记录等，不视为违反本协议或隐私承诺。',
    },
    {
      title: '知识产权',
      body: '本站的页面设计、程序、文字、图形、标识等内容受法律保护。你上传的内容权利归你或原权利人所有；你授予本站为提供展示、存储、审核、分发和技术处理所必需的许可。发现侵权内容时，可通过 contact@furzl.cn 投诉，我们会依法处理。',
    },
    {
      title: '服务变更、中断与责任限制',
      body: '本站可能因维护、升级、网络故障、第三方服务异常或不可抗力暂停或调整部分服务。我们会尽力提前公告并减少影响。对因你违反本协议、账号保管不当、上传内容或使用第三方服务产生的损失，由你依法承担相应责任；本站依法不能免除的责任不因本条款而免除。',
    },
    {
      title: '协议更新与适用法律',
      body: '我们可能根据法律法规和服务变化更新本协议，更新后会在本页面公示。你继续使用本站服务，视为接受更新后的协议；重大变更会以站内提示等合理方式通知。\n\n本协议适用中华人民共和国大陆地区法律。因本协议产生的争议，双方应先协商解决；协商不成的，依法向本站运营者所在地有管辖权的人民法院提起诉讼。',
    },
  ]
})
</script>

<template>
  <div class="max-w-3xl mx-auto px-4 py-14">
    <div class="glass-card p-8 sm:p-10">
      <div class="border-b border-primary-100/70 pb-6">
        <p class="text-xs text-primary-700 font-medium">{{ siteName }}</p>
        <h1 class="mt-2 text-2xl font-bold text-ink">{{ meta.title }}</h1>
        <p class="mt-2 text-sm text-sub">{{ meta.intro }}</p>
        <p class="mt-2 text-xs text-faint">最近更新：{{ UPDATED_AT }}</p>
      </div>

      <div class="mt-7 space-y-7">
        <section v-for="section in sections" :key="section.title">
          <h2 class="text-base font-semibold text-ink">{{ section.title }}</h2>
          <a
            v-if="kind === 'contact' && section.title === '联系邮箱'"
            class="mt-2 inline-block text-sm font-medium text-primary-700 hover:underline"
            :href="`mailto:${section.body}`"
          >
            {{ section.body }}
          </a>
          <p v-else class="mt-2 text-sm leading-7 text-sub whitespace-pre-line">{{ section.body }}</p>
          <ul v-if="section.links?.length" class="mt-3 space-y-2">
            <li v-for="link in section.links" :key="link.href + link.label" class="text-sm leading-6">
              <RouterLink
                v-if="link.href.startsWith('/')"
                class="font-medium text-primary-700 hover:underline"
                :to="link.href"
              >
                {{ link.label }}
              </RouterLink>
              <a
                v-else
                class="font-medium text-primary-700 hover:underline"
                :href="link.href"
                target="_blank"
                rel="noopener noreferrer"
              >
                {{ link.label }}
              </a>
              <span v-if="link.note" class="text-sub">：{{ link.note }}</span>
            </li>
          </ul>
        </section>
      </div>
    </div>
  </div>
</template>
