'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { chatApi } from '@/lib/api'
import { ChatMessage, ChatResponse } from '@/types'
import { useToast } from '@/components/ui/use-toast'
import { formatDate } from '@/lib/utils'

export function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { toast } = useToast()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      message: inputMessage,
      timestamp: new Date().toISOString(),
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsLoading(true)

    try {
      const response: ChatResponse = await chatApi.sendMessage(inputMessage)
      
      const aiMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        message: response.response,
        response: response.response,
        sources: response.sources,
        confidence: response.confidence,
        processing_time: response.processing_time,
        timestamp: new Date().toISOString(),
      }

      setMessages(prev => [...prev, aiMessage])
    } catch (error) {
      console.error('Error sending message:', error)
      toast({
        title: 'Error',
        description: 'Failed to send message. Please try again.',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const clearChat = () => {
    setMessages([])
    toast({
      title: 'Chat Cleared',
      description: 'All messages have been removed.',
    })
  }

  return (
    <Card className="h-[600px] flex flex-col">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <CardTitle className="flex items-center space-x-2">
          <Bot className="h-5 w-5" />
          <span>Financial AI Assistant</span>
        </CardTitle>
        <Button variant="outline" size="sm" onClick={clearChat}>
          Clear Chat
        </Button>
      </CardHeader>
      
      <CardContent className="flex-1 flex flex-col space-y-4">
        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto space-y-4 custom-scrollbar">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
              <Bot className="h-12 w-12 text-muted-foreground" />
              <div>
                <h3 className="text-lg font-semibold">Welcome to RAG Financial AI</h3>
                <p className="text-muted-foreground">
                  Ask questions about your uploaded financial documents
                </p>
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <div key={message.id} className="space-y-2">
                {/* User Message */}
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0">
                    <User className="h-6 w-6 text-primary" />
                  </div>
                  <div className="flex-1 space-y-1">
                    <div className="bg-primary/10 rounded-lg p-3">
                      <p className="text-sm">{message.message}</p>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {formatDate(message.timestamp)}
                    </p>
                  </div>
                </div>

                {/* AI Response */}
                {message.response && (
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0">
                      <Bot className="h-6 w-6 text-green-600" />
                    </div>
                    <div className="flex-1 space-y-2">
                      <div className="bg-secondary rounded-lg p-3">
                        <p className="text-sm whitespace-pre-wrap">{message.response}</p>
                      </div>
                      
                      {/* Sources and Metadata */}
                      {(message.sources?.length || message.confidence !== undefined) && (
                        <div className="text-xs text-muted-foreground space-y-1">
                          {message.confidence !== undefined && (
                            <p>Confidence: {(message.confidence * 100).toFixed(1)}%</p>
                          )}
                          {message.processing_time && (
                            <p>Processing time: {message.processing_time.toFixed(2)}s</p>
                          )}
                          {message.sources && message.sources.length > 0 && (
                            <div>
                              <p className="font-medium">Sources:</p>
                              <ul className="list-disc list-inside">
                                {message.sources.map((source, index) => (
                                  <li key={index} className="truncate">{source}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
          
          {/* Loading Indicator */}
          {isLoading && (
            <div className="flex items-center space-x-3">
              <div className="flex-shrink-0">
                <Bot className="h-6 w-6 text-green-600" />
              </div>
              <div className="flex items-center space-x-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm text-muted-foreground">Processing your question...</span>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t pt-4">
          <div className="flex space-x-2">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask a question about your financial documents..."
              className="flex-1 min-h-[40px] max-h-[120px] px-3 py-2 text-sm border border-input rounded-md bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
              disabled={isLoading}
            />
            <Button
              onClick={handleSendMessage}
              disabled={!inputMessage.trim() || isLoading}
              size="icon"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
