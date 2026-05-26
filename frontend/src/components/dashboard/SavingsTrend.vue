<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, MarkLineComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, MarkLineComponent, CanvasRenderer])

const props = defineProps({
  data: { type: Array, default: () => [] },
})

const chartOption = computed(() => {
  if (!props.data.length) return {}
  const months = props.data.map(d => d.month + '月')
  const savings = props.data.map(d => d.savings)

  let cumulative = 0
  const cumulativeData = savings.map(s => { cumulative += s; return Math.round(cumulative * 100) / 100 })

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['月节省', '累计节省'], top: 0 },
    grid: { left: 60, right: 20, bottom: 30, top: 50 },
    xAxis: { type: 'category', data: months },
    yAxis: { type: 'value', name: '元' },
    series: [
      {
        name: '月节省', type: 'line', data: savings,
        itemStyle: { color: '#22c55e' },
        markLine: { data: [{ yAxis: 0, lineStyle: { color: '#9ca3af', type: 'dashed' } }] },
      },
      {
        name: '累计节省', type: 'line', data: cumulativeData,
        itemStyle: { color: '#3b82f6' },
        areaStyle: { color: 'rgba(59,130,246,0.1)' },
      },
    ],
  }
})
</script>

<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <h2 class="text-lg font-semibold mb-4">节省趋势</h2>
    <v-chart v-if="data.length" :option="chartOption" class="chart-container" autoresize />
    <p v-else class="text-center py-4 text-gray-400">暂无数据</p>
  </div>
</template>

<style scoped>
.chart-container { height: 280px; }
</style>
