'use client'

import { useState, useEffect } from 'react'
import { FileText, Trash2, Eye, Calendar, Hash } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { documentsApi } from '@/lib/api'
import { Document } from '@/types'
import { useToast } from '@/components/ui/use-toast'
import { formatDate, formatFileSize } from '@/lib/utils'

export function DocumentList() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set())
  const { toast } = useToast()

  useEffect(() => {
    loadDocuments()
  }, [])

  const loadDocuments = async () => {
    try {
      setLoading(true)
      const response = await documentsApi.listDocuments()
      setDocuments(response.documents || [])
    } catch (error) {
      console.error('Error loading documents:', error)
      toast({
        title: 'Error',
        description: 'Failed to load documents. Please try again.',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (documentId: string) => {
    if (!confirm('Are you sure you want to delete this document? This action cannot be undone.')) {
      return
    }

    try {
      setDeletingIds(prev => new Set(prev).add(documentId))
      await documentsApi.deleteDocument(documentId)
      setDocuments(prev => prev.filter(doc => doc.document_id !== documentId))
      toast({
        title: 'Document deleted',
        description: 'The document has been successfully removed.',
      })
    } catch (error) {
      console.error('Error deleting document:', error)
      toast({
        title: 'Delete failed',
        description: 'Failed to delete the document. Please try again.',
        variant: 'destructive',
      })
    } finally {
      setDeletingIds(prev => {
        const newSet = new Set(prev)
        newSet.delete(documentId)
        return newSet
      })
    }
  }

  const getFileIcon = (fileType: string) => {
    switch (fileType) {
      case '.pdf':
        return <FileText className="h-8 w-8 text-red-600" />
      case '.docx':
        return <FileText className="h-8 w-8 text-blue-600" />
      case '.txt':
        return <FileText className="h-8 w-8 text-gray-600" />
      case '.html':
        return <FileText className="h-8 w-8 text-orange-600" />
      case '.md':
        return <FileText className="h-8 w-8 text-green-600" />
      default:
        return <FileText className="h-8 w-8 text-muted-foreground" />
    }
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Documents</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-32">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2"></div>
              <p className="text-sm text-muted-foreground">Loading documents...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle>Uploaded Documents</CardTitle>
          <Button variant="outline" size="sm" onClick={loadDocuments}>
            Refresh
          </Button>
        </CardHeader>
        <CardContent>
          {documents.length === 0 ? (
            <div className="text-center py-8">
              <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
              <h3 className="text-lg font-semibold mb-2">No documents uploaded</h3>
              <p className="text-muted-foreground">
                Upload some financial documents to get started with AI analysis.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {documents.map((document) => (
                <div
                  key={document.document_id}
                  className="flex items-center space-x-4 p-4 border rounded-lg hover:bg-secondary/50 transition-colors"
                >
                  {/* File Icon */}
                  <div className="flex-shrink-0">
                    {getFileIcon(document.file_type)}
                  </div>

                  {/* Document Info */}
                  <div className="flex-1 min-w-0 space-y-1">
                    <h4 className="font-medium truncate">{document.filename}</h4>
                    <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                      <div className="flex items-center space-x-1">
                        <Calendar className="h-4 w-4" />
                        <span>{formatDate(document.created_at)}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <Hash className="h-4 w-4" />
                        <span>{document.chunk_count} chunks</span>
                      </div>
                      <span className="uppercase font-mono text-xs bg-secondary px-2 py-1 rounded">
                        {document.file_type.replace('.', '')}
                      </span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => {
                        // TODO: Implement view chunks functionality
                        toast({
                          title: 'Feature coming soon',
                          description: 'Document chunk viewing will be available in the next update.',
                        })
                      }}
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => handleDelete(document.document_id)}
                      disabled={deletingIds.has(document.document_id)}
                    >
                      {deletingIds.has(document.document_id) ? (
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Statistics */}
      {documents.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Statistics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-primary">
                  {documents.length}
                </div>
                <p className="text-sm text-muted-foreground">Total Documents</p>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-primary">
                  {documents.reduce((sum, doc) => sum + doc.chunk_count, 0)}
                </div>
                <p className="text-sm text-muted-foreground">Total Chunks</p>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-primary">
                  {new Set(documents.map(doc => doc.file_type)).size}
                </div>
                <p className="text-sm text-muted-foreground">File Types</p>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-primary">
                  {Math.round(documents.reduce((sum, doc) => sum + doc.chunk_count, 0) / documents.length)}
                </div>
                <p className="text-sm text-muted-foreground">Avg. Chunks</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
