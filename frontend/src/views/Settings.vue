<!-- Copyright 2026 smart-ebocr Contributors
SPDX-License-Identifier: Apache-2.0 -->

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useUsageStore } from '../stores/usage'
import { useUserStore } from '../stores/user'
import AdvancedPolicyManager from '../components/AdvancedPolicyManager.vue'

const store = useUsageStore()
const userStore = useUserStore()
const form = ref({})
const saving = ref(false)
const newMemberName = ref('')

async function loadPolicy() {
  await store.fetchPolicy(userStore.selectedMemberId)
  if (store.policy) {
    form.value = { ...store.policy }
  }
}

onMounted(async () => {
  await userStore.ensureLoaded()
  await loadPolicy()
})

const rateMatrix = computed(() => {
  const f = form.value
  if (!f.tier1_rate) return []
  const t2diff = +(f.tier2_rate - f.tier1_rate).toFixed(4)
  const t3diff = +(f.tier3_rate - f.tier1_rate).toFixed(4)
  return [
    {
      tier: '第一档',
      range: `0~${f.tier1_limit}`,
      diff: '—',
      peak: f.peak_rate,
      valley: f.valley_rate,
      heating_peak: f.peak_rate,
      heating_valley: f.heating_valley_rate,
    },
    {
      tier: '第二档',
      range: `${f.tier1_limit}~${f.tier2_limit}`,
      diff: `+${t2diff}`,
      peak: +(f.peak_rate + t2diff).toFixed(4),
      valley: +(f.valley_rate + t2diff).toFixed(4),
      heating_peak: +(f.peak_rate + t2diff).toFixed(4),
      heating_valley: +(f.heating_valley_rate + t2diff).toFixed(4),
    },
    {
      tier: '第三档',
      range: `>${f.tier2_limit}`,
      diff: `+${t3diff}`,
      peak: +(f.peak_rate + t3diff).toFixed(4),
      valley: +(f.valley_rate + t3diff).toFixed(4),
      heating_peak: +(f.peak_rate + t3diff).toFixed(4),
      heating_valley: +(f.heating_valley_rate + t3diff).toFixed(4),
    },
  ]
})

async function save() {
  saving.value = true
  try {
    await store.updatePolicy(form.value)
    alert('保存成功')
  } catch (err) {
    alert('保存失败: ' + (err.response?.data?.error || err.message))
  } finally {
    saving.value = false
  }
}

async function addMember() {
  if (!newMemberName.value.trim()) return
  try {
    await userStore.createMember(newMemberName.value)
    newMemberName.value = ''
  } catch (err) {
    alert('添加失败: ' + (err.response?.data?.error || err.message))
  }
}

async function deleteMember(id) {
  if (!confirm('确定删除该成员？')) return
  try {
    await userStore.deleteMember(id)
  } catch (err) {
    alert('删除失败: ' + (err.response?.data?.error || err.message))
  }
}
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold text-gray-800">设置</h1>

    <!-- 子账户管理 -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h2 class="text-lg font-semibold mb-4">账户管理</h2>

      <!-- 成员列表 -->
      <div v-if="userStore.familyMembers.length > 0" class="space-y-2 mb-4">
        <div v-for="member in userStore.familyMembers" :key="member.id"
          class="flex items-center justify-between p-3 border rounded-lg">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full flex items-center justify-center text-white font-medium"
              :style="{ backgroundColor: member.avatar_color }">
              {{ member.name[0] }}
            </div>
            <span class="font-medium">{{ member.name }}</span>
          </div>
          <button @click="deleteMember(member.id)" class="text-red-500 text-sm hover:text-red-700">
            删除
          </button>
        </div>
      </div>

      <!-- 添加成员 -->
      <div class="flex gap-2">
        <input v-model="newMemberName" placeholder="输入成员名称"
          class="flex-1 border rounded-lg px-3 py-2" @keyup.enter="addMember" />
        <button @click="addMember" :disabled="!newMemberName.trim()"
          class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50">
          添加
        </button>
      </div>
    </div>

    <!-- 电价设置 -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-6">
      <h2 class="text-lg font-semibold">电价设置</h2>

      <div>
        <h2 class="text-lg font-semibold mb-3">阶梯电价（不分峰谷）</h2>
        <div class="grid grid-cols-3 gap-4">
          <div>
            <label class="block text-sm text-gray-600 mb-1">第一档 (0~{{ form.tier1_limit }} kWh/年)</label>
            <div class="flex items-center gap-2">
              <input v-model.number="form.tier1_rate" type="number" step="0.0001"
                class="border rounded px-3 py-2 w-full" />
              <span class="text-sm text-gray-500">元/kWh</span>
            </div>
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">第二档 ({{ form.tier1_limit }}~{{ form.tier2_limit }} kWh/年)</label>
            <div class="flex items-center gap-2">
              <input v-model.number="form.tier2_rate" type="number" step="0.0001"
                class="border rounded px-3 py-2 w-full" />
              <span class="text-sm text-gray-500">元/kWh</span>
            </div>
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">第三档 (> {{ form.tier2_limit }} kWh/年)</label>
            <div class="flex items-center gap-2">
              <input v-model.number="form.tier3_rate" type="number" step="0.0001"
                class="border rounded px-3 py-2 w-full" />
              <span class="text-sm text-gray-500">元/kWh</span>
            </div>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4 mt-4">
          <div>
            <label class="block text-sm text-gray-600 mb-1">第一档上限 (kWh/年)</label>
            <input v-model.number="form.tier1_limit" type="number" class="border rounded px-3 py-2 w-full" />
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">第二档上限 (kWh/年)</label>
            <input v-model.number="form.tier2_limit" type="number" class="border rounded px-3 py-2 w-full" />
          </div>
        </div>
      </div>

      <div>
        <h2 class="text-lg font-semibold mb-3">峰谷电价</h2>

        <!-- 基础费率（可编辑） -->
        <div class="grid grid-cols-3 gap-4">
          <div>
            <label class="block text-sm text-gray-600 mb-1">第一档峰段费率</label>
            <div class="flex items-center gap-2">
              <input v-model.number="form.peak_rate" type="number" step="0.0001"
                class="border rounded px-3 py-2 w-full" />
              <span class="text-sm text-gray-500">元/kWh</span>
            </div>
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">第一档谷段费率（非采暖季 4-10月）</label>
            <div class="flex items-center gap-2">
              <input v-model.number="form.valley_rate" type="number" step="0.0001"
                class="border rounded px-3 py-2 w-full" />
              <span class="text-sm text-gray-500">元/kWh</span>
            </div>
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">第一档谷段费率（采暖季 11-3月）</label>
            <div class="flex items-center gap-2">
              <input v-model.number="form.heating_valley_rate" type="number" step="0.0001"
                class="border rounded px-3 py-2 w-full" />
              <span class="text-sm text-gray-500">元/kWh</span>
            </div>
          </div>
        </div>

        <!-- 各档费率速查表（只读） -->
        <div class="mt-6">
          <h3 class="text-sm font-semibold text-gray-600 mb-2">各档峰谷电价速查（元/kWh）</h3>
          <div class="overflow-x-auto">
            <table class="w-full text-sm border-collapse">
              <thead>
                <tr class="bg-gray-50">
                  <th class="border px-3 py-2 text-left">档位</th>
                  <th class="border px-3 py-2 text-left">年度范围 (kWh)</th>
                  <th class="border px-3 py-2 text-left">加价</th>
                  <th class="border px-3 py-2 text-center bg-orange-50" colspan="2">非采暖季 (4-10月)</th>
                  <th class="border px-3 py-2 text-center bg-blue-50" colspan="2">采暖季 (11-3月)</th>
                </tr>
                <tr class="bg-gray-50 text-xs text-gray-500">
                  <th class="border px-2 py-1"></th>
                  <th class="border px-2 py-1"></th>
                  <th class="border px-2 py-1"></th>
                  <th class="border px-2 py-1 bg-orange-50">峰段</th>
                  <th class="border px-2 py-1 bg-orange-50">谷段</th>
                  <th class="border px-2 py-1 bg-blue-50">峰段</th>
                  <th class="border px-2 py-1 bg-blue-50">谷段</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in rateMatrix" :key="r.tier">
                  <td class="border px-3 py-2 font-medium">{{ r.tier }}</td>
                  <td class="border px-3 py-2 text-gray-500">{{ r.range }}</td>
                  <td class="border px-3 py-2 text-gray-500">{{ r.diff }}</td>
                  <td class="border px-3 py-2 text-right text-orange-700">{{ r.peak }}</td>
                  <td class="border px-3 py-2 text-right text-orange-700">{{ r.valley }}</td>
                  <td class="border px-3 py-2 text-right text-blue-700">{{ r.heating_peak }}</td>
                  <td class="border px-3 py-2 text-right text-blue-700">{{ r.heating_valley }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <button @click="save" :disabled="saving"
        class="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
        {{ saving ? '保存中...' : '保存设置' }}
      </button>
    </div>

    <div v-if="!form.id" class="text-center py-8 text-gray-500">加载中...</div>

    <!-- 高级电价策略（高级用户） -->
    <AdvancedPolicyManager />

    <!-- 版本信息 -->
    <div class="mt-4 text-center text-xs text-gray-400">
      v{{ __APP_VERSION__ }}
    </div>
  </div>
</template>