<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps({
  data: { type: Array, default: () => [] },
})

const chartOption = computed(() => {
  if (!props.data.length) return {}
  const months = props.data.map(d => d.month + '月')
  const tier1 = props.data.map(d => d.flat_cost_by_tier?.[0] || 0)
  const tier2 = props.data.map(d => d.flat_cost_by_tier?.[1] || 0)
  const tier3 = props.data.map(d => d.flat_cost_by_tier?.[2] || 0)
  const tou = props.data.map(d => d.tou_cost)

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['一档费用', '二档费用', '三档费用', 'TOU费用'], top: 0 },
    grid: { left: 60, right: 20, bottom: 30, top: 50 },
    xAxis: { type: 'category', data: months },
    yAxis: { type: 'value', name: '元' },
    series: [
      { name: '一档费用', type: 'bar', stack: 'flat', data: tier1, itemStyle: { color: '#4ade80' } },
      { name: '二档费用', type: 'bar', stack: 'flat', data: tier2, itemStyle: { color: '#facc15' } },
      { name: '三档费用', type: 'bar', stack: 'flat', data: tier3, itemStyle: { color: '#f87171' } },
      { name: 'TOU费用', type: 'line', data: tou, itemStyle: { color: '#3b82f6' }, lineStyle: { width: 2 } },
    ],
  }
})
</script>

<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <h2 class="text-lg font-semibold mb-4">费用构成</h2>
    <v-chart v-if="data.length" :option="chartOption" class="chart-container" autoresize />
    <p v-else class="text-center py-4 text-gray-400">暂无数据</p>
  </div>
</template>

<style scoped>
.chart-container { height: 280px; }
</style>
