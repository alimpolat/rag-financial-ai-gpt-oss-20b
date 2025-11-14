export interface ChatMessage {
  id: string
  message: string
  response?: string
  sources?: string[]
  confidence?: number
  processing_time?: number
  timestamp: string
  isLoading?: boolean
}

export interface Document {
  document_id: string
  filename: string
  source: string
  file_type: string
  created_at: string
  chunk_count: number
}

export interface DocumentChunk {
  id: string
  content: string
  metadata: {
    document_id: string
    source: string
    chunk_index: number
    filename: string
    file_type: string
    created_at: string
  }
}

export interface ChatResponse {
  response: string
  sources: string[]
  confidence: number
  processing_time: number
  conversation_id?: string
}

export interface UploadResponse {
  message: string
  document_id: string
  chunks_created: number
  filename: string
}

export interface HealthStatus {
  status: string
  timestamp: string
  version: string
  service: string
  components?: {
    api: string
    vector_db: string
    ai_model: string
  }
}
