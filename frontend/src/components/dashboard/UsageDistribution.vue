<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, MarkLineComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([BarChart, GridComponent, TooltipComponent, LegendComponent, MarkLineComponent, CanvasRenderer])

const props = defineProps({
  data: { type: Object, default: () => ({}) },
})

const chartOption = computed(() => {
  const d = props.data
  if (!d || !d.buckets || !d.buckets.length) return {}

  const ranges = d.buckets.map(b => b.range)
  const heating = d.buckets.map(b => b.count_heating)
  const nonHeating = d.buckets.map(b => b.count_non_heating)

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['采暖季', '非采暖季'], top: 0 },
    grid: { left: 60, right: 20, bottom: 30, top: 50 },
    xAxis: { type: 'category', data: ranges, name: 'kWh' },
    yAxis: { type: 'value', name: '天数' },
    series: [
      {
        name: '采暖季', type: 'bar', data: heating, stack: 'days',
        itemStyle: { color: '#3b82f6' },
      },
      {
        name: '非采暖季', type: 'bar', data: nonHeating, stack: 'days',
        itemStyle: { color: '#f97316' },
        markLine: d.median > 0 ? {
          silent: true,
          data: [
            { xAxis: d.average ? ranges.findIndex(r => {
              const low = parseInt(r)
              return d.average >= low && d.average < low + 5
            }) : -1, name: '均值', lineStyle: { color: '#22c55e' } },
          ],
        } : undefined,
      },
    ],
  }
})
</script>

<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <h2 class="text-lg font-semibold mb-4">用电分布</h2>
    <div v-if="data && data.median" class="flex gap-4 mb-2 text-sm text-gray-500">
      <span>中位数: {{ data.median }} kWh</span>
      <span>平均: {{ data.average }} kWh</span>
    </div>
    <v-chart v-if="data && data.buckets && data.buckets.length" :option="chartOption" class="chart-container" autoresize />
    <p v-else class="text-center py-4 text-gray-400">暂无数据</p>
  </div>
</template>

<style scoped>
.chart-container { height: 280px; }
</style>
