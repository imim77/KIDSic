import { createContext, useContext } from 'react'

// FrameControls lets children lay out for the expanded frame and enter it
// from their own controls, such as a selected result.
export interface FrameControls {
  expanded: boolean
  expand: () => void
}

export const FrameContext = createContext<FrameControls>({ expanded: false, expand: () => {} })

// useFrameControls reads the nearest FullscreenFrame's state and expand action.
export function useFrameControls() {
  return useContext(FrameContext)
}
