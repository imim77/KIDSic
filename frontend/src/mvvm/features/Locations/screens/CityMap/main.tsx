import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@/mvvm/tailwind.css'
import { CityMapApp } from './CityMapApp'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <CityMapApp />
  </StrictMode>,
)
