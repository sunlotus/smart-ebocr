import { test, expect } from '@playwright/test'

test.describe('页面导航', () => {
  test('应正确显示首页', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('h1')).toContainText('电费分析系统')
  })

  test('导航栏应包含所有链接', async ({ page }) => {
    await page.goto('/')
    const nav = page.locator('nav')
    await expect(nav).toContainText('上传截图')
    await expect(nav).toContainText('月度数据')
    await expect(nav).toContainText('电费对比')
    await expect(nav).toContainText('电价设置')
  })

  test('应导航到上传页面', async ({ page }) => {
    await page.goto('/')
    await page.click('a:has-text("上传截图")')
    await expect(page).toHaveURL('/upload')
    await expect(page.locator('h1')).toContainText('OCR 识别')
  })

  test('应导航到月度数据页面', async ({ page }) => {
    await page.goto('/')
    await page.click('a:has-text("月度数据")')
    await expect(page).toHaveURL('/monthly')
    await expect(page.locator('h1')).toContainText('月度数据')
  })

  test('应导航到电费对比页面', async ({ page }) => {
    await page.goto('/')
    await page.click('a:has-text("电费对比")')
    await expect(page).toHaveURL('/billing')
    await expect(page.locator('h1')).toContainText('电费对比')
  })

  test('应导航到电价设置页面', async ({ page }) => {
    await page.goto('/')
    await page.click('a:has-text("电价设置")')
    await expect(page).toHaveURL('/settings')
  })
})
