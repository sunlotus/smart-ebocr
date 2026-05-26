<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([PieChart, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps({
  peak: { type: Number, default: 0 },
  valley: { type: Number, default: 0 },
})

const chartOption = computed(() => {
  const total = props.peak + props.valley
  if (total === 0) return {}

  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} kWh ({d}%)' },
    legend: { bottom: 0, data: ['峰段', '谷段'] },
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['50%', '45%'],
      label: { show: true, formatter: '{d}%' },
      data: [
        { value: props.peak, name: '峰段', itemStyle: { color: '#f97316' } },
        { value: props.valley, name: '谷段', itemStyle: { color: '#3b82f6' } },
      ],
    }],
    graphic: total > 0 ? [{
      type: 'text',
      left: 'center',
      top: '38%',
      style: {
        text: `${total}\nkWh`,
        textAlign: 'center',
        fill: '#374151',
        fontSize: 14,
        fontWeight: 'bold',
      },
    }] : [],
  }
})
</script>

<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <h2 class="text-lg font-semibold mb-4">峰谷用电占比</h2>
    <v-chart v-if="peak + valley > 0" :option="chartOption" class="chart-container" autoresize />
    <p v-else class="text-center py-4 text-gray-400">暂无数据</p>
  </div>
</template>

<style scoped>
.chart-container { height: 250px; }
</style>
