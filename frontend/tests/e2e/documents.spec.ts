import { test, expect } from '@playwright/test'
import path from 'path'

test.describe('Document Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login')
    await page.getByPlaceholder('you@example.com').fill('test@example.com')
    await page.getByPlaceholder('Enter your password').fill('password123')
    await page.getByRole('button', { name: 'Sign In' }).click()
    await page.waitForURL('/dashboard')
    
    // Navigate to documents section
    await page.getByRole('link', { name: 'Documents' }).click()
  })

  test('should display document upload interface', async ({ page }) => {
    await expect(page.getByText('Drag & drop documents here')).toBeVisible()
    await expect(page.getByText('or click to browse')).toBeVisible()
    await expect(page.getByText('Supported formats: PDF, DOCX, TXT')).toBeVisible()
    await expect(page.getByText('Max file size: 50MB')).toBeVisible()
  })

  test('should upload a document via file selection', async ({ page }) => {
    // Create a test file
    const fileInput = page.locator('input[type="file"]')
    
    // Set the file
    await fileInput.setInputFiles({
      name: 'test-document.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('PDF test content')
    })
    
    // File should appear in preview
    await expect(page.getByText('test-document.pdf')).toBeVisible()
    await expect(page.getByText(/\d+\.\d+ KB/)).toBeVisible()
    
    // Upload button should appear
    const uploadButton = page.getByRole('button', { name: 'Upload' })
    await expect(uploadButton).toBeVisible()
    
    // Click upload
    await uploadButton.click()
    
    // Progress indicator should appear
    await expect(page.getByRole('progressbar')).toBeVisible()
    
    // Success message should appear
    await expect(page.getByText(/Upload successful|Document uploaded/)).toBeVisible({
      timeout: 10000
    })
  })

  test('should handle drag and drop upload', async ({ page }) => {
    // Get drop zone
    const dropZone = page.getByTestId('drop-zone')
    
    // Create DataTransfer
    const dataTransfer = await page.evaluateHandle(() => new DataTransfer())
    
    // Create file
    await page.evaluateHandle(
      ([dt]) => {
        const file = new File(['Test content'], 'dropped-file.txt', { type: 'text/plain' })
        dt.items.add(file)
      },
      [dataTransfer]
    )
    
    // Simulate drag and drop
    await dropZone.dispatchEvent('dragenter', { dataTransfer })
    await expect(dropZone).toHaveClass(/drag-active/)
    
    await dropZone.dispatchEvent('drop', { dataTransfer })
    
    // File should appear
    await expect(page.getByText('dropped-file.txt')).toBeVisible()
  })

  test('should validate file types', async ({ page }) => {
    const fileInput = page.locator('input[type="file"]')
    
    // Try to upload invalid file type
    await fileInput.setInputFiles({
      name: 'invalid.exe',
      mimeType: 'application/x-executable',
      buffer: Buffer.from('EXE content')
    })
    
    // Error message should appear
    await expect(page.getByText(/File type not supported/)).toBeVisible()
    
    // File should not be in preview
    await expect(page.getByText('invalid.exe')).not.toBeVisible()
  })

  test('should validate file size', async ({ page }) => {
    const fileInput = page.locator('input[type="file"]')
    
    // Create large file (60MB)
    const largeBuffer = Buffer.alloc(60 * 1024 * 1024)
    
    await fileInput.setInputFiles({
      name: 'large-file.pdf',
      mimeType: 'application/pdf',
      buffer: largeBuffer
    })
    
    // Error message should appear
    await expect(page.getByText(/File size exceeds 50MB limit/)).toBeVisible()
    
    // File should not be in preview
    await expect(page.getByText('large-file.pdf')).not.toBeVisible()
  })

  test('should handle multiple file selection', async ({ page }) => {
    const fileInput = page.locator('input[type="file"]')
    
    // Upload multiple files
    await fileInput.setInputFiles([
      {
        name: 'file1.pdf',
        mimeType: 'application/pdf',
        buffer: Buffer.from('PDF 1')
      },
      {
        name: 'file2.txt',
        mimeType: 'text/plain',
        buffer: Buffer.from('Text file')
      },
      {
        name: 'file3.docx',
        mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        buffer: Buffer.from('DOCX content')
      }
    ])
    
    // All files should appear
    await expect(page.getByText('file1.pdf')).toBeVisible()
    await expect(page.getByText('file2.txt')).toBeVisible()
    await expect(page.getByText('file3.docx')).toBeVisible()
    
    // File count should be displayed
    await expect(page.getByText('3 files selected')).toBeVisible()
  })

  test('should remove files from selection', async ({ page }) => {
    const fileInput = page.locator('input[type="file"]')
    
    // Add files
    await fileInput.setInputFiles([
      {
        name: 'file1.pdf',
        mimeType: 'application/pdf',
        buffer: Buffer.from('PDF 1')
      },
      {
        name: 'file2.pdf',
        mimeType: 'application/pdf',
        buffer: Buffer.from('PDF 2')
      }
    ])
    
    // Files should appear
    await expect(page.getByText('file1.pdf')).toBeVisible()
    await expect(page.getByText('file2.pdf')).toBeVisible()
    
    // Remove first file
    await page.getByTestId('remove-file1.pdf').click()
    
    // First file should be removed
    await expect(page.getByText('file1.pdf')).not.toBeVisible()
    await expect(page.getByText('file2.pdf')).toBeVisible()
  })

  test('should display existing documents', async ({ page }) => {
    // Mock API to return documents
    await page.route('**/api/v1/documents', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          documents: [
            {
              document_id: 'doc-1',
              filename: 'financial_report.pdf',
              file_size: 1024000,
              upload_timestamp: '2024-01-01T09:00:00',
              status: 'processed',
              page_count: 10,
              chunk_count: 25
            },
            {
              document_id: 'doc-2',
              filename: 'quarterly_results.docx',
              file_size: 512000,
              upload_timestamp: '2024-01-01T10:00:00',
              status: 'processing',
              page_count: 5,
              chunk_count: 0
            }
          ]
        })
      })
    })
    
    // Refresh to load documents
    await page.reload()
    
    // Documents should be displayed
    await expect(page.getByText('financial_report.pdf')).toBeVisible()
    await expect(page.getByText('quarterly_results.docx')).toBeVisible()
    
    // Status badges should be visible
    await expect(page.getByText('Processed')).toBeVisible()
    await expect(page.getByText('Processing')).toBeVisible()
  })

  test('should delete documents', async ({ page }) => {
    // Ensure document exists
    await page.route('**/api/v1/documents', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          documents: [{
            document_id: 'doc-1',
            filename: 'to_delete.pdf',
            file_size: 1024000,
            status: 'processed'
          }]
        })
      })
    })
    
    await page.reload()
    await expect(page.getByText('to_delete.pdf')).toBeVisible()
    
    // Click delete button
    await page.getByTestId('delete-doc-1').click()
    
    // Confirm deletion
    await page.getByRole('button', { name: 'Confirm' }).click()
    
    // Document should be removed
    await expect(page.getByText('to_delete.pdf')).not.toBeVisible()
    await expect(page.getByText('Document deleted successfully')).toBeVisible()
  })

  test('should search documents', async ({ page }) => {
    // Mock documents
    await page.route('**/api/v1/documents', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          documents: [
            { document_id: '1', filename: 'revenue_2024.pdf', status: 'processed' },
            { document_id: '2', filename: 'expenses_2024.pdf', status: 'processed' },
            { document_id: '3', filename: 'budget_2023.pdf', status: 'processed' }
          ]
        })
      })
    })
    
    await page.reload()
    
    // All documents should be visible initially
    await expect(page.getByText('revenue_2024.pdf')).toBeVisible()
    await expect(page.getByText('expenses_2024.pdf')).toBeVisible()
    await expect(page.getByText('budget_2023.pdf')).toBeVisible()
    
    // Search for '2024'
    await page.getByPlaceholder('Search documents...').fill('2024')
    
    // Only 2024 documents should be visible
    await expect(page.getByText('revenue_2024.pdf')).toBeVisible()
    await expect(page.getByText('expenses_2024.pdf')).toBeVisible()
    await expect(page.getByText('budget_2023.pdf')).not.toBeVisible()
  })

  test('should handle upload errors gracefully', async ({ page }) => {
    const fileInput = page.locator('input[type="file"]')
    
    // Mock upload failure
    await page.route('**/api/v1/documents/upload', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Upload failed' })
      })
    })
    
    // Try to upload
    await fileInput.setInputFiles({
      name: 'test.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('PDF content')
    })
    
    await page.getByRole('button', { name: 'Upload' }).click()
    
    // Error message should appear
    await expect(page.getByText(/Upload failed/)).toBeVisible()
    
    // Should allow retry
    const uploadButton = page.getByRole('button', { name: 'Upload' })
    await expect(uploadButton).toBeEnabled()
  })
})