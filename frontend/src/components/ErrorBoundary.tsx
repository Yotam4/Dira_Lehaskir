import { Component, type ReactNode } from 'react'

interface Props { children: ReactNode }
interface State { error: Error | null }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    console.error('DiraScan render error:', error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', flexDirection: 'column', gap: 12, color: '#374151' }}>
          <div style={{ fontSize: 18, fontWeight: 700 }}>שגיאה בטעינת האפליקציה</div>
          <div style={{ fontSize: 13, color: '#6b7280' }}>{this.state.error.message}</div>
          <button
            onClick={() => window.location.reload()}
            style={{ marginTop: 8, padding: '8px 20px', background: '#1d4ed8', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600 }}
          >
            רענן דף
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
