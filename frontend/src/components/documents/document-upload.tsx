'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, File, X, CheckCircle, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { documentsApi } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'
import { formatFileSize } from '@/lib/utils'

interface UploadingFile {
  file: File
  progress: number
  status: 'uploading' | 'success' | 'error'
  error?: string
}

export function DocumentUpload() {
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([])
  const { toast } = useToast()

  const onDrop = useCallback((acceptedFiles: File[]) => {
    // Filter for allowed file types
    const allowedTypes = ['.pdf', '.docx', '.txt', '.html', '.md']
    const validFiles = acceptedFiles.filter(file => {
      const extension = '.' + file.name.split('.').pop()?.toLowerCase()
      return allowedTypes.includes(extension)
    })

    if (validFiles.length !== acceptedFiles.length) {
      toast({
        title: 'Some files were rejected',
        description: 'Only PDF, DOCX, TXT, HTML, and MD files are supported.',
        variant: 'destructive',
      })
    }

    // Add files to uploading state
    const newUploadingFiles = validFiles.map(file => ({
      file,
      progress: 0,
      status: 'uploading' as const,
    }))

    setUploadingFiles(prev => [...prev, ...newUploadingFiles])

    // Upload each file
    newUploadingFiles.forEach(uploadingFile => {
      uploadFile(uploadingFile.file)
    })
  }, [toast])

  const uploadFile = async (file: File) => {
    try {
      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setUploadingFiles(prev =>
          prev.map(uf =>
            uf.file === file && uf.status === 'uploading'
              ? { ...uf, progress: Math.min(uf.progress + Math.random() * 30, 90) }
              : uf
          )
        )
      }, 500)

      const result = await documentsApi.uploadDocument(file)

      clearInterval(progressInterval)

      setUploadingFiles(prev =>
        prev.map(uf =>
          uf.file === file
            ? { ...uf, progress: 100, status: 'success' }
            : uf
        )
      )

      toast({
        title: 'Upload successful',
        description: `${file.name} uploaded and processed successfully. ${result.chunks_created} chunks created.`,
      })

    } catch (error) {
      setUploadingFiles(prev =>
        prev.map(uf =>
          uf.file === file
            ? { 
                ...uf, 
                status: 'error', 
                error: error instanceof Error ? error.message : 'Upload failed' 
              }
            : uf
        )
      )

      toast({
        title: 'Upload failed',
        description: `Failed to upload ${file.name}. Please try again.`,
        variant: 'destructive',
      })
    }
  }

  const removeFile = (file: File) => {
    setUploadingFiles(prev => prev.filter(uf => uf.file !== file))
  }

  const clearCompleted = () => {
    setUploadingFiles(prev => prev.filter(uf => uf.status === 'uploading'))
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'text/html': ['.html'],
      'text/markdown': ['.md'],
    },
    maxSize: 50 * 1024 * 1024, // 50MB
  })

  return (
    <div className="space-y-6">
      {/* Upload Area */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Upload className="h-5 w-5" />
            <span>Upload Financial Documents</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
              isDragActive
                ? 'border-primary bg-primary/5'
                : 'border-muted-foreground/25 hover:border-primary/50'
            }`}
          >
            <input {...getInputProps()} />
            <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            {isDragActive ? (
              <p className="text-lg">Drop the files here...</p>
            ) : (
              <div className="space-y-2">
                <p className="text-lg">Drag & drop files here, or click to select</p>
                <p className="text-sm text-muted-foreground">
                  Supports PDF, DOCX, TXT, HTML, and MD files (up to 50MB)
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Upload Progress */}
      {uploadingFiles.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle>Upload Progress</CardTitle>
            <Button variant="outline" size="sm" onClick={clearCompleted}>
              Clear Completed
            </Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {uploadingFiles.map((uploadingFile, index) => (
                <div key={index} className="flex items-center space-x-3 p-3 border rounded-lg">
                  <File className="h-8 w-8 text-muted-foreground flex-shrink-0" />
                  
                  <div className="flex-1 min-w-0 space-y-1">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium truncate">
                        {uploadingFile.file.name}
                      </p>
                      <span className="text-xs text-muted-foreground">
                        {formatFileSize(uploadingFile.file.size)}
                      </span>
                    </div>
                    
                    {uploadingFile.status === 'uploading' && (
                      <div className="w-full bg-secondary rounded-full h-2">
                        <div
                          className="bg-primary h-2 rounded-full transition-all duration-300"
                          style={{ width: `${uploadingFile.progress}%` }}
                        />
                      </div>
                    )}
                    
                    {uploadingFile.status === 'error' && (
                      <p className="text-xs text-destructive">{uploadingFile.error}</p>
                    )}
                  </div>

                  <div className="flex items-center space-x-2">
                    {uploadingFile.status === 'success' && (
                      <CheckCircle className="h-5 w-5 text-green-600" />
                    )}
                    {uploadingFile.status === 'error' && (
                      <AlertCircle className="h-5 w-5 text-destructive" />
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => removeFile(uploadingFile.file)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Instructions */}
      <Card>
        <CardHeader>
          <CardTitle>Tips for Better Results</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-start space-x-3">
            <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-xs font-medium text-primary">1</span>
            </div>
            <div>
              <h4 className="font-medium">Use high-quality documents</h4>
              <p className="text-sm text-muted-foreground">
                Clear, text-based PDFs work better than scanned images
              </p>
            </div>
          </div>
          
          <div className="flex items-start space-x-3">
            <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-xs font-medium text-primary">2</span>
            </div>
            <div>
              <h4 className="font-medium">Financial documents work best</h4>
              <p className="text-sm text-muted-foreground">
                Annual reports, earnings calls, SEC filings, and financial statements
              </p>
            </div>
          </div>
          
          <div className="flex items-start space-x-3">
            <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-xs font-medium text-primary">3</span>
            </div>
            <div>
              <h4 className="font-medium">Multiple documents</h4>
              <p className="text-sm text-muted-foreground">
                Upload multiple related documents for comprehensive analysis
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
