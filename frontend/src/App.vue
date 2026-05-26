<!-- Copyright 2026 smart-ebocr Contributors
SPDX-License-Identifier: Apache-2.0 -->

<script setup>
import AccountSelector from './components/AccountSelector.vue'
import { useUserStore } from './stores/user'

const userStore = useUserStore()
userStore.ensureLoaded()
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <nav class="bg-white shadow-sm border-b border-gray-200">
      <div class="max-w-6xl mx-auto px-4 py-3 flex items-center gap-6">
        <router-link to="/" class="text-xl font-bold text-blue-600">电费分析工具</router-link>
        <div class="flex gap-4 text-sm">
          <router-link to="/upload" class="text-gray-600 hover:text-blue-600">上传截图</router-link>
          <router-link to="/monthly" class="text-gray-600 hover:text-blue-600">月度数据</router-link>
          <router-link to="/billing" class="text-gray-600 hover:text-blue-600">电费对比</router-link>
          <router-link to="/settings" class="text-gray-600 hover:text-blue-600">电价设置</router-link>
          <router-link to="/advanced-charts" class="text-gray-600 hover:text-blue-600">高级图表</router-link>
          <router-link to="/upgrade" class="text-gray-600 hover:text-blue-600">赞助</router-link>
        </div>
        <div class="ml-auto flex items-center gap-3">
          <AccountSelector />
        </div>
      </div>
    </nav>
    <main class="max-w-6xl mx-auto px-4 py-6">
      <router-view />
    </main>
  </div>
</template>
