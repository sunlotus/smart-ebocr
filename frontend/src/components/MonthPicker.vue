<!-- Copyright 2026 smart-ebocr Contributors
SPDX-License-Identifier: Apache-2.0 -->

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: { type: Object, required: true }, // { year, month }
})

const emit = defineEmits(['update:modelValue'])

const open = ref(false)
const panelYear = ref(props.modelValue.year)

const now = new Date()
const currentYear = now.getFullYear()
const currentMonth = now.getMonth() + 1

function update(year, month) {
  emit('update:modelValue', { year, month })
}

function prevMonth() {
  const { year, month } = props.modelValue
  if (month === 1) update(year - 1, 12)
  else update(year, month - 1)
}

function nextMonth() {
  const { year, month } = props.modelValue
  if (month === 12) update(year + 1, 1)
  else update(year, month + 1)
}

function toggle() {
  panelYear.value = props.modelValue.year
  open.value = !open.value
}

function selectMonth(m) {
  update(panelYear.value, m)
  open.value = false
}

function prevYear() {
  panelYear.value--
}

function nextYear() {
  panelYear.value++
}

function onClickOutside() {
  if (open.value) open.value = false
}

onMounted(() => document.addEventListener('click', onClickOutside))
onUnmounted(() => document.removeEventListener('click', onClickOutside))
</script>

<template>
  <div class="relative inline-flex items-center gap-3">
    <button @click="prevMonth" class="px-3 py-1 bg-gray-200 rounded hover:bg-gray-300">&lt;</button>
    <span class="text-lg font-semibold cursor-pointer hover:text-blue-600 select-none"
      @click.stop="toggle">
      {{ modelValue.year }}年{{ String(modelValue.month).padStart(2, '0') }}月
    </span>
    <button @click="nextMonth" class="px-3 py-1 bg-gray-200 rounded hover:bg-gray-300">&gt;</button>

    <Transition
      enter-active-class="transition ease-out duration-100"
      enter-from-class="opacity-0 scale-95"
      enter-to-class="opacity-100 scale-100"
      leave-active-class="transition ease-in duration-75"
      leave-from-class="opacity-100 scale-100"
      leave-to-class="opacity-0 scale-95">
      <div v-if="open"
        @click.stop
        class="absolute top-full right-0 mt-2 bg-white rounded-lg shadow-lg border border-gray-200 p-4 z-50 w-64">
        <!-- Year navigation -->
        <div class="flex items-center justify-between mb-3">
          <button @click="prevYear" class="px-2 py-1 hover:bg-gray-100 rounded">&lt;</button>
          <span class="font-semibold">{{ panelYear }}年</span>
          <button @click="nextYear" class="px-2 py-1 hover:bg-gray-100 rounded">&gt;</button>
        </div>
        <!-- Month grid -->
        <div class="grid grid-cols-4 gap-1">
          <button v-for="m in 12" :key="m" @click="selectMonth(m)"
            class="px-2 py-2 text-sm rounded transition-colors"
            :class="{
              'bg-blue-600 text-white font-medium':
                panelYear === modelValue.year && m === modelValue.month,
              'text-blue-600 font-medium':
                panelYear === currentYear && m === currentMonth
                  && !(panelYear === modelValue.year && m === modelValue.month),
              'hover:bg-gray-100':
                !(panelYear === modelValue.year && m === modelValue.month),
            }">
            {{ String(m).padStart(2, '0') }}月
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>