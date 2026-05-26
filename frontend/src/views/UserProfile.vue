<!-- Copyright 2026 smart-ebocr Contributors
SPDX-License-Identifier: Apache-2.0 -->

<script setup>
import { onMounted } from 'vue'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()

onMounted(() => {
  if (userStore.isLoggedIn) {
    userStore.fetchUser()
  }
})

const planLabels = {
  free: '免费用户',
  supporter: '支持者（¥9/月）',
  premium: '高级用户（¥30/月）',
  super: '超级用户（¥99/月）',
}
</script>

<template>
  <div class="max-w-2xl mx-auto">
    <h1 class="text-2xl font-bold text-gray-800 mb-6">个人中心</h1>

    <div v-if="!userStore.isLoggedIn" class="text-center py-12">
      <p class="text-gray-500 mb-4">尚未登录</p>
      <button
        @click="userStore.login()"
        class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
      >
        爱发电登录
      </button>
    </div>

    <div v-else class="space-y-6">
      <!-- 用户信息 -->
      <div class="bg-white rounded-lg border border-gray-200 p-6">
        <div class="flex items-center gap-4">
          <img
            v-if="userStore.user?.avatar_url"
            :src="userStore.user.avatar_url"
            :alt="userStore.user.name"
            class="w-16 h-16 rounded-full"
          />
          <div>
            <h2 class="text-lg font-semibold text-gray-800">{{ userStore.user?.name }}</h2>
            <p class="text-sm text-gray-500">
              {{ planLabels[userStore.planName] || '免费用户' }}
            </p>
          </div>
        </div>
      </div>

      <!-- 赞助状态 -->
      <div class="bg-white rounded-lg border border-gray-200 p-6">
        <h3 class="font-medium text-gray-800 mb-3">赞助状态</h3>
        <div class="space-y-2 text-sm">
          <div class="flex justify-between">
            <span class="text-gray-500">当前档位</span>
            <span class="font-medium">{{ planLabels[userStore.planName] || '免费用户' }}</span>
          </div>
          <div v-if="userStore.user?.expires_at" class="flex justify-between">
            <span class="text-gray-500">到期时间</span>
            <span class="font-medium">{{ userStore.user.expires_at.slice(0, 10) }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">已解锁功能</span>
            <span class="font-medium">{{ userStore.features.length }} 项</span>
          </div>
        </div>

        <div class="mt-4 flex gap-3">
          <button
            @click="userStore.syncStatus()"
            :disabled="userStore.loading"
            class="px-4 py-2 text-sm rounded-md border border-gray-300 hover:bg-gray-50 disabled:opacity-50"
          >
            {{ userStore.loading ? '同步中...' : '刷新赞助状态' }}
          </button>
          <router-link
            to="/upgrade"
            class="px-4 py-2 text-sm rounded-md bg-blue-600 text-white hover:bg-blue-700"
          >
            查看赞助方案
          </router-link>
        </div>
      </div>

      <!-- 爱发电主页 -->
      <div class="bg-white rounded-lg border border-gray-200 p-6">
        <h3 class="font-medium text-gray-800 mb-2">爱发电主页</h3>
        <p class="text-sm text-gray-500 mb-3">前往爱发电管理你的赞助</p>
        <a
          href="https://ifdian.net/a/smart-ebocr"
          target="_blank"
          rel="noopener"
          class="inline-block px-4 py-2 text-sm rounded-md bg-orange-500 text-white hover:bg-orange-600"
        >
          打开爱发电
        </a>
      </div>
    </div>
  </div>
</template>