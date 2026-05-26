<!-- Copyright 2026 smart-ebocr Contributors
SPDX-License-Identifier: Apache-2.0 -->

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useUsageStore } from '../stores/usage'
import { useUserStore } from '../stores/user'
import { pdfApi } from '../api'
import BillingComparison from '../components/BillingComparison.vue'
import FeatureGate from '../components/FeatureGate.vue'
import MonthPicker from '../components/MonthPicker.vue'

const store = useUsageStore()
const userStore = useUserStore()
const selected = ref({ year: new Date().getFullYear(), month: new Date().getMonth() + 1 })
const pdfYear = ref(new Date().getFullYear())
const pdfLoading = ref(false)

watch(selected, () => {
  store.fetchMonthly(selected.value.year, selected.value.month, userStore.selectedMemberId)
}, { deep: true })

watch(() => userStore.selectedMemberId, () => {
  store.fetchMonthly(selected.value.year, selected.value.month, userStore.selectedMemberId)
})

onMounted(() => {
  store.fetchMonthly(selected.value.year, selected.value.month, userStore.selectedMemberId)
})

async function downloadPdf() {
  pdfLoading.value = true
  try {
    const res = await pdfApi.annualPdf(pdfYear.value, userStore.selectedMemberId)
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `electricity-report-${pdfYear.value}.pdf`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (err) {
    alert('PDF 导出失败: ' + (err.response?.data?.error || err.message))
  } finally {
    pdfLoading.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-gray-800">电费对比</h1>
      <MonthPicker v-model="selected" />
    </div>

    <div v-if="store.loading" class="text-center py-8 text-gray-500">加载中...</div>

    <BillingComparison v-else-if="store.billingResult" :result="store.billingResult" />

    <div v-else class="text-center py-8 text-gray-500">暂无数据，请先上传截图或手动输入用电量</div>

    <!-- PDF 年度报告导出（高级用户） -->
    <FeatureGate requiredPlan="premium">
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 class="text-lg font-semibold mb-4">PDF 年度报告导出</h2>
        <div class="flex items-center gap-4">
          <div class="flex items-center gap-2">
            <button @click="pdfYear--" class="px-3 py-1 bg-gray-200 rounded hover:bg-gray-300">&lt;</button>
            <span class="text-lg font-semibold w-16 text-center">{{ pdfYear }}年</span>
            <button @click="pdfYear++" class="px-3 py-1 bg-gray-200 rounded hover:bg-gray-300">&gt;</button>
          </div>
          <button @click="downloadPdf" :disabled="pdfLoading"
            class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
            {{ pdfLoading ? '生成中...' : '下载 PDF 报告' }}
          </button>
        </div>
      </div>
    </FeatureGate>
  </div>
</template>