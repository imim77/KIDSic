import { createContext, useContext } from 'react'



export interface FrameControls {
  expanded: boolean
  expand: () => void
}

export const FrameContext = createContext<FrameControls>({ expanded: false, expand: () => {} })


export function useFrameControls() {
  return useContext(FrameContext)
}
