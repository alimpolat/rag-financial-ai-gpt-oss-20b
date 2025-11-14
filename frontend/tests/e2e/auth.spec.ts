import { test, expect } from '@playwright/test'

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('should display login page for unauthenticated users', async ({ page }) => {
    await expect(page.getByText('Welcome Back')).toBeVisible()
    await expect(page.getByPlaceholder('you@example.com')).toBeVisible()
    await expect(page.getByPlaceholder('Enter your password')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible()
  })

  test('should show validation errors for invalid input', async ({ page }) => {
    // Try to submit empty form
    await page.getByRole('button', { name: 'Sign In' }).click()
    
    // Should show validation errors
    await expect(page.getByText('Invalid email address')).toBeVisible()
    await expect(page.getByText('Password must be at least 6 characters')).toBeVisible()
  })

  test('should successfully login with valid credentials', async ({ page }) => {
    // Fill in login form
    await page.getByPlaceholder('you@example.com').fill('test@example.com')
    await page.getByPlaceholder('Enter your password').fill('password123')
    
    // Submit form
    await page.getByRole('button', { name: 'Sign In' }).click()
    
    // Should redirect to dashboard
    await page.waitForURL('/dashboard')
    await expect(page.getByText('Chat with Financial AI')).toBeVisible()
  })

  test('should show error for invalid credentials', async ({ page }) => {
    // Fill in login form with wrong credentials
    await page.getByPlaceholder('you@example.com').fill('wrong@example.com')
    await page.getByPlaceholder('Enter your password').fill('wrongpassword')
    
    // Submit form
    await page.getByRole('button', { name: 'Sign In' }).click()
    
    // Should show error message
    await expect(page.getByText('Invalid email or password')).toBeVisible()
    
    // Should not redirect
    expect(page.url()).toContain('/login')
  })

  test('should toggle password visibility', async ({ page }) => {
    const passwordInput = page.getByPlaceholder('Enter your password')
    
    // Initially password should be hidden
    await expect(passwordInput).toHaveAttribute('type', 'password')
    
    // Click show password button
    await page.getByLabel('Show password').click()
    
    // Password should be visible
    await expect(passwordInput).toHaveAttribute('type', 'text')
    
    // Click hide password button
    await page.getByLabel('Hide password').click()
    
    // Password should be hidden again
    await expect(passwordInput).toHaveAttribute('type', 'password')
  })

  test('should persist authentication across page refreshes', async ({ page, context }) => {
    // Login
    await page.getByPlaceholder('you@example.com').fill('test@example.com')
    await page.getByPlaceholder('Enter your password').fill('password123')
    await page.getByRole('button', { name: 'Sign In' }).click()
    
    // Wait for redirect
    await page.waitForURL('/dashboard')
    
    // Refresh page
    await page.reload()
    
    // Should still be on dashboard
    expect(page.url()).toContain('/dashboard')
    await expect(page.getByText('Chat with Financial AI')).toBeVisible()
    
    // Check localStorage has tokens
    const localStorage = await page.evaluate(() => window.localStorage)
    expect(localStorage['access_token']).toBeTruthy()
    expect(localStorage['refresh_token']).toBeTruthy()
  })

  test('should logout successfully', async ({ page }) => {
    // Login first
    await page.getByPlaceholder('you@example.com').fill('test@example.com')
    await page.getByPlaceholder('Enter your password').fill('password123')
    await page.getByRole('button', { name: 'Sign In' }).click()
    await page.waitForURL('/dashboard')
    
    // Click logout
    await page.getByRole('button', { name: 'Logout' }).click()
    
    // Should redirect to login
    await page.waitForURL('/login')
    await expect(page.getByText('Welcome Back')).toBeVisible()
    
    // Tokens should be cleared
    const localStorage = await page.evaluate(() => window.localStorage)
    expect(localStorage['access_token']).toBeFalsy()
    expect(localStorage['refresh_token']).toBeFalsy()
  })

  test('should redirect to login when accessing protected routes', async ({ page }) => {
    // Try to access dashboard directly
    await page.goto('/dashboard')
    
    // Should redirect to login
    await page.waitForURL('/login')
    await expect(page.getByText('Welcome Back')).toBeVisible()
  })

  test('should handle session expiration', async ({ page }) => {
    // Login
    await page.getByPlaceholder('you@example.com').fill('test@example.com')
    await page.getByPlaceholder('Enter your password').fill('password123')
    await page.getByRole('button', { name: 'Sign In' }).click()
    await page.waitForURL('/dashboard')
    
    // Simulate token expiration by clearing localStorage
    await page.evaluate(() => {
      window.localStorage.removeItem('access_token')
    })
    
    // Try to perform an action that requires auth
    await page.getByPlaceholder('Type your question').fill('Test message')
    await page.getByRole('button', { name: 'Send' }).click()
    
    // Should redirect to login
    await page.waitForURL('/login')
    await expect(page.getByText('Welcome Back')).toBeVisible()
  })
})