<!-- Copyright 2026 smart-ebocr Contributors
SPDX-License-Identifier: Apache-2.0 -->

<script setup>
import { ref } from 'vue'

const currentYear = new Date().getFullYear()
const currentMonth = new Date().getMonth() + 1
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold text-gray-800">电费分析系统</h1>
    <p class="text-gray-600">上传国家电网 APP 截图，自动识别峰谷电量，对比两种计费方式哪种更省钱。</p>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
      <router-link to="/upload"
        class="block p-6 bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
        <h3 class="text-lg font-semibold text-gray-800 mb-2">上传截图</h3>
        <p class="text-sm text-gray-500">OCR 自动识别用电数据，支持手动修正</p>
      </router-link>

      <router-link to="/monthly"
        class="block p-6 bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
        <h3 class="text-lg font-semibold text-gray-800 mb-2">月度数据</h3>
        <p class="text-sm text-gray-500">按月查看每日用电量和峰谷分布图表</p>
      </router-link>

      <router-link to="/billing"
        class="block p-6 bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
        <h3 class="text-lg font-semibold text-gray-800 mb-2">电费对比</h3>
        <p class="text-sm text-gray-500">峰谷计费 vs 不分峰谷，哪种更省钱</p>
      </router-link>
    </div>
  </div>
</template>