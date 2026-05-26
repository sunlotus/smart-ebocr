<!-- Copyright 2026 smart-ebocr Contributors
SPDX-License-Identifier: Apache-2.0 -->

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, MarkAreaComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, MarkAreaComponent, CanvasRenderer])

const props = defineProps({
  forecastData: { type: Object, default: null },
})

const chartOption = computed(() => {
  if (!props.forecastData) return {}
  const d = props.forecastData
  const months = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']

  const actualData = d.forecast.map(f => f.type === 'actual' ? f.value : null)
  const forecastData = d.forecast.map(f => f.type === 'forecast' ? f.value : null)

  // 找到预测起始的索引（第一个 forecast 的前一个位置也需要连线）
  const firstForecastIdx = d.forecast.findIndex(f => f.type === 'forecast')
  if (firstForecastIdx > 0) {
    forecastData[firstForecastIdx - 1] = actualData[firstForecastIdx - 1]
  }

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['实际用电', '预测用电'], top: 0 },
    grid: { left: 60, right: 20, bottom: 30, top: 50 },
    xAxis: { type: 'category', data: months },
    yAxis: { type: 'value', name: 'kWh' },
    series: [
      {
        name: '实际用电', type: 'line', data: actualData,
        itemStyle: { color: '#3b82f6' },
        lineStyle: { width: 2 },
        markArea: firstForecastIdx >= 0 ? {
          silent: true,
          data: [[
            { xAxis: months[firstForecastIdx > 0 ? firstForecastIdx - 1 : 0], itemStyle: { color: 'rgba(59,130,246,0.06)' } },
            { xAxis: months[11] },
          ]],
        } : undefined,
      },
      {
        name: '预测用电', type: 'line', data: forecastData,
        itemStyle: { color: '#93c5fd' },
        lineStyle: { width: 2, type: 'dashed' },
      },
    ],
  }
})
</script>

<template>
  <div v-if="forecastData">
    <!-- 摘要卡片 -->
    <div class="grid grid-cols-2 gap-4 mb-4">
      <div class="bg-white rounded-lg border p-4 text-center">
        <div class="text-sm text-gray-500">预测年度总电量</div>
        <div class="text-2xl font-bold text-gray-800">{{ forecastData.forecasted_total }} <span class="text-sm font-normal">kWh</span></div>
      </div>
      <div class="bg-white rounded-lg border p-4 text-center">
        <div class="text-sm text-gray-500">月均用电</div>
        <div class="text-2xl font-bold text-gray-600">{{ forecastData.avg_monthly }} <span class="text-sm font-normal">kWh</span></div>
      </div>
    </div>

    <!-- 图表 -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h2 class="text-lg font-semibold mb-4">用电趋势预测</h2>
      <v-chart :option="chartOption" class="chart-container" autoresize />
    </div>
  </div>
</template>

<style scoped>
.chart-container { height: 350px; }
</style>
