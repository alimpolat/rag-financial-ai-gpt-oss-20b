import React from 'react'
import { render, screen, waitFor, fireEvent } from '@/test/test-utils'
import { DocumentUpload } from '../document-upload'
import { server } from '@/test/mocks/server'
import { http, HttpResponse } from 'msw'

// Start MSW server
beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

// Mock file creation helper
const createMockFile = (
  name: string,
  size: number,
  type: string
): File => {
  const file = new File(['test content'], name, { type })
  Object.defineProperty(file, 'size', { value: size })
  return file
}

describe('DocumentUpload', () => {
  describe('Rendering', () => {
    it('renders upload area with instructions', () => {
      render(<DocumentUpload />)
      
      expect(screen.getByText(/drag & drop documents here/i)).toBeInTheDocument()
      expect(screen.getByText(/or click to browse/i)).toBeInTheDocument()
      expect(screen.getByText(/supported formats/i)).toBeInTheDocument()
    })

    it('displays file size limit', () => {
      render(<DocumentUpload />)
      
      expect(screen.getByText(/max file size: 50mb/i)).toBeInTheDocument()
    })

    it('shows upload button when files are selected', async () => {
      const { user } = render(<DocumentUpload />)
      const file = createMockFile('test.pdf', 1024, 'application/pdf')
      
      const input = screen.getByTestId('file-input') as HTMLInputElement
      await user.upload(input, file)
      
      expect(screen.getByRole('button', { name: /upload/i })).toBeInTheDocument()
    })
  })

  describe('File Selection', () => {
    it('accepts valid file types', async () => {
      const { user } = render(<DocumentUpload />)
      const validFiles = [
        createMockFile('test.pdf', 1024, 'application/pdf'),
        createMockFile('test.docx', 1024, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
        createMockFile('test.txt', 1024, 'text/plain'),
      ]
      
      const input = screen.getByTestId('file-input') as HTMLInputElement
      
      for (const file of validFiles) {
        await user.upload(input, file)
        expect(screen.getByText(file.name)).toBeInTheDocument()
        
        // Clear for next test
        const removeButton = screen.getByTestId(`remove-${file.name}`)
        await user.click(removeButton)
      }
    })

    it('rejects invalid file types', async () => {
      const { user } = render(<DocumentUpload />)
      const invalidFile = createMockFile('test.exe', 1024, 'application/x-executable')
      
      const input = screen.getByTestId('file-input') as HTMLInputElement
      await user.upload(input, invalidFile)
      
      expect(screen.getByText(/file type not supported/i)).toBeInTheDocument()
      expect(screen.queryByText('test.exe')).not.toBeInTheDocument()
    })

    it('rejects files exceeding size limit', async () => {
      const { user } = render(<DocumentUpload />)
      const largeFile = createMockFile('large.pdf', 60 * 1024 * 1024, 'application/pdf') // 60MB
      
      const input = screen.getByTestId('file-input') as HTMLInputElement
      await user.upload(input, largeFile)
      
      expect(screen.getByText(/file size exceeds 50mb limit/i)).toBeInTheDocument()
      expect(screen.queryByText('large.pdf')).not.toBeInTheDocument()
    })

    it('allows multiple file selection', async () => {
      const { user } = render(<DocumentUpload />)
      const files = [
        createMockFile('file1.pdf', 1024, 'application/pdf'),
        createMockFile('file2.pdf', 2048, 'application/pdf'),
        createMockFile('file3.pdf', 3072, 'application/pdf'),
      ]
      
      const input = screen.getByTestId('file-input') as HTMLInputElement
      await user.upload(input, files)
      
      files.forEach(file => {
        expect(screen.getByText(file.name)).toBeInTheDocument()
      })
      
      expect(screen.getByText(/3 files selected/i)).toBeInTheDocument()
    })

    it('removes files from selection', async () => {
      const { user } = render(<DocumentUpload />)
      const file = createMockFile('test.pdf', 1024, 'application/pdf')
      
      const input = screen.getByTestId('file-input') as HTMLInputElement
      await user.upload(input, file)
      
      expect(screen.getByText('test.pdf')).toBeInTheDocument()
      
      const removeButton = screen.getByTestId('remove-test.pdf')
      await user.click(removeButton)
      
      expect(screen.queryByText('test.pdf')).not.toBeInTheDocument()
    })
  })

  describe('Drag and Drop', () => {
    it('handles file drop', async () => {
      render(<DocumentUpload />)
      const dropZone = screen.getByTestId('drop-zone')
      const file = createMockFile('dropped.pdf', 1024, 'application/pdf')
      
      // Simulate drag enter
      fireEvent.dragEnter(dropZone)
      expect(dropZone).toHaveClass('drag-active')
      
      // Simulate drop
      fireEvent.drop(dropZone, {
        dataTransfer: {
          files: [file],
          items: [{ kind: 'file', getAsFile: () => file }],
          types: ['Files'],
        },
      })
      
      await waitFor(() => {
        expect(screen.getByText('dropped.pdf')).toBeInTheDocument()
      })
    })

    it('shows visual feedback on drag over', () => {
      render(<DocumentUpload />)
      const dropZone = screen.getByTestId('drop-zone')
      
      fireEvent.dragEnter(dropZone)
      expect(dropZone).toHaveClass('drag-active')
      
      fireEvent.dragLeave(dropZone)
      expect(dropZone).not.toHaveClass('drag-active')
    })

    it('prevents default drag behavior', () => {
      render(<DocumentUpload />)
      const dropZone = screen.getByTestId('drop-zone')
      
      const dragOverEvent = new Event('dragover', { bubbles: true })
      const preventDefaultSpy = jest.spyOn(dragOverEvent, 'preventDefault')
      
      fireEvent(dropZone, dragOverEvent)
      expect(preventDefaultSpy).toHaveBeenCalled()
    })
  })

  describe('Upload Process', () => {
    it('uploads files successfully', async () => {
      const { user } = render(<DocumentUpload />)
      const file = createMockFile('test.pdf', 1024, 'application/pdf')
      
      const input = screen.getByTestId('file-input') as HTMLInputElement
      await user.upload(input, file)
      
      const uploadButton = screen.getByRole('button', { name: /upload/i })
      await user.click(uploadButton)
      
      await waitFor(() => {
        expect(screen.getByText(/upload successful/i)).toBeInTheDocument()
      })
    })

    it('shows progress during upload', async () => {
      const { user } = render(<DocumentUpload />)
      const file = createMockFile('test.pdf', 1024, 'application/pdf')
      
      const input = screen.getByTestId('file-input') as HTMLInputElement
      await user.upload(input, file)
      
      const uploadButton = screen.getByRole('button', { name: /upload/i })
      await user.click(uploadButton)
      
      // Check for progress indicator
      expect(screen.getByRole('progressbar')).toBeInTheDocument()
      
      await waitFor(() => {
        expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
      })
    })

    it('handles upload errors', async () => {
      server.use(
        http.post('*/api/v1/documents/upload', () => {
          return HttpResponse.json(
            { detail: 'Upload failed' },
            { status: 500 }
          )
        })
      )
      
      const { user } = render(<DocumentUpload />)
      const file = createMockFile('test.pdf', 1024, 'application/pdf')
      
      const input = screen.getByTestId('file-input') as HTMLInputElement
      await user.upload(input, file)
      
      const uploadButton = screen.getByRole('button', { name: /upload/i })
      await user.click(uploadButton)
      
      await waitFor(() => {
        expect(screen.getByText(/upload failed/i)).toBeInTheDocument()
      })
    })

    it('disables upload button during processing', async () => {
      const { user } = render(<DocumentUpload />)
      const file = createMockFile('test.pdf', 1024, 'application/pdf')
      
      const input = screen.getByTestId('file-input') as HTMLInputElement
      await user.upload(input, file)
      
      const uploadButton = screen.getByRole('button', { name: /upload/i })
      await user.click(uploadButton)
      
      expect(uploadButton).toBeDisabled()
      
      await waitFor(() => {
        expect(uploadButton).not.toBeDisabled()
      })
    })

    it('clears file list after successful upload', async () => {
      const { user } = render(<DocumentUpload />)
      const file = createMockFile('test.pdf', 1024, 'application/pdf')
      
      const input = screen.getByTestId('file-input') as HTMLInputElement
      await user.upload(input, file)
      
      const uploadButton = screen.getByRole('button', { name: /upload/i })
      await user.click(uploadButton)
      
      await waitFor(() => {
        expect(screen.queryByText('test.pdf')).not.toBeInTheDocument()
      })
    })

    it('uploads multiple files in batch', async () => {
      const { user } = render(<DocumentUpload />)
      const files = [
        createMockFile('file1.pdf', 1024, 'application/pdf'),
        createMockFile('file2.pdf', 2048, 'application/pdf'),
      ]
      
      const input = screen.getByTestId('file-input') as HTMLInputElement
      await user.upload(input, files)
      
      const uploadButton = screen.getByRole('button', { name: /upload/i })
      await user.click(uploadButton)
      
      await waitFor(() => {
        expect(screen.getByText(/2 files uploaded successfully/i)).toBeInTheDocument()
      })
    })
  })

  describe('File Preview', () => {
    it('displays file information', async () => {
      const { user } = render(<DocumentUpload />)
      const file = createMockFile('test.pdf', 1024000, 'application/pdf')
      
      const input = screen.getByTestId('file-input') as HTMLInputElement
      await user.upload(input, file)
      
      expect(screen.getByText('test.pdf')).toBeInTheDocument()
      expect(screen.getByText(/1.00 mb/i)).toBeInTheDocument()
      expect(screen.getByText(/pdf/i)).toBeInTheDocument()
    })

    it('shows appropriate file icons', async () => {
      const { user } = render(<DocumentUpload />)
      const files = [
        createMockFile('test.pdf', 1024, 'application/pdf'),
        createMockFile('test.docx', 1024, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
        createMockFile('test.txt', 1024, 'text/plain'),
      ]
      
      const input = screen.getByTestId('file-input') as HTMLInputElement
      
      for (const file of files) {
        await user.upload(input, file)
        const icon = screen.getByTestId(`icon-${file.name}`)
        expect(icon).toBeInTheDocument()
        
        // Clear for next test
        const removeButton = screen.getByTestId(`remove-${file.name}`)
        await user.click(removeButton)
      }
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA labels', () => {
      render(<DocumentUpload />)
      
      const dropZone = screen.getByTestId('drop-zone')
      expect(dropZone).toHaveAttribute('aria-label', 'File upload drop zone')
      
      const input = screen.getByTestId('file-input')
      expect(input).toHaveAttribute('aria-label', 'Choose files to upload')
    })

    it('announces file selection to screen readers', async () => {
      const { user } = render(<DocumentUpload />)
      const file = createMockFile('test.pdf', 1024, 'application/pdf')
      
      const input = screen.getByTestId('file-input') as HTMLInputElement
      await user.upload(input, file)
      
      const announcement = screen.getByRole('status')
      expect(announcement).toHaveTextContent(/1 file selected/i)
    })

    it('supports keyboard navigation', async () => {
      const { user } = render(<DocumentUpload />)
      
      await user.tab()
      const input = screen.getByTestId('file-input')
      expect(input).toHaveFocus()
      
      // Trigger file selection with Enter key
      await user.keyboard('{Enter}')
      // File dialog would open in real browser
    })

    it('announces upload status', async () => {
      const { user } = render(<DocumentUpload />)
      const file = createMockFile('test.pdf', 1024, 'application/pdf')
      
      const input = screen.getByTestId('file-input') as HTMLInputElement
      await user.upload(input, file)
      
      const uploadButton = screen.getByRole('button', { name: /upload/i })
      await user.click(uploadButton)
      
      await waitFor(() => {
        const status = screen.getByRole('status')
        expect(status).toHaveTextContent(/upload successful/i)
      })
    })
  })

  describe('Error States', () => {
    it('displays multiple validation errors', async () => {
      const { user } = render(<DocumentUpload />)
      const invalidFiles = [
        createMockFile('test.exe', 1024, 'application/x-executable'),
        createMockFile('large.pdf', 60 * 1024 * 1024, 'application/pdf'),
      ]
      
      const input = screen.getByTestId('file-input') as HTMLInputElement
      await user.upload(input, invalidFiles)
      
      expect(screen.getByText(/file type not supported/i)).toBeInTheDocument()
      expect(screen.getByText(/file size exceeds/i)).toBeInTheDocument()
    })

    it('recovers from errors gracefully', async () => {
      server.use(
        http.post('*/api/v1/documents/upload', () => {
          return HttpResponse.json(
            { detail: 'Upload failed' },
            { status: 500 }
          )
        })
      )
      
      const { user } = render(<DocumentUpload />)
      const file = createMockFile('test.pdf', 1024, 'application/pdf')
      
      const input = screen.getByTestId('file-input') as HTMLInputElement
      await user.upload(input, file)
      
      const uploadButton = screen.getByRole('button', { name: /upload/i })
      await user.click(uploadButton)
      
      await waitFor(() => {
        expect(screen.getByText(/upload failed/i)).toBeInTheDocument()
      })
      
      // Should allow retry
      expect(uploadButton).not.toBeDisabled()
      expect(screen.getByText('test.pdf')).toBeInTheDocument()
    })
  })
})