<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([BarChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps({
  heating: { type: Object, default: () => ({}) },
  nonHeating: { type: Object, default: () => ({}) },
})

const chartOption = computed(() => {
  const h = props.heating
  const nh = props.nonHeating
  if (!h.total_kwh && !nh.total_kwh) return {}

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['采暖季', '非采暖季'], top: 0 },
    grid: { left: 60, right: 20, bottom: 30, top: 50 },
    xAxis: { type: 'category', data: ['总电量', '峰电量', '谷电量'] },
    yAxis: { type: 'value', name: 'kWh' },
    series: [
      {
        name: '采暖季', type: 'bar', data: [h.total_kwh, h.peak_kwh, h.valley_kwh],
        itemStyle: { color: '#3b82f6' }, barGap: '10%',
      },
      {
        name: '非采暖季', type: 'bar', data: [nh.total_kwh, nh.peak_kwh, nh.valley_kwh],
        itemStyle: { color: '#f97316' },
      },
    ],
  }
})
</script>

<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <h2 class="text-lg font-semibold mb-4">季节对比</h2>
    <v-chart v-if="chartOption.series" :option="chartOption" class="chart-container" autoresize />
    <p v-else class="text-center py-4 text-gray-400">暂无数据</p>
  </div>
</template>

<style scoped>
.chart-container { height: 280px; }
</style>
