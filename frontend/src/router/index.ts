import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('@/views/Home.vue') },
    { path: '/about', name: 'about', component: () => import('@/views/About.vue') },
    { path: '/gallery', name: 'gallery', component: () => import('@/views/Gallery.vue') },
    { path: '/schedule', name: 'schedule', component: () => import('@/views/Schedule.vue'), meta: { requiresAuth: true } },
    { path: '/profile', name: 'profile', component: () => import('@/views/Profile.vue'), meta: { requiresAuth: true } },
    { path: '/profile/:username', name: 'user-profile', component: () => import('@/views/Profile.vue') },
    { path: '/login', name: 'login', component: () => import('@/views/Login.vue') },
    { path: '/register', name: 'register', component: () => import('@/views/Register.vue') },
    { path: '/register/pending', name: 'register-pending', component: () => import('@/views/RegisterPending.vue') },
    { path: '/forgot-password', name: 'forgot-password', component: () => import('@/views/ForgotPassword.vue') },
    { path: '/events', name: 'events', component: () => import('@/views/Events.vue') },
    { path: '/p/:slug', name: 'dynamic', component: () => import('@/views/DynamicPage.vue') },

    // 管理后台
    {
      path: '/admin',
      component: () => import('@/layouts/AdminLayout.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
      children: [
        { path: '', name: 'admin-dashboard', component: () => import('@/views/admin/AdminDashboard.vue') },
        { path: 'users', name: 'admin-users', component: () => import('@/views/admin/AdminUsers.vue') },
        { path: 'images', name: 'admin-images', component: () => import('@/views/admin/AdminImages.vue') },
        { path: 'events', name: 'admin-events', component: () => import('@/views/admin/AdminEvents.vue') },
        { path: 'pages', name: 'admin-pages', component: () => import('@/views/admin/AdminPages.vue') },
        { path: 'settings', name: 'admin-settings', component: () => import('@/views/admin/AdminSettings.vue') },
      ],
    },

    { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFound.vue') },
  ],
})

router.beforeEach((to) => {
  // 导航守卫只负责体验，真正的权限由后端判定
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return { name: 'home' }
  }
})

export default router