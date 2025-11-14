import React, { ReactElement } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import userEvent from '@testing-library/user-event'

// Create a custom render function that includes providers
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  })
}

interface AllTheProvidersProps {
  children: React.ReactNode
}

function AllTheProviders({ children }: AllTheProvidersProps) {
  const queryClient = createTestQueryClient()
  
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => {
  return {
    user: userEvent.setup(),
    ...render(ui, { wrapper: AllTheProviders, ...options })
  }
}

// Re-export everything
export * from '@testing-library/react'
export { customRender as render, userEvent }

// Test data factories
export const createMockUser = (overrides = {}) => ({
  user_id: 'test-user-123',
  email: 'test@example.com',
  full_name: 'Test User',
  roles: ['user'],
  is_active: true,
  created_at: '2024-01-01T00:00:00',
  last_login: '2024-01-02T00:00:00',
  ...overrides,
})

export const createMockDocument = (overrides = {}) => ({
  document_id: 'doc-123',
  filename: 'test.pdf',
  file_size: 1024000,
  upload_timestamp: '2024-01-01T00:00:00',
  status: 'processed',
  page_count: 10,
  chunk_count: 25,
  ...overrides,
})

export const createMockChatMessage = (overrides = {}) => ({
  id: 'msg-123',
  message: 'Test message',
  timestamp: '2024-01-01T00:00:00',
  role: 'user',
  ...overrides,
})

export const createMockChatResponse = (overrides = {}) => ({
  response: 'Test response',
  sources: ['doc1.pdf', 'doc2.pdf'],
  confidence: 0.85,
  processing_time: 1.23,
  cached: false,
  ...overrides,
})