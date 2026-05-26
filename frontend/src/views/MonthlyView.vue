<!-- Copyright 2026 smart-ebocr Contributors
SPDX-License-Identifier: Apache-2.0 -->

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useUsageStore } from '../stores/usage'
import { useUserStore } from '../stores/user'
import DailyUsageTable from '../components/DailyUsageTable.vue'
import UsageChart from '../components/UsageChart.vue'
import MonthPicker from '../components/MonthPicker.vue'

const store = useUsageStore()
const userStore = useUserStore()
const selected = ref({ year: new Date().getFullYear(), month: new Date().getMonth() + 1 })

function loadData() {
  store.fetchMonthly(selected.value.year, selected.value.month, userStore.selectedMemberId)
}

watch(selected, () => {
  loadData()
}, { deep: true })

watch(() => userStore.selectedMemberId, () => {
  loadData()
})

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-gray-800">月度数据</h1>
      <MonthPicker v-model="selected" />
    </div>

    <div v-if="store.loading" class="text-center py-8 text-gray-500">加载中...</div>

    <template v-else>
      <div v-if="store.billingResult" class="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <p class="text-sm text-gray-500">本月用电量</p>
          <p class="text-2xl font-bold text-gray-800">{{ store.billingResult.total_kwh }} kWh</p>
        </div>
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <p class="text-sm text-gray-500">年度累计</p>
          <p class="text-2xl font-bold text-indigo-600">{{ store.billingResult.year_cumulative }} kWh</p>
        </div>
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <p class="text-sm text-gray-500">峰段电量</p>
          <p class="text-2xl font-bold text-orange-600">{{ store.billingResult.peak_kwh }} kWh</p>
        </div>
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <p class="text-sm text-gray-500">谷段电量</p>
          <p class="text-2xl font-bold text-blue-600">{{ store.billingResult.valley_kwh }} kWh</p>
        </div>
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <p class="text-sm text-gray-500">尖段电量</p>
          <p class="text-2xl font-bold text-red-600">{{ store.billingResult.sharp_kwh }} kWh</p>
        </div>
      </div>

      <UsageChart :records="store.billingResult?.daily_breakdown || []" />

      <DailyUsageTable
        :records="store.monthlyRecords"
        :year="selected.year"
        :month="selected.month"
        @refresh="loadData" />
    </template>
  </div>
</template>
