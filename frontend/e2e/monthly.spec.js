import { test, expect } from '@playwright/test'

test.describe('月度数据页面', () => {
  test('应正确显示页面标题和月份切换', async ({ page }) => {
    await page.goto('/monthly')
    await expect(page.locator('h1')).toContainText('月度数据')

    // 应显示年月和切换按钮
    await expect(page.locator('text=/\\d{4}年\\d{2}月/')).toBeVisible()
  })

  test('应能切换到上一个月', async ({ page }) => {
    await page.goto('/monthly')
    const monthText = await page.locator('text=/\\d{4}年\\d{2}月/').first().textContent()

    await page.locator('button:has-text("<")').first().click()

    const newMonthText = await page.locator('text=/\\d{4}年\\d{2}月/').first().textContent()
    expect(newMonthText).not.toBe(monthText)
  })

  test('应能切换到下一个月', async ({ page }) => {
    await page.goto('/monthly')
    const monthText = await page.locator('text=/\\d{4}年\\d{2}月/').first().textContent()

    await page.locator('button:has-text(">")').first().click()

    const newMonthText = await page.locator('text=/\\d{4}年\\d{2}月/').first().textContent()
    expect(newMonthText).not.toBe(monthText)
  })

  test('应显示手动添加按钮', async ({ page }) => {
    await page.goto('/monthly')
    await expect(page.locator('button:has-text("手动添加")')).toBeVisible()
  })

  test('手动添加记录应成功', async ({ page }) => {
    await page.goto('/monthly')

    // 点击手动添加
    await page.click('button:has-text("手动添加")')

    // 应出现表单
    await expect(page.locator('input[type="date"]')).toBeVisible()

    // 填写数据
    const today = new Date()
    const dateStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`

    await page.locator('input[type="date"]').fill(dateStr)
    await page.locator('input[type="number"]').first().fill('15.5')

    // 保存（监听 dialog 自动确认）
    page.on('dialog', dialog => dialog.accept())
    await page.click('button:has-text("保存")')

    // 等待表单消失或页面刷新
    await page.waitForTimeout(2000)
  })
})

test.describe('电费对比页面', () => {
  test('应正确显示页面', async ({ page }) => {
    await page.goto('/billing')
    await expect(page.locator('h1')).toContainText('电费对比')
  })
})

test.describe('电价设置页面', () => {
  test('应正确显示页面', async ({ page }) => {
    await page.goto('/settings')
    await expect(page.locator('h1')).toContainText('电价')
  })

  test('应显示当前电价策略', async ({ page }) => {
    await page.goto('/settings')
    // 应显示阶梯电价和分时电价区域
    await expect(page.locator('text=阶梯电价')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('h2:has-text("峰谷电价")').first()).toBeVisible()
    await expect(page.locator('text=保存设置')).toBeVisible()
  })
})

test.describe('API 健康检查', () => {
  test('后端 API 应可访问', async ({ page }) => {
    const resp = await page.request.get('http://localhost:5000/api/policy/')
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    expect(data).toHaveProperty('name')
  })

  test('用电数据 API 应可访问', async ({ page }) => {
    const resp = await page.request.get('http://localhost:5000/api/usage/?year=2026&month=4')
    expect(resp.ok()).toBeTruthy()
  })

  test('目录扫描 API 应返回目录列表', async ({ page }) => {
    const resp = await page.request.get('http://localhost:5000/api/screenshot/scan-dir')
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    expect(data).toHaveProperty('directories')
  })
})
