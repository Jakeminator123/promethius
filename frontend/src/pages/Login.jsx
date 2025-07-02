import React, { useState } from 'react'
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Alert,
  Container,
  IconButton,
  InputAdornment,
  alpha,
} from '@mui/material'
import {
  Visibility,
  VisibilityOff,
  Shield as ShieldIcon,
  Security as SecurityIcon,
} from '@mui/icons-material'
import { motion } from 'framer-motion'
import axios from 'axios'

function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await axios.post('/api/login', {
        username,
        password,
      })

      if (response.data.success) {
        onLogin(response.data.token)
      } else {
        setError(response.data.message || 'Authentication failed')
      }
    } catch (err) {
      setError('Could not connect to server')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container component="main" maxWidth="xs">
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          style={{ width: '100%' }}
        >
          <Paper 
            elevation={0} 
            sx={{ 
              padding: 4, 
              width: '100%',
              background: 'linear-gradient(135deg, rgba(17, 24, 39, 0.9) 0%, rgba(17, 24, 39, 0.7) 100%)',
              backdropFilter: 'blur(20px)',
              border: '1px solid rgba(0, 212, 255, 0.2)',
              borderRadius: 3,
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
            }}
          >
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mb: 4 }}>
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
              >
                <Box
                  sx={{
                    p: 2,
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, #00d4ff 0%, #00a8cc 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    mb: 2,
                    boxShadow: '0 8px 32px rgba(0, 212, 255, 0.4)',
                  }}
                >
                  <ShieldIcon sx={{ fontSize: 48, color: 'white' }} />
                </Box>
              </motion.div>
              
              <Typography 
                component="h1" 
                variant="h4" 
                align="center"
                sx={{
                  fontWeight: 700,
                  background: 'linear-gradient(135deg, #00d4ff 0%, #00ff88 100%)',
                  backgroundClip: 'text',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  mb: 1,
                }}
              >
                PokerGuard AI
              </Typography>
              <Typography 
                variant="subtitle1" 
                align="center" 
                sx={{ 
                  color: 'text.secondary',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                }}
              >
                <SecurityIcon sx={{ fontSize: 18 }} />
                Anti-Fraud Analytics Platform
              </Typography>
            </Box>

            {error && (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.3 }}
              >
                <Alert 
                  severity="error" 
                  sx={{ 
                    mb: 2,
                    backgroundColor: alpha('#ff4757', 0.1),
                    color: '#ff4757',
                    border: '1px solid rgba(255, 71, 87, 0.3)',
                  }}
                >
                  {error}
                </Alert>
              </motion.div>
            )}

            <Box component="form" onSubmit={handleSubmit}>
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 }}
              >
                <TextField
                  margin="normal"
                  required
                  fullWidth
                  id="username"
                  label="Username"
                  name="username"
                  autoComplete="username"
                  autoFocus
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      '& fieldset': {
                        borderColor: 'rgba(255, 255, 255, 0.2)',
                      },
                      '&:hover fieldset': {
                        borderColor: '#00d4ff',
                      },
                      '&.Mui-focused fieldset': {
                        borderColor: '#00d4ff',
                      },
                    },
                    '& .MuiInputLabel-root': {
                      color: 'text.secondary',
                      '&.Mui-focused': {
                        color: '#00d4ff',
                      },
                    },
                  }}
                />
              </motion.div>
              
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.4 }}
              >
                <TextField
                  margin="normal"
                  required
                  fullWidth
                  name="password"
                  label="Password"
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          onClick={() => setShowPassword(!showPassword)}
                          edge="end"
                          sx={{ color: 'text.secondary' }}
                        >
                          {showPassword ? <VisibilityOff /> : <Visibility />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      '& fieldset': {
                        borderColor: 'rgba(255, 255, 255, 0.2)',
                      },
                      '&:hover fieldset': {
                        borderColor: '#00d4ff',
                      },
                      '&.Mui-focused fieldset': {
                        borderColor: '#00d4ff',
                      },
                    },
                    '& .MuiInputLabel-root': {
                      color: 'text.secondary',
                      '&.Mui-focused': {
                        color: '#00d4ff',
                      },
                    },
                  }}
                />
              </motion.div>
              
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
              >
                <Button
                  type="submit"
                  fullWidth
                  variant="contained"
                  sx={{ 
                    mt: 3, 
                    mb: 2,
                    py: 1.5,
                    background: loading 
                      ? 'rgba(255, 255, 255, 0.1)'
                      : 'linear-gradient(135deg, #00d4ff 0%, #00a8cc 100%)',
                    '&:hover': {
                      background: loading
                        ? 'rgba(255, 255, 255, 0.1)'
                        : 'linear-gradient(135deg, #4de3ff 0%, #00d4ff 100%)',
                    },
                    fontWeight: 600,
                    fontSize: '1rem',
                    boxShadow: loading
                      ? 'none'
                      : '0 4px 24px rgba(0, 212, 255, 0.4)',
                    transition: 'all 0.3s ease',
                  }}
                  disabled={loading}
                >
                  {loading ? (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                      >
                        <SecurityIcon />
                      </motion.div>
                      Authenticating...
                    </Box>
                  ) : (
                    'Sign In'
                  )}
                </Button>
              </motion.div>
            </Box>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6 }}
            >
              <Typography 
                variant="body2" 
                sx={{ 
                  color: 'text.secondary', 
                  textAlign: 'center',
                  mt: 2,
                  p: 2,
                  borderRadius: 1,
                  backgroundColor: alpha('#00d4ff', 0.05),
                  border: '1px solid rgba(0, 212, 255, 0.1)',
                }}
              >
                Demo credentials: <strong>test/test</strong>
              </Typography>
            </motion.div>
          </Paper>
        </motion.div>

        {/* Background decoration */}
        <Box
          sx={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: -1,
            overflow: 'hidden',
            '&::before': {
              content: '""',
              position: 'absolute',
              top: '-50%',
              left: '-50%',
              width: '200%',
              height: '200%',
              background: 'radial-gradient(ellipse at center, rgba(0, 212, 255, 0.1) 0%, transparent 70%)',
              animation: 'pulse 10s ease-in-out infinite',
            },
            '&::after': {
              content: '""',
              position: 'absolute',
              bottom: '-50%',
              right: '-50%',
              width: '200%',
              height: '200%',
              background: 'radial-gradient(ellipse at center, rgba(0, 255, 136, 0.05) 0%, transparent 70%)',
              animation: 'pulse 15s ease-in-out infinite',
            }
          }}
        />
      </Box>
    </Container>
  )
}

export default Login 