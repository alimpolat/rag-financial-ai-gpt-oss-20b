'use client'

import { useState } from 'react'
import { Header } from '@/components/layout/header'
import { ChatInterface } from '@/components/chat/chat-interface'
import { DocumentUpload } from '@/components/documents/document-upload'
import { DocumentList } from '@/components/documents/document-list'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export default function HomePage() {
  const [activeTab, setActiveTab] = useState('chat')

  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      <main className="container mx-auto px-4 py-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-foreground mb-4">
              RAG Financial AI Assistant
            </h1>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Upload financial documents and get intelligent insights powered by GPT-OSS:20B
            </p>
          </div>

          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="chat">AI Chat</TabsTrigger>
              <TabsTrigger value="upload">Upload Documents</TabsTrigger>
              <TabsTrigger value="documents">Manage Documents</TabsTrigger>
            </TabsList>

            <TabsContent value="chat" className="mt-6">
              <ChatInterface />
            </TabsContent>

            <TabsContent value="upload" className="mt-6">
              <DocumentUpload />
            </TabsContent>

            <TabsContent value="documents" className="mt-6">
              <DocumentList />
            </TabsContent>
          </Tabs>
        </div>
      </main>
    </div>
  )
}
