<!-- Copyright 2026 smart-ebocr Contributors
SPDX-License-Identifier: Apache-2.0 -->

<script setup>
import { ref, computed } from 'vue'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
const showDropdown = ref(false)

const allAccounts = computed(() => {
  return [
    { id: null, name: userStore.user?.name || '我', avatar_color: null },
    ...userStore.familyMembers,
  ]
})

const currentAccount = computed(() => {
  if (userStore.selectedMemberId) {
    const member = userStore.familyMembers.find(m => m.id === userStore.selectedMemberId)
    if (member) return member
  }
  return allAccounts.value[0]
})

function selectAccount(account) {
  userStore.selectMember(account.id)
  showDropdown.value = false
}
</script>

<template>
  <div v-if="userStore.loading" class="text-xs text-gray-400">加载中...</div>
  <div v-else-if="userStore.familyMembers.length > 0" class="relative">
    <button
      @click="showDropdown = !showDropdown"
      class="flex items-center gap-2 text-sm px-2.5 py-1 rounded-md border border-gray-300 hover:bg-gray-50 text-gray-700"
    >
      <div
        v-if="currentAccount.avatar_color"
        class="w-5 h-5 rounded-full flex items-center justify-center text-white text-xs font-medium"
        :style="{ backgroundColor: currentAccount.avatar_color }"
      >
        {{ currentAccount.name[0] }}
      </div>
      <img
        v-else-if="userStore.user?.avatar_url"
        :src="userStore.user.avatar_url"
        class="w-5 h-5 rounded-full"
      />
      <span class="max-w-[80px] truncate">{{ currentAccount.name }}</span>
      <svg class="w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    <div
      v-if="showDropdown"
      class="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50"
    >
      <p class="px-4 py-1 text-xs text-gray-400">切换账户</p>
      <button
        v-for="account in allAccounts" :key="account.id ?? 'default'"
        @click="selectAccount(account)"
        :class="[
          'w-full flex items-center gap-3 px-4 py-2 text-sm hover:bg-gray-50',
          userStore.selectedMemberId === account.id ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
        ]"
      >
        <div
          v-if="account.avatar_color"
          class="w-5 h-5 rounded-full flex items-center justify-center text-white text-xs font-medium"
          :style="{ backgroundColor: account.avatar_color }"
        >
          {{ account.name[0] }}
        </div>
        <div
          v-else
          class="w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center text-white text-xs font-medium"
        >
          {{ (account.name || '我')[0] }}
        </div>
        <span>{{ account.name }}</span>
      </button>
    </div>

    <div v-if="showDropdown" class="fixed inset-0 z-40" @click="showDropdown = false" />
  </div>
</template>
