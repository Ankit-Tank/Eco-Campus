import { useCallback, useEffect, useRef, useState } from 'react'

// Loads data from a service function and tracks loading / error / ready.
//   const { status, data, error, reload } = useApi(() => getSomething(params), [params], { interval: 15000 })
// "interval" (ms) refreshes quietly in the background without showing the loading state again.
export function useApi(fetcher, deps = [], { interval } = {}) {
  const [state, setState] = useState({ status: 'loading', data: null, error: null })
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher
  const latest = useRef(0) // ignore answers that arrive after a newer request started

  const load = useCallback((quiet = false) => {
    const id = ++latest.current
    if (!quiet) setState((s) => ({ ...s, status: 'loading', error: null }))
    return fetcherRef
      .current()
      .then((data) => {
        if (id === latest.current) setState({ status: 'ready', data, error: null })
      })
      .catch((error) => {
        if (id === latest.current && !quiet) setState({ status: 'error', data: null, error })
      })
  }, [])

  useEffect(() => {
    load()
    if (!interval) return undefined
    const timer = setInterval(() => load(true), interval)
    return () => clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, interval, load])

  return { ...state, reload: () => load() }
}
