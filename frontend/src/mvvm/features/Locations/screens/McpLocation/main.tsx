import { createRoot } from 'react-dom/client'
import '@/mvvm/tailwind.css'
import { McpLocationApp } from './McpLocationApp'

createRoot(document.getElementById('root')!).render(<McpLocationApp />)
