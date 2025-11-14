import { http, HttpResponse } from 'msw'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const handlers = [
  // Auth endpoints
  http.post(`${API_URL}/api/v1/auth/login`, async ({ request }) => {
    const body = await request.json() as any
    
    if (body.email === 'test@example.com' && body.password === 'password123') {
      return HttpResponse.json({
        access_token: 'mock-access-token',
        refresh_token: 'mock-refresh-token',
        token_type: 'bearer',
        expires_in: 3600,
      })
    }
    
    return HttpResponse.json(
      { detail: 'Invalid credentials' },
      { status: 401 }
    )
  }),

  http.get(`${API_URL}/api/v1/auth/me`, () => {
    return HttpResponse.json({
      user_id: 'test-user-123',
      email: 'test@example.com',
      full_name: 'Test User',
      roles: ['user'],
      is_active: true,
      created_at: '2024-01-01T00:00:00',
      last_login: '2024-01-02T00:00:00',
    })
  }),

  // Chat endpoints
  http.post(`${API_URL}/api/v1/chat`, async ({ request }) => {
    const body = await request.json() as any
    
    return HttpResponse.json({
      response: `Mock response to: ${body.message}`,
      sources: ['document1.pdf', 'document2.pdf'],
      confidence: 0.85,
      processing_time: 1.23,
      cached: false,
    })
  }),

  http.get(`${API_URL}/api/v1/chat/history`, () => {
    return HttpResponse.json({
      messages: [
        {
          id: '1',
          message: 'What is revenue?',
          timestamp: '2024-01-01T10:00:00',
          role: 'user',
        },
        {
          id: '2',
          message: 'Revenue is $10M',
          timestamp: '2024-01-01T10:00:05',
          role: 'assistant',
          sources: ['report.pdf'],
          confidence: 0.9,
        },
      ],
    })
  }),

  // Document endpoints
  http.post(`${API_URL}/api/v1/documents/upload`, async ({ request }) => {
    const formData = await request.formData()
    const file = formData.get('file') as File
    
    if (file) {
      return HttpResponse.json({
        message: 'Document uploaded successfully',
        document_id: 'doc-123',
        chunks_created: 10,
        filename: file.name,
        task_id: 'task-456',
      })
    }
    
    return HttpResponse.json(
      { detail: 'No file provided' },
      { status: 400 }
    )
  }),

  http.get(`${API_URL}/api/v1/documents`, () => {
    return HttpResponse.json({
      documents: [
        {
          document_id: 'doc-1',
          filename: 'financial_report.pdf',
          file_size: 1024000,
          upload_timestamp: '2024-01-01T09:00:00',
          status: 'processed',
          page_count: 10,
          chunk_count: 25,
        },
        {
          document_id: 'doc-2',
          filename: 'quarterly_results.docx',
          file_size: 512000,
          upload_timestamp: '2024-01-01T10:00:00',
          status: 'processing',
          page_count: 5,
          chunk_count: 0,
        },
      ],
    })
  }),

  http.delete(`${API_URL}/api/v1/documents/:id`, ({ params }) => {
    return HttpResponse.json({
      message: 'Document deleted successfully',
      document_id: params.id,
    })
  }),

  // Health check
  http.get(`${API_URL}/api/v1/health`, () => {
    return HttpResponse.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      services: {
        database: 'connected',
        vector_store: 'connected',
        ollama: 'connected',
        redis: 'connected',
      },
    })
  }),
]