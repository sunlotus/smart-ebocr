// Copyright 2026 smart-ebocr Contributors
// SPDX-License-Identifier: Apache-2.0

import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'home', component: () => import('./views/Home.vue') },
  { path: '/upload', name: 'upload', component: () => import('./views/Upload.vue') },
  { path: '/monthly', name: 'monthly', component: () => import('./views/MonthlyView.vue') },
  { path: '/billing', name: 'billing', component: () => import('./views/BillingCompare.vue') },
  { path: '/settings', name: 'settings', component: () => import('./views/Settings.vue') },
  { path: '/advanced-charts', name: 'advanced-charts', component: () => import('./views/AdvancedCharts.vue') },
  { path: '/upgrade', name: 'upgrade', component: () => import('./views/Upgrade.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
