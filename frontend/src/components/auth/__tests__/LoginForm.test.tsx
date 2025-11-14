import React from 'react'
import { render, screen, waitFor } from '@/test/test-utils'
import { LoginForm } from '../login-form'
import { server } from '@/test/mocks/server'
import { http, HttpResponse } from 'msw'
import { AuthProvider } from '@/lib/auth-context'

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

// Wrapper component for tests
function LoginFormWrapper() {
  return (
    <AuthProvider>
      <LoginForm />
    </AuthProvider>
  )
}

describe('LoginForm', () => {
  describe('Rendering', () => {
    it('renders login form with all elements', () => {
      render(<LoginFormWrapper />)
      
      expect(screen.getByText(/welcome back/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/email address/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
      expect(screen.getByText(/forgot your password/i)).toBeInTheDocument()
    })

    it('renders with empty input fields initially', () => {
      render(<LoginFormWrapper />)
      
      const emailInput = screen.getByLabelText(/email address/i) as HTMLInputElement
      const passwordInput = screen.getByLabelText(/^password$/i) as HTMLInputElement
      
      expect(emailInput.value).toBe('')
      expect(passwordInput.value).toBe('')
    })

    it('shows password field as password type by default', () => {
      render(<LoginFormWrapper />)
      
      const passwordInput = screen.getByLabelText(/^password$/i) as HTMLInputElement
      expect(passwordInput.type).toBe('password')
    })
  })

  describe('Form Validation', () => {
    it('shows error for invalid email format', async () => {
      const { user } = render(<LoginFormWrapper />)
      
      const emailInput = screen.getByLabelText(/email address/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'invalid-email')
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText(/invalid email address/i)).toBeInTheDocument()
      })
    })

    it('shows error for short password', async () => {
      const { user } = render(<LoginFormWrapper />)
      
      const passwordInput = screen.getByLabelText(/^password$/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(passwordInput, '12345')
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText(/password must be at least 6 characters/i)).toBeInTheDocument()
      })
    })

    it('shows multiple validation errors', async () => {
      const { user } = render(<LoginFormWrapper />)
      
      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'bad')
      await user.type(passwordInput, '123')
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText(/invalid email address/i)).toBeInTheDocument()
        expect(screen.getByText(/password must be at least 6 characters/i)).toBeInTheDocument()
      })
    })

    it('does not submit with empty fields', async () => {
      const { user } = render(<LoginFormWrapper />)
      
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      await user.click(submitButton)
      
      // Should show validation errors
      await waitFor(() => {
        expect(screen.getByText(/invalid email address/i)).toBeInTheDocument()
        expect(screen.getByText(/password must be at least 6 characters/i)).toBeInTheDocument()
      })
      
      // Should not have called the API
      expect(mockPush).not.toHaveBeenCalled()
    })
  })

  describe('Password Visibility Toggle', () => {
    it('toggles password visibility when eye icon is clicked', async () => {
      const { user } = render(<LoginFormWrapper />)
      
      const passwordInput = screen.getByLabelText(/^password$/i) as HTMLInputElement
      const toggleButton = screen.getByLabelText(/show password/i)
      
      // Initially password type
      expect(passwordInput.type).toBe('password')
      
      // Click to show
      await user.click(toggleButton)
      expect(passwordInput.type).toBe('text')
      expect(screen.getByLabelText(/hide password/i)).toBeInTheDocument()
      
      // Click to hide again
      await user.click(screen.getByLabelText(/hide password/i))
      expect(passwordInput.type).toBe('password')
    })

    it('maintains input value when toggling visibility', async () => {
      const { user } = render(<LoginFormWrapper />)
      
      const passwordInput = screen.getByLabelText(/^password$/i) as HTMLInputElement
      const toggleButton = screen.getByLabelText(/show password/i)
      
      await user.type(passwordInput, 'mypassword123')
      await user.click(toggleButton)
      
      expect(passwordInput.value).toBe('mypassword123')
      expect(passwordInput.type).toBe('text')
    })
  })

  describe('Form Submission', () => {
    it('successfully logs in with valid credentials', async () => {
      const { user } = render(<LoginFormWrapper />)
      
      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)
      
      await waitFor(() => {
        // Should store tokens
        expect(localStorage.getItem('access_token')).toBe('mock-access-token')
        expect(localStorage.getItem('refresh_token')).toBe('mock-refresh-token')
        
        // Should redirect to dashboard
        expect(mockPush).toHaveBeenCalledWith('/dashboard')
      })
    })

    it('shows loading state during submission', async () => {
      const { user } = render(<LoginFormWrapper />)
      
      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      
      // Start submission
      await user.click(submitButton)
      
      // Check for loading state immediately
      expect(screen.getByText(/signing in/i)).toBeInTheDocument()
      expect(submitButton).toBeDisabled()
      
      // Wait for completion
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalled()
      })
    })

    it('disables form during submission', async () => {
      const { user } = render(<LoginFormWrapper />)
      
      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)
      
      // Check that button is disabled during submission
      expect(submitButton).toBeDisabled()
      
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalled()
      })
    })
  })

  describe('Error Handling', () => {
    it('shows error message for invalid credentials', async () => {
      server.use(
        http.post('*/api/v1/auth/login', () => {
          return HttpResponse.json(
            { detail: 'Invalid credentials' },
            { status: 401 }
          )
        })
      )
      
      const { user } = render(<LoginFormWrapper />)
      
      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'wrong@example.com')
      await user.type(passwordInput, 'wrongpassword')
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText(/invalid email or password/i)).toBeInTheDocument()
      })
      
      // Should not store tokens or redirect
      expect(localStorage.getItem('access_token')).toBeNull()
      expect(mockPush).not.toHaveBeenCalled()
    })

    it('shows generic error for server errors', async () => {
      server.use(
        http.post('*/api/v1/auth/login', () => {
          return HttpResponse.json(
            { detail: 'Internal server error' },
            { status: 500 }
          )
        })
      )
      
      const { user } = render(<LoginFormWrapper />)
      
      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText(/failed to login/i)).toBeInTheDocument()
      })
    })

    it('handles network errors gracefully', async () => {
      server.use(
        http.post('*/api/v1/auth/login', () => {
          return HttpResponse.error()
        })
      )
      
      const { user } = render(<LoginFormWrapper />)
      
      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText(/failed to login/i)).toBeInTheDocument()
      })
    })

    it('clears previous errors on new submission', async () => {
      // First submission will fail
      server.use(
        http.post('*/api/v1/auth/login', () => {
          return HttpResponse.json(
            { detail: 'Invalid credentials' },
            { status: 401 }
          )
        })
      )
      
      const { user } = render(<LoginFormWrapper />)
      
      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      // First attempt - fail
      await user.type(emailInput, 'wrong@example.com')
      await user.type(passwordInput, 'wrongpassword')
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText(/invalid email or password/i)).toBeInTheDocument()
      })
      
      // Reset handler for success
      server.use(
        http.post('*/api/v1/auth/login', () => {
          return HttpResponse.json({
            access_token: 'mock-access-token',
            refresh_token: 'mock-refresh-token',
            token_type: 'bearer',
            expires_in: 3600,
          })
        })
      )
      
      // Clear and try again
      await user.clear(emailInput)
      await user.clear(passwordInput)
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)
      
      await waitFor(() => {
        // Error should be gone
        expect(screen.queryByText(/invalid email or password/i)).not.toBeInTheDocument()
        expect(mockPush).toHaveBeenCalled()
      })
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA labels', () => {
      render(<LoginFormWrapper />)
      
      expect(screen.getByLabelText(/email address/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
    })

    it('supports keyboard navigation', async () => {
      const { user } = render(<LoginFormWrapper />)
      
      // Tab through form elements
      await user.tab()
      expect(screen.getByLabelText(/email address/i)).toHaveFocus()
      
      await user.tab()
      expect(screen.getByLabelText(/^password$/i)).toHaveFocus()
      
      await user.tab()
      expect(screen.getByLabelText(/show password/i)).toHaveFocus()
      
      await user.tab()
      expect(screen.getByRole('button', { name: /sign in/i })).toHaveFocus()
    })

    it('submits form with Enter key', async () => {
      const { user } = render(<LoginFormWrapper />)
      
      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      
      // Press Enter in password field
      await user.keyboard('{Enter}')
      
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/dashboard')
      })
    })

    it('has proper autocomplete attributes', () => {
      render(<LoginFormWrapper />)
      
      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      
      expect(emailInput).toHaveAttribute('autocomplete', 'email')
      expect(passwordInput).toHaveAttribute('autocomplete', 'current-password')
    })
  })

  describe('Input Behavior', () => {
    it('trims whitespace from email', async () => {
      const { user } = render(<LoginFormWrapper />)
      
      const emailInput = screen.getByLabelText(/email address/i) as HTMLInputElement
      const passwordInput = screen.getByLabelText(/^password$/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, '  test@example.com  ')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/dashboard')
      })
    })

    it('maintains focus after validation error', async () => {
      const { user } = render(<LoginFormWrapper />)
      
      const emailInput = screen.getByLabelText(/email address/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'invalid')
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText(/invalid email address/i)).toBeInTheDocument()
      })
      
      // Input should still be focusable
      await user.click(emailInput)
      expect(emailInput).toHaveFocus()
    })

    it('clears password field after failed login', async () => {
      server.use(
        http.post('*/api/v1/auth/login', () => {
          return HttpResponse.json(
            { detail: 'Invalid credentials' },
            { status: 401 }
          )
        })
      )
      
      const { user } = render(<LoginFormWrapper />)
      
      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i) as HTMLInputElement
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'wrongpassword')
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText(/invalid email or password/i)).toBeInTheDocument()
      })
      
      // Password should be cleared for security
      expect(passwordInput.value).toBe('')
    })
  })
})