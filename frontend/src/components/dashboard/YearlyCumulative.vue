<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, MarkLineComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, MarkLineComponent, CanvasRenderer])

const props = defineProps({
  monthly: { type: Array, default: () => [] },
  forecast: { type: Array, default: () => [] },
  tier1Limit: { type: Number, default: 2520 },
  tier2Limit: { type: Number, default: 4800 },
})

const chartOption = computed(() => {
  if (!props.monthly.length) return {}
  const months = props.monthly.map(d => d.month + '月')
  const cumulative = props.monthly.map(d => d.cumulative_kwh)

  const forecastValues = props.forecast.map(f => {
    const m = f.month
    const existing = props.monthly.find(d => d.month === m)
    return existing ? null : cumulative[cumulative.length - 1] + f.value
  })
  // 连接线：最后一个实际值
  const lastActualIdx = cumulative.findLastIndex(v => v > 0)
  if (lastActualIdx >= 0 && lastActualIdx < forecastValues.length) {
    forecastValues[lastActualIdx] = cumulative[lastActualIdx]
  }

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['累计用电', '预测累计'], top: 0 },
    grid: { left: 60, right: 20, bottom: 30, top: 50 },
    xAxis: { type: 'category', data: months },
    yAxis: { type: 'value', name: 'kWh' },
    series: [
      {
        name: '累计用电', type: 'line', data: cumulative,
        areaStyle: { color: 'rgba(59,130,246,0.15)' },
        itemStyle: { color: '#3b82f6' },
        markLine: {
          silent: true,
          data: [
            { yAxis: props.tier1Limit, name: '一档上限', lineStyle: { color: '#22c55e', type: 'dashed' } },
            { yAxis: props.tier2Limit, name: '二档上限', lineStyle: { color: '#f59e0b', type: 'dashed' } },
          ],
        },
      },
      {
        name: '预测累计', type: 'line', data: forecastValues,
        itemStyle: { color: '#93c5fd' },
        lineStyle: { type: 'dashed' },
      },
    ],
  }
})
</script>

<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <h2 class="text-lg font-semibold mb-4">年度累计用电</h2>
    <v-chart v-if="monthly.length" :option="chartOption" class="chart-container" autoresize />
    <p v-else class="text-center py-4 text-gray-400">暂无数据</p>
  </div>
</template>

<style scoped>
.chart-container { height: 280px; }
</style>
