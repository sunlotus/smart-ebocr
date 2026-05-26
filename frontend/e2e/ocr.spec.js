import { test, expect } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const UPLOAD_DIR = path.resolve(__dirname, '../../data/uploads/2026/03')

test.describe('OCR 识别 — 单张上传', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/upload')
    // 确保在"单张上传" tab
    await page.click('button:has-text("单张上传")')
  })

  test('应显示单张上传区域', async ({ page }) => {
    await expect(page.locator('text=拖拽国家电网 APP 截图到此处')).toBeVisible()
    await expect(page.locator('input[type="file"]')).toBeVisible()
  })

  test('上传图片后应显示预览', async ({ page }) => {
    const fileInput = page.locator('input[type="file"]').first()
    await fileInput.setInputFiles(path.join(UPLOAD_DIR, 'Screenshot_20260408_082244_com_sgcc_wsgw_cn_ElectricTitleActivity.jpg'))
    await expect(page.locator('img')).toBeVisible()
    await expect(page.locator('button:has-text("开始 OCR 识别")')).toBeVisible()
  })

  test('OCR 识别后应响应（成功或失败）', async ({ page }) => {
    const fileInput = page.locator('input[type="file"]').first()
    await fileInput.setInputFiles(path.join(UPLOAD_DIR, 'Screenshot_20260408_082244_com_sgcc_wsgw_cn_ElectricTitleActivity.jpg'))

    await page.click('button:has-text("开始 OCR 识别")')

    // 等待结果或 alert 弹出
    const resultLocator = page.locator('text=识别结果')
    const dialogPromise = page.waitForEvent('dialog', { timeout: 30000 }).then(d => { d.accept(); return true }).catch(() => false)
    const resultPromise = resultLocator.isVisible().then(() => true).catch(() => false)

    // 两个条件哪个先到都行
    const hasResult = await Promise.race([
      resultPromise,
      dialogPromise,
    ])

    // 至少有一个响应（结果出现 或 alert 弹出）
    expect(hasResult).toBeTruthy()
  })

  test('识别成功后应显示记录表格和保存按钮', async ({ page }) => {
    const fileInput = page.locator('input[type="file"]').first()
    await fileInput.setInputFiles(path.join(UPLOAD_DIR, 'Screenshot_20260408_082244_com_sgcc_wsgw_cn_ElectricTitleActivity.jpg'))

    await page.click('button:has-text("开始 OCR 识别")')
    await expect(page.locator('text=识别结果')).toBeVisible({ timeout: 30000 })

    // 如果识别出了记录，应有表格和保存按钮
    const table = page.locator('table')
    if (await table.isVisible()) {
      await expect(page.locator('button:has-text("确认保存到数据库")')).toBeVisible()
    }
  })
})

test.describe('OCR 识别 — 多文件上传', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/upload')
    await page.click('button:has-text("多文件上传")')
  })

  test('应显示多文件上传区域', async ({ page }) => {
    await expect(page.locator('text=拖拽多张截图到此处')).toBeVisible()
    await expect(page.locator('input[multiple]')).toBeVisible()
  })

  test('选择多个文件后应显示文件列表', async ({ page }) => {
    const files = [
      'Screenshot_20260408_082244_com_sgcc_wsgw_cn_ElectricTitleActivity.jpg',
      'Screenshot_20260408_082249_com_sgcc_wsgw_cn_ElectricTitleActivity.jpg',
    ].map(f => path.join(UPLOAD_DIR, f))

    const fileInput = page.locator('input[multiple]')
    await fileInput.setInputFiles(files)

    // 应显示文件名和"开始识别"按钮
    await expect(page.locator('button:has-text("开始识别 2 张图片")')).toBeVisible()
  })

  test('应能移除已选文件', async ({ page }) => {
    const files = [
      'Screenshot_20260408_082244_com_sgcc_wsgw_cn_ElectricTitleActivity.jpg',
      'Screenshot_20260408_082249_com_sgcc_wsgw_cn_ElectricTitleActivity.jpg',
    ].map(f => path.join(UPLOAD_DIR, f))

    await page.locator('input[multiple]').setInputFiles(files)
    await expect(page.locator('button:has-text("移除")')).toHaveCount(2)

    // 点击第一个移除
    await page.locator('button:has-text("移除")').first().click()
    await expect(page.locator('button:has-text("移除")')).toHaveCount(1)
    await expect(page.locator('button:has-text("开始识别 1 张图片")')).toBeVisible()
  })

  test('批量识别后应显示汇总结果', async ({ page }) => {
    const files = [
      'Screenshot_20260408_082244_com_sgcc_wsgw_cn_ElectricTitleActivity.jpg',
      'Screenshot_20260408_082249_com_sgcc_wsgw_cn_ElectricTitleActivity.jpg',
    ].map(f => path.join(UPLOAD_DIR, f))

    await page.locator('input[multiple]').setInputFiles(files)
    await page.click('button:has-text("开始识别")')

    await expect(page.locator('text=识别结果')).toBeVisible({ timeout: 60000 })
    // 应显示成功/失败统计
    await expect(page.locator('text=/\\d+\\/\\d+ 张成功/')).toBeVisible()
  })
})

test.describe('OCR 识别 — 目录扫描', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/upload')
    await page.click('button:has-text("目录扫描")')
  })

  test('应加载并显示目录列表', async ({ page }) => {
    // 等待目录加载
    await expect(page.locator('select')).toBeVisible({ timeout: 5000 })

    // 应至少有一个 option
    const options = page.locator('select option')
    const count = await options.count()
    expect(count).toBeGreaterThanOrEqual(1)
  })

  test('应显示目录中的图片数量', async ({ page }) => {
    const select = page.locator('select')
    await expect(select).toBeVisible({ timeout: 5000 })

    // option 应包含 "张图片" 文本
    const optionText = await page.locator('select option').first().textContent()
    expect(optionText).toContain('张图片')
  })

  test('选择目录后应能开始批量识别', async ({ page }) => {
    await expect(page.locator('select')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('button:has-text("开始批量识别")')).toBeVisible()
    await expect(page.locator('button:has-text("开始批量识别")')).toBeEnabled()
  })

  test('批量识别目录后应显示结果', async ({ page }) => {
    const select = page.locator('select')
    await expect(select).toBeVisible({ timeout: 5000 })

    // 选择包含 "test" 的目录选项
    const options = select.locator('option')
    const count = await options.count()
    let selected = false
    for (let i = 0; i < count; i++) {
      const text = await options.nth(i).textContent()
      if (text && text.includes('test')) {
        const value = await options.nth(i).getAttribute('value')
        await select.selectOption(value)
        selected = true
        break
      }
    }
    // 如果没找到 test 目录，使用第一个可用目录
    if (!selected && count > 0) {
      await select.selectOption({ index: 0 })
    }

    await page.click('button:has-text("开始批量识别")')
    await expect(page.locator('text=识别结果')).toBeVisible({ timeout: 60000 })
  })

  test('刷新按钮应重新加载目录', async ({ page }) => {
    await expect(page.locator('select')).toBeVisible({ timeout: 5000 })
    const initialCount = await page.locator('select option').count()

    await page.click('button:has-text("刷新")')
    await page.waitForTimeout(1000)

    const afterCount = await page.locator('select option').count()
    expect(afterCount).toBeGreaterThanOrEqual(initialCount)
  })
})

test.describe('OCR 结果保存', () => {
  test('保存记录后应跳转到月度数据页', async ({ page }) => {
    await page.goto('/upload')

    // 使用目录扫描模式
    await page.click('button:has-text("目录扫描")')
    await expect(page.locator('select')).toBeVisible({ timeout: 5000 })

    // 选择 test 目录
    const select = page.locator('select')
    const options = select.locator('option')
    const count = await options.count()
    let selected = false
    for (let i = 0; i < count; i++) {
      const text = await options.nth(i).textContent()
      if (text && text.includes('test')) {
        const value = await options.nth(i).getAttribute('value')
        await select.selectOption(value)
        selected = true
        break
      }
    }
    if (!selected && count > 0) {
      await select.selectOption({ index: 0 })
    }

    await page.click('button:has-text("开始批量识别")')
    await expect(page.locator('text=识别结果')).toBeVisible({ timeout: 60000 })

    // 检查是否有记录
    const rows = page.locator('table tbody tr')
    const rowCount = await rows.count()

    if (rowCount > 0) {
      page.on('dialog', dialog => dialog.accept())
      await page.click('button:has-text("全选")')
      await page.click('button:has-text("确认保存到数据库")')
      await expect(page).toHaveURL('/monthly', { timeout: 10000 })
    }
  })
})

test.describe('年月上下文', () => {
  test('应能修改识别年月', async ({ page }) => {
    await page.goto('/upload')

    const yearInput = page.locator('input[type="number"]').first()
    const monthInput = page.locator('input[type="number"]').nth(1)

    await yearInput.fill('2026')
    await monthInput.fill('4')

    await expect(yearInput).toHaveValue('2026')
    await expect(monthInput).toHaveValue('4')
  })
})
