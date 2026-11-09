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
    { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFound.vue') },
  ],
})

router.beforeEach((to) => {
  // 导航守卫只负责体验，真正的权限由后端判定
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
})

export default router