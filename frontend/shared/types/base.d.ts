// region Install ////
export interface IStep {
  action: () => Promise<void>
  caption?: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- install steps keep arbitrary batch results
  data?: Record<string, any>
}
// endregion ////
