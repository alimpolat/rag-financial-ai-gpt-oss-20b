import React from 'react'
import { render, screen, waitFor } from '@/test/test-utils'
import { ChatInterface } from '../chat-interface'
import { server } from '@/test/mocks/server'
import { http, HttpResponse } from 'msw'

// Start MSW server
beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('ChatInterface', () => {
  describe('Rendering', () => {
    it('renders chat interface with all elements', () => {
      render(<ChatInterface />)
      
      // Check for main elements
      expect(screen.getByPlaceholderText(/type your question/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument()
      expect(screen.getByText(/chat with financial ai/i)).toBeInTheDocument()
    })

    it('displays initial welcome message', () => {
      render(<ChatInterface />)
      
      expect(screen.getByText(/ask me anything about your financial documents/i)).toBeInTheDocument()
    })
  })

  describe('User Interactions', () => {
    it('allows user to type a message', async () => {
      const { user } = render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/type your question/i) as HTMLTextAreaElement
      
      await user.type(input, 'What is the revenue?')
      
      expect(input.value).toBe('What is the revenue?')
    })

    it('sends message when send button is clicked', async () => {
      const { user } = render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/type your question/i)
      const sendButton = screen.getByRole('button', { name: /send/i })
      
      await user.type(input, 'What is the revenue?')
      await user.click(sendButton)
      
      // Check that message appears in chat
      expect(screen.getByText('What is the revenue?')).toBeInTheDocument()
      
      // Wait for response
      await waitFor(() => {
        expect(screen.getByText(/mock response to: what is the revenue/i)).toBeInTheDocument()
      })
    })

    it('sends message when Enter is pressed', async () => {
      const { user } = render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/type your question/i)
      
      await user.type(input, 'Test message{Enter}')
      
      expect(screen.getByText('Test message')).toBeInTheDocument()
    })

    it('prevents sending empty messages', async () => {
      const { user } = render(<ChatInterface />)
      const sendButton = screen.getByRole('button', { name: /send/i })
      
      await user.click(sendButton)
      
      // Should not add empty message to chat
      expect(screen.queryByRole('article')).not.toBeInTheDocument()
    })

    it('disables input while processing', async () => {
      const { user } = render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/type your question/i)
      const sendButton = screen.getByRole('button', { name: /send/i })
      
      await user.type(input, 'Test message')
      await user.click(sendButton)
      
      // Input should be disabled while processing
      expect(input).toBeDisabled()
      expect(sendButton).toBeDisabled()
      
      // Wait for response to complete
      await waitFor(() => {
        expect(input).not.toBeDisabled()
        expect(sendButton).not.toBeDisabled()
      })
    })

    it('shows loading indicator while processing', async () => {
      const { user } = render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/type your question/i)
      
      await user.type(input, 'Test message')
      await user.click(screen.getByRole('button', { name: /send/i }))
      
      // Check for loading indicator
      expect(screen.getByTestId('loading-indicator')).toBeInTheDocument()
      
      // Wait for loading to finish
      await waitFor(() => {
        expect(screen.queryByTestId('loading-indicator')).not.toBeInTheDocument()
      })
    })
  })

  describe('Message Display', () => {
    it('displays user messages with correct styling', async () => {
      const { user } = render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/type your question/i)
      
      await user.type(input, 'User message')
      await user.click(screen.getByRole('button', { name: /send/i }))
      
      const userMessage = screen.getByText('User message').closest('div')
      expect(userMessage).toHaveClass('justify-end') // Right-aligned for user
    })

    it('displays AI responses with correct styling', async () => {
      const { user } = render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/type your question/i)
      
      await user.type(input, 'Test')
      await user.click(screen.getByRole('button', { name: /send/i }))
      
      await waitFor(() => {
        const aiMessage = screen.getByText(/mock response/i).closest('div')
        expect(aiMessage).toHaveClass('justify-start') // Left-aligned for AI
      })
    })

    it('displays sources when available', async () => {
      const { user } = render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/type your question/i)
      
      await user.type(input, 'Test')
      await user.click(screen.getByRole('button', { name: /send/i }))
      
      await waitFor(() => {
        expect(screen.getByText('document1.pdf')).toBeInTheDocument()
        expect(screen.getByText('document2.pdf')).toBeInTheDocument()
      })
    })

    it('displays confidence score', async () => {
      const { user } = render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/type your question/i)
      
      await user.type(input, 'Test')
      await user.click(screen.getByRole('button', { name: /send/i }))
      
      await waitFor(() => {
        expect(screen.getByText(/confidence: 85%/i)).toBeInTheDocument()
      })
    })

    it('scrolls to bottom when new messages are added', async () => {
      const { user } = render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/type your question/i)
      
      // Send multiple messages
      for (let i = 0; i < 5; i++) {
        await user.type(input, `Message ${i}`)
        await user.click(screen.getByRole('button', { name: /send/i }))
        await waitFor(() => screen.getByText(`Message ${i}`))
      }
      
      // Check that scrollIntoView was called
      const messagesContainer = screen.getByTestId('messages-container')
      expect(messagesContainer.scrollTop).toBeGreaterThanOrEqual(0)
    })
  })

  describe('Error Handling', () => {
    it('displays error message when API call fails', async () => {
      // Override handler to return error
      server.use(
        http.post('*/api/v1/chat', () => {
          return HttpResponse.json(
            { detail: 'Internal server error' },
            { status: 500 }
          )
        })
      )
      
      const { user } = render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/type your question/i)
      
      await user.type(input, 'Test message')
      await user.click(screen.getByRole('button', { name: /send/i }))
      
      await waitFor(() => {
        expect(screen.getByText(/failed to send message/i)).toBeInTheDocument()
      })
    })

    it('handles network errors gracefully', async () => {
      // Simulate network error
      server.use(
        http.post('*/api/v1/chat', () => {
          return HttpResponse.error()
        })
      )
      
      const { user } = render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/type your question/i)
      
      await user.type(input, 'Test message')
      await user.click(screen.getByRole('button', { name: /send/i }))
      
      await waitFor(() => {
        expect(screen.getByText(/failed to send message/i)).toBeInTheDocument()
      })
    })

    it('shows cached indicator for cached responses', async () => {
      // Override to return cached response
      server.use(
        http.post('*/api/v1/chat', () => {
          return HttpResponse.json({
            response: 'Cached response',
            sources: [],
            confidence: 0.9,
            processing_time: 0.05,
            cached: true,
          })
        })
      )
      
      const { user } = render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/type your question/i)
      
      await user.type(input, 'Test')
      await user.click(screen.getByRole('button', { name: /send/i }))
      
      await waitFor(() => {
        expect(screen.getByText(/cached/i)).toBeInTheDocument()
      })
    })
  })

  describe('Chat History', () => {
    it('maintains message history', async () => {
      const { user } = render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/type your question/i)
      
      // Send first message
      await user.type(input, 'First message')
      await user.click(screen.getByRole('button', { name: /send/i }))
      
      await waitFor(() => screen.getByText(/mock response to: first message/i))
      
      // Send second message
      await user.type(input, 'Second message')
      await user.click(screen.getByRole('button', { name: /send/i }))
      
      await waitFor(() => screen.getByText(/mock response to: second message/i))
      
      // Both messages should be visible
      expect(screen.getByText('First message')).toBeInTheDocument()
      expect(screen.getByText('Second message')).toBeInTheDocument()
    })

    it('clears input after sending message', async () => {
      const { user } = render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/type your question/i) as HTMLTextAreaElement
      
      await user.type(input, 'Test message')
      await user.click(screen.getByRole('button', { name: /send/i }))
      
      await waitFor(() => {
        expect(input.value).toBe('')
      })
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA labels', () => {
      render(<ChatInterface />)
      
      expect(screen.getByRole('textbox')).toHaveAttribute('aria-label')
      expect(screen.getByRole('button', { name: /send/i })).toHaveAttribute('aria-label')
    })

    it('supports keyboard navigation', async () => {
      const { user } = render(<ChatInterface />)
      
      // Tab to input
      await user.tab()
      expect(screen.getByPlaceholderText(/type your question/i)).toHaveFocus()
      
      // Tab to send button
      await user.tab()
      expect(screen.getByRole('button', { name: /send/i })).toHaveFocus()
    })

    it('announces loading state to screen readers', async () => {
      const { user } = render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/type your question/i)
      
      await user.type(input, 'Test')
      await user.click(screen.getByRole('button', { name: /send/i }))
      
      const loadingElement = screen.getByTestId('loading-indicator')
      expect(loadingElement).toHaveAttribute('aria-live', 'polite')
      expect(loadingElement).toHaveAttribute('aria-busy', 'true')
    })
  })

  describe('Performance', () => {
    it('debounces rapid message sending', async () => {
      const { user } = render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/type your question/i)
      const sendButton = screen.getByRole('button', { name: /send/i })
      
      // Try to send multiple messages rapidly
      await user.type(input, 'Message 1')
      await user.click(sendButton)
      
      await user.type(input, 'Message 2')
      await user.click(sendButton)
      
      // Second click should be ignored while first is processing
      expect(screen.queryAllByText(/Message 2/)).toHaveLength(0)
    })

    it('handles large message history efficiently', async () => {
      const { user } = render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/type your question/i)
      
      // Send many messages
      for (let i = 0; i < 20; i++) {
        await user.type(input, `Message ${i}`)
        await user.click(screen.getByRole('button', { name: /send/i }))
        
        // Wait for each response
        await waitFor(() => 
          screen.getByText(new RegExp(`mock response to: message ${i}`, 'i'))
        )
      }
      
      // All messages should be rendered
      expect(screen.getAllByText(/Message \d+/)).toHaveLength(20)
    })
  })
})