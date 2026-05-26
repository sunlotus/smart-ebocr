<!-- Copyright 2026 smart-ebocr Contributors
SPDX-License-Identifier: Apache-2.0 -->

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([BarChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps({
  records: { type: Array, default: () => [] },
})

const chartOption = computed(() => {
  const dates = props.records.map(r => r.date.slice(8))
  const peakData = props.records.map(r => r.peak_kwh)
  const valleyData = props.records.map(r => r.valley_kwh)
  const sharpData = props.records.map(r => r.sharp_kwh)
  const flatData = props.records.map(r => r.flat_kwh)

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['峰段', '谷段', '尖段', '平段'], top: 0 },
    grid: { left: 50, right: 20, bottom: 30, top: 50 },
    xAxis: { type: 'category', data: dates, name: '日' },
    yAxis: { type: 'value', name: 'kWh' },
    series: [
      { name: '峰段', type: 'bar', stack: 'usage', data: peakData, itemStyle: { color: '#f97316' } },
      { name: '谷段', type: 'bar', stack: 'usage', data: valleyData, itemStyle: { color: '#3b82f6' } },
      { name: '尖段', type: 'bar', stack: 'usage', data: sharpData, itemStyle: { color: '#ef4444' } },
      { name: '平段', type: 'bar', stack: 'usage', data: flatData, itemStyle: { color: '#22c55e' } },
    ],
  }
})
</script>

<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <h2 class="text-lg font-semibold mb-4">每日分时用电</h2>
    <v-chart v-if="records.length" :option="chartOption" class="chart-container" autoresize />
    <p v-else class="text-center py-4 text-gray-400">暂无图表数据</p>
  </div>
</template>

<style scoped>
.chart-container { height: 300px; }
</style>