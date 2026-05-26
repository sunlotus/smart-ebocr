<!-- Copyright 2026 smart-ebocr Contributors
SPDX-License-Identifier: Apache-2.0 -->

<script setup>
import { ref, onMounted, watch } from 'vue'
import { advancedPolicyApi } from '../api'
import { useUserStore } from '../stores/user'
import FeatureGate from './FeatureGate.vue'

const userStore = useUserStore()
const policies = ref([])
const loading = ref(false)
const showForm = ref(false)
const editingId = ref(null)
const saving = ref(false)

const defaultForm = () => ({
  name: '',
  region: 'custom',
  tier1_rate: 0.5469,
  tier1_limit: 2520,
  tier2_rate: 0.5969,
  tier2_limit: 4800,
  tier3_rate: 0.8469,
  peak_rate: 0.5769,
  valley_rate: 0.3769,
  heating_valley_rate: 0.3469,
  sharp_rate: 0.6769,
  flat_rate: 0.0,
  peak_hours: [{ start: '08:00', end: '22:00' }],
  valley_hours: [{ start: '22:00', end: '06:00' }],
  is_active: false,
})

const form = ref(defaultForm())

function parseHours(jsonStr) {
  try { return JSON.parse(jsonStr) } catch { return [{ start: '', end: '' }] }
}

function serializeHours(arr) {
  return JSON.stringify(arr.filter(h => h.start && h.end))
}

async function loadPolicies() {
  loading.value = true
  try {
    const res = await advancedPolicyApi.list(userStore.selectedMemberId)
    policies.value = res.data.policies || []
  } catch (err) {
    console.error('加载策略失败:', err)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.value = defaultForm()
  showForm.value = true
}

function openEdit(policy) {
  editingId.value = policy.id
  form.value = {
    name: policy.name,
    region: policy.region || 'custom',
    tier1_rate: policy.tier1_rate,
    tier1_limit: policy.tier1_limit,
    tier2_rate: policy.tier2_rate,
    tier2_limit: policy.tier2_limit,
    tier3_rate: policy.tier3_rate,
    peak_rate: policy.peak_rate,
    valley_rate: policy.valley_rate,
    heating_valley_rate: policy.heating_valley_rate,
    sharp_rate: policy.sharp_rate,
    flat_rate: policy.flat_rate,
    peak_hours: parseHours(policy.peak_hours),
    valley_hours: parseHours(policy.valley_hours),
    is_active: policy.is_active,
  }
  showForm.value = true
}

function cancelForm() {
  showForm.value = false
  editingId.value = null
}

async function saveForm() {
  saving.value = true
  try {
    const payload = {
      ...form.value,
      peak_hours: serializeHours(form.value.peak_hours),
      valley_hours: serializeHours(form.value.valley_hours),
      family_member_id: userStore.selectedMemberId,
    }
    if (editingId.value) {
      await advancedPolicyApi.update(editingId.value, payload)
    } else {
      await advancedPolicyApi.create(payload)
    }
    showForm.value = false
    await loadPolicies()
  } catch (err) {
    alert('保存失败: ' + (err.response?.data?.error || err.message))
  } finally {
    saving.value = false
  }
}

async function deletePolicy(id) {
  if (!confirm('确定删除该策略？')) return
  try {
    await advancedPolicyApi.delete(id)
    await loadPolicies()
  } catch (err) {
    alert('删除失败: ' + (err.response?.data?.error || err.message))
  }
}

async function activatePolicy(id) {
  try {
    await advancedPolicyApi.update(id, { is_active: true })
    await loadPolicies()
  } catch (err) {
    alert('激活失败: ' + (err.response?.data?.error || err.message))
  }
}

function addTimeSlot(type) {
  form.value[type].push({ start: '', end: '' })
}

function removeTimeSlot(type, index) {
  form.value[type].splice(index, 1)
}

onMounted(loadPolicies)
watch(() => userStore.selectedMemberId, loadPolicies)
</script>

<template>
  <FeatureGate requiredPlan="premium">
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold">高级电价策略</h2>
        <button @click="openCreate"
          class="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700">
          + 新建策略
        </button>
      </div>

      <div v-if="loading" class="text-center py-4 text-gray-500">加载中...</div>

      <!-- 策略列表 -->
      <div v-else-if="policies.length" class="space-y-3 mb-4">
        <div v-for="p in policies" :key="p.id"
          class="flex items-center justify-between p-3 border rounded-lg"
          :class="p.is_active ? 'border-blue-300 bg-blue-50' : ''">
          <div>
            <div class="flex items-center gap-2">
              <span class="font-medium">{{ p.name }}</span>
              <span v-if="p.is_active"
                class="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">激活中</span>
            </div>
            <span class="text-sm text-gray-500">{{ p.region }}</span>
          </div>
          <div class="flex items-center gap-2">
            <button v-if="!p.is_active" @click="activatePolicy(p.id)"
              class="text-sm text-blue-600 hover:text-blue-800">激活</button>
            <button @click="openEdit(p)"
              class="text-sm text-gray-600 hover:text-gray-800">编辑</button>
            <button v-if="!p.is_active" @click="deletePolicy(p.id)"
              class="text-sm text-red-500 hover:text-red-700">删除</button>
          </div>
        </div>
      </div>

      <p v-else-if="!loading" class="text-center py-4 text-gray-400">暂无自定义策略</p>

      <!-- 创建/编辑表单 -->
      <div v-if="showForm" class="border-t pt-4 space-y-4">
        <h3 class="font-medium">{{ editingId ? '编辑策略' : '新建策略' }}</h3>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm text-gray-600 mb-1">策略名称</label>
            <input v-model="form.name" type="text" class="border rounded px-3 py-2 w-full" />
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">地区</label>
            <input v-model="form.region" type="text" class="border rounded px-3 py-2 w-full" />
          </div>
        </div>

        <!-- 阶梯费率 -->
        <div>
          <h4 class="text-sm font-semibold text-gray-600 mb-2">阶梯电价</h4>
          <div class="grid grid-cols-3 gap-4">
            <div>
              <label class="block text-xs text-gray-500 mb-1">第一档费率</label>
              <input v-model.number="form.tier1_rate" type="number" step="0.0001"
                class="border rounded px-3 py-2 w-full" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">第二档费率</label>
              <input v-model.number="form.tier2_rate" type="number" step="0.0001"
                class="border rounded px-3 py-2 w-full" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">第三档费率</label>
              <input v-model.number="form.tier3_rate" type="number" step="0.0001"
                class="border rounded px-3 py-2 w-full" />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4 mt-2">
            <div>
              <label class="block text-xs text-gray-500 mb-1">第一档上限 (kWh/年)</label>
              <input v-model.number="form.tier1_limit" type="number"
                class="border rounded px-3 py-2 w-full" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">第二档上限 (kWh/年)</label>
              <input v-model.number="form.tier2_limit" type="number"
                class="border rounded px-3 py-2 w-full" />
            </div>
          </div>
        </div>

        <!-- TOU 费率 -->
        <div>
          <h4 class="text-sm font-semibold text-gray-600 mb-2">分时电价</h4>
          <div class="grid grid-cols-3 gap-4">
            <div>
              <label class="block text-xs text-gray-500 mb-1">峰段费率</label>
              <input v-model.number="form.peak_rate" type="number" step="0.0001"
                class="border rounded px-3 py-2 w-full" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">谷段费率</label>
              <input v-model.number="form.valley_rate" type="number" step="0.0001"
                class="border rounded px-3 py-2 w-full" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">采暖季谷段费率</label>
              <input v-model.number="form.heating_valley_rate" type="number" step="0.0001"
                class="border rounded px-3 py-2 w-full" />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4 mt-2">
            <div>
              <label class="block text-xs text-gray-500 mb-1">尖段费率</label>
              <input v-model.number="form.sharp_rate" type="number" step="0.0001"
                class="border rounded px-3 py-2 w-full" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">平段费率</label>
              <input v-model.number="form.flat_rate" type="number" step="0.0001"
                class="border rounded px-3 py-2 w-full" />
            </div>
          </div>
        </div>

        <!-- 时间段 -->
        <div>
          <h4 class="text-sm font-semibold text-gray-600 mb-2">峰段时段</h4>
          <div v-for="(h, i) in form.peak_hours" :key="'p' + i" class="flex items-center gap-2 mb-2">
            <input v-model="h.start" type="time" class="border rounded px-3 py-2" />
            <span class="text-gray-400">~</span>
            <input v-model="h.end" type="time" class="border rounded px-3 py-2" />
            <button v-if="form.peak_hours.length > 1" @click="removeTimeSlot('peak_hours', i)"
              class="text-red-400 text-sm hover:text-red-600">移除</button>
          </div>
          <button @click="addTimeSlot('peak_hours')"
            class="text-sm text-blue-600 hover:text-blue-800">+ 添加时段</button>
        </div>

        <div>
          <h4 class="text-sm font-semibold text-gray-600 mb-2">谷段时段</h4>
          <div v-for="(h, i) in form.valley_hours" :key="'v' + i" class="flex items-center gap-2 mb-2">
            <input v-model="h.start" type="time" class="border rounded px-3 py-2" />
            <span class="text-gray-400">~</span>
            <input v-model="h.end" type="time" class="border rounded px-3 py-2" />
            <button v-if="form.valley_hours.length > 1" @click="removeTimeSlot('valley_hours', i)"
              class="text-red-400 text-sm hover:text-red-600">移除</button>
          </div>
          <button @click="addTimeSlot('valley_hours')"
            class="text-sm text-blue-600 hover:text-blue-800">+ 添加时段</button>
        </div>

        <div class="flex gap-3 pt-2">
          <button @click="saveForm" :disabled="saving || !form.name"
            class="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
            {{ saving ? '保存中...' : '保存策略' }}
          </button>
          <button @click="cancelForm"
            class="px-6 py-2 border rounded hover:bg-gray-50">取消</button>
        </div>
      </div>
    </div>
  </FeatureGate>
</template>
