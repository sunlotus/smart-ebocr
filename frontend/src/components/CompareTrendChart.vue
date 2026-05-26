<!-- Copyright 2026 smart-ebocr Contributors
SPDX-License-Identifier: Apache-2.0 -->

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps({
  compareData: { type: Object, default: null },
  prevYearTotals: { type: Array, default: () => [] },
})

const chartOption = computed(() => {
  if (!props.compareData) return {}
  const d = props.compareData
  const months = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['当年电量', '去年同期'], top: 0 },
    grid: { left: 60, right: 20, bottom: 30, top: 50 },
    xAxis: { type: 'category', data: months },
    yAxis: { type: 'value', name: 'kWh' },
    series: [
      {
        name: '当年电量', type: 'bar', data: d.monthly_totals,
        itemStyle: { color: '#3b82f6' },
      },
      {
        name: '去年同期', type: 'bar', data: props.prevYearTotals,
        itemStyle: { color: '#93c5fd' },
      },
    ],
  }
})
</script>

<template>
  <div v-if="compareData">
    <!-- 摘要卡片 -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
      <div class="bg-white rounded-lg border p-4 text-center">
        <div class="text-sm text-gray-500">当月用电</div>
        <div class="text-2xl font-bold text-gray-800">{{ compareData.current_total }} <span class="text-sm font-normal">kWh</span></div>
      </div>
      <div class="bg-white rounded-lg border p-4 text-center">
        <div class="text-sm text-gray-500">去年同期</div>
        <div class="text-2xl font-bold text-gray-400">{{ compareData.prev_year_total }} <span class="text-sm font-normal">kWh</span></div>
      </div>
      <div class="bg-white rounded-lg border p-4 text-center">
        <div class="text-sm text-gray-500">同比变化</div>
        <div class="text-2xl font-bold" :class="compareData.yoy_change > 0 ? 'text-red-600' : 'text-green-600'">
          {{ compareData.yoy_change != null ? (compareData.yoy_change > 0 ? '+' : '') + compareData.yoy_change + '%' : '—' }}
        </div>
      </div>
      <div class="bg-white rounded-lg border p-4 text-center">
        <div class="text-sm text-gray-500">环比变化</div>
        <div class="text-2xl font-bold" :class="compareData.mom_change > 0 ? 'text-red-600' : 'text-green-600'">
          {{ compareData.mom_change != null ? (compareData.mom_change > 0 ? '+' : '') + compareData.mom_change + '%' : '—' }}
        </div>
      </div>
    </div>

    <!-- 图表 -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h2 class="text-lg font-semibold mb-4">同比环比对比</h2>
      <v-chart :option="chartOption" class="chart-container" autoresize />
    </div>
  </div>
</template>

<style scoped>
.chart-container { height: 350px; }
</style>
