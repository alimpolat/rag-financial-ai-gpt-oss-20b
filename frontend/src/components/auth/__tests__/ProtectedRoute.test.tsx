import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { ProtectedRoute } from '../protected-route'
import { AuthProvider } from '@/lib/auth-context'
import { server } from '@/test/mocks/server'
import { http, HttpResponse } from 'msw'

// Mock next/navigation
const mockPush = jest.fn()
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: jest.fn(),
    prefetch: jest.fn(),
  }),
}))

// Start MSW server
beforeAll(() => server.listen())
afterEach(() => {
  server.resetHandlers()
  mockPush.mockClear()
  localStorage.clear()
})
afterAll(() => server.close())

// Test component
function TestContent() {
  return <div>Protected Content</div>
}

// Wrapper with AuthProvider
function TestWrapper({ children }: { children: React.ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>
}

describe('ProtectedRoute', () => {
  describe('Loading State', () => {
    it('shows loading indicator while checking authentication', () => {
      render(
        <TestWrapper>
          <ProtectedRoute>
            <TestContent />
          </ProtectedRoute>
        </TestWrapper>
      )
      
      expect(screen.getByText(/loading/i)).toBeInTheDocument()
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    })

    it('shows loading spinner animation', () => {
      render(
        <TestWrapper>
          <ProtectedRoute>
            <TestContent />
          </ProtectedRoute>
        </TestWrapper>
      )
      
      const spinner = screen.getByText(/loading/i).previousElementSibling
      expect(spinner).toHaveClass('animate-spin')
    })
  })

  describe('Authentication Check', () => {
    it('renders children when user is authenticated', async () => {
      localStorage.setItem('access_token', 'valid-token')
      
      render(
        <TestWrapper>
          <ProtectedRoute>
            <TestContent />
          </ProtectedRoute>
        </TestWrapper>
      )
      
      await waitFor(() => {
        expect(screen.getByText('Protected Content')).toBeInTheDocument()
      })
      
      expect(mockPush).not.toHaveBeenCalled()
    })

    it('redirects to login when user is not authenticated', async () => {
      // No token in localStorage
      
      render(
        <TestWrapper>
          <ProtectedRoute>
            <TestContent />
          </ProtectedRoute>
        </TestWrapper>
      )
      
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login')
      })
      
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    })

    it('redirects to custom path when specified', async () => {
      render(
        <TestWrapper>
          <ProtectedRoute redirectTo="/custom-login">
            <TestContent />
          </ProtectedRoute>
        </TestWrapper>
      )
      
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/custom-login')
      })
    })

    it('handles authentication check failure gracefully', async () => {
      localStorage.setItem('access_token', 'invalid-token')
      
      server.use(
        http.get('*/api/v1/auth/me', () => {
          return HttpResponse.json(
            { detail: 'Unauthorized' },
            { status: 401 }
          )
        })
      )
      
      render(
        <TestWrapper>
          <ProtectedRoute>
            <TestContent />
          </ProtectedRoute>
        </TestWrapper>
      )
      
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login')
      })
      
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    })
  })

  describe('Role-Based Access Control', () => {
    it('renders content when user has required role', async () => {
      localStorage.setItem('access_token', 'valid-token')
      
      server.use(
        http.get('*/api/v1/auth/me', () => {
          return HttpResponse.json({
            user_id: 'test-user-123',
            email: 'test@example.com',
            full_name: 'Test User',
            roles: ['user', 'admin'],
            is_active: true,
          })
        })
      )
      
      render(
        <TestWrapper>
          <ProtectedRoute requiredRoles={['admin']}>
            <TestContent />
          </ProtectedRoute>
        </TestWrapper>
      )
      
      await waitFor(() => {
        expect(screen.getByText('Protected Content')).toBeInTheDocument()
      })
      
      expect(mockPush).not.toHaveBeenCalled()
    })

    it('redirects to unauthorized when user lacks required role', async () => {
      localStorage.setItem('access_token', 'valid-token')
      
      server.use(
        http.get('*/api/v1/auth/me', () => {
          return HttpResponse.json({
            user_id: 'test-user-123',
            email: 'test@example.com',
            full_name: 'Test User',
            roles: ['user'],
            is_active: true,
          })
        })
      )
      
      render(
        <TestWrapper>
          <ProtectedRoute requiredRoles={['admin']}>
            <TestContent />
          </ProtectedRoute>
        </TestWrapper>
      )
      
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/unauthorized')
      })
      
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    })

    it('accepts user with any of multiple required roles', async () => {
      localStorage.setItem('access_token', 'valid-token')
      
      server.use(
        http.get('*/api/v1/auth/me', () => {
          return HttpResponse.json({
            user_id: 'test-user-123',
            email: 'test@example.com',
            full_name: 'Test User',
            roles: ['editor'],
            is_active: true,
          })
        })
      )
      
      render(
        <TestWrapper>
          <ProtectedRoute requiredRoles={['admin', 'editor', 'viewer']}>
            <TestContent />
          </ProtectedRoute>
        </TestWrapper>
      )
      
      await waitFor(() => {
        expect(screen.getByText('Protected Content')).toBeInTheDocument()
      })
      
      expect(mockPush).not.toHaveBeenCalled()
    })

    it('allows access when no roles are required', async () => {
      localStorage.setItem('access_token', 'valid-token')
      
      server.use(
        http.get('*/api/v1/auth/me', () => {
          return HttpResponse.json({
            user_id: 'test-user-123',
            email: 'test@example.com',
            full_name: 'Test User',
            roles: [],
            is_active: true,
          })
        })
      )
      
      render(
        <TestWrapper>
          <ProtectedRoute>
            <TestContent />
          </ProtectedRoute>
        </TestWrapper>
      )
      
      await waitFor(() => {
        expect(screen.getByText('Protected Content')).toBeInTheDocument()
      })
    })
  })

  describe('Edge Cases', () => {
    it('handles user with null roles', async () => {
      localStorage.setItem('access_token', 'valid-token')
      
      server.use(
        http.get('*/api/v1/auth/me', () => {
          return HttpResponse.json({
            user_id: 'test-user-123',
            email: 'test@example.com',
            full_name: 'Test User',
            roles: null,
            is_active: true,
          })
        })
      )
      
      render(
        <TestWrapper>
          <ProtectedRoute requiredRoles={['admin']}>
            <TestContent />
          </ProtectedRoute>
        </TestWrapper>
      )
      
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/unauthorized')
      })
    })

    it('handles user with undefined roles', async () => {
      localStorage.setItem('access_token', 'valid-token')
      
      server.use(
        http.get('*/api/v1/auth/me', () => {
          return HttpResponse.json({
            user_id: 'test-user-123',
            email: 'test@example.com',
            full_name: 'Test User',
            is_active: true,
            // roles field missing
          })
        })
      )
      
      render(
        <TestWrapper>
          <ProtectedRoute requiredRoles={['admin']}>
            <TestContent />
          </ProtectedRoute>
        </TestWrapper>
      )
      
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/unauthorized')
      })
    })

    it('handles empty required roles array', async () => {
      localStorage.setItem('access_token', 'valid-token')
      
      render(
        <TestWrapper>
          <ProtectedRoute requiredRoles={[]}>
            <TestContent />
          </ProtectedRoute>
        </TestWrapper>
      )
      
      await waitFor(() => {
        expect(screen.getByText('Protected Content')).toBeInTheDocument()
      })
      
      expect(mockPush).not.toHaveBeenCalledWith('/unauthorized')
    })
  })

  describe('Component Updates', () => {
    it('re-checks authentication when auth state changes', async () => {
      const { rerender } = render(
        <TestWrapper>
          <ProtectedRoute>
            <TestContent />
          </ProtectedRoute>
        </TestWrapper>
      )
      
      // Initially not authenticated
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login')
      })
      
      mockPush.mockClear()
      
      // Simulate authentication
      localStorage.setItem('access_token', 'new-token')
      
      rerender(
        <TestWrapper>
          <ProtectedRoute>
            <TestContent />
          </ProtectedRoute>
        </TestWrapper>
      )
      
      await waitFor(() => {
        expect(screen.queryByText('Protected Content')).toBeInTheDocument()
      })
    })

    it('updates when required roles change', async () => {
      localStorage.setItem('access_token', 'valid-token')
      
      server.use(
        http.get('*/api/v1/auth/me', () => {
          return HttpResponse.json({
            user_id: 'test-user-123',
            email: 'test@example.com',
            full_name: 'Test User',
            roles: ['user'],
            is_active: true,
          })
        })
      )
      
      const { rerender } = render(
        <TestWrapper>
          <ProtectedRoute requiredRoles={['user']}>
            <TestContent />
          </ProtectedRoute>
        </TestWrapper>
      )
      
      await waitFor(() => {
        expect(screen.getByText('Protected Content')).toBeInTheDocument()
      })
      
      // Change required roles
      rerender(
        <TestWrapper>
          <ProtectedRoute requiredRoles={['admin']}>
            <TestContent />
          </ProtectedRoute>
        </TestWrapper>
      )
      
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/unauthorized')
      })
    })
  })

  describe('Multiple Protected Routes', () => {
    it('handles multiple protected routes independently', async () => {
      localStorage.setItem('access_token', 'valid-token')
      
      server.use(
        http.get('*/api/v1/auth/me', () => {
          return HttpResponse.json({
            user_id: 'test-user-123',
            email: 'test@example.com',
            full_name: 'Test User',
            roles: ['user'],
            is_active: true,
          })
        })
      )
      
      render(
        <TestWrapper>
          <div>
            <ProtectedRoute>
              <div>Content 1</div>
            </ProtectedRoute>
            <ProtectedRoute requiredRoles={['admin']}>
              <div>Admin Content</div>
            </ProtectedRoute>
            <ProtectedRoute requiredRoles={['user']}>
              <div>User Content</div>
            </ProtectedRoute>
          </div>
        </TestWrapper>
      )
      
      await waitFor(() => {
        expect(screen.getByText('Content 1')).toBeInTheDocument()
        expect(screen.getByText('User Content')).toBeInTheDocument()
        expect(screen.queryByText('Admin Content')).not.toBeInTheDocument()
      })
    })
  })

  describe('Cleanup', () => {
    it('does not cause memory leaks on unmount', async () => {
      localStorage.setItem('access_token', 'valid-token')
      
      const { unmount } = render(
        <TestWrapper>
          <ProtectedRoute>
            <TestContent />
          </ProtectedRoute>
        </TestWrapper>
      )
      
      await waitFor(() => {
        expect(screen.getByText('Protected Content')).toBeInTheDocument()
      })
      
      unmount()
      
      // Should not throw or cause issues
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    })
  })
})