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

// Create theme
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
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