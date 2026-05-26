<!-- Copyright 2026 smart-ebocr Contributors
SPDX-License-Identifier: Apache-2.0 -->

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, MarkLineComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([BarChart, GridComponent, TooltipComponent, LegendComponent, MarkLineComponent, CanvasRenderer])

const props = defineProps({
  result: { type: Object, required: true },
})

const savingsText = computed(() => {
  const s = props.result.savings
  if (s > 0) return `峰谷计费更省，每月省 ¥${s.toFixed(2)}`
  if (s < 0) return `不分峰谷更省，每月省 ¥${Math.abs(s).toFixed(2)}`
  return '两种方式费用相同'
})

const savingsColor = computed(() => {
  const s = props.result.savings
  if (s > 0) return 'text-green-600'
  if (s < 0) return 'text-blue-600'
  return 'text-gray-600'
})

const summaryHtml = computed(() => {
  const r = props.result
  if (!r?.daily_breakdown?.length) return null
  const { year, month, flat_cost, tou_cost, savings } = r
  const abs = Math.abs(savings).toFixed(2)
  const f = flat_cost.toFixed(2)
  const t = tou_cost.toFixed(2)

  if (savings === 0) {
    return `${year} 年 ${month} 月通过电费分析工具完成峰谷计费与不分峰谷计费的电费对比分析，两种计费方式费用相同，当前用电模式下无差异。`
  }
  if (savings > 0) {
    return `${year} 年 ${month} 月通过电费分析工具完成峰谷计费与不分峰谷计费的电费对比分析，核心结论为 <strong>峰谷计费模式实现显著降本</strong>，当月累计节省电费 <strong>${abs} 元</strong>。具体分析：不分峰谷计费的预估总电费为 <strong>¥${f}</strong>，峰谷计费的预估总电费为 <strong>¥${t}</strong>，两者差额达 <strong>¥${abs}</strong>，峰谷计费模式下每月可稳定节省该金额。`
  }
  // savings < 0：不分峰谷更省
  return `${year} 年 ${month} 月通过电费分析工具完成峰谷计费与不分峰谷计费的电费对比分析，核心结论为 <strong>不分峰谷计费模式更为经济</strong>，当月累计节省电费 <strong>${abs} 元</strong>。具体分析：峰谷计费的预估总电费为 <strong>¥${t}</strong>，不分峰谷计费的预估总电费为 <strong>¥${f}</strong>，两者差额达 <strong>¥${abs}</strong>，不分峰谷计费模式下每月可稳定节省该金额。`
})

const chartOption = computed(() => {
  const dates = props.result.daily_breakdown.map(r => r.date.slice(8))
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['不分峰谷', '峰谷计费'], top: 0 },
    grid: { left: 50, right: 20, bottom: 30, top: 40 },
    xAxis: { type: 'category', data: dates, name: '日' },
    yAxis: { type: 'value', name: '元' },
    series: [
      { name: '不分峰谷', type: 'bar', data: props.result.daily_breakdown.map(r => r.daily_flat), itemStyle: { color: '#6b7280' } },
      { name: '峰谷计费', type: 'bar', data: props.result.daily_breakdown.map(r => r.daily_tou), itemStyle: { color: '#3b82f6' } },
    ],
  }
})
</script>

<template>
  <div class="space-y-6">
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 text-center">
        <p class="text-sm text-gray-500 mb-1">不分峰谷电费</p>
        <p class="text-3xl font-bold text-gray-700">¥{{ result.flat_cost?.toFixed(2) }}</p>
      </div>
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 text-center">
        <p class="text-sm text-gray-500 mb-1">峰谷计费电费</p>
        <p class="text-3xl font-bold text-blue-600">¥{{ result.tou_cost?.toFixed(2) }}</p>
      </div>
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 text-center">
        <p class="text-sm text-gray-500 mb-1">差额</p>
        <p class="text-3xl font-bold" :class="savingsColor">¥{{ Math.abs(result.savings)?.toFixed(2) }}</p>
        <p class="text-sm mt-2" :class="savingsColor">{{ savingsText }}</p>
      </div>
    </div>

    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h2 class="text-lg font-semibold mb-4">每日电费对比</h2>
      <v-chart v-if="result.daily_breakdown?.length" :option="chartOption" class="chart-container" autoresize />
      <p v-else class="text-center py-4 text-gray-400">暂无数据</p>
    </div>

    <div v-if="summaryHtml" class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h2 class="text-lg font-semibold mb-4">对比总结</h2>
      <p class="text-sm text-gray-700 leading-relaxed" v-html="summaryHtml" />
    </div>
  </div>
</template>

<style scoped>
.chart-container { height: 300px; }
</style>