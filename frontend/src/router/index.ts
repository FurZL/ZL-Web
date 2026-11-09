import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('@/views/Home.vue') },
    { path: '/gallery', name: 'gallery', component: () => import('@/views/Gallery.vue') },
    { path: '/schedule', name: 'schedule', component: () => import('@/views/Schedule.vue') },
    { path: '/events', name: 'events', component: () => import('@/views/Events.vue') },
    { path: '/about', name: 'about', component: () => import('@/views/About.vue') },
    { path: '/profile', name: 'profile', component: () => import('@/views/Profile.vue') },
    { path: '/p/:slug', name: 'dynamic', component: () => import('@/views/DynamicPage.vue') },
  ],
})

export default router