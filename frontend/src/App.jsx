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

// Create modern poker theme
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#00E5A0', // Mint green
      light: '#33E8B0',
      dark: '#00C088',
      contrastText: '#000000',
    },
    secondary: {
      main: '#FF6B9D', // Pink
      light: '#FF8FB5',
      dark: '#E5527A',
    },
    background: {
      default: '#0A0A0F', // Very dark blue-black
      paper: '#1A1A24', // Slightly lighter dark
    },
    surface: {
      main: '#252530', // Card surfaces
      light: '#2A2A36',
    },
    text: {
      primary: '#FFFFFF',
      secondary: '#B8BCC8',
    },
    success: {
      main: '#00E5A0',
      light: '#33E8B0',
      dark: '#00C088',
    },
    warning: {
      main: '#FFB800',
      light: '#FFC433',
      dark: '#E5A500',
    },
    error: {
      main: '#FF4757',
      light: '#FF6B7A',
      dark: '#E53E3E',
    },
    info: {
      main: '#3FABFF',
      light: '#66BBFF',
      dark: '#2E8BCC',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontWeight: 700,
      letterSpacing: '-0.02em',
    },
    h2: {
      fontWeight: 600,
      letterSpacing: '-0.01em',
    },
    h3: {
      fontWeight: 600,
    },
    h4: {
      fontWeight: 600,
    },
    h5: {
      fontWeight: 500,
    },
    h6: {
      fontWeight: 500,
    },
    body1: {
      lineHeight: 1.6,
    },
    body2: {
      lineHeight: 1.5,
    },
  },
  shape: {
    borderRadius: 12,
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          background: 'linear-gradient(135deg, #0A0A0F 0%, #1A1A24 50%, #252530 100%)',
          minHeight: '100vh',
          backgroundAttachment: 'fixed',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          background: 'linear-gradient(145deg, #1A1A24 0%, #252530 100%)',
          border: '1px solid rgba(255, 255, 255, 0.05)',
          backdropFilter: 'blur(10px)',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          background: 'linear-gradient(145deg, #1A1A24 0%, #252530 100%)',
          border: '1px solid rgba(255, 255, 255, 0.05)',
          backdropFilter: 'blur(10px)',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            transform: 'translateY(-2px)',
            boxShadow: '0 12px 48px rgba(0, 229, 160, 0.15)',
            border: '1px solid rgba(0, 229, 160, 0.2)',
          },
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 500,
          padding: '8px 24px',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        },
        contained: {
          background: 'linear-gradient(135deg, #00E5A0 0%, #00C088 100%)',
          color: '#000000',
          '&:hover': {
            background: 'linear-gradient(135deg, #33E8B0 0%, #00E5A0 100%)',
            transform: 'translateY(-1px)',
            boxShadow: '0 8px 25px rgba(0, 229, 160, 0.3)',
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
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
        },
        head: {
          background: 'rgba(0, 229, 160, 0.08)',
          fontWeight: 600,
          color: '#00E5A0',
        },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: {
          '&:hover': {
            background: 'rgba(0, 229, 160, 0.05)',
          },
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