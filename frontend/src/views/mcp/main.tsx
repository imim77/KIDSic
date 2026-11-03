import { createRoot } from 'react-dom/client'
import '../../shared/theme.css'
import '../welcome/welcome.css'
import { McpLocationApp } from './McpLocationApp'

createRoot(document.getElementById('root')!).render(<McpLocationApp />)
