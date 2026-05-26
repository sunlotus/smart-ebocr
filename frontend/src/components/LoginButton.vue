<!-- Copyright 2026 smart-ebocr Contributors
SPDX-License-Identifier: Apache-2.0 -->

<script setup>
import { ref, computed } from 'vue'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
const showMenu = ref(false)

const allAccounts = computed(() => {
  if (!userStore.hasPlan('supporter') || userStore.familyMembers.length === 0) return []
  return [
    { id: null, name: userStore.user?.name || '我', avatar_color: null },
    ...userStore.familyMembers
  ]
})

const currentAccountName = computed(() => {
  if (!userStore.isLoggedIn) return ''
  if (userStore.selectedMemberId) {
    const member = userStore.familyMembers.find(m => m.id === userStore.selectedMemberId)
    return member?.name || userStore.user?.name
  }
  return userStore.user?.name
})

function handleLogin() {
  userStore.login()
}

function handleLogout() {
  showMenu.value = false
  userStore.logout()
}

function selectAccount(account) {
  userStore.selectMember(account.id)
  showMenu.value = false
}
</script>

<template>
  <div v-if="userStore.isLoggedIn" class="relative">
    <button
      @click="showMenu = !showMenu"
      class="flex items-center gap-2 text-sm text-gray-600 hover:text-blue-600"
    >
      <img
        v-if="userStore.user?.avatar_url"
        :src="userStore.user.avatar_url"
        :alt="userStore.user.name"
        class="w-6 h-6 rounded-full"
      />
      <span>{{ currentAccountName }}</span>
      <svg v-if="allAccounts.length > 0" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    <div
      v-if="showMenu"
      class="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50"
    >
      <div class="px-4 py-2 border-b border-gray-100">
        <p class="text-sm font-medium text-gray-900">{{ userStore.user?.name }}</p>
        <p class="text-xs text-gray-500">
          {{ { free: '免费用户', supporter: '支持者', premium: '高级用户', super: '超级用户' }[userStore.planName] || '免费用户' }}
        </p>
      </div>

      <!-- 账户切换（有子账户时显示） -->
      <div v-if="allAccounts.length > 0" class="border-b border-gray-100 py-1">
        <p class="px-4 py-1 text-xs text-gray-400">切换账户</p>
        <button
          v-for="account in allAccounts" :key="account.id ?? 'default'"
          @click="selectAccount(account)"
          :class="[
            'w-full flex items-center gap-3 px-4 py-2 text-sm hover:bg-gray-50',
            userStore.selectedMemberId === account.id ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
          ]">
          <div
            v-if="account.avatar_color"
            class="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-medium"
            :style="{ backgroundColor: account.avatar_color }">
            {{ account.name[0] }}
          </div>
          <span>{{ account.name }}</span>
        </button>
      </div>

      <router-link
        to="/profile"
        class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
        @click="showMenu = false"
      >
        个人中心
      </router-link>

      <button
        @click="handleLogout"
        class="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-gray-50"
      >
        退出登录
      </button>
    </div>

    <!-- 点击外部关闭 -->
    <div v-if="showMenu" class="fixed inset-0 z-40" @click="showMenu = false" />
  </div>

  <button
    v-else
    @click="handleLogin"
    class="text-sm px-3 py-1.5 rounded-md bg-blue-600 text-white hover:bg-blue-700"
  >
    爱发电登录
  </button>
</template>
