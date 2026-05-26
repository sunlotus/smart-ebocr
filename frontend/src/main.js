// Copyright 2026 smart-ebocr Contributors
// SPDX-License-Identifier: Apache-2.0

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import './style.css'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')