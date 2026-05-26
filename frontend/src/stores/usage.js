// Copyright 2026 smart-ebocr Contributors
// SPDX-License-Identifier: Apache-2.0

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { usageApi, billingApi, policyApi } from '../api'

export const useUsageStore = defineStore('usage', () => {
  const monthlyRecords = ref([])
  const yearCumulativeBefore = ref(0)
  const billingResult = ref(null)
  const policy = ref(null)
  const loading = ref(false)

  async function fetchMonthly(year, month, familyMemberId = null) {
    loading.value = true
    try {
      const params = { year, month }
      if (familyMemberId) params.family_member_id = familyMemberId
      const [usageRes, billingRes] = await Promise.all([
        usageApi.list(year, month, familyMemberId),
        billingApi.compare(year, month, familyMemberId),
      ])
      monthlyRecords.value = usageRes.data.records
      yearCumulativeBefore.value = usageRes.data.year_cumulative_before
      billingResult.value = billingRes.data
    } finally {
      loading.value = false
    }
  }

  async function addRecord(data, familyMemberId) {
    await usageApi.add(data, familyMemberId)
  }

  async function batchAdd(records, familyMemberId) {
    await usageApi.batchAdd(records, familyMemberId)
  }

  async function deleteRecord(date, familyMemberId = null) {
    await usageApi.delete(date, familyMemberId)
  }

  async function batchDelete(dates, familyMemberId = null) {
    await usageApi.batchDelete(dates, familyMemberId)
  }

  async function fetchPolicy(familyMemberId = null) {
    const params = {}
    if (familyMemberId) params.family_member_id = familyMemberId
    const res = await policyApi.get(params)
    policy.value = res.data
  }

  async function updatePolicy(data) {
    const res = await policyApi.update(data)
    policy.value = res.data
  }

  return {
    monthlyRecords,
    yearCumulativeBefore,
    billingResult,
    policy,
    loading,
    fetchMonthly,
    addRecord,
    batchAdd,
    deleteRecord,
    batchDelete,
    fetchPolicy,
    updatePolicy,
  }
})
