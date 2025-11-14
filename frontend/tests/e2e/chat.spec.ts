import { test, expect } from '@playwright/test'

test.describe('Chat Interface', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login')
    await page.getByPlaceholder('you@example.com').fill('test@example.com')
    await page.getByPlaceholder('Enter your password').fill('password123')
    await page.getByRole('button', { name: 'Sign In' }).click()
    await page.waitForURL('/dashboard')
  })

  test('should display chat interface elements', async ({ page }) => {
    await expect(page.getByText('Chat with Financial AI')).toBeVisible()
    await expect(page.getByPlaceholder('Type your question about financial documents...')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Send' })).toBeVisible()
    await expect(page.getByText('Ask me anything about your financial documents')).toBeVisible()
  })

  test('should send and receive messages', async ({ page }) => {
    // Type a message
    const input = page.getByPlaceholder('Type your question about financial documents...')
    await input.fill('What is the company revenue?')
    
    // Send message
    await page.getByRole('button', { name: 'Send' }).click()
    
    // User message should appear
    await expect(page.getByText('What is the company revenue?')).toBeVisible()
    
    // Loading indicator should appear
    await expect(page.getByTestId('loading-indicator')).toBeVisible()
    
    // AI response should appear
    await expect(page.getByText(/Based on the financial reports/)).toBeVisible({
      timeout: 10000
    })
    
    // Sources should be displayed
    await expect(page.getByText(/Sources:/)).toBeVisible()
    await expect(page.getByText(/Confidence:/)).toBeVisible()
  })

  test('should maintain conversation history', async ({ page }) => {
    const input = page.getByPlaceholder('Type your question about financial documents...')
    
    // Send first message
    await input.fill('What is the revenue?')
    await page.getByRole('button', { name: 'Send' }).click()
    await expect(page.getByText('What is the revenue?')).toBeVisible()
    
    // Wait for response
    await page.waitForSelector('[data-testid="ai-response"]')
    
    // Send second message
    await input.fill('What about expenses?')
    await page.getByRole('button', { name: 'Send' }).click()
    
    // Both conversations should be visible
    await expect(page.getByText('What is the revenue?')).toBeVisible()
    await expect(page.getByText('What about expenses?')).toBeVisible()
    
    // Should maintain context
    const responses = await page.locator('[data-testid="ai-response"]').count()
    expect(responses).toBeGreaterThanOrEqual(2)
  })

  test('should handle empty message submission', async ({ page }) => {
    // Try to send empty message
    await page.getByRole('button', { name: 'Send' }).click()
    
    // Should not add empty message
    const messages = await page.locator('[data-testid="chat-message"]').count()
    expect(messages).toBe(0)
  })

  test('should disable input while processing', async ({ page }) => {
    const input = page.getByPlaceholder('Type your question about financial documents...')
    const sendButton = page.getByRole('button', { name: 'Send' })
    
    // Send a message
    await input.fill('Test message')
    await sendButton.click()
    
    // Input and button should be disabled
    await expect(input).toBeDisabled()
    await expect(sendButton).toBeDisabled()
    
    // Wait for response
    await page.waitForSelector('[data-testid="ai-response"]')
    
    // Should be enabled again
    await expect(input).toBeEnabled()
    await expect(sendButton).toBeEnabled()
  })

  test('should scroll to bottom on new messages', async ({ page }) => {
    const input = page.getByPlaceholder('Type your question about financial documents...')
    
    // Send multiple messages to create scroll
    for (let i = 1; i <= 5; i++) {
      await input.fill(`Message ${i}`)
      await page.getByRole('button', { name: 'Send' }).click()
      await page.waitForSelector(`text=Message ${i}`)
    }
    
    // Check if scrolled to bottom
    const isScrolledToBottom = await page.evaluate(() => {
      const container = document.querySelector('[data-testid="messages-container"]')
      if (!container) return false
      return Math.abs(container.scrollHeight - container.scrollTop - container.clientHeight) < 10
    })
    
    expect(isScrolledToBottom).toBeTruthy()
  })

  test('should display error for failed messages', async ({ page }) => {
    // Intercept API and force error
    await page.route('**/api/v1/chat', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' })
      })
    })
    
    // Send message
    const input = page.getByPlaceholder('Type your question about financial documents...')
    await input.fill('This will fail')
    await page.getByRole('button', { name: 'Send' }).click()
    
    // Error message should appear
    await expect(page.getByText(/Failed to send message/)).toBeVisible()
  })

  test('should handle keyboard shortcuts', async ({ page }) => {
    const input = page.getByPlaceholder('Type your question about financial documents...')
    
    // Type and press Enter to send
    await input.fill('Test with Enter key')
    await input.press('Enter')
    
    // Message should be sent
    await expect(page.getByText('Test with Enter key')).toBeVisible()
  })

  test('should show cached indicator for cached responses', async ({ page }) => {
    const input = page.getByPlaceholder('Type your question about financial documents...')
    
    // Send same message twice
    await input.fill('What is the revenue?')
    await page.getByRole('button', { name: 'Send' }).click()
    
    // Wait for first response
    await page.waitForSelector('[data-testid="ai-response"]')
    
    // Send same message again
    await input.fill('What is the revenue?')
    await page.getByRole('button', { name: 'Send' }).click()
    
    // Second response should show cached indicator
    await expect(page.getByText('Cached').last()).toBeVisible()
  })

  test('should handle network disconnection gracefully', async ({ page, context }) => {
    // Go offline
    await context.setOffline(true)
    
    // Try to send message
    const input = page.getByPlaceholder('Type your question about financial documents...')
    await input.fill('Offline test')
    await page.getByRole('button', { name: 'Send' }).click()
    
    // Should show network error
    await expect(page.getByText(/Network error|Failed to send/)).toBeVisible()
    
    // Go back online
    await context.setOffline(false)
    
    // Should be able to send again
    await input.fill('Back online')
    await page.getByRole('button', { name: 'Send' }).click()
    await expect(page.getByText('Back online')).toBeVisible()
  })
})