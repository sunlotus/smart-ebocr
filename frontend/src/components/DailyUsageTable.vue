<!-- Copyright 2026 smart-ebocr Contributors
SPDX-License-Identifier: Apache-2.0 -->

<script setup>
import { ref, computed } from 'vue'
import { useUsageStore } from '../stores/usage'
import { useUserStore } from '../stores/user'

const props = defineProps({
  records: { type: Array, default: () => [] },
  year: { type: Number, required: true },
  month: { type: Number, required: true },
})

const emit = defineEmits(['refresh'])
const store = useUsageStore()
const userStore = useUserStore()
const showAddForm = ref(false)
const newRecord = ref({ date: '', total_kwh: 0, peak_kwh: 0, valley_kwh: 0, sharp_kwh: 0, flat_kwh: 0 })
const selectedDates = ref(new Set())
const filterAbnormal = ref(false)
const editingDate = ref(null)
const editForm = ref({})

function hasWarnings(r) {
  return r.warnings && r.warnings.length > 0
}

const displayRecords = computed(() => {
  if (!filterAbnormal.value) return props.records
  return props.records.filter(r => hasWarnings(r))
})

const abnormalCount = computed(() => props.records.filter(r => hasWarnings(r)).length)

const isAllSelected = computed(() =>
  displayRecords.value.length > 0 && selectedDates.value.size === displayRecords.value.length
)

function openAddForm() {
  const m = String(props.month).padStart(2, '0')
  newRecord.value = {
    date: `${props.year}-${m}-01`,
    total_kwh: 0, peak_kwh: 0, valley_kwh: 0, sharp_kwh: 0, flat_kwh: 0,
  }
  showAddForm.value = true
}

async function submitRecord() {
  await store.addRecord(newRecord.value, userStore.selectedMemberId)
  showAddForm.value = false
  emit('refresh')
}

async function removeRecord(date) {
  if (!confirm(`确定删除 ${date} 的记录？`)) return
  await store.deleteRecord(date, userStore.selectedMemberId)
  emit('refresh')
}

function toggleRecord(date) {
  const s = new Set(selectedDates.value)
  if (s.has(date)) s.delete(date)
  else s.add(date)
  selectedDates.value = s
}

function toggleAll() {
  if (isAllSelected.value) {
    selectedDates.value = new Set()
  } else {
    selectedDates.value = new Set(displayRecords.value.map(r => r.date))
  }
}

function clearSelection() {
  selectedDates.value = new Set()
}

async function batchRemove() {
  const count = selectedDates.value.size
  if (!confirm(`确定删除选中的 ${count} 条记录？`)) return
  await store.batchDelete([...selectedDates.value], userStore.selectedMemberId)
  selectedDates.value = new Set()
  emit('refresh')
}

function startEdit(r) {
  editingDate.value = r.date
  editForm.value = {
    date: r.date,
    total_kwh: r.total_kwh,
    peak_kwh: r.peak_kwh,
    valley_kwh: r.valley_kwh,
    sharp_kwh: r.sharp_kwh,
    flat_kwh: r.flat_kwh,
  }
}

function cancelEdit() {
  editingDate.value = null
  editForm.value = {}
}

function autoCorrect() {
  const f = editForm.value
  const sum = +(f.peak_kwh || 0) + +(f.valley_kwh || 0)
  const total = +(f.total_kwh || 0)
  if (sum === total) return

  if (sum < total) {
    f.peak_kwh = +(total - (f.valley_kwh || 0)).toFixed(2)
  } else {
    f.valley_kwh = +(total - (f.peak_kwh || 0)).toFixed(2)
  }
}

async function saveEdit() {
  autoCorrect()
  await store.addRecord(editForm.value, userStore.selectedMemberId)
  editingDate.value = null
  editForm.value = {}
  emit('refresh')
}
</script>

<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-semibold">每日用电明细</h2>
      <div class="flex items-center gap-2">
        <button v-if="abnormalCount > 0" @click="filterAbnormal = !filterAbnormal"
          class="px-3 py-1 text-sm rounded"
          :class="filterAbnormal ? 'bg-yellow-500 text-white' : 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200'">
          {{ filterAbnormal ? '查看全部' : `异常 (${abnormalCount})` }}
        </button>
        <template v-if="selectedDates.size > 0">
          <span class="text-sm text-gray-500">已选 {{ selectedDates.size }} 条</span>
          <button @click="clearSelection"
            class="px-3 py-1 bg-gray-200 text-gray-600 rounded text-sm hover:bg-gray-300">
            取消选择
          </button>
          <button @click="batchRemove"
            class="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700">
            批量删除 ({{ selectedDates.size }})
          </button>
        </template>
        <button @click="openAddForm"
          class="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
          + 手动添加
        </button>
      </div>
    </div>

    <div v-if="showAddForm" class="mb-4 p-4 bg-gray-50 rounded-lg">
      <div class="grid grid-cols-6 gap-3 items-end">
        <div>
          <label class="block text-xs text-gray-500 mb-1">日期</label>
          <input v-model="newRecord.date" type="date" class="border rounded px-2 py-1 w-full text-sm" />
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">总电量 (kWh)</label>
          <input v-model.number="newRecord.total_kwh" type="number" step="0.01" class="border rounded px-2 py-1 w-full text-sm" />
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">峰段 (kWh)</label>
          <input v-model.number="newRecord.peak_kwh" type="number" step="0.01" class="border rounded px-2 py-1 w-full text-sm" />
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">谷段 (kWh)</label>
          <input v-model.number="newRecord.valley_kwh" type="number" step="0.01" class="border rounded px-2 py-1 w-full text-sm" />
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">尖段 (kWh)</label>
          <input v-model.number="newRecord.sharp_kwh" type="number" step="0.01" class="border rounded px-2 py-1 w-full text-sm" />
        </div>
        <div class="flex gap-2">
          <button @click="submitRecord" class="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700">保存</button>
          <button @click="showAddForm = false" class="px-3 py-1 bg-gray-300 text-gray-700 rounded text-sm">取消</button>
        </div>
      </div>
    </div>

    <table v-if="displayRecords.length" class="w-full text-sm">
      <thead>
        <tr class="border-b text-gray-500">
          <th class="py-2 px-2 w-10">
            <input type="checkbox" :checked="isAllSelected" @change="toggleAll" class="rounded" />
          </th>
          <th class="text-left py-2 px-2">日期</th>
          <th class="text-right py-2 px-2">总电量</th>
          <th class="text-right py-2 px-2">峰段</th>
          <th class="text-right py-2 px-2">谷段</th>
          <th class="text-right py-2 px-2">尖段</th>
          <th class="text-right py-2 px-2">平段</th>
          <th class="text-right py-2 px-2">年度累计</th>
          <th class="text-center py-2 px-2">来源</th>
          <th class="text-center py-2 px-2">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in displayRecords" :key="r.date" class="border-b hover:bg-gray-50"
          :class="{
            'bg-red-50': selectedDates.has(r.date),
            'bg-yellow-50': hasWarnings(r) && !selectedDates.has(r.date),
            'bg-blue-50': editingDate === r.date,
          }">
          <td class="py-2 px-2">
            <input type="checkbox" :checked="selectedDates.has(r.date)"
              @change="toggleRecord(r.date)" class="rounded" />
          </td>
          <td class="py-2 px-2">
            <span class="flex items-center gap-1">
              <span v-if="hasWarnings(r)" class="text-yellow-500" title="异常数据">&#9888;</span>
              {{ r.date }}
            </span>
          </td>
          <!-- 编辑模式 -->
          <template v-if="editingDate === r.date">
            <td class="py-1 px-1">
              <input v-model.number="editForm.total_kwh" type="number" step="0.01"
                class="border rounded px-2 py-1 w-20 text-right text-sm" />
            </td>
            <td class="py-1 px-1">
              <input v-model.number="editForm.peak_kwh" type="number" step="0.01"
                class="border rounded px-2 py-1 w-20 text-right text-sm text-orange-600" />
            </td>
            <td class="py-1 px-1">
              <input v-model.number="editForm.valley_kwh" type="number" step="0.01"
                class="border rounded px-2 py-1 w-20 text-right text-sm text-blue-600" />
            </td>
            <td class="py-1 px-1">
              <input v-model.number="editForm.sharp_kwh" type="number" step="0.01"
                class="border rounded px-2 py-1 w-20 text-right text-sm text-red-600" />
            </td>
            <td class="py-1 px-1">
              <input v-model.number="editForm.flat_kwh" type="number" step="0.01"
                class="border rounded px-2 py-1 w-20 text-right text-sm text-green-600" />
            </td>
            <td class="py-2 px-2 text-right text-gray-400">-</td>
            <td class="text-center py-2 px-2">
              <span class="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600">手动</span>
            </td>
            <td class="text-center py-1 px-1 whitespace-nowrap">
              <button @click="saveEdit" class="text-green-600 hover:text-green-800 text-xs font-medium">保存</button>
              <button @click="cancelEdit" class="text-gray-500 hover:text-gray-700 text-xs ml-2">取消</button>
            </td>
          </template>
          <!-- 普通显示模式 -->
          <template v-else>
            <td class="text-right py-2 px-2 font-medium">{{ r.total_kwh }}</td>
            <td class="text-right py-2 px-2 text-orange-600">{{ r.peak_kwh }}</td>
            <td class="text-right py-2 px-2 text-blue-600">{{ r.valley_kwh }}</td>
            <td class="text-right py-2 px-2 text-red-600">{{ r.sharp_kwh }}</td>
            <td class="text-right py-2 px-2 text-green-600">{{ r.flat_kwh }}</td>
            <td class="text-right py-2 px-2 text-indigo-600 font-medium">{{ r.yearly_cumulative_kwh }}</td>
            <td class="text-center py-2 px-2">
              <span class="text-xs px-2 py-0.5 rounded"
                :class="r.source === 'ocr' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'">
                {{ r.source === 'ocr' ? 'OCR' : '手动' }}
              </span>
            </td>
            <td class="text-center py-2 px-2 whitespace-nowrap">
              <button @click="startEdit(r)" class="text-blue-500 hover:text-blue-700 text-xs">编辑</button>
              <button @click="removeRecord(r.date)" class="text-red-500 hover:text-red-700 text-xs ml-2">删除</button>
            </td>
          </template>
        </tr>
      </tbody>
    </table>
    <p v-else class="text-center py-4 text-gray-400">暂无数据</p>
  </div>
</template>
