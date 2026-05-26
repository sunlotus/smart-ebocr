<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Object, required: true },
})

const pct = computed(() => {
  const d = props.data
  if (!d || !d.tier2_limit) return 0
  return Math.min(100, (d.cumulative / d.tier2_limit) * 100)
})

const projectedPct = computed(() => {
  const d = props.data
  if (!d || !d.tier2_limit || !d.projected_year_end) return 0
  return Math.min(100, (d.projected_year_end / d.tier2_limit) * 100)
})

const currentTier = computed(() => {
  const d = props.data
  if (!d) return 1
  if (d.cumulative > d.tier2_limit) return 3
  if (d.cumulative > d.tier1_limit) return 2
  return 1
})
</script>

<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <h2 class="text-lg font-semibold mb-4">阶梯进度</h2>
    <div v-if="data" class="space-y-4">
      <div class="relative h-10 rounded-lg overflow-hidden bg-gray-100">
        <!-- 三段色带 -->
        <div class="absolute inset-0 flex">
          <div class="bg-green-200" :style="{ width: (data.tier1_limit / data.tier2_limit * 100) + '%' }"></div>
          <div class="bg-yellow-200" :style="{ width: ((data.tier2_limit - data.tier1_limit) / data.tier2_limit * 100) + '%' }"></div>
          <div class="bg-red-200 flex-1"></div>
        </div>
        <!-- 当前累计标记 -->
        <div class="absolute top-0 bottom-0 w-0.5 bg-blue-600 z-10"
          :style="{ left: pct + '%' }">
          <div class="absolute -top-5 left-1/2 -translate-x-1/2 text-xs font-bold text-blue-600 whitespace-nowrap">
            {{ data.cumulative }} kWh
          </div>
        </div>
        <!-- 预计年末标记 -->
        <div v-if="projectedPct > pct" class="absolute top-0 bottom-0 w-0.5 bg-blue-300 border-dashed z-10"
          :style="{ left: projectedPct + '%' }">
          <div class="absolute -bottom-5 left-1/2 -translate-x-1/2 text-xs text-blue-400 whitespace-nowrap">
            预计 {{ data.projected_year_end }}
          </div>
        </div>
      </div>

      <!-- 阶梯标签 -->
      <div class="flex justify-between text-xs text-gray-500">
        <span>第一档 ({{ data.tier1_rate }}元)</span>
        <span class="text-yellow-700">第二档 ({{ data.tier2_rate }}元)</span>
        <span class="text-red-700">第三档 ({{ data.tier3_rate }}元)</span>
      </div>

      <div class="text-center">
        <span class="text-sm text-gray-600">当前处于</span>
        <span class="font-bold" :class="currentTier === 1 ? 'text-green-600' : currentTier === 2 ? 'text-yellow-600' : 'text-red-600'">
          第{{ currentTier }}档
        </span>
      </div>
    </div>
    <p v-else class="text-center py-4 text-gray-400">暂无数据</p>
  </div>
</template>
