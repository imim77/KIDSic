// reducedMotion treats a missing matchMedia as reduced motion, so tests and
// odd hosts see the final state at once.
export function reducedMotion() {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? true
}
