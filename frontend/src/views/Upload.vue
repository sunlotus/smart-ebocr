<!-- Copyright 2026 smart-ebocr Contributors
SPDX-License-Identifier: Apache-2.0 -->

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { screenshotApi, usageApi, createBatchSSE } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

// Tab state
const activeTab = ref('single')

// Single file upload
const dragging = ref(false)
const file = ref(null)
const previewUrl = ref(null)
const singleLoading = ref(false)

// Multi-file upload
const multiFiles = ref([])
const multiDragging = ref(false)
const multiLoading = ref(false)

// Directory scan
const directories = ref([])
const selectedDir = ref('')
const dirLoading = ref(false)

// Shared OCR result state
const ocrResult = ref(null)
const ocrLoading = ref(false)
const saving = ref(false)
const selectedRecords = ref(new Set())

// Batch progress (SSE)
const batchProgress = ref(null)
let closeSSE = null

// Year/month context
const yearInput = ref(new Date().getFullYear())
const monthInput = ref(new Date().getMonth() + 1)

// --- Single file ---
function handleDrop(e) {
  dragging.value = false
  const files = e.dataTransfer.files
  if (files.length) selectFile(files[0])
}

function handleFileInput(e) {
  if (e.target.files.length) selectFile(e.target.files[0])
}

function selectFile(f) {
  file.value = f
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = URL.createObjectURL(f)
  ocrResult.value = null
}

async function uploadSingle() {
  if (!file.value) return
  ocrLoading.value = true
  try {
    const res = await screenshotApi.upload(file.value, userStore.selectedMemberId)
    ocrResult.value = _normalizeResult(res.data)
  } catch (err) {
    alert('识别失败: ' + (err.response?.data?.error || err.message))
  } finally {
    ocrLoading.value = false
  }
}

// --- Multi-file ---
function handleMultiDrop(e) {
  multiDragging.value = false
  const files = Array.from(e.dataTransfer.files).filter(f =>
    f.type.startsWith('image/')
  )
  if (files.length) multiFiles.value.push(...files)
}

function handleMultiInput(e) {
  const files = Array.from(e.target.files)
  if (files.length) multiFiles.value.push(...files)
  e.target.value = ''
}

function removeMultiFile(index) {
  multiFiles.value.splice(index, 1)
}

async function uploadMulti() {
  if (!multiFiles.value.length) return
  ocrLoading.value = true
  try {
    const res = await screenshotApi.batchUpload(
      multiFiles.value, yearInput.value, monthInput.value, userStore.selectedMemberId
    )
    ocrResult.value = _sortRecords(res.data)
  } catch (err) {
    alert('批量识别失败: ' + (err.response?.data?.error || err.message))
  } finally {
    ocrLoading.value = false
  }
}

// --- Directory scan ---
async function loadDirectories() {
  dirLoading.value = true
  try {
    const res = await screenshotApi.scanDir()
    directories.value = res.data.directories || []
    if (directories.value.length && !selectedDir.value) {
      selectedDir.value = directories.value[0].path || ''
    }
  } catch (err) {
    console.error('扫描目录失败:', err)
  } finally {
    dirLoading.value = false
  }
}

async function batchProcessDir() {
  if (!selectedDir.value) return
  ocrLoading.value = true
  ocrResult.value = null
  batchProgress.value = null

  try {
    // 1. Submit job — returns immediately with job_id
    const res = await screenshotApi.batchProcess(
      selectedDir.value, yearInput.value, monthInput.value, userStore.selectedMemberId
    )
    if (res.data.error) {
      alert('提交失败: ' + res.data.error)
      ocrLoading.value = false
      return
    }

    const jobId = res.data.job_id
    batchProgress.value = { total: res.data.total, processed: 0, status: 'processing' }

    // 2. Open SSE stream for progress
    closeSSE = createBatchSSE(jobId, {
      onProgress: (data) => {
        batchProgress.value = data
      },
      onComplete: (data) => {
        batchProgress.value = data
        ocrResult.value = _sortRecords(data)
        ocrLoading.value = false
        closeSSE = null
      },
      onError: (err) => {
        alert('连接中断: ' + err.message)
        ocrLoading.value = false
        closeSSE = null
      },
    })
  } catch (err) {
    alert('提交失败: ' + (err.response?.data?.error || err.message))
    ocrLoading.value = false
  }
}

// --- Result handling ---
function _sortRecords(data) {
  if (data?.all_records) {
    data.all_records.sort((a, b) => a.date?.localeCompare(b.date))
  }
  return data
}
function _normalizeResult(data) {
  // Single file result -> wrap into batch format
  // Handle both process_and_build_records (data.records) and
  // process_screenshot (data.parsed.daily_records) response shapes
  const records = data.records || data.parsed?.daily_records || []
  if (records.length || (data.records && !data.results)) {
    return {
      total_files: 1,
      success_count: 1,
      fail_count: 0,
      results: [{
        filename: file.value?.name || 'unknown',
        status: records.length ? 'success' : 'empty',
        records,
        days_extracted: data.days_extracted || records.length,
        warnings: data.parsed?.warnings || data.warnings || [],
        raw_texts: data.raw_blocks?.map(b => b.text).filter(Boolean) || [],
      }],
      all_records: records,
    }
  }
  return data
}

function toggleRecord(index) {
  const s = new Set(selectedRecords.value)
  if (s.has(index)) s.delete(index)
  else s.add(index)
  selectedRecords.value = s
}

function toggleAll() {
  if (!ocrResult.value?.all_records) return
  if (selectedRecords.value.size === ocrResult.value.all_records.length) {
    selectedRecords.value = new Set()
  } else {
    selectedRecords.value = new Set(ocrResult.value.all_records.map((_, i) => i))
  }
}

async function saveRecords() {
  if (!selectedRecords.value.size) {
    alert('请先勾选要保存的记录')
    return
  }
  const records = ocrResult.value.all_records.filter((_, i) =>
    selectedRecords.value.has(i)
  )

  // Check for conflicts (dates that already exist)
  saving.value = true
  try {
    const dates = records.map(r => r.date)
    const conflictRes = await usageApi.checkConflicts(dates)
    const conflicts = conflictRes.data.conflicts || []

    let conflictMode = 'overwrite'
    if (conflicts.length > 0) {
      const ok = confirm(
        `以下 ${conflicts.length} 个日期已有记录：${conflicts.join(', ')}\n\n点击"确定"覆盖已有记录\n点击"取消"跳过这些日期仅保存新记录`
      )
      conflictMode = ok ? 'overwrite' : 'skip'
    }

    const res = await screenshotApi.confirm(records, conflictMode, userStore.selectedMemberId)
    const { saved, skipped } = res.data
    let msg = `成功保存 ${saved} 条记录`
    if (skipped > 0) msg += `，跳过 ${skipped} 条重复`
    alert(msg)
    ocrResult.value = null
    selectedRecords.value = new Set()
    router.push('/monthly')
  } catch (err) {
    alert('保存失败: ' + (err.response?.data?.error || err.message))
  } finally {
    saving.value = false
  }
}

function resetAll() {
  if (closeSSE) { closeSSE(); closeSSE = null }
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  file.value = null
  previewUrl.value = null
  multiFiles.value = []
  ocrResult.value = null
  batchProgress.value = null
  selectedRecords.value = new Set()
}

onMounted(() => {
  loadDirectories()
})

onUnmounted(() => {
  if (closeSSE) { closeSSE(); closeSSE = null }
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold text-gray-800">OCR 识别</h1>

    <!-- Tabs -->
    <div class="flex border-b border-gray-200">
      <button v-for="tab in [
        { id: 'single', label: '单张上传' },
        { id: 'multi', label: '多文件上传' },
        { id: 'directory', label: '目录扫描' },
      ]" :key="tab.id"
        @click="activeTab = tab.id; resetAll()"
        class="px-4 py-2 text-sm font-medium transition-colors"
        :class="activeTab === tab.id
          ? 'text-blue-600 border-b-2 border-blue-600'
          : 'text-gray-500 hover:text-gray-700'">
        {{ tab.label }}
      </button>
    </div>

    <!-- Year/Month context -->
    <div class="flex items-center gap-3 text-sm">
      <label class="text-gray-600">识别年月:</label>
      <input v-model.number="yearInput" type="number" min="2020" max="2030"
        class="w-20 px-2 py-1 border rounded text-center" />
      <span class="text-gray-400">年</span>
      <input v-model.number="monthInput" type="number" min="1" max="12"
        class="w-16 px-2 py-1 border rounded text-center" />
      <span class="text-gray-400">月</span>
    </div>

    <!-- Tab: Single file -->
    <div v-if="activeTab === 'single'" class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div class="border-2 border-dashed rounded-lg p-8 text-center"
        :class="dragging ? 'border-blue-400 bg-blue-50' : 'border-gray-300'"
        @dragover.prevent="dragging = true"
        @dragleave="dragging = false"
        @drop.prevent="handleDrop">
        <template v-if="!previewUrl">
          <p class="text-gray-500 mb-2">拖拽国家电网 APP 截图到此处</p>
          <p class="text-sm text-gray-400 mb-4">或点击选择文件</p>
          <input type="file" accept="image/*" @change="handleFileInput"
            class="block mx-auto text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" />
        </template>
        <template v-else>
          <img :src="previewUrl" class="max-h-64 mx-auto rounded" />
          <div class="mt-4 flex gap-3 justify-center">
            <button @click="uploadSingle" :disabled="ocrLoading"
              class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {{ ocrLoading ? '识别中...' : '开始 OCR 识别' }}
            </button>
            <button @click="file = null; previewUrl = null"
              class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300">
              重新选择
            </button>
          </div>
        </template>
      </div>
    </div>

    <!-- Tab: Multi file -->
    <div v-if="activeTab === 'multi'" class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div class="border-2 border-dashed rounded-lg p-8 text-center"
        :class="multiDragging ? 'border-blue-400 bg-blue-50' : 'border-gray-300'"
        @dragover.prevent="multiDragging = true"
        @dragleave="multiDragging = false"
        @drop.prevent="handleMultiDrop">
        <p class="text-gray-500 mb-2">拖拽多张截图到此处</p>
        <p class="text-sm text-gray-400 mb-4">或点击选择多个文件</p>
        <input type="file" accept="image/*" multiple @change="handleMultiInput"
          class="block mx-auto text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" />
      </div>
      <div v-if="multiFiles.length" class="mt-4 space-y-2">
        <div v-for="(f, i) in multiFiles" :key="i"
          class="flex items-center justify-between px-3 py-2 bg-gray-50 rounded">
          <span class="text-sm text-gray-700 truncate">{{ f.name }}</span>
          <button @click="removeMultiFile(i)" class="text-red-400 hover:text-red-600 text-sm">移除</button>
        </div>
        <button @click="uploadMulti" :disabled="ocrLoading"
          class="w-full mt-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
          {{ ocrLoading ? '批量识别中...' : `开始识别 ${multiFiles.length} 张图片` }}
        </button>
      </div>
    </div>

    <!-- Tab: Directory scan -->
    <div v-if="activeTab === 'directory'" class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div v-if="dirLoading" class="text-center text-gray-400 py-4">扫描目录中...</div>
      <div v-else-if="!directories.length" class="text-center text-gray-400 py-4">
        未找到包含图片的目录，请先将截图放入 data/uploads/ 目录
      </div>
      <div v-else class="space-y-4">
        <div class="flex items-center gap-3">
          <label class="text-sm text-gray-600">选择目录:</label>
          <select v-model="selectedDir"
            class="flex-1 px-3 py-2 border rounded text-sm">
            <option v-for="d in directories" :key="d.path" :value="d.path">
              {{ d.path || '(根目录)' }} — {{ d.file_count }} 张图片
            </option>
          </select>
          <button @click="loadDirectories"
            class="px-3 py-2 text-sm text-blue-600 hover:text-blue-800">
            刷新
          </button>
        </div>
        <button @click="batchProcessDir" :disabled="ocrLoading || !selectedDir"
          class="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
          {{ ocrLoading ? '批量识别中...' : '开始批量识别' }}
        </button>

        <!-- SSE Progress -->
        <div v-if="batchProgress && ocrLoading" class="space-y-2 pt-2">
          <div class="flex items-center justify-between text-sm">
            <span class="text-gray-600">
              处理中 {{ batchProgress.processed }}/{{ batchProgress.total }}
            </span>
            <span class="text-xs text-gray-400 truncate max-w-48">
              {{ batchProgress.current_file }}
            </span>
          </div>
          <div class="w-full bg-gray-200 rounded-full h-2">
            <div class="bg-blue-600 h-2 rounded-full transition-all duration-300"
              :style="{ width: batchProgress.total ? (batchProgress.processed / batchProgress.total * 100) + '%' : '0%' }">
            </div>
          </div>
          <div class="flex gap-4 text-xs text-gray-500">
            <span class="text-green-600">{{ batchProgress.success_count }} 成功</span>
            <span class="text-red-500">{{ batchProgress.fail_count }} 失败</span>
          </div>
        </div>
      </div>
    </div>

    <!-- OCR Results -->
    <div v-if="ocrResult" class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-4">
      <!-- Summary -->
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold">识别结果</h2>
        <span class="text-sm text-gray-500">
          {{ ocrResult.success_count }}/{{ ocrResult.total_files }} 张成功
          <template v-if="ocrResult.all_records?.length">
            · 共 {{ ocrResult.all_records.length }} 天数据
          </template>
        </span>
      </div>

      <!-- Failed files -->
      <div v-if="ocrResult.fail_count > 0" class="space-y-1">
        <p class="text-sm text-red-600 font-medium">失败文件:</p>
        <div v-for="r in ocrResult.results.filter(r => r.status === 'error')" :key="r.filename"
          class="text-sm text-red-500 pl-4">
          {{ r.filename }}: {{ r.error }}
        </div>
      </div>

      <!-- Per-file breakdown -->
      <details v-if="ocrResult.results?.length > 1" class="text-sm">
        <summary class="cursor-pointer text-blue-600 hover:text-blue-800">
          查看各文件详情
        </summary>
        <div class="mt-2 space-y-1">
          <div v-for="r in ocrResult.results" :key="r.filename"
            class="flex items-center gap-2 pl-4">
            <span :class="r.status === 'success' ? 'text-green-600' : 'text-red-500'">
              {{ r.status === 'success' ? '✓' : '✗' }}
            </span>
            <span class="text-gray-700">{{ r.filename }}</span>
            <span class="text-gray-400">
              {{ r.status === 'success' ? `${r.days_extracted} 天` : r.error }}
            </span>
          </div>
        </div>
      </details>

      <!-- Records table -->
      <div v-if="ocrResult.all_records?.length" class="space-y-3">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-medium text-gray-700">识别出的用电记录</h3>
          <button @click="toggleAll" class="text-sm text-blue-600 hover:text-blue-800">
            {{ selectedRecords.size === ocrResult.all_records.length ? '取消全选' : '全选' }}
          </button>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b text-gray-600">
                <th class="py-2 px-2 text-left w-8"></th>
                <th class="py-2 px-2 text-left">日期</th>
                <th class="py-2 px-2 text-right">峰(kWh)</th>
                <th class="py-2 px-2 text-right">谷(kWh)</th>
                <th class="py-2 px-2 text-right">尖(kWh)</th>
                <th class="py-2 px-2 text-right">平(kWh)</th>
                <th class="py-2 px-2 text-right">合计</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(rec, i) in ocrResult.all_records" :key="i"
                class="border-b hover:bg-gray-50"
                :class="selectedRecords.has(i) ? 'bg-blue-50' : ''">
                <td class="py-2 px-2">
                  <input type="checkbox" :checked="selectedRecords.has(i)"
                    @change="toggleRecord(i)" class="rounded" />
                </td>
                <td class="py-2 px-2">{{ rec.date }}</td>
                <td class="py-2 px-2 text-right">{{ rec.peak_kwh }}</td>
                <td class="py-2 px-2 text-right">{{ rec.valley_kwh }}</td>
                <td class="py-2 px-2 text-right">{{ rec.sharp_kwh }}</td>
                <td class="py-2 px-2 text-right">{{ rec.flat_kwh }}</td>
                <td class="py-2 px-2 text-right font-medium">{{ rec.total_kwh }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Save button -->
        <div class="flex items-center justify-between pt-2">
          <span class="text-sm text-gray-500">
            已选 {{ selectedRecords.size }} 条记录
          </span>
          <button @click="saveRecords" :disabled="saving || !selectedRecords.size"
            class="px-6 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50">
            {{ saving ? '保存中...' : '确认保存到数据库' }}
          </button>
        </div>
      </div>

      <div v-else class="space-y-4">
        <p class="text-gray-400 text-sm text-center py-2">未识别出有效的用电记录</p>

        <!-- Raw OCR texts for debugging -->
        <details v-if="ocrResult.results?.some(r => r.raw_texts?.length)" class="text-sm">
          <summary class="cursor-pointer text-blue-600 hover:text-blue-800">
            查看 OCR 原始文本（调试用）
          </summary>
          <div v-for="r in ocrResult.results.filter(r => r.raw_texts)" :key="r.filename" class="mt-2">
            <p class="text-xs text-gray-500 mb-1">{{ r.filename }}</p>
            <p class="text-xs text-gray-400 bg-gray-50 rounded p-2 break-all">
              {{ r.raw_texts?.join(' | ') }}
            </p>
          </div>
        </details>

        <!-- Actions when no records -->
        <div class="flex gap-3 justify-center pt-2">
          <router-link to="/monthly"
            class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm">
            手动输入数据
          </router-link>
          <button @click="activeTab = 'single'; resetAll()"
            class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 text-sm">
            重新上传截图
          </button>
        </div>
      </div>
    </div>
  </div>
</template>