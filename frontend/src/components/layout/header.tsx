'use client'

import { useState } from 'react'
import { Brain, Menu, X } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          {/* Logo and Title */}
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
              <Brain className="h-8 w-8 text-primary" />
              <div className="hidden sm:block">
                <h1 className="text-xl font-bold text-foreground">RAG Financial AI</h1>
                <p className="text-xs text-muted-foreground">GPT-OSS:20B Powered</p>
              </div>
            </div>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-6">
            <a href="#chat" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
              AI Chat
            </a>
            <a href="#upload" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
              Upload
            </a>
            <a href="#documents" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
              Documents
            </a>
            <div className="w-px h-6 bg-border" />
            <Button variant="outline" size="sm">
              <Brain className="h-4 w-4 mr-2" />
              API Status
            </Button>
          </nav>

          {/* Mobile Menu Button */}
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
          >
            {isMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </Button>
        </div>

        {/* Mobile Navigation */}
        {isMenuOpen && (
          <div className="md:hidden border-t bg-background">
            <nav className="flex flex-col space-y-4 p-4">
              <a href="#chat" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                AI Chat
              </a>
              <a href="#upload" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Upload Documents
              </a>
              <a href="#documents" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Manage Documents
              </a>
              <Button variant="outline" size="sm" className="w-fit">
                <Brain className="h-4 w-4 mr-2" />
                API Status
              </Button>
            </nav>
          </div>
        )}
      </div>
    </header>
  )
}
