import React, { useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'

// Pages
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import HandHistorySearch from './pages/HandHistorySearch'
import BettingVsStrength from './pages/BettingVsStrength'
import AdvancedComparison from './pages/AdvancedComparison'
import Layout from './components/Layout'

// Create dark theme with anti-fraud professional look
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#00d4ff',
      light: '#4de3ff',
      dark: '#00a8cc',
    },
    secondary: {
      main: '#ff4757',
      light: '#ff6b7a',
      dark: '#cc3545',
    },
    success: {
      main: '#00ff88',
      light: '#4dffaa',
      dark: '#00cc6a',
    },
    warning: {
      main: '#ffa502',
      light: '#ffb94d',
      dark: '#cc8400',
    },
    error: {
      main: '#ff3838',
      light: '#ff6b6b',
      dark: '#cc2d2d',
    },
    background: {
      default: '#0a0e1a',
      paper: '#111827',
    },
    text: {
      primary: '#e4e6eb',
      secondary: '#b0b3b8',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontWeight: 700,
      letterSpacing: '-0.02em',
    },
    h2: {
      fontWeight: 700,
      letterSpacing: '-0.01em',
    },
    h3: {
      fontWeight: 600,
    },
    h4: {
      fontWeight: 600,
    },
    h5: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 600,
    },
    button: {
      textTransform: 'none',
      fontWeight: 500,
    },
  },
  shape: {
    borderRadius: 12,
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          backgroundColor: '#111827',
          border: '1px solid rgba(255, 255, 255, 0.05)',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          backgroundColor: '#111827',
          border: '1px solid rgba(255, 255, 255, 0.05)',
          boxShadow: '0 4px 24px rgba(0, 0, 0, 0.4)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          boxShadow: 'none',
          '&:hover': {
            boxShadow: '0 4px 12px rgba(0, 212, 255, 0.3)',
          },
        },
        contained: {
          background: 'linear-gradient(135deg, #00d4ff 0%, #00a8cc 100%)',
          '&:hover': {
            background: 'linear-gradient(135deg, #4de3ff 0%, #00d4ff 100%)',
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 6,
          fontWeight: 500,
        },
      },
    },
  },
})

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(
    () => localStorage.getItem('authToken') !== null
  )

  const handleLogin = (token) => {
    // Spara token i localStorage eller state management
    localStorage.setItem('authToken', token)
    setIsAuthenticated(true)
  }

  const handleLogout = () => {
    localStorage.removeItem('authToken')
    setIsAuthenticated(false)
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Routes>
        <Route 
          path="/login" 
          element={
            isAuthenticated ? 
              <Navigate to="/" /> : 
              <Login onLogin={handleLogin} />
          } 
        />
        
        <Route
          path="/"
          element={
            isAuthenticated ? 
              <Layout onLogout={handleLogout} /> : 
              <Navigate to="/login" />
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="hands" element={<HandHistorySearch />} />
          <Route path="betting-analysis" element={<BettingVsStrength />} />
          <Route path="advanced-comparison" element={<AdvancedComparison />} />
        </Route>
      </Routes>
    </ThemeProvider>
  )
}

export default App 