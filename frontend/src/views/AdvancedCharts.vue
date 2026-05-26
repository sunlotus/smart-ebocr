<!-- Copyright 2026 smart-ebocr Contributors
SPDX-License-Identifier: Apache-2.0 -->

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { dashboardApi } from '../api'
import { useUserStore } from '../stores/user'
import FeatureGate from '../components/FeatureGate.vue'
import CompareTrendChart from '../components/CompareTrendChart.vue'
import TierProgress from '../components/dashboard/TierProgress.vue'
import PeakValleyPie from '../components/dashboard/PeakValleyPie.vue'
import CostBreakdown from '../components/dashboard/CostBreakdown.vue'
import SavingsTrend from '../components/dashboard/SavingsTrend.vue'
import YearlyCumulative from '../components/dashboard/YearlyCumulative.vue'
import SeasonalCompare from '../components/dashboard/SeasonalCompare.vue'
import UsageDistribution from '../components/dashboard/UsageDistribution.vue'

const userStore = useUserStore()
const loading = ref(false)
const dashboardData = ref(null)
const year = ref(new Date().getFullYear())

async function fetchData() {
  loading.value = true
  try {
    const res = await dashboardApi.annualDashboard(year.value, userStore.selectedMemberId)
    dashboardData.value = res.data
  } catch (err) {
    console.error('加载仪表盘数据失败:', err)
    dashboardData.value = null
  } finally {
    loading.value = false
  }
}

const summary = computed(() => dashboardData.value?.summary || {})
const tierProgress = computed(() => dashboardData.value?.tier_progress || {})
const monthly = computed(() => dashboardData.value?.monthly_breakdown || [])
const distribution = computed(() => dashboardData.value?.distribution || {})
const seasonal = computed(() => dashboardData.value?.seasonal || {})
const compareTrend = computed(() => dashboardData.value?.compare_trend || null)
const forecast = computed(() => dashboardData.value?.forecast || [])

watch(year, fetchData)
watch(() => userStore.selectedMemberId, fetchData)
onMounted(fetchData)
</script>

<template>
  <FeatureGate requiredPlan="premium">
    <div class="space-y-6">
      <!-- 标题 + 年份控制 -->
      <div class="flex items-center justify-between">
        <h1 class="text-2xl font-bold text-gray-800">高级分析仪表盘</h1>
        <div class="flex items-center gap-2">
          <button @click="year--" class="px-3 py-1 bg-gray-200 rounded hover:bg-gray-300">&lt;</button>
          <span class="text-lg font-semibold w-16 text-center">{{ year }}年</span>
          <button @click="year++" class="px-3 py-1 bg-gray-200 rounded hover:bg-gray-300">&gt;</button>
        </div>
      </div>

      <div v-if="loading" class="text-center py-8 text-gray-500">加载中...</div>

      <template v-else-if="dashboardData">
        <!-- 汇总卡片 -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="bg-white rounded-lg border p-4 text-center">
            <div class="text-sm text-gray-500">年度总电量</div>
            <div class="text-2xl font-bold text-gray-800">{{ summary.total_kwh }} <span class="text-sm font-normal">kWh</span></div>
          </div>
          <div class="bg-white rounded-lg border p-4 text-center">
            <div class="text-sm text-gray-500">年度总费用</div>
            <div class="text-2xl font-bold text-gray-800">{{ summary.total_cost_tou }} <span class="text-sm font-normal">元</span></div>
          </div>
          <div class="bg-white rounded-lg border p-4 text-center">
            <div class="text-sm text-gray-500">节省金额</div>
            <div class="text-2xl font-bold" :class="summary.savings > 0 ? 'text-green-600' : 'text-red-600'">
              {{ summary.savings > 0 ? '+' : '' }}{{ summary.savings }} <span class="text-sm font-normal">元</span>
            </div>
          </div>
          <div class="bg-white rounded-lg border p-4 text-center">
            <div class="text-sm text-gray-500">日均用电</div>
            <div class="text-2xl font-bold text-gray-600">{{ summary.avg_daily }} <span class="text-sm font-normal">kWh</span></div>
          </div>
        </div>

        <!-- 第一行：阶梯进度 + 峰谷占比 -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <TierProgress :data="tierProgress" />
          <PeakValleyPie :peak="summary.peak_kwh" :valley="summary.valley_kwh" />
        </div>

        <!-- 第二行：费用构成 + 节省趋势 -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <CostBreakdown :data="monthly" />
          <SavingsTrend :data="monthly" />
        </div>

        <!-- 第三行：年度累计 + 同比环比 -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <YearlyCumulative
            :monthly="monthly"
            :forecast="forecast.forecast || []"
            :tier1Limit="tierProgress.tier1_limit"
            :tier2Limit="tierProgress.tier2_limit"
          />
          <CompareTrendChart
            v-if="compareTrend"
            :compareData="compareTrend"
            :prevYearTotals="compareTrend.prev_year_totals || []"
          />
        </div>

        <!-- 第四行：季节对比 + 用电分布 -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <SeasonalCompare :heating="seasonal.heating || {}" :nonHeating="seasonal.non_heating || {}" />
          <UsageDistribution :data="distribution" />
        </div>
      </template>

      <div v-else class="text-center py-8 text-gray-500">暂无数据</div>
    </div>
  </FeatureGate>
</template>
