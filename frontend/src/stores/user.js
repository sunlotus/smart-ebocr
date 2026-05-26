// Copyright 2026 smart-ebocr Contributors
// SPDX-License-Identifier: Apache-2.0

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export const useUserStore = defineStore('user', () => {
  const user = ref({ name: '用户', is_anonymous: true })
  const loading = ref(false)

  // 子账户相关
  const familyMembers = ref([])
  const selectedMemberId = ref(null)

  let _initPromise = null

  const planName = computed(() => 'free')

  function hasPlan() {
    return true
  }

  async function init() {
    loading.value = true
    try {
      await fetchFamilyMembers()
    } finally {
      loading.value = false
    }
  }

  function ensureLoaded() {
    if (!_initPromise) {
      _initPromise = init()
    }
    return _initPromise
  }

  // 子账户管理
  async function fetchFamilyMembers() {
    try {
      const { data } = await api.get('/family-members/')
      familyMembers.value = data.members
    } catch (err) {
      console.error('Failed to fetch family members:', err)
    }
  }

  async function createMember(name) {
    const { data } = await api.post('/family-members/', { name })
    familyMembers.value.push(data)
    return data
  }

  async function deleteMember(id) {
    await api.delete(`/family-members/${id}`)
    familyMembers.value = familyMembers.value.filter(m => m.id !== id)
    if (selectedMemberId.value === id) {
      selectedMemberId.value = null
    }
  }

  function selectMember(id) {
    selectedMemberId.value = id
  }

  return {
    user,
    loading,
    planName,
    hasPlan,
    ensureLoaded,
    familyMembers,
    selectedMemberId,
    fetchFamilyMembers,
    createMember,
    deleteMember,
    selectMember,
  }
})
